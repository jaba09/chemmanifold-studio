/*
 * ChemManifold surrogate chemistry for Ansys Fluent (written against Fluent 2020 R2 / 20.2,
 * double precision, serial or parallel).
 *
 * Hooks
 *   user_chem_step        DEFINE_CHEM_STEP: replaces the stiff ODE integration of each cell's
 *                         chemistry over dt with the ResNet-FiLM or Phy-ChemNODE surrogate.
 *                         Same name as the hook already set in the burner case
 *                         (udf/chem-step-fcn "user_chem_step::libudf").
 *   chemmanifold_monitor  DEFINE_ADJUST: once per iteration, prints and logs (CSV) how many cells
 *                         were advanced and how many were outside the sampled space.
 *   chemmanifold_on_load  DEFINE_EXECUTE_ON_LOADING: reads chemmanifold.ini and the model file.
 *   chemmanifold_reload   DEFINE_ON_DEMAND: re-reads both (after changing the ini file).
 *   chemmanifold_selftest DEFINE_ON_DEMAND: checks the compiled code against the PyTorch model.
 *
 * User-defined memory (allocate at least 7 UDMs; written for every cell the hook advances)
 *   UDM 0  ood_any            1 if any out-of-distribution check fired, else 0
 *   UDM 1  ood_flags          bitmask of the CM_* flags in chemmanifold_core.h
 *   UDM 2  manifold_ratio     distance off the training manifold / its threshold (> 1 = off)
 *   UDM 3  data_ratio         distance to the nearest training state / its threshold (> 1 = far)
 *   UDM 4  mixture_fraction   Bilger Z of the cell
 *   UDM 5  heat_release_rate  W/m3 from the surrogate step
 *   UDM 6  n_substeps         surrogate steps used for the cell's dt
 *
 * See fluent/README.md for building, setup and the options in chemmanifold.ini.
 */
#include "udf.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <direct.h>
#define cm_getcwd _getcwd
#else
#include <unistd.h>
#define cm_getcwd getcwd
#endif

#include "chemmanifold_core.h"

#define CM_N_UDM 7
#define CM_PATH 512

typedef struct {
    double calls, advanced, frozen, skipped, invalid, capped, scaled, substeps, ood_any;
    double ood[6];
    double max_manifold, max_data;
    double dt_min, dt_max;   /* chemistry dt Fluent passed this iteration [s] (0 = no call) */
} cm_counters;

static cm_model *cm_m = NULL;
static cm_options cm_opt;
static int cm_map[CM_MAX_SPECIES];   /* Fluent species index -> model species index */
static int cm_map_n = -1;            /* n_spe the map was built for; -1 = not built */
static int cm_load_failed = 0;
static int cm_udm_warned = 0;
static int cm_write_udm = 1;
static int cm_verbose = 0;
static double cm_op_pressure = 101325.0;
static char cm_model_path[CM_PATH] = "chemmanifold_model.txt";
static char cm_tests_path[CM_PATH] = "chemmanifold_tests.txt";
static char cm_log_path[CM_PATH] = "chemmanifold_monitor.csv";
static cm_counters cm_cnt;
static int cm_capped_warned = 0;

/* ------------------------------------------------------------------------------------------ */

static void cm_trim(char *s)
{
    char *e;
    while (*s == ' ' || *s == '\t') memmove(s, s + 1, strlen(s));
    e = s + strlen(s);
    while (e > s && (e[-1] == ' ' || e[-1] == '\t' || e[-1] == '\r' || e[-1] == '\n')) *--e = '\0';
}

/* chemmanifold.ini in the working directory: "key = value" lines, '#' starts a comment. */
static void cm_read_options(void)
{
    FILE *f = fopen("chemmanifold.ini", "r");
    char line[CM_PATH + 64];
    cm_default_options(&cm_opt);
    cm_opt.T_freeze = 600.0;   /* CH4/air chemistry is frozen below ~600 K on 10-40 us steps */
    if (!f) return;
    while (fgets(line, sizeof line, f)) {
        char *eq, *key = line, *val;
        char *hash = strchr(line, '#');
        if (hash) *hash = '\0';
        eq = strchr(line, '=');
        if (!eq) continue;
        *eq = '\0';
        val = eq + 1;
        cm_trim(key);
        cm_trim(val);
        if (strcmp(key, "model") == 0) snprintf(cm_model_path, CM_PATH, "%s", val);
        else if (strcmp(key, "tests") == 0) snprintf(cm_tests_path, CM_PATH, "%s", val);
        else if (strcmp(key, "log") == 0) snprintf(cm_log_path, CM_PATH, "%s", val);
        else if (strcmp(key, "T_freeze") == 0) cm_opt.T_freeze = atof(val);
        else if (strcmp(key, "max_substeps") == 0) cm_opt.max_substeps = atoi(val);
        else if (strcmp(key, "ood_action") == 0) cm_opt.ood_action = atoi(val);
        else if (strcmp(key, "T_margin") == 0) cm_opt.T_margin = atof(val);
        else if (strcmp(key, "y_margin") == 0) cm_opt.y_margin = atof(val);
        else if (strcmp(key, "p_tol") == 0) cm_opt.p_tol = atof(val);
        else if (strcmp(key, "check_ood") == 0) cm_opt.check_ood = atoi(val);
        else if (strcmp(key, "write_udm") == 0) cm_write_udm = atoi(val);
        else if (strcmp(key, "verbose") == 0) cm_verbose = atoi(val);
        else Message("chemmanifold: unknown option '%s' in chemmanifold.ini\n", key);
    }
    fclose(f);
    if (cm_opt.max_substeps < 1) cm_opt.max_substeps = 1;
}

static void cm_load_all(void)
{
#if !RP_HOST
    char err[512];
    cm_read_options();
    if (cm_m) cm_free(cm_m);
    cm_m = cm_load(cm_model_path, err, sizeof err);
    cm_map_n = -1;
    cm_load_failed = (cm_m == NULL);
    memset(&cm_cnt, 0, sizeof cm_cnt);
    cm_capped_warned = 0;
    if (!cm_m) {
        char cwd[CM_PATH];
        if (!cm_getcwd(cwd, sizeof cwd)) snprintf(cwd, sizeof cwd, "?");
        Message0("\nchemmanifold: ERROR %s - chemistry is FROZEN until a model loads "
                 "(fix chemmanifold.ini, then run chemmanifold_reload)\n", err);
        Message0("chemmanifold: the model and ini files are looked for in Fluent's working folder: %s\n", cwd);
        return;
    }
    Message0("\nchemmanifold: loaded %s (%s, %d species, trained dt %.3g-%.3g s, OOD tables %s)\n",
             cm_model_path, cm_arch(cm_m), cm_n_species(cm_m), cm_dt_min(cm_m), cm_dt_max(cm_m),
             cm_has_ood(cm_m) ? "yes" : "no");
    Message0("chemmanifold: T_freeze %g K, max_substeps %d, ood_action %d\n", cm_opt.T_freeze,
             cm_opt.max_substeps, cm_opt.ood_action);
    if (strcmp(cm_arch(cm_m), "chemnode") == 0)
        Message0("chemmanifold: WARNING Phy-ChemNODE is not stable on the burner flame yet "
                 "(late ignition, can collapse to 280 K). Use ResNet-FiLM for production runs.\n");
#endif
}

/* Fluent name of a mechanism species: lower case, CH2(S) -> ch2<s> */
static void cm_fluent_name(const char *s, char *out, int n)
{
    int i;
    for (i = 0; s[i] && i < n - 1; i++) {
        char c = s[i];
        if (c >= 'A' && c <= 'Z') c = (char)(c - 'A' + 'a');
        else if (c == '(') c = '<';
        else if (c == ')') c = '>';
        out[i] = c;
    }
    out[i] = '\0';
}

static int cm_build_map(int n_spe)
{
    Material *mix = mixture_material(Get_Domain(1));
    int Ns = cm_n_species(cm_m), k, i, found = 0;
    char name[CM_MAX_NAME];
    cm_op_pressure = RP_Get_Real("operating-pressure");   /* the case is loaded by now */
    if (n_spe != Ns) {
        Message0("chemmanifold: ERROR Fluent has %d species, the model %d - chemistry frozen\n", n_spe, Ns);
        return 0;
    }
    for (i = 0; i < n_spe; i++) cm_map[i] = -1;
    for (k = 0; k < Ns && mix; k++) {
        cm_fluent_name(cm_species_name(cm_m, k), name, sizeof name);
        i = mixture_specie_index(mix, name);
        if (i >= 0 && i < n_spe && cm_map[i] < 0) {
            cm_map[i] = k;
            found++;
        }
    }
    if (found != Ns) {
        Message0("chemmanifold: WARNING matched %d of %d species by name; assuming Fluent uses the "
                 "mechanism's species order\n", found, Ns);
        for (i = 0; i < n_spe; i++) cm_map[i] = i;
    } else if (cm_verbose) {
        Message0("chemmanifold: all %d species matched by name\n", Ns);
    }
    cm_map_n = n_spe;
    return 1;
}

/* ------------------------------------------------------------------------------------------ */

DEFINE_EXECUTE_ON_LOADING(chemmanifold_on_load, libname)
{
    cm_load_all();
}

DEFINE_ON_DEMAND(chemmanifold_reload)
{
    cm_load_all();
}

DEFINE_ON_DEMAND(chemmanifold_selftest)
{
#if !RP_HOST
    char report[512];
#if RP_NODE
    if (!I_AM_NODE_ZERO_P) return;
#endif
    if (!cm_m) {
        Message("chemmanifold: no model loaded\n");
        return;
    }
    cm_selftest(cm_m, cm_tests_path, report, sizeof report);
    Message("\nchemmanifold: %s\n", report);
#endif
}

DEFINE_CHEM_STEP(user_chem_step, c, t, p, num_p, n_spe, dt, pres, temp, yk)
{
#if !RP_HOST
    double Y[CM_MAX_SPECIES], P;
    cm_info info;
    int i, b;
    if (!cm_m) {
        if (!cm_load_failed) cm_load_all();   /* library loaded without the on-load hook */
        if (!cm_m) return;                    /* yk unchanged: frozen chemistry */
    }
    if (cm_map_n != n_spe && !cm_build_map(n_spe)) return;

    for (i = 0; i < n_spe; i++) Y[cm_map[i]] = yk[i];
    P = *pres;
    if (P < 0.5 * 101325.0) P += cm_op_pressure;   /* gauge pressure passed: make it absolute */
    cm_advance(cm_m, &cm_opt, Y, *temp, P, *dt, &info);
    for (i = 0; i < n_spe; i++) yk[i] = Y[cm_map[i]];

    cm_cnt.calls += 1;
    if (cm_cnt.dt_min <= 0.0 || *dt < cm_cnt.dt_min) cm_cnt.dt_min = *dt;
    if (*dt > cm_cnt.dt_max) cm_cnt.dt_max = *dt;
    if (info.flags & CM_FROZEN) cm_cnt.frozen += 1;
    else if (info.flags & CM_OOD_SKIPPED) cm_cnt.skipped += 1;
    else if (info.flags & CM_INVALID) cm_cnt.invalid += 1;
    else cm_cnt.advanced += 1;
    if (info.flags & CM_DT_CAPPED) cm_cnt.capped += 1;
    if (info.flags & CM_DT_SCALED) cm_cnt.scaled += 1;
    cm_cnt.substeps += info.n_sub;
    if (info.flags & CM_OOD_ANY) cm_cnt.ood_any += 1;
    for (b = 0; b < 6; b++)
        if (info.flags & (1u << b)) cm_cnt.ood[b] += 1;
    if (info.manifold_ratio > cm_cnt.max_manifold) cm_cnt.max_manifold = info.manifold_ratio;
    if (info.data_ratio > cm_cnt.max_data) cm_cnt.max_data = info.data_ratio;
    if (cm_verbose > 1)
        Message("chemmanifold: T %.1f K dt %.3e s -> T %.1f K, %d steps, flags 0x%x\n", *temp, *dt,
                info.T_out, info.n_sub, info.flags);

    if (cm_write_udm && p == NULL && t != NULL) {
        if (N_UDM >= CM_N_UDM) {
            C_UDMI(c, t, 0) = (info.flags & CM_OOD_ANY) ? 1.0 : 0.0;
            C_UDMI(c, t, 1) = (double)info.flags;
            C_UDMI(c, t, 2) = info.manifold_ratio;
            C_UDMI(c, t, 3) = info.data_ratio;
            C_UDMI(c, t, 4) = info.Z;
            C_UDMI(c, t, 5) = C_R(c, t) * info.hrr;
            C_UDMI(c, t, 6) = (double)info.n_sub;
        } else if (!cm_udm_warned) {
            cm_udm_warned = 1;
            Message0("chemmanifold: WARNING only %d user-defined memories allocated, %d needed for the "
                     "OOD fields (Define > User-Defined > Memory)\n", N_UDM, CM_N_UDM);
        }
    }
#endif
}

DEFINE_ADJUST(chemmanifold_monitor, d)
{
#if !RP_HOST
    cm_counters g = cm_cnt;
    double n;
    int b;
    FILE *f;
    memset(&cm_cnt, 0, sizeof cm_cnt);
#if RP_NODE
    g.calls = PRF_GRSUM1(g.calls);
    g.advanced = PRF_GRSUM1(g.advanced);
    g.frozen = PRF_GRSUM1(g.frozen);
    g.skipped = PRF_GRSUM1(g.skipped);
    g.invalid = PRF_GRSUM1(g.invalid);
    g.capped = PRF_GRSUM1(g.capped);
    g.scaled = PRF_GRSUM1(g.scaled);
    g.substeps = PRF_GRSUM1(g.substeps);
    g.ood_any = PRF_GRSUM1(g.ood_any);
    for (b = 0; b < 6; b++) g.ood[b] = PRF_GRSUM1(g.ood[b]);
    g.max_manifold = PRF_GRHIGH1(g.max_manifold);
    g.max_data = PRF_GRHIGH1(g.max_data);
    if (g.dt_min <= 0.0) g.dt_min = 1e30;   /* no call on this node */
    g.dt_min = PRF_GRLOW1(g.dt_min);
    g.dt_max = PRF_GRHIGH1(g.dt_max);
    if (!I_AM_NODE_ZERO_P) return;
#endif
    if (g.calls <= 0) return;   /* first iteration, or the hook is not active */
    n = g.calls;
    Message("chemmanifold: %.0f cells, %.0f advanced (%.2f steps avg), %.0f frozen, %.0f outside sampled space "
            "(%.2f%%: T %.0f, T|Z %.0f, p %.0f, species %.0f, manifold %.0f, data %.0f), dt capped %.0f, "
            "invalid %.0f\n", n, g.advanced, g.advanced > 0 ? g.substeps / g.advanced : 0.0, g.frozen,
            g.ood_any, 100.0 * g.ood_any / n, g.ood[0], g.ood[1], g.ood[2], g.ood[3], g.ood[4], g.ood[5],
            g.capped, g.invalid);
    Message("chemmanifold: chemistry dt passed by Fluent %.3g - %.3g s\n", g.dt_min, g.dt_max);
    if (!cm_capped_warned && g.advanced > 0 && g.capped > 0.05 * g.advanced) {
        cm_capped_warned = 1;
        Message("chemmanifold: WARNING %.0f%% of the advanced cells got a chemistry dt above %.3g s and "
                "were advanced LESS than dt. The surrogate is meant for a transient run with a time step "
                "of about 4e-5 s (at most 1e-4 s); see fluent/README.md.\n",
                100.0 * g.capped / g.advanced, cm_opt.max_substeps * (cm_m ? cm_dt_max(cm_m) : 4e-5));
    }
    f = fopen(cm_log_path, "r");
    b = (f == NULL);
    if (f) fclose(f);
    f = fopen(cm_log_path, "a");
    if (!f) return;
    if (b)
        fprintf(f, "iteration,flow_time,cells,advanced,frozen,ood_skipped,invalid,dt_capped,dt_scaled,"
                   "mean_substeps,ood_any,ood_T,ood_T_at_Z,ood_pressure,ood_species,ood_manifold,ood_data,"
                   "ood_fraction,max_manifold_ratio,max_data_ratio,dt_chem_min,dt_chem_max\n");
    fprintf(f, "%d,%.9g,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,%.4f,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,%.6f,%.4g,%.4g,%.4g,%.4g\n",
            N_ITER, CURRENT_TIME, n, g.advanced, g.frozen, g.skipped, g.invalid, g.capped, g.scaled,
            g.advanced > 0 ? g.substeps / g.advanced : 0.0, g.ood_any, g.ood[0], g.ood[1], g.ood[2],
            g.ood[3], g.ood[4], g.ood[5], g.ood_any / n, g.max_manifold, g.max_data, g.dt_min, g.dt_max);
    fclose(f);
#endif
}

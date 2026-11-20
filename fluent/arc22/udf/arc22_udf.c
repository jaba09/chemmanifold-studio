/*
 * ARC_GRI30_NOx22 direct chemistry for Ansys Fluent (2026 R1, also Student; double precision; serial or
 * parallel). Fluent transports the 22 ARC species; this UDF replaces Fluent's stiff ODE solver with the
 * ARC rates (21 QSS radicals by linearized QSSA), an L-stable Rosenbrock integrator (ROS34PW2, or ROS4)
 * and an element projection after each step, the same chemistry step as the OpenFOAM ARC run (arcChemStep).
 *
 * Hooks
 *   arc22_chem_step   DEFINE_CHEM_STEP: advances one cell's 22 mass fractions over Fluent's chemistry dt
 *                     at constant pressure and enthalpy.
 *   arc22_monitor     DEFINE_ADJUST: per iteration prints how many cells were advanced, steps per cell,
 *                     failures, and the time spent in chemistry; also logs it to arc22_monitor.csv.
 *   arc22_on_load     DEFINE_EXECUTE_ON_LOADING: reads arc22.ini (optional) and prints the settings.
 *   arc22_reload      DEFINE_ON_DEMAND: re-reads arc22.ini.
 *   arc22_selftest    DEFINE_ON_DEMAND: checks the compiled rates and the integrator against values
 *                     computed outside Fluent (prints "arc22 selftest PASSED").
 *
 * User-defined memory (optional; 3 locations, written for every advanced cell)
 *   UDM 0  heat release rate [W/m3]      UDM 1  Rosenbrock steps      UDM 2  element correction (relative)
 *
 * Source files: arc22_udf.c arc22_core.c arc22_kernel.c; headers: arc22_core.h arc22_kernel.h.
 * See fluent/arc22/README.md.
 */
#include "udf.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "arc22_core.h"

#define A22_N_UDM 3

typedef struct {
    double calls, advanced, frozen, quiet, failed, steps, rejects, jacs, cpu, elem_fix, dt_min, dt_max;
} a22_counters;

static arc22_options a22_opt;
static int a22_opt_read = 0;
static int a22_map[ARC22_NSP];   /* Fluent species index -> ARC index */
static int a22_map_n = -1;       /* n_spe the map was built for; 0 = mismatch (chemistry frozen) */
static int a22_write_udm = 1;
static int a22_udm_warned = 0;
static int a22_verbose = 0;
static double a22_op_pressure = 101325.0;
static a22_counters a22_cnt;
static char a22_log_path[256] = "arc22_monitor.csv";

static void a22_trim(char *s)
{
    char *e;
    while (*s == ' ' || *s == '\t') memmove(s, s + 1, strlen(s));
    e = s + strlen(s);
    while (e > s && (e[-1] == ' ' || e[-1] == '\t' || e[-1] == '\r' || e[-1] == '\n')) *--e = '\0';
}

/* arc22.ini in Fluent's working folder: "key = value" lines, '#' starts a comment */
static void a22_read_options(void)
{
    FILE *f;
    char line[512];
    arc22_default_options(&a22_opt);
    a22_opt_read = 1;
    f = fopen("arc22.ini", "r");
    if (f) {
        while (fgets(line, sizeof line, f)) {
            char *eq, *key = line, *val, *hash = strchr(line, '#');
            if (hash) *hash = '\0';
            eq = strchr(line, '=');
            if (!eq) continue;
            *eq = '\0';
            val = eq + 1;
            a22_trim(key);
            a22_trim(val);
            if (strcmp(key, "rtol") == 0) a22_opt.rtol = atof(val);
            else if (strcmp(key, "atol") == 0) a22_opt.atol = atof(val);
            else if (strcmp(key, "atol_T") == 0) a22_opt.atol_T = atof(val);
            else if (strcmp(key, "T_freeze") == 0) a22_opt.T_freeze = atof(val);
            else if (strcmp(key, "T_quiet") == 0) a22_opt.T_quiet = atof(val);
            else if (strcmp(key, "max_steps") == 0) a22_opt.max_steps = atoi(val);
            else if (strcmp(key, "project") == 0) a22_opt.project = atoi(val);
            else if (strcmp(key, "method") == 0) a22_opt.method = atoi(val);
            else if (strcmp(key, "jac_reuse") == 0) a22_opt.jac_reuse = atoi(val);
            else if (strcmp(key, "write_udm") == 0) a22_write_udm = atoi(val);
            else if (strcmp(key, "verbose") == 0) a22_verbose = atoi(val);
            else if (strcmp(key, "log") == 0) snprintf(a22_log_path, sizeof a22_log_path, "%s", val);
            else Message("arc22: unknown option '%s' in arc22.ini (ignored)\n", key);
        }
        fclose(f);
    }
    if (a22_opt.max_steps < 1) a22_opt.max_steps = 1;
    if (a22_opt.jac_reuse < 1) a22_opt.jac_reuse = 1;
    a22_map_n = -1;
    memset(&a22_cnt, 0, sizeof a22_cnt);
    Message0("\narc22: ARC_GRI30_NOx22 chemistry (22 transported + 21 QSS species), %s, "
             "rtol %g, atol %g (T %g K), T_freeze %g K, T_quiet %g K, element projection %s%s\n",
             a22_opt.method == 0 ? "Rosenbrock ROS4" : "Rosenbrock-W ROS34PW2 (Jacobian reused)",
             a22_opt.rtol, a22_opt.atol, a22_opt.atol_T, a22_opt.T_freeze, a22_opt.T_quiet,
             a22_opt.project ? "on" : "OFF", f ? " (from arc22.ini)" : " (defaults, no arc22.ini)");
}

/* Fluent's species name: lower case (CHEMKIN import) */
static void a22_lower(const char *s, char *out, int n)
{
    int i;
    for (i = 0; s[i] && i < n - 1; i++) out[i] = (s[i] >= 'A' && s[i] <= 'Z') ? (char)(s[i] - 'A' + 'a') : s[i];
    out[i] = '\0';
}

static int a22_build_map(int n_spe)
{
#if !RP_HOST
    Material *mix = mixture_material(Get_Domain(1));
    int k, i, found = 0;
    char name[32];
    a22_op_pressure = RP_Get_Real("operating-pressure");
    a22_map_n = 0;
    if (n_spe != ARC22_NSP) {
        Message0("arc22: ERROR the mixture has %d species, ARC_GRI30_NOx22 needs exactly 22 "
                 "(import fluent/arc22/mechanism/arc22_chem.inp) - chemistry FROZEN\n", n_spe);
        return 0;
    }
    for (i = 0; i < n_spe; i++) a22_map[i] = -1;
    for (k = 0; k < ARC22_NSP && mix; k++) {
        a22_lower(arc22_name(k), name, sizeof name);
        i = mixture_specie_index(mix, name);
        if (i >= 0 && i < n_spe && a22_map[i] < 0) {
            a22_map[i] = k;
            found++;
        } else {
            Message0("arc22: ERROR species '%s' is not in the Fluent mixture\n", name);
        }
    }
    if (found != ARC22_NSP) {
        Message0("arc22: ERROR matched %d of 22 species by name - chemistry FROZEN\n", found);
        return 0;
    }
    a22_map_n = n_spe;
    Message0("arc22: all 22 species matched by name, operating pressure %g Pa\n", a22_op_pressure);
#endif
    return 1;
}

DEFINE_EXECUTE_ON_LOADING(arc22_on_load, libname)
{
    a22_read_options();
}

DEFINE_ON_DEMAND(arc22_reload)
{
    a22_read_options();
}

DEFINE_ON_DEMAND(arc22_selftest)
{
#if !RP_HOST
    /* burnt phi 0.9 gas (GRI-Mech 3.0, 2.4 ms after 1500 K) and its rhs from the Python build */
    static const double st_y[23] = {0.00092513415596634908, 0.00024851556894886929, 0.0040034508314089152, 0.037184401220255875, 0.012458204642778959, 0.095035432855479759, 8.3320056798082312e-06, 3.4154063547456911e-07, 3.009413096200395e-16, 2.5721755856952585e-15, 0.032240270187307941, 0.0862988160448417, 1.7261042076526847e-10, 6.3200761983149078e-17, 4.5251736711737673e-19, 2.1000880934319117e-24, 1.034274500426225e-30, 0.72633948757032285, 0.0052545065640780984, 2.2584739232295692e-06, 8.478727285160179e-07, 2.930304495982937e-10, 2711.6712273815956};
    static const double st_f[23] = {0.0048559482131514346, -0.0032127509832060863, -0.15300736073552751, -1.5612190208930423, -0.25665470829752507, 0.1213147300561337, -0.00028895474680542578, 2.9294638591192835e-05, 9.566724397023019e-15, -8.0660576714905532e-11, 0.052258365730312291, -0.082108033032723668, 1.1012368869088999e-09, -4.0948983879664051e-13, -1.685258374379079e-14, 1.3052443857200579e-19, 2.6495533984052699e-24, -1.6437579849518364, 3.520283293624344, 0.0014788326295498079, 3.4036851386048824e-05, 1.9509988699384152e-07, -3806.7351906712224};
    double f[23], err = 0.0, Y[ARC22_NSP], T = 1400.0, Tprev = 1400.0, dTmax = 0.0, tau = 0.0;
    double xo2 = 2.0, xn2 = 2.0 * 0.79 / 0.21, xch4 = 1.0, Wm;   /* mol per mol CH4 */
    arc22_options o;
    arc22_info info;
    int k, i, ok_rhs, ok_ign, failed = 0;
    clock_t c0;
#if RP_NODE
    if (!I_AM_NODE_ZERO_P) return;
#endif
    arc22_rhs(101325.0, st_y, f);
    for (k = 0; k < 23; k++) {
        double e = fabs(f[k] - st_f[k]) / (fabs(st_f[k]) + 1e-12 * (k < 22 ? 1.0 : 1e3) + 1e-6 * fabs(st_f[3]));
        if (e > err) err = e;
    }
    ok_rhs = err < 1e-6;
    Message("\narc22 selftest 1 (rates + thermo at 2712 K): max relative difference %.2e -> %s\n", err,
            ok_rhs ? "ok" : "FAILED");

    /* stoichiometric CH4/air (O2:N2 = 0.21:0.79 by mole) at 1400 K, 1 atm, 600 calls of 10 us:
       ignition (max dT/dt) at 3.45 ms (GRI-Mech 3.0 3.43 ms), end T 2702.8 K */
    arc22_default_options(&o);
    Wm = xch4 * arc22_W(8) + xo2 * arc22_W(3) + xn2 * arc22_W(17);
    for (k = 0; k < ARC22_NSP; k++) Y[k] = 0.0;
    Y[8] = xch4 * arc22_W(8) / Wm;
    Y[3] = xo2 * arc22_W(3) / Wm;
    Y[17] = xn2 * arc22_W(17) / Wm;
    c0 = clock();
    for (i = 1; i <= 600; i++) {
        if (arc22_advance(&o, Y, T, 101325.0, 1e-5, &info) < 0) failed++;
        T = info.T_out;
        if (T - Tprev > dTmax) { dTmax = T - Tprev; tau = i * 1e-5; }
        Tprev = T;
    }
    ok_ign = !failed && fabs(tau - 3.45e-3) < 0.05e-3 && fabs(T - 2702.8) < 2.0;
    Message("arc22 selftest 2 (stoichiometric ignition at 1400 K): tau %.3f ms (expected 3.45), end T %.1f K "
            "(expected 2702.8), %d failed calls, %.0f us per call -> %s\n", tau * 1e3, T, failed,
            1e6 * (double)(clock() - c0) / CLOCKS_PER_SEC / 600.0, ok_ign ? "ok" : "FAILED");
    Message("arc22 selftest %s\n", (ok_rhs && ok_ign) ? "PASSED" : "FAILED - do not run the case with this build");
#endif
}

DEFINE_CHEM_STEP(arc22_chem_step, c, t, p, num_p, n_spe, dt, pres, temp, yk)
{
#if !RP_HOST
    double Y[ARC22_NSP], P;
    arc22_info info;
    clock_t c0;
    int i;
    if (!a22_opt_read) a22_read_options();   /* library loaded without the on-load hook */
    if (a22_map_n != n_spe) {
        if (a22_map_n == 0) return;           /* mismatch already reported: frozen */
        if (!a22_build_map(n_spe)) return;
    }
    for (i = 0; i < n_spe; i++) Y[a22_map[i]] = yk[i];
    P = *pres;
    if (P < 0.5 * 101325.0) P += a22_op_pressure;   /* gauge pressure passed: make it absolute */
    c0 = clock();
    arc22_advance(&a22_opt, Y, *temp, P, *dt, &info);
    a22_cnt.cpu += (double)(clock() - c0) / CLOCKS_PER_SEC;
    if (info.status == 0 || info.status == 2)
        for (i = 0; i < n_spe; i++) yk[i] = Y[a22_map[i]];

    a22_cnt.calls += 1;
    if (a22_cnt.dt_min <= 0.0 || *dt < a22_cnt.dt_min) a22_cnt.dt_min = *dt;
    if (*dt > a22_cnt.dt_max) a22_cnt.dt_max = *dt;
    if (info.status == 0) a22_cnt.advanced += 1;
    else if (info.status == 2) a22_cnt.quiet += 1;
    else if (info.status == 1) a22_cnt.frozen += 1;
    else a22_cnt.failed += 1;
    a22_cnt.steps += info.n_steps;
    a22_cnt.rejects += info.n_reject;
    a22_cnt.jacs += info.n_jac;
    if (info.elem_fix > a22_cnt.elem_fix) a22_cnt.elem_fix = info.elem_fix;
    if (a22_verbose > 1 || (a22_verbose && info.status < 0))
        Message("arc22: T %.1f K p %.0f Pa dt %.3e s -> T %.1f K, status %d, %d steps, %d rejected\n", *temp, P,
                *dt, info.T_out, info.status, info.n_steps, info.n_reject);

    if (a22_write_udm && p == NULL && t != NULL) {
        if (N_UDM >= A22_N_UDM) {
            C_UDMI(c, t, 0) = C_R(c, t) * info.hrr;
            C_UDMI(c, t, 1) = (double)info.n_steps;
            C_UDMI(c, t, 2) = info.elem_fix;
        } else if (!a22_udm_warned) {
            a22_udm_warned = 1;
            Message0("arc22: note: %d user-defined memories allocated; 3 give the heat release, steps and "
                     "element-correction fields (User-Defined > Memory)\n", N_UDM);
        }
    }
#endif
}

DEFINE_ADJUST(arc22_monitor, d)
{
#if !RP_HOST
    a22_counters g = a22_cnt;
    FILE *f;
    int fresh;
    memset(&a22_cnt, 0, sizeof a22_cnt);
#if RP_NODE
    g.calls = PRF_GRSUM1(g.calls);
    g.advanced = PRF_GRSUM1(g.advanced);
    g.frozen = PRF_GRSUM1(g.frozen);
    g.quiet = PRF_GRSUM1(g.quiet);
    g.failed = PRF_GRSUM1(g.failed);
    g.steps = PRF_GRSUM1(g.steps);
    g.rejects = PRF_GRSUM1(g.rejects);
    g.jacs = PRF_GRSUM1(g.jacs);
    g.cpu = PRF_GRHIGH1(g.cpu);            /* the slowest process sets the wall time */
    g.elem_fix = PRF_GRHIGH1(g.elem_fix);
    if (g.dt_min <= 0.0) g.dt_min = 1e30;
    g.dt_min = PRF_GRLOW1(g.dt_min);
    g.dt_max = PRF_GRHIGH1(g.dt_max);
    if (!I_AM_NODE_ZERO_P) return;
#endif
    if (g.calls <= 0) return;   /* no chemistry call since the last iteration */
    Message("arc22: %.0f cells: %.0f integrated (%.1f steps avg, %.0f rejected), %.0f quiet, %.0f frozen, "
            "%.0f FAILED; chemistry %.2f s (slowest process); dt %.3g - %.3g s; max element fix %.1e\n",
            g.calls, g.advanced, g.advanced > 0 ? g.steps / g.advanced : 0.0, g.rejects, g.quiet, g.frozen,
            g.failed, g.cpu, g.dt_min, g.dt_max, g.elem_fix);
    f = fopen(a22_log_path, "r");
    fresh = (f == NULL);
    if (f) fclose(f);
    f = fopen(a22_log_path, "a");
    if (!f) return;
    if (fresh)
        fprintf(f, "iteration,flow_time,cells,integrated,quiet,frozen,failed,mean_steps,rejected,jacobians,"
                   "chem_cpu_s,dt_min,dt_max,max_elem_fix\n");
    fprintf(f, "%d,%.9g,%.0f,%.0f,%.0f,%.0f,%.0f,%.3f,%.0f,%.0f,%.4f,%.4g,%.4g,%.3g\n", N_ITER, CURRENT_TIME,
            g.calls, g.advanced, g.quiet, g.frozen, g.failed, g.advanced > 0 ? g.steps / g.advanced : 0.0,
            g.rejects, g.jacs, g.cpu, g.dt_min, g.dt_max, g.elem_fix);
    fclose(f);
#endif
}

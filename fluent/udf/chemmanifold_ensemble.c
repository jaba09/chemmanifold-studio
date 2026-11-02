/* A set of ChemManifold surrogates used as one model. See chemmanifold_ensemble.h. */
#include "chemmanifold_ensemble.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct cm_ensemble {
    int blend, n, Ns, n_z;
    cm_model *m[CME_MAX_MEMBERS];
    double T_lo[CME_MAX_MEMBERS], T_hi[CME_MAX_MEMBERS], T_w[CME_MAX_MEMBERS];
    double c_lo[CME_MAX_MEMBERS], c_hi[CME_MAX_MEMBERS], c_w[CME_MAX_MEMBERS];
    double zlin[CM_MAX_SPECIES], zlin_b, prog[CM_MAX_SPECIES];
    double z_tab[CME_MAX_ZTAB], yc_tab[CME_MAX_ZTAB];
};

/* next whitespace token, skipping '#' comments to the end of the line */
static int token(FILE *f, char *buf, int len)
{
    int c, i = 0;
    for (;;) {
        c = fgetc(f);
        if (c == EOF) return 0;
        if (c == '#') {
            while (c != '\n' && c != EOF) c = fgetc(f);
            continue;
        }
        if (c > ' ') break;
    }
    while (c != EOF && c > ' ' && i < len - 1) {
        buf[i++] = (char)c;
        c = fgetc(f);
    }
    buf[i] = 0;
    return 1;
}

static int number(FILE *f, double *x)
{
    char t[128];
    char *end;
    if (!token(f, t, sizeof t)) return 0;
    *x = strtod(t, &end);
    return *end == 0;
}

#define FAIL(...) do { snprintf(err, errlen, __VA_ARGS__); if (f) fclose(f); cme_free(e); return NULL; } while (0)

cm_ensemble *cme_load(const char *path, char *err, int errlen)
{
    FILE *f = fopen(path, "r");
    cm_ensemble *e = calloc(1, sizeof *e);
    char t[1024], dir[1024], full[2048], names[CM_MAX_SPECIES][CM_MAX_NAME];
    const char *slash;
    double x;
    int k, i, version;

    if (!e) { if (f) fclose(f); snprintf(err, errlen, "out of memory"); return NULL; }
    if (!f) FAIL("cannot open ensemble file '%s'", path);
    slash = strrchr(path, '/');
    if (!slash) slash = strrchr(path, '\\');
    if (slash) {
        int L = (int)(slash - path) + 1;
        if (L >= (int)sizeof dir) L = (int)sizeof dir - 1;
        memcpy(dir, path, L);
        dir[L] = 0;
    } else {
        dir[0] = 0;
    }
    if (!token(f, t, sizeof t) || strcmp(t, "chemmanifold_ensemble") != 0) FAIL("%s: not an ensemble file", path);
    if (!number(f, &x)) FAIL("%s: no version", path);
    version = (int)x;
    if (version != 1) FAIL("%s: unsupported ensemble version %d", path, version);
    while (token(f, t, sizeof t)) {
        if (!strcmp(t, "blend")) {
            if (!token(f, t, sizeof t)) FAIL("blend: missing value");
            if (!strcmp(t, "mean")) e->blend = CME_BLEND_MEAN;
            else if (!strcmp(t, "gate")) e->blend = CME_BLEND_GATE;
            else FAIL("blend: unknown value '%s'", t);
        } else if (!strcmp(t, "n_species")) {
            if (!number(f, &x) || x < 1 || x > CM_MAX_SPECIES) FAIL("bad n_species");
            e->Ns = (int)x;
        } else if (!strcmp(t, "species")) {
            for (k = 0; k < e->Ns; k++) {
                if (!token(f, names[k], CM_MAX_NAME)) FAIL("species: list too short");
            }
        } else if (!strcmp(t, "zlin")) {
            for (k = 0; k < e->Ns; k++) if (!number(f, &e->zlin[k])) FAIL("zlin: too short");
            if (!number(f, &e->zlin_b)) FAIL("zlin: no offset");
        } else if (!strcmp(t, "prog")) {
            for (k = 0; k < e->Ns; k++) if (!number(f, &e->prog[k])) FAIL("prog: too short");
        } else if (!strcmp(t, "ceq")) {
            if (!number(f, &x) || x < 2 || x > CME_MAX_ZTAB) FAIL("ceq: bad table size");
            e->n_z = (int)x;
            for (i = 0; i < e->n_z; i++)
                if (!number(f, &e->z_tab[i]) || !number(f, &e->yc_tab[i])) FAIL("ceq: table too short");
        } else if (!strcmp(t, "members")) {
            if (!number(f, &x) || x < 1 || x > CME_MAX_MEMBERS) FAIL("bad member count");
        } else if (!strcmp(t, "member")) {
            if (e->n >= CME_MAX_MEMBERS) FAIL("too many members");
            if (!token(f, t, sizeof t)) FAIL("member: missing path");
            if (t[0] == '/' || dir[0] == 0) snprintf(full, sizeof full, "%s", t);
            else snprintf(full, sizeof full, "%s%s", dir, t);
            i = e->n;
            if (!number(f, &e->T_lo[i]) || !number(f, &e->T_hi[i]) || !number(f, &e->T_w[i]) ||
                !number(f, &e->c_lo[i]) || !number(f, &e->c_hi[i]) || !number(f, &e->c_w[i]))
                FAIL("member %d: needs T_lo T_hi T_width c_lo c_hi c_width", i);
            e->m[i] = cm_load(full, err, errlen);
            if (!e->m[i]) { fclose(f); cme_free(e); return NULL; }   /* err already filled by cm_load */
            e->n++;
        } else {
            FAIL("%s: unknown keyword '%s'", path, t);
        }
    }
    fclose(f);
    f = NULL;
    if (e->n < 1) FAIL("%s: no members", path);
    if (e->Ns == 0) e->Ns = cm_n_species(e->m[0]);
    for (i = 0; i < e->n; i++) {
        if (cm_n_species(e->m[i]) != e->Ns) FAIL("member %d: %d species, expected %d", i, cm_n_species(e->m[i]), e->Ns);
        for (k = 0; k < e->Ns; k++) {
            const char *s = cm_species_name(e->m[i], k);
            if (strcmp(s, cm_species_name(e->m[0], k)) != 0) FAIL("member %d: species %d is %s, not %s", i, k, s,
                                                                    cm_species_name(e->m[0], k));
            if (names[0][0] && strcmp(s, names[k]) != 0) FAIL("member %d: species %d is %s, file says %s", i, k, s, names[k]);
        }
    }
    if (e->blend == CME_BLEND_GATE && e->n_z < 2) {
        int need_c = 0;
        for (i = 0; i < e->n; i++) need_c |= e->c_lo[i] > -1e8 || e->c_hi[i] < 1e8;
        if (need_c) FAIL("%s: gate on c needs the ceq table", path);
    }
    return e;
}

void cme_free(cm_ensemble *e)
{
    int i;
    if (!e) return;
    for (i = 0; i < e->n; i++) cm_free(e->m[i]);
    free(e);
}

int cme_n_members(const cm_ensemble *e) { return e->n; }
int cme_n_species(const cm_ensemble *e) { return e->Ns; }
const char *cme_species_name(const cm_ensemble *e, int k) { return cm_species_name(e->m[0], k); }
int cme_blend(const cm_ensemble *e) { return e->blend; }

/* soft box: 1 inside, 0 outside, linear over a width w centred on each edge (w <= 0: sharp, [lo, hi)) */
static double box(double x, double lo, double hi, double w)
{
    double a, b;
    if (!(w > 0.0)) return (x >= lo && x < hi) ? 1.0 : 0.0;
    a = (x - lo) / w + 0.5;
    b = (hi - x) / w + 0.5;
    a = a < 0.0 ? 0.0 : (a > 1.0 ? 1.0 : a);
    b = b < 0.0 ? 0.0 : (b > 1.0 ? 1.0 : b);
    return a * b;
}

int cme_weights(const cm_ensemble *e, const double *Y, double T, double *w, double *Zo, double *co)
{
    double Z = e->zlin_b, yc = 0.0, yeq = 1.0, c = 0.0, s = 0.0;
    int k, i, used = 0;
    for (k = 0; k < e->Ns; k++) {
        Z += e->zlin[k] * Y[k];
        yc += e->prog[k] * Y[k];
    }
    if (e->n_z >= 2) {
        if (Z <= e->z_tab[0]) yeq = e->yc_tab[0];
        else if (Z >= e->z_tab[e->n_z - 1]) yeq = e->yc_tab[e->n_z - 1];
        else {
            i = 0;
            while (i < e->n_z - 2 && Z > e->z_tab[i + 1]) i++;
            yeq = e->yc_tab[i] + (e->yc_tab[i + 1] - e->yc_tab[i]) * (Z - e->z_tab[i]) / (e->z_tab[i + 1] - e->z_tab[i]);
        }
        c = yc / (yeq > 1e-12 ? yeq : 1e-12);
    }
    if (Zo) *Zo = Z;
    if (co) *co = c;
    for (i = 0; i < e->n; i++) {
        w[i] = e->blend == CME_BLEND_MEAN ? 1.0
             : box(T, e->T_lo[i], e->T_hi[i], e->T_w[i]) * box(c, e->c_lo[i], e->c_hi[i], e->c_w[i]);
        s += w[i];
    }
    if (!(s > 0.0)) {
        for (i = 0; i < e->n; i++) w[i] = 1.0 / e->n;
        return 0;
    }
    for (i = 0; i < e->n; i++) {
        w[i] /= s;
        used += w[i] > 0.0;
    }
    return used;
}

void cme_ood(const cm_ensemble *e, const cm_options *o, const double *Y, double T, double P, cm_info *info)
{
    double w[CME_MAX_MEMBERS];
    cm_info mi;
    unsigned fl = 0;
    int i, first = 1;
    int used = cme_weights(e, Y, T, w, NULL, NULL);
    memset(info, 0, sizeof *info);
    for (i = 0; i < e->n; i++) {
        if (!(w[i] > 0.0)) continue;
        memset(&mi, 0, sizeof mi);                   /* cm_ood only sets bits */
        cm_ood(e->m[i], o, Y, T, P, &mi);
        fl |= mi.flags;
        if (first || mi.manifold_ratio > info->manifold_ratio) info->manifold_ratio = mi.manifold_ratio;
        if (first || mi.data_ratio > info->data_ratio) info->data_ratio = mi.data_ratio;
        info->Z = mi.Z;
        first = 0;
    }
    if (used == 0) fl |= CME_NO_MEMBER;
    info->flags = fl;
    info->T_out = T;
}

int cme_advance(const cm_ensemble *e, const cm_options *o, double *Y, double T, double P, double dt,
                cm_info *info, double *spread_T)
{
    const int Ns = e->Ns;
    double w[CME_MAX_MEMBERS], Ti[CME_MAX_MEMBERS], Yi[CM_MAX_SPECIES], Yb[CM_MAX_SPECIES];
    double ws = 0.0, Tg = 0.0, hrr = 0.0, h, mean = 0.0, var = 0.0;
    cm_options om = *o;
    cm_info mi;
    unsigned fl = 0;
    int i, k, n_ok = 0, used;

    if (spread_T) *spread_T = 0.0;
    if (o->check_ood) {
        cme_ood(e, o, Y, T, P, info);
    } else {
        memset(info, 0, sizeof *info);
        info->T_out = T;
    }
    fl = info->flags;
    if (!(dt > 0.0) || !isfinite(T)) return 0;
    if (T < o->T_freeze) {
        info->flags = (fl & ~(unsigned)CM_OOD_ANY) | CM_FROZEN;
        info->manifold_ratio = info->data_ratio = 0.0;
        return 0;
    }
    if (o->ood_action == 1 && (fl & CM_OOD_ANY)) {
        info->flags |= CM_OOD_SKIPPED;
        return 0;
    }
    used = cme_weights(e, Y, T, w, NULL, NULL);
    if (used == 0) fl |= CME_NO_MEMBER;
    om.check_ood = 0;        /* done above, on the members the gate uses */
    om.ood_action = 0;
    h = cm_enthalpy(e->m[0], Y, T);
    for (k = 0; k < Ns; k++) Yb[k] = 0.0;
    for (i = 0; i < e->n; i++) {
        if (!(w[i] > 0.0)) continue;
        for (k = 0; k < Ns; k++) Yi[k] = Y[k];
        if (cm_advance(e->m[i], &om, Yi, T, P, dt, &mi) != 0 || !isfinite(mi.T_out))
            continue;                                /* a failed member is left out of the blend */
        fl |= mi.flags & ~(unsigned)CM_INVALID;
        for (k = 0; k < Ns; k++) Yb[k] += w[i] * Yi[k];
        ws += w[i];
        Tg += w[i] * mi.T_out;
        hrr += w[i] * mi.hrr;
        Ti[n_ok++] = mi.T_out;
        if (n_ok == 1) {
            info->n_sub = mi.n_sub;
            info->dt_sub = mi.dt_sub;
        }
    }
    if (n_ok == 0) {
        info->flags = fl | CM_INVALID;
        info->T_out = T;
        return -1;
    }
    for (k = 0; k < Ns; k++) Y[k] = Yb[k] / ws;
    info->T_out = cm_temperature(e->m[0], Y, h, Tg / ws);
    info->hrr = hrr / ws;
    info->flags = fl;
    if (spread_T && n_ok > 1) {
        for (i = 0; i < n_ok; i++) mean += Ti[i];
        mean /= n_ok;
        for (i = 0; i < n_ok; i++) var += (Ti[i] - mean) * (Ti[i] - mean);
        *spread_T = sqrt(var / n_ok);
    }
    return 0;
}

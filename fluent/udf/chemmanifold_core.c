/*
 * ChemManifold surrogate inference in plain C; see chemmanifold_core.h.
 *
 * Model file format (text, written by scripts/12_export_fluent.py): a header line
 * "CHEMMANIFOLD_SURROGATE <version>", then records of the form
 *     A <name> <count> <values...>      numeric array (flattened, row-major)
 *     S <name> <count> <tokens...>      string list
 * Network weights keep their PyTorch state_dict names (net.inp.weight, ...).
 * C89-compatible apart from // -free declarations after statements, so it builds with the
 * compilers Fluent uses (MSVC or the bundled Clang on Windows, gcc on Linux).
 */
#include "chemmanifold_core.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CM_RU 8314.462618
#define CM_EPS_BOXCOX 1e-15
#define CM_W_EPS 1e-15
#define CM_RIDGE 1e-18
#define CM_N_ACTIVE 3
#define CM_N_NEWTON 4
#define CM_T_LO 280.0
#define CM_T_HI 3800.0
#define CM_LN_EPS 1e-5     /* torch.nn.LayerNorm default */
#define CM_MAX_FEAT (CM_MAX_SPECIES + 1)

enum { ARCH_RESNET = 1, ARCH_NODE = 2 };

typedef struct {
    char name[96];
    int n;
    double *v;
} cm_array;

typedef struct { const double *W, *b; int n_out, n_in; } cm_linear;

struct cm_model {
    int arch;
    char arch_name[CM_MAX_NAME];
    int Ns, Ne;
    char species[CM_MAX_SPECIES][CM_MAX_NAME];
    double lam, dt_base, dt_min, dt_max, P_ref;
    const double *mu_y, *sigma_y, *ctx_mu, *ctx_sigma;
    const double *A, *W, *T_mid, *a_lo, *a_hi;   /* A: Ne x Ns, a_*: Ns x 7 */
    double R[CM_MAX_SPECIES], h_form[CM_MAX_SPECIES];
    int P_frozen;                                  /* trained at a single pressure */

    /* ResNet-FiLM */
    int hidden, n_blocks;
    cm_linear inp, out, film[8], lin1[8], lin2[8];
    const double *ln_w[8], *ln_b[8];

    /* Phy-ChemNODE */
    int latent, n_substeps;
    cm_linear enc[3], fld[3], dec[3];

    /* OOD data */
    int has_ood;
    double T_lo, T_hi, beta_f, beta_o;
    const double *beta_coef, *yt_min, *yt_max;
    int n_zb;
    const double *z_edges, *T_min_z, *T_max_z;
    int vq_K, vq_d;
    const double *vq_centroid, *vq_mean, *vq_basis, *vq_thr;  /* K x F, K x F, K x F x d, K */
    int n_land;
    const double *land, *land_thr;                              /* n_land x F, 1 */

    int n_arrays;
    cm_array *arrays;
};

/* ------------------------------------------------------------------------------------------ */
/* loading                                                                                    */

static const cm_array *find(const cm_model *m, const char *name)
{
    int i;
    for (i = 0; i < m->n_arrays; i++)
        if (strcmp(m->arrays[i].name, name) == 0) return &m->arrays[i];
    return NULL;
}

static const double *get(const cm_model *m, const char *name, int n, char *err, int errlen, int *ok)
{
    const cm_array *a = find(m, name);
    if (!a) {
        if (*ok) snprintf(err, errlen, "model file has no array '%s'", name);
        *ok = 0;
        return NULL;
    }
    if (n >= 0 && a->n != n) {
        if (*ok) snprintf(err, errlen, "array '%s' has %d values, expected %d", name, a->n, n);
        *ok = 0;
        return NULL;
    }
    return a->v;
}

static double get_scalar(const cm_model *m, const char *name, double dflt)
{
    const cm_array *a = find(m, name);
    return (a && a->n >= 1) ? a->v[0] : dflt;
}

static void linear(const cm_model *m, cm_linear *L, const char *prefix, int n_out, int n_in,
                   char *err, int errlen, int *ok)
{
    char name[128];
    snprintf(name, sizeof name, "%s.weight", prefix);
    L->W = get(m, name, n_out * n_in, err, errlen, ok);
    snprintf(name, sizeof name, "%s.bias", prefix);
    L->b = get(m, name, n_out, err, errlen, ok);
    L->n_out = n_out;
    L->n_in = n_in;
}

static void copy_name(char *dst, const char *src)
{
    int i;
    for (i = 0; i < CM_MAX_NAME - 1 && src[i]; i++) dst[i] = src[i];
    dst[i] = '\0';
}

static int read_file(cm_model *m, FILE *f, char *err, int errlen)
{
    char tag[8], name[96], tok[256];
    int n, i, cap = 64, version = 0;
    if (fscanf(f, "%255s %d", tok, &version) != 2 || strcmp(tok, "CHEMMANIFOLD_SURROGATE") != 0) {
        snprintf(err, errlen, "not a ChemManifold surrogate file");
        return 0;
    }
    if (version != 1) {
        snprintf(err, errlen, "unsupported model file version %d", version);
        return 0;
    }
    m->arrays = (cm_array *)calloc(cap, sizeof(cm_array));
    while (fscanf(f, "%7s %95s %d", tag, name, &n) == 3) {
        if (n < 0) {
            snprintf(err, errlen, "bad record '%s'", name);
            return 0;
        }
        if (tag[0] == 'S') {
            if (strcmp(name, "species") == 0) {
                if (n > CM_MAX_SPECIES) {
                    snprintf(err, errlen, "too many species (%d > %d)", n, CM_MAX_SPECIES);
                    return 0;
                }
                for (i = 0; i < n; i++) {
                    if (fscanf(f, "%255s", tok) != 1) goto truncated;
                    copy_name(m->species[i], tok);
                }
            } else if (strcmp(name, "arch") == 0 && n == 1) {
                if (fscanf(f, "%255s", tok) != 1) goto truncated;
                copy_name(m->arch_name, tok);
            } else {
                for (i = 0; i < n; i++)
                    if (fscanf(f, "%255s", tok) != 1) goto truncated;
            }
            continue;
        }
        if (tag[0] != 'A') {
            snprintf(err, errlen, "unknown record type '%s'", tag);
            return 0;
        }
        if (m->n_arrays == cap) {
            cap *= 2;
            m->arrays = (cm_array *)realloc(m->arrays, cap * sizeof(cm_array));
        }
        {
            cm_array *a = &m->arrays[m->n_arrays];
            strncpy(a->name, name, sizeof a->name - 1);
            a->name[sizeof a->name - 1] = '\0';
            a->n = n;
            a->v = (double *)malloc((n > 0 ? n : 1) * sizeof(double));
            for (i = 0; i < n; i++)
                if (fscanf(f, "%lf", &a->v[i]) != 1) goto truncated;
            m->n_arrays++;
        }
    }
    return 1;
truncated:
    snprintf(err, errlen, "model file truncated in '%s'", name);
    return 0;
}

static double nasa_h_RT(const double *a, double T)
{
    return a[0] + a[1] / 2 * T + a[2] / 3 * T * T + a[3] / 4 * T * T * T + a[4] / 5 * T * T * T * T + a[5] / T;
}

cm_model *cm_load(const char *path, char *err, int errlen)
{
    FILE *f = fopen(path, "r");
    cm_model *m;
    int ok = 1, Ns, Ne, H, i, k, F;
    char name[64];
    if (!f) {
        snprintf(err, errlen, "cannot open model file '%s'", path);
        return NULL;
    }
    m = (cm_model *)calloc(1, sizeof(cm_model));
    if (!read_file(m, f, err, errlen)) {
        fclose(f);
        cm_free(m);
        return NULL;
    }
    fclose(f);

    Ns = m->Ns = (int)get_scalar(m, "n_species", 0);
    Ne = m->Ne = (int)get_scalar(m, "n_elements", 0);
    if (Ns <= 0 || Ns > CM_MAX_SPECIES || Ne <= 0 || Ne > CM_MAX_ELEMENTS) {
        snprintf(err, errlen, "bad n_species/n_elements (%d, %d)", Ns, Ne);
        cm_free(m);
        return NULL;
    }
    m->lam = get_scalar(m, "boxcox_lambda", 0.1);
    m->dt_base = get_scalar(m, "dt_base", 1e-5);
    m->dt_min = get_scalar(m, "dt_min", m->dt_base);
    m->dt_max = get_scalar(m, "dt_max", m->dt_base);
    m->mu_y = get(m, "mu_y", Ns, err, errlen, &ok);
    m->sigma_y = get(m, "sigma_y", Ns, err, errlen, &ok);
    m->ctx_mu = get(m, "ctx_mu", 4, err, errlen, &ok);
    m->ctx_sigma = get(m, "ctx_sigma", 4, err, errlen, &ok);
    m->A = get(m, "A", Ne * Ns, err, errlen, &ok);
    m->W = get(m, "W", Ns, err, errlen, &ok);
    m->T_mid = get(m, "T_mid", Ns, err, errlen, &ok);
    m->a_lo = get(m, "a_lo", Ns * 7, err, errlen, &ok);
    m->a_hi = get(m, "a_hi", Ns * 7, err, errlen, &ok);
    if (!ok) {
        cm_free(m);
        return NULL;
    }
    m->P_ref = get_scalar(m, "P_ref", m->ctx_mu[1]);
    m->P_frozen = m->ctx_sigma[1] < 1e-6 * fabs(m->ctx_mu[1]) + 1e-9;
    for (k = 0; k < Ns; k++) {
        const double Tf = 298.15;
        const double *a = (Tf >= m->T_mid[k]) ? m->a_hi + 7 * k : m->a_lo + 7 * k;
        m->R[k] = CM_RU / m->W[k];
        m->h_form[k] = m->R[k] * Tf * nasa_h_RT(a, Tf);
    }

    if (strcmp(m->arch_name, "resnet_film") == 0) {
        const cm_array *a = find(m, "net.inp.bias");
        m->arch = ARCH_RESNET;
        m->hidden = H = a ? a->n : 0;
        m->n_blocks = (int)get_scalar(m, "n_blocks", 0);
        if (H <= 0 || H > CM_MAX_HIDDEN || m->n_blocks <= 0 || m->n_blocks > 8) {
            snprintf(err, errlen, "bad ResNet-FiLM size (hidden %d, blocks %d)", H, m->n_blocks);
            cm_free(m);
            return NULL;
        }
        linear(m, &m->inp, "net.inp", H, Ns + 4, err, errlen, &ok);
        linear(m, &m->out, "net.out", Ns, H, err, errlen, &ok);
        for (i = 0; i < m->n_blocks; i++) {
            snprintf(name, sizeof name, "net.blocks.%d.film", i);
            linear(m, &m->film[i], name, 2 * H, 4, err, errlen, &ok);
            snprintf(name, sizeof name, "net.blocks.%d.lin1", i);
            linear(m, &m->lin1[i], name, H, H, err, errlen, &ok);
            snprintf(name, sizeof name, "net.blocks.%d.lin2", i);
            linear(m, &m->lin2[i], name, H, H, err, errlen, &ok);
            snprintf(name, sizeof name, "net.blocks.%d.norm.weight", i);
            m->ln_w[i] = get(m, name, H, err, errlen, &ok);
            snprintf(name, sizeof name, "net.blocks.%d.norm.bias", i);
            m->ln_b[i] = get(m, name, H, err, errlen, &ok);
        }
    } else if (strcmp(m->arch_name, "chemnode") == 0) {
        const cm_array *a = find(m, "net.encoder.0.bias");
        const cm_array *z = find(m, "net.encoder.4.bias");
        int d;
        m->arch = ARCH_NODE;
        H = m->hidden = a ? a->n : 0;
        d = m->latent = z ? z->n : 0;
        m->n_substeps = (int)get_scalar(m, "node_substeps", 2);
        if (H <= 0 || H > CM_MAX_HIDDEN || d <= 0 || d > CM_MAX_LATENT || m->n_substeps <= 0) {
            snprintf(err, errlen, "bad Phy-ChemNODE size (hidden %d, latent %d)", H, d);
            cm_free(m);
            return NULL;
        }
        linear(m, &m->enc[0], "net.encoder.0", H, Ns + 1, err, errlen, &ok);
        linear(m, &m->enc[1], "net.encoder.2", H, H, err, errlen, &ok);
        linear(m, &m->enc[2], "net.encoder.4", d, H, err, errlen, &ok);
        linear(m, &m->fld[0], "net.field.0", H, d + 2, err, errlen, &ok);
        linear(m, &m->fld[1], "net.field.2", H, H, err, errlen, &ok);
        linear(m, &m->fld[2], "net.field.4", d, H, err, errlen, &ok);
        linear(m, &m->dec[0], "net.decoder.0", H, d, err, errlen, &ok);
        linear(m, &m->dec[1], "net.decoder.2", H, H, err, errlen, &ok);
        linear(m, &m->dec[2], "net.decoder.4", Ns, H, err, errlen, &ok);
    } else {
        snprintf(err, errlen, "unknown architecture '%s'", m->arch_name);
        cm_free(m);
        return NULL;
    }
    if (!ok) {
        cm_free(m);
        return NULL;
    }

    /* OOD tables are optional: without them only the step itself runs */
    F = Ns + 1;
    if (find(m, "ood.T_range")) {
        const double *Tr = get(m, "ood.T_range", 2, err, errlen, &ok);
        m->beta_coef = get(m, "ood.beta_coef", Ne, err, errlen, &ok);
        m->beta_f = get_scalar(m, "ood.beta_fuel", 1.0);
        m->beta_o = get_scalar(m, "ood.beta_ox", 0.0);
        m->yt_min = get(m, "ood.yt_min", Ns, err, errlen, &ok);
        m->yt_max = get(m, "ood.yt_max", Ns, err, errlen, &ok);
        m->n_zb = (int)get_scalar(m, "ood.n_zbins", 0);
        m->z_edges = get(m, "ood.z_edges", m->n_zb + 1, err, errlen, &ok);
        m->T_min_z = get(m, "ood.T_min_z", m->n_zb, err, errlen, &ok);
        m->T_max_z = get(m, "ood.T_max_z", m->n_zb, err, errlen, &ok);
        m->vq_K = (int)get_scalar(m, "ood.vq_K", 0);
        m->vq_d = (int)get_scalar(m, "ood.vq_d", 0);
        m->vq_centroid = get(m, "ood.vq_centroid", m->vq_K * F, err, errlen, &ok);
        m->vq_mean = get(m, "ood.vq_mean", m->vq_K * F, err, errlen, &ok);
        m->vq_basis = get(m, "ood.vq_basis", m->vq_K * F * m->vq_d, err, errlen, &ok);
        m->vq_thr = get(m, "ood.vq_threshold", m->vq_K, err, errlen, &ok);
        m->n_land = (int)get_scalar(m, "ood.n_landmarks", 0);
        m->land = get(m, "ood.landmarks", m->n_land * F, err, errlen, &ok);
        m->land_thr = get(m, "ood.landmark_threshold", 1, err, errlen, &ok);
        if (!ok || m->vq_d > CM_MAX_FEAT) {
            if (ok) snprintf(err, errlen, "bad OOD tables");
            cm_free(m);
            return NULL;
        }
        m->T_lo = Tr[0];
        m->T_hi = Tr[1];
        m->has_ood = 1;
    }
    return m;
}

void cm_free(cm_model *m)
{
    int i;
    if (!m) return;
    for (i = 0; i < m->n_arrays; i++) free(m->arrays[i].v);
    free(m->arrays);
    free(m);
}

void cm_default_options(cm_options *o)
{
    o->T_freeze = 0.0;
    o->max_substeps = 50;
    o->ood_action = 0;
    o->T_margin = 25.0;
    o->y_margin = 0.25;
    o->p_tol = 0.05;
    o->check_ood = 1;
}

int cm_n_species(const cm_model *m) { return m->Ns; }
const char *cm_species_name(const cm_model *m, int k) { return m->species[k]; }
const char *cm_arch(const cm_model *m) { return m->arch_name; }
double cm_dt_min(const cm_model *m) { return m->dt_min; }
double cm_dt_max(const cm_model *m) { return m->dt_max; }
int cm_has_ood(const cm_model *m) { return m->has_ood; }

/* ------------------------------------------------------------------------------------------ */
/* thermodynamics and physics layers                                                          */

static const double *coeffs(const cm_model *m, int k, double T)
{
    return (T >= m->T_mid[k]) ? m->a_hi + 7 * k : m->a_lo + 7 * k;
}

double cm_enthalpy(const cm_model *m, const double *Y, double T)
{
    double h = 0.0;
    int k;
    for (k = 0; k < m->Ns; k++) h += Y[k] * m->R[k] * T * nasa_h_RT(coeffs(m, k, T), T);
    return h;
}

double cm_temperature(const cm_model *m, const double *Y, double h0, double T)
{
    int it, k;
    for (it = 0; it < CM_N_NEWTON; it++) {
        double h = 0.0, cp = 0.0;
        for (k = 0; k < m->Ns; k++) {
            const double *a = coeffs(m, k, T);
            cp += Y[k] * m->R[k] * (a[0] + a[1] * T + a[2] * T * T + a[3] * T * T * T + a[4] * T * T * T * T);
            h += Y[k] * m->R[k] * T * nasa_h_RT(a, T);
        }
        if (cp < 100.0) cp = 100.0;
        T -= (h - h0) / cp;
        if (T < CM_T_LO) T = CM_T_LO;
        if (T > CM_T_HI) T = CM_T_HI;
    }
    return T;
}

/* Solve the small SPD system G x = r (n <= CM_MAX_ELEMENTS) by Gaussian elimination. */
static void solve_small(int n, double G[CM_MAX_ELEMENTS][CM_MAX_ELEMENTS], double *r)
{
    int i, j, k, p;
    for (k = 0; k < n; k++) {
        p = k;
        for (i = k + 1; i < n; i++)
            if (fabs(G[i][k]) > fabs(G[p][k])) p = i;
        if (p != k) {
            double t;
            for (j = 0; j < n; j++) { t = G[k][j]; G[k][j] = G[p][j]; G[p][j] = t; }
            t = r[k]; r[k] = r[p]; r[p] = t;
        }
        if (G[k][k] == 0.0) G[k][k] = 1e-300;
        for (i = k + 1; i < n; i++) {
            double f = G[i][k] / G[k][k];
            for (j = k; j < n; j++) G[i][j] -= f * G[k][j];
            r[i] -= f * r[k];
        }
    }
    for (k = n - 1; k >= 0; k--) {
        for (j = k + 1; j < n; j++) r[k] -= G[k][j] * r[j];
        r[k] /= G[k][k];
    }
}

/* NullSpaceProjection.forward: Y (in: candidate, out: projected) onto {Y >= 0, A Y = A Y0}. */
static void project(const cm_model *m, const double *Y0, double *Y)
{
    const int Ns = m->Ns, Ne = m->Ne;
    double G[CM_MAX_ELEMENTS][CM_MAX_ELEMENTS], r[CM_MAX_ELEMENTS], w[CM_MAX_SPECIES];
    int it, i, j, k;
    for (k = 0; k < Ns; k++)
        if (Y[k] < 0.0) Y[k] = 0.0;
    for (it = 0; it < CM_N_ACTIVE; it++) {
        for (k = 0; k < Ns; k++) {
            if (Y[k] < 0.0) Y[k] = 0.0;
            w[k] = Y[k] + CM_W_EPS;
        }
        for (i = 0; i < Ne; i++) {
            const double *Ai = m->A + i * Ns;
            r[i] = 0.0;
            for (k = 0; k < Ns; k++) r[i] += Ai[k] * (Y[k] - Y0[k]);
            for (j = 0; j < Ne; j++) {
                const double *Aj = m->A + j * Ns;
                double s = 0.0;
                for (k = 0; k < Ns; k++) s += Ai[k] * w[k] * Aj[k];
                G[i][j] = s + (i == j ? CM_RIDGE : 0.0);
            }
        }
        solve_small(Ne, G, r);
        for (k = 0; k < Ns; k++) {
            double s = 0.0;
            for (i = 0; i < Ne; i++) s += r[i] * m->A[i * Ns + k];
            Y[k] -= w[k] * s;
        }
    }
    for (k = 0; k < Ns; k++)
        if (Y[k] < 0.0) Y[k] = 0.0;
}

static double boxcox(double Y, double lam)
{
    return (pow((Y > 0.0 ? Y : 0.0) + CM_EPS_BOXCOX, lam) - 1.0) / lam;
}

static double inv_boxcox(double y, double lam)
{
    double base = lam * y + 1.0, Y;
    if (base < CM_EPS_BOXCOX) base = CM_EPS_BOXCOX;
    Y = pow(base, 1.0 / lam);
    return Y < 0.0 ? 0.0 : (Y > 1.0 ? 1.0 : Y);
}

/* ------------------------------------------------------------------------------------------ */
/* networks                                                                                   */

static double silu(double x) { return x / (1.0 + exp(-x)); }

static void apply(const cm_linear *L, const double *x, double *y, int act)
{
    int i, j;
    const int n4 = L->n_in & ~3;
    for (i = 0; i < L->n_out; i++) {
        /* four partial sums: lets the compiler vectorize the dot product without -ffast-math */
        const double *w = L->W + (size_t)i * L->n_in;
        double s0 = 0.0, s1 = 0.0, s2 = 0.0, s3 = 0.0, s;
        for (j = 0; j < n4; j += 4) {
            s0 += w[j] * x[j];
            s1 += w[j + 1] * x[j + 1];
            s2 += w[j + 2] * x[j + 2];
            s3 += w[j + 3] * x[j + 3];
        }
        for (; j < L->n_in; j++) s0 += w[j] * x[j];
        s = L->b[i] + ((s0 + s1) + (s2 + s3));
        y[i] = act ? silu(s) : s;
    }
}

static void resnet_film(const cm_model *m, const double *yt, const double *c, double *y_cand)
{
    const int H = m->hidden, Ns = m->Ns;
    double x[CM_MAX_SPECIES + 4], h[CM_MAX_HIDDEN], u[CM_MAX_HIDDEN], v[CM_MAX_HIDDEN];
    double gb[2 * CM_MAX_HIDDEN];
    int b, i;
    for (i = 0; i < Ns; i++) x[i] = yt[i];
    for (i = 0; i < 4; i++) x[Ns + i] = c[i];
    apply(&m->inp, x, h, 1);                                   /* Eq. 32 */
    for (b = 0; b < m->n_blocks; b++) {                        /* Eqs. 33-36 */
        double mean = 0.0, var = 0.0, inv;
        apply(&m->film[b], c, gb, 0);                          /* gamma = gb[:H], beta = gb[H:] */
        apply(&m->lin1[b], h, u, 0);
        for (i = 0; i < H; i++) mean += u[i];
        mean /= H;
        for (i = 0; i < H; i++) var += (u[i] - mean) * (u[i] - mean);
        inv = 1.0 / sqrt(var / H + CM_LN_EPS);
        for (i = 0; i < H; i++) {
            double n = (u[i] - mean) * inv * m->ln_w[b][i] + m->ln_b[b][i];
            u[i] = silu(n) * (1.0 + gb[i]) + gb[H + i];
        }
        apply(&m->lin2[b], u, v, 1);
        for (i = 0; i < H; i++) h[i] += v[i];
    }
    apply(&m->out, h, y_cand, 0);                              /* Eq. 37 */
    for (i = 0; i < Ns; i++) y_cand[i] += yt[i];
}

static void mlp3(const cm_linear *L, const double *x, double *y)
{
    double a[CM_MAX_HIDDEN], b[CM_MAX_HIDDEN];
    apply(&L[0], x, a, 1);
    apply(&L[1], a, b, 1);
    apply(&L[2], b, y, 0);
}

static void node_field(const cm_model *m, const double *z, const double *ph, double *dz)
{
    double x[CM_MAX_LATENT + 2];
    int i;
    for (i = 0; i < m->latent; i++) x[i] = z[i];
    x[m->latent] = ph[0];
    x[m->latent + 1] = ph[1];
    mlp3(m->fld, x, dz);
}

static void chemnode(const cm_model *m, const double *yt, const double *c, double dt_star, double *y_cand)
{
    const int Ns = m->Ns, d = m->latent;
    double x[CM_MAX_SPECIES + 1], z0[CM_MAX_LATENT], z[CM_MAX_LATENT], zt[CM_MAX_LATENT];
    double k1[CM_MAX_LATENT], k2[CM_MAX_LATENT], k3[CM_MAX_LATENT], k4[CM_MAX_LATENT];
    double d0[CM_MAX_SPECIES], d1[CM_MAX_SPECIES];
    const double hs = dt_star / m->n_substeps;
    int s, i;
    for (i = 0; i < Ns; i++) x[i] = yt[i];
    x[Ns] = c[0];
    mlp3(m->enc, x, z0);                                       /* E([y~; T~]) */
    for (i = 0; i < d; i++) z[i] = z0[i];
    for (s = 0; s < m->n_substeps; s++) {                      /* RK4, Eqs. 38-40 */
        node_field(m, z, c + 1, k1);
        for (i = 0; i < d; i++) zt[i] = z[i] + 0.5 * hs * k1[i];
        node_field(m, zt, c + 1, k2);
        for (i = 0; i < d; i++) zt[i] = z[i] + 0.5 * hs * k2[i];
        node_field(m, zt, c + 1, k3);
        for (i = 0; i < d; i++) zt[i] = z[i] + hs * k3[i];
        node_field(m, zt, c + 1, k4);
        for (i = 0; i < d; i++) z[i] += hs / 6.0 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]);
    }
    mlp3(m->dec, z0, d0);
    mlp3(m->dec, z, d1);
    for (i = 0; i < Ns; i++) y_cand[i] = yt[i] + (d1[i] - d0[i]);  /* Eq. 41 */
}

static int cm_finite(double x) { return x == x && x < 1e300 && x > -1e300; }

int cm_step(const cm_model *m, const double *Y, double T, double P, double h, double dt,
            double *Y_out, double *T_out)
{
    const int Ns = m->Ns;
    double yt[CM_MAX_SPECIES], yc[CM_MAX_SPECIES], c[4], raw[4];
    int k;
    for (k = 0; k < Ns; k++) yt[k] = (boxcox(Y[k], m->lam) - m->mu_y[k]) / m->sigma_y[k];
    /* A model trained at one pressure has ctx_sigma[P] ~ 1e-12: feed it its own pressure,
       otherwise a few Pa of pressure variation in the CFD would be amplified ~1e12 times. */
    raw[0] = T;
    raw[1] = m->P_frozen ? m->ctx_mu[1] : P;
    raw[2] = h;
    raw[3] = log10(dt);
    for (k = 0; k < 4; k++) c[k] = (raw[k] - m->ctx_mu[k]) / m->ctx_sigma[k];
    if (m->arch == ARCH_RESNET)
        resnet_film(m, yt, c, yc);
    else
        chemnode(m, yt, c, dt / m->dt_base, yc);
    for (k = 0; k < Ns; k++) {
        Y_out[k] = inv_boxcox(yc[k] * m->sigma_y[k] + m->mu_y[k], m->lam);
        if (!cm_finite(Y_out[k])) return -1;
    }
    project(m, Y, Y_out);
    *T_out = cm_temperature(m, Y_out, h, T);
    for (k = 0; k < Ns; k++)
        if (!cm_finite(Y_out[k])) return -1;
    return cm_finite(*T_out) ? 0 : -1;
}

/* ------------------------------------------------------------------------------------------ */
/* out-of-distribution checks                                                                 */

void cm_ood(const cm_model *m, const cm_options *o, const double *Y, double T, double P, cm_info *info)
{
    const int Ns = m->Ns, F = Ns + 1;
    double x[CM_MAX_FEAT], beta = 0.0;
    int k, i, j;
    info->Z = 0.0;
    info->manifold_ratio = 0.0;
    info->data_ratio = 0.0;
    if (fabs(P / m->P_ref - 1.0) > o->p_tol) info->flags |= CM_OOD_P;
    if (!m->has_ood) return;

    for (i = 0; i < m->Ne; i++) {
        double s = 0.0;
        for (k = 0; k < Ns; k++) s += m->A[i * Ns + k] * Y[k];
        beta += m->beta_coef[i] * s;
    }
    info->Z = (beta - m->beta_o) / (m->beta_f - m->beta_o);
    if (T < m->T_lo - o->T_margin || T > m->T_hi + o->T_margin) info->flags |= CM_OOD_T;
    if (m->n_zb > 0) {
        double Z = info->Z;
        int b = 0;
        while (b < m->n_zb - 1 && Z >= m->z_edges[b + 1]) b++;
        if (T < m->T_min_z[b] - o->T_margin || T > m->T_max_z[b] + o->T_margin) info->flags |= CM_OOD_TZ;
    }

    for (k = 0; k < Ns; k++) {
        x[k] = (boxcox(Y[k], m->lam) - m->mu_y[k]) / m->sigma_y[k];
        if (x[k] < m->yt_min[k] - o->y_margin || x[k] > m->yt_max[k] + o->y_margin) info->flags |= CM_OOD_SPECIES;
    }
    x[Ns] = (T - m->ctx_mu[0]) / m->ctx_sigma[0];

    if (m->vq_K > 0) {   /* nearest VQ cluster, then the residual off its local PCA plane */
        int best = 0;
        double dbest = 1e300, res = 0.0, xc[CM_MAX_FEAT], s[CM_MAX_FEAT];
        for (j = 0; j < m->vq_K; j++) {
            double dd = 0.0;
            for (k = 0; k < F; k++) {
                double e = x[k] - m->vq_centroid[j * F + k];
                dd += e * e;
            }
            if (dd < dbest) { dbest = dd; best = j; }
        }
        for (k = 0; k < F; k++) xc[k] = x[k] - m->vq_mean[best * F + k];
        for (i = 0; i < m->vq_d; i++) {
            s[i] = 0.0;
            for (k = 0; k < F; k++) s[i] += m->vq_basis[((size_t)best * F + k) * m->vq_d + i] * xc[k];
        }
        for (k = 0; k < F; k++) {
            double e = xc[k];
            for (i = 0; i < m->vq_d; i++) e -= m->vq_basis[((size_t)best * F + k) * m->vq_d + i] * s[i];
            res += e * e;
        }
        info->manifold_ratio = sqrt(res) / m->vq_thr[best];
        if (info->manifold_ratio > 1.0) info->flags |= CM_OOD_MANIFOLD;
    }
    if (m->n_land > 0) {
        double dbest = 1e300;
        for (j = 0; j < m->n_land; j++) {
            const double *l = m->land + (size_t)j * F;
            double dd = 0.0;
            for (k = 0; k < F && dd < dbest; k++) {
                double e = x[k] - l[k];
                dd += e * e;
            }
            if (dd < dbest) dbest = dd;
        }
        info->data_ratio = sqrt(dbest) / m->land_thr[0];
        if (info->data_ratio > 1.0) info->flags |= CM_OOD_DATA;
    }
}

/* ------------------------------------------------------------------------------------------ */
/* time stepping                                                                              */

int cm_advance(const cm_model *m, const cm_options *o, double *Y, double T, double P, double dt,
               cm_info *info)
{
    const int Ns = m->Ns;
    double Y0[CM_MAX_SPECIES], Yn[CM_MAX_SPECIES], h, Tn = T, dts, scale = 1.0, hrr = 0.0;
    int n, s, k;

    memset(info, 0, sizeof *info);
    info->T_out = T;
    if (o->check_ood) cm_ood(m, o, Y, T, P, info);
    if (!(dt > 0.0) || !cm_finite(T)) return 0;
    if (T < o->T_freeze) {   /* the surrogate is not used here, so neither are its OOD checks */
        info->flags = (info->flags & ~(unsigned)CM_OOD_ANY) | CM_FROZEN;
        info->manifold_ratio = info->data_ratio = 0.0;
        return 0;
    }
    if (o->ood_action == 1 && (info->flags & CM_OOD_ANY)) {
        info->flags |= CM_OOD_SKIPPED;
        return 0;
    }

    /* Inside the trained dt range [dt_min, dt_max] take n equal steps; below it take one dt_min
       step and scale its increment (keeps A Y and Y >= 0, since it is a convex combination). */
    if (dt < m->dt_min) {
        n = 1;
        dts = m->dt_min;
        scale = dt / m->dt_min;
        info->flags |= CM_DT_SCALED;
    } else {
        n = (int)ceil(dt / m->dt_max * (1.0 - 1e-12));
        if (n < 1) n = 1;
        if (n > o->max_substeps) {
            n = o->max_substeps;
            dts = m->dt_max;
            info->flags |= CM_DT_CAPPED;
        } else {
            dts = dt / n;
        }
    }

    for (k = 0; k < Ns; k++) Y0[k] = Y[k];
    h = cm_enthalpy(m, Y, T);
    for (s = 0; s < n; s++) {
        if (cm_step(m, Y, Tn, P, h, dts, Yn, &Tn) != 0) {
            for (k = 0; k < Ns; k++) Y[k] = Y0[k];
            info->flags |= CM_INVALID;
            info->T_out = T;
            return -1;
        }
        for (k = 0; k < Ns; k++) Y[k] = Yn[k];
    }
    if (scale < 1.0) {
        for (k = 0; k < Ns; k++) Y[k] = Y0[k] + scale * (Y[k] - Y0[k]);
        Tn = cm_temperature(m, Y, h, T);
    }
    for (k = 0; k < Ns; k++) hrr -= m->h_form[k] * (Y[k] - Y0[k]);
    info->hrr = hrr / dt;
    info->n_sub = n;
    info->dt_sub = dts;
    info->T_out = Tn;
    return 0;
}

/* ------------------------------------------------------------------------------------------ */
/* self-test against the PyTorch reference                                                    */

int cm_selftest(const cm_model *m, const char *path, char *report, int len)
{
    FILE *f = fopen(path, "r");
    char tok[64];
    int version, n, Ns, i, k, fail = 0, flag_mismatch = 0;
    double max_dY = 0.0, max_dT = 0.0, max_dr = 0.0, max_dhrr = 0.0;
    cm_options o;
    if (!f) {
        snprintf(report, len, "cannot open test file '%s'", path);
        return -1;
    }
    if (fscanf(f, "%63s %d %d %d", tok, &version, &n, &Ns) != 4 || strcmp(tok, "CHEMMANIFOLD_TESTS") != 0
        || Ns != m->Ns) {
        fclose(f);
        snprintf(report, len, "'%s' is not a test file for this model", path);
        return -1;
    }
    cm_default_options(&o);
    for (i = 0; i < n; i++) {
        double dt, P, T, Y[CM_MAX_SPECIES], Te, Ye[CM_MAX_SPECIES], fl, mr, dr, Z, ns, hrr, e;
        cm_info info;
        int ok = 1, bad = 0;
        ok &= fscanf(f, "%lf %lf %lf", &dt, &P, &T) == 3;
        for (k = 0; k < Ns; k++) ok &= fscanf(f, "%lf", &Y[k]) == 1;
        ok &= fscanf(f, "%lf", &Te) == 1;
        for (k = 0; k < Ns; k++) ok &= fscanf(f, "%lf", &Ye[k]) == 1;
        ok &= fscanf(f, "%lf %lf %lf %lf %lf %lf", &fl, &mr, &dr, &Z, &ns, &hrr) == 6;
        if (!ok) {
            fclose(f);
            snprintf(report, len, "test file truncated at case %d", i);
            return -1;
        }
        cm_advance(m, &o, Y, T, P, dt, &info);
        for (k = 0; k < Ns; k++) {
            e = fabs(Y[k] - Ye[k]);
            if (e > max_dY) max_dY = e;
            if (e > 1e-8) bad = 1;
        }
        e = fabs(info.T_out - Te);
        if (e > max_dT) max_dT = e;
        if (e > 1e-4) bad = 1;
        e = fabs(info.manifold_ratio - mr) + fabs(info.data_ratio - dr) + fabs(info.Z - Z);
        if (e > max_dr) max_dr = e;
        if (e > 1e-6) bad = 1;
        e = fabs(info.hrr - hrr) / (fabs(hrr) + 1e3);
        if (e > max_dhrr) max_dhrr = e;
        if (e > 1e-5) bad = 1;
        if ((int)info.flags != (int)fl || info.n_sub != (int)ns) flag_mismatch++, bad = 1;
        fail += bad;
    }
    fclose(f);
    snprintf(report, len,
             "%s: %d/%d cases match PyTorch (max |dY| %.2e, max |dT| %.2e K, max OOD-metric diff %.2e, "
             "max rel. HRR diff %.2e, %d flag/sub-step mismatches)",
             fail ? "SELFTEST FAILED" : "selftest passed", n - fail, n, max_dY, max_dT, max_dr, max_dhrr,
             flag_mismatch);
    return fail;
}

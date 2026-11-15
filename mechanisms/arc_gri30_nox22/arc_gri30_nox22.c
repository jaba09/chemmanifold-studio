/* ARC_GRI30_NOx22 chemistry core, see arc_gri30_nox22.h and gen_arc.py. */
#include "arc_gri30_nox22.h"
#include "arc_gri30_nox22_data.h"
#include <math.h>
#include <string.h>

#if ARC_NODE != ARC_N_ODE || ARC_NQSS != ARC_N_QSS || ARC_NSP != ARC_N_SP
#error "generated data does not match the header"
#endif

#define RU 8314.462618   /* J/kmol/K */
#define P0 101325.0      /* Pa */

const char* arc_species_name(int k) { return arc_names[k]; }
double arc_species_W(int k) { return arc_W[k]; }
void arc_species_elements(int k, double el[4])
{
    for (int e = 0; e < 4; e++) el[e] = arc_el[k][e];
}

static inline const double* nasa(int k, double T)
{
    return (T > arc_nasa[k][0]) ? &arc_nasa[k][1] : &arc_nasa[k][8];
}

void arc_species_h_cp(int k, double T, double* h, double* cp)
{
    const double* a = nasa(k, T);
    double T2 = T * T, T3 = T2 * T, T4 = T3 * T;
    if (cp) *cp = RU * (a[0] + a[1] * T + a[2] * T2 + a[3] * T3 + a[4] * T4);
    if (h) *h = RU * (a[0] * T + a[1] * T2 / 2 + a[2] * T3 / 3 + a[3] * T4 / 4
                      + a[4] * T4 * T / 5 + a[5]);
}

/* g/RT of all species */
static void g_RT(double T, double* g)
{
    double lnT = log(T), T2 = T * T, T3 = T2 * T, T4 = T3 * T;
    for (int k = 0; k < ARC_NSP; k++) {
        const double* a = nasa(k, T);
        double h = a[0] + a[1] * T / 2 + a[2] * T2 / 3 + a[3] * T3 / 4 + a[4] * T4 / 5 + a[5] / T;
        double s = a[0] * lnT + a[1] * T + a[2] * T2 / 2 + a[3] * T3 / 3 + a[4] * T4 / 4 + a[6];
        g[k] = h - s;
    }
}

/* forward / reverse rate constants (third-body and falloff included) */
static void rate_constants(double T, const double* c43, double* kf, double* kr)
{
    double g[ARC_NSP];
    g_RT(T, g);
    double lnT = log(T), RT = RU * T, lnP0RT = log(P0 / RT);
    for (int r = 0; r < ARC_NR; r++) {
        double k = arc_A[r] * exp(arc_b[r] * lnT - arc_E[r] / RT);
        int ty = arc_rtype[r];
        if (ty >= 1) {
            double M = 0;
            for (int s = 0; s < ARC_NSP; s++) M += arc_eff[r][s] * c43[s];
            if (ty == 1) k *= M;
            else {
                double k0 = arc_A0[r] * exp(arc_b0[r] * lnT - arc_E0[r] / RT);
                double Pr = k0 * M / k;
                double F = 1.0;
                if (ty == 2 && Pr > 1e-300) {
                    const double* t = arc_troe[r];
                    double Fc = (1 - t[0]) * exp(-T / t[1]) + t[0] * exp(-T / t[2]);
                    if (arc_ntroe[r] == 4) Fc += exp(-t[3] / T);
                    double lFc = log10(Fc > 1e-300 ? Fc : 1e-300);
                    double cc = -0.4 - 0.67 * lFc, n = 0.75 - 1.27 * lFc;
                    double x = log10(Pr) + cc;
                    double f1 = x / (n - 0.14 * x);
                    F = pow(10.0, lFc / (1 + f1 * f1));
                }
                k = k * Pr / (1 + Pr) * F;
            }
        }
        kf[r] = k;
        if (arc_rev[r]) {
            double dG = 0, dn = 0;
            for (int i = 0; i < arc_np[r]; i++) { dG += arc_pn[r][i] * g[arc_pi[r][i]]; dn += arc_pn[r][i]; }
            for (int i = 0; i < arc_nr[r]; i++) { dG -= arc_rn[r][i] * g[arc_ri[r][i]]; dn -= arc_rn[r][i]; }
            /* Kc = exp(-dG) (P0/RT)^dn */
            kr[r] = k * exp(dG - dn * lnP0RT);
        } else kr[r] = 0;
    }
}

static inline double ipow(double x, double n)
{
    return n == 1 ? x : (n == 2 ? x * x : (n == 3 ? x * x * x : pow(x, n)));
}

static void net_rates(const double* kf, const double* kr, const double* c43, double* w43)
{
    memset(w43, 0, sizeof(double) * ARC_NSP);
    for (int r = 0; r < ARC_NR; r++) {
        double qf = kf[r], qr = kr[r];
        for (int i = 0; i < arc_nr[r]; i++) qf *= ipow(c43[arc_ri[r][i]], arc_rn[r][i]);
        if (qr != 0) for (int i = 0; i < arc_np[r]; i++) qr *= ipow(c43[arc_pi[r][i]], arc_pn[r][i]);
        double q = qf - qr;
        for (int i = 0; i < arc_nr[r]; i++) w43[arc_ri[r][i]] -= arc_rn[r][i] * q;
        for (int i = 0; i < arc_np[r]; i++) w43[arc_pi[r][i]] += arc_pn[r][i] * q;
    }
}

void arc_wdot_skeletal(double T, const double* c43, double* wdot43)
{
    double kf[ARC_NR], kr[ARC_NR];
    rate_constants(T, c43, kf, kr);
    net_rates(kf, kr, c43, wdot43);
}

/* One direction of a reaction in the QSS balances: species (si, sn), product
 * side (oi, on). Adds to A (NQ x NQ) and b. */
static void qss_dir(double k, const double* c43, int nr, const int* si, const double* sn,
                    int np, const int* oi, const double* on, double A[][ARC_NQSS], double* b)
{
    if (k == 0) return;
    double C = k;
    int nq = 0, j = -1;
    for (int i = 0; i < nr; i++) {
        int s = si[i];
        if (s < ARC_NODE) C *= ipow(c43[s], sn[i]);
        else { nq += (int)sn[i]; j = s - ARC_NODE; }
    }
    if (nq >= 2 || C == 0) return; /* QSS-QSS direction: truncated in the balances */
    /* net stoichiometry of each QSS species in this direction */
    for (int i = 0; i < np; i++) {
        int s = oi[i];
        if (s < ARC_NODE) continue;
        if (nq == 0) b[s - ARC_NODE] -= on[i] * C;
        else A[s - ARC_NODE][j] += on[i] * C;
    }
    for (int i = 0; i < nr; i++) {
        int s = si[i];
        if (s < ARC_NODE) continue;
        if (nq == 0) b[s - ARC_NODE] += sn[i] * C;
        else A[s - ARC_NODE][j] -= sn[i] * C;
    }
}

static void lu_solve(double A[][ARC_NQSS], double* b, double* x)
{
    const int n = ARC_NQSS;
    for (int k = 0; k < n; k++) {
        int p = k;
        double m = fabs(A[k][k]);
        for (int i = k + 1; i < n; i++) if (fabs(A[i][k]) > m) { m = fabs(A[i][k]); p = i; }
        if (m == 0) { A[k][k] = -1e-300; }
        if (p != k) {
            for (int j = 0; j < n; j++) { double t = A[k][j]; A[k][j] = A[p][j]; A[p][j] = t; }
            double t = b[k]; b[k] = b[p]; b[p] = t;
        }
        for (int i = k + 1; i < n; i++) {
            double f = A[i][k] / A[k][k];
            if (f == 0) continue;
            for (int j = k + 1; j < n; j++) A[i][j] -= f * A[k][j];
            b[i] -= f * b[k];
        }
    }
    for (int i = n - 1; i >= 0; i--) {
        double s = b[i];
        for (int j = i + 1; j < n; j++) s -= A[i][j] * x[j];
        x[i] = s / A[i][i];
    }
}

void arc_wdot(double T, double p, const double* c, double* wdot, double* xq)
{
    (void)p;
    double c43[ARC_NSP];
    for (int k = 0; k < ARC_NODE; k++) c43[k] = c[k];
    for (int k = ARC_NODE; k < ARC_NSP; k++) c43[k] = 0; /* third bodies: ODE species only */
    double kf[ARC_NR], kr[ARC_NR];
    rate_constants(T, c43, kf, kr);
    double A[ARC_NQSS][ARC_NQSS], b[ARC_NQSS], x[ARC_NQSS];
    memset(A, 0, sizeof A);
    memset(b, 0, sizeof b);
    for (int r = 0; r < ARC_NR; r++) {
        qss_dir(kf[r], c43, arc_nr[r], arc_ri[r], arc_rn[r], arc_np[r], arc_pi[r], arc_pn[r], A, b);
        qss_dir(kr[r], c43, arc_np[r], arc_pi[r], arc_pn[r], arc_nr[r], arc_ri[r], arc_rn[r], A, b);
    }
    /* tiny regularization of the consumption terms (cold gas: all rates ~0) */
    for (int i = 0; i < ARC_NQSS; i++) A[i][i] -= 1e-12 * fabs(A[i][i]) + 1e-30;
    lu_solve(A, b, x);
    for (int i = 0; i < ARC_NQSS; i++) {
        double v = x[i];
        if (!(v > 0)) v = 0; /* also catches NaN */
        c43[ARC_NODE + i] = v;
        if (xq) xq[i] = v;
    }
    double w43[ARC_NSP];
    net_rates(kf, kr, c43, w43);
    for (int k = 0; k < ARC_NODE; k++) wdot[k] = w43[k];
}

void arc_rhs(double p, const double* y, double* dydt)
{
    double T = y[ARC_NODE];
    double sYW = 0;
    for (int k = 0; k < ARC_NODE; k++) sYW += y[k] / arc_W[k];
    double rho = p / (RU * T * sYW);
    double c[ARC_NODE], w[ARC_NODE];
    for (int k = 0; k < ARC_NODE; k++) c[k] = rho * y[k] / arc_W[k];
    arc_wdot(T, p, c, w, 0);
    double cp = 0, q = 0;
    for (int k = 0; k < ARC_NODE; k++) {
        double h, cpk;
        arc_species_h_cp(k, T, &h, &cpk);
        cp += y[k] * cpk / arc_W[k];
        q += h * w[k];
        dydt[k] = w[k] * arc_W[k] / rho;
    }
    dydt[ARC_NODE] = -q / (rho * cp);
}

void arc_elements(const double* Y, double el[4])
{
    for (int e = 0; e < 4; e++) el[e] = 0;
    for (int k = 0; k < ARC_NODE; k++)
        for (int e = 0; e < 4; e++) el[e] += arc_el[k][e] * Y[k] / arc_W[k];
}

static int sp_index(const char* n)
{
    for (int k = 0; k < ARC_NODE; k++) if (!strcmp(arc_names[k], n)) return k;
    return -1;
}

void arc_project(double* Y, const double el0[4])
{
    static int iCO2 = -1, iH2O, iO2, iN2;
    if (iCO2 < 0) { iH2O = sp_index("H2O"); iO2 = sp_index("O2"); iN2 = sp_index("N2"); iCO2 = sp_index("CO2"); }
    for (int pass = 0; pass < 2; pass++) { /* second pass removes round-off */
        double el[4];
        arc_elements(Y, el);
        double dC = el0[0] - el[0], dH = el0[1] - el[1], dO = el0[2] - el[2], dN = el0[3] - el[3];
        /* kmol/kg changes: CO2 carries C, H2O carries H, N2 carries N, O2 the rest of O */
        double nCO2 = dC, nH2O = dH / 2, nN2 = dN / 2, nO2 = (dO - 2 * nCO2 - nH2O) / 2;
        Y[iCO2] += nCO2 * arc_W[iCO2];
        Y[iH2O] += nH2O * arc_W[iH2O];
        Y[iN2] += nN2 * arc_W[iN2];
        Y[iO2] += nO2 * arc_W[iO2];
    }
}

void arc_rhs_many(double p, int n, const double* y, double* dydt)
{
    for (int i = 0; i < n; i++) arc_rhs(p, y + i * (ARC_NODE + 1), dydt + i * (ARC_NODE + 1));
}

void arc_rhs_skeletal(double p, const double* y, double* dydt)
{
    double T = y[ARC_NSP];
    double sYW = 0;
    for (int k = 0; k < ARC_NSP; k++) sYW += y[k] / arc_W[k];
    double rho = p / (RU * T * sYW);
    double c[ARC_NSP], w[ARC_NSP];
    for (int k = 0; k < ARC_NSP; k++) c[k] = rho * y[k] / arc_W[k];
    arc_wdot_skeletal(T, c, w);
    double cp = 0, q = 0;
    for (int k = 0; k < ARC_NSP; k++) {
        double h, cpk;
        arc_species_h_cp(k, T, &h, &cpk);
        cp += y[k] * cpk / arc_W[k];
        q += h * w[k];
        dydt[k] = w[k] * arc_W[k] / rho;
    }
    dydt[ARC_NSP] = -q / (rho * cp);
}

void arc_rhs_skeletal_many(double p, int n, const double* y, double* dydt)
{
    for (int i = 0; i < n; i++) arc_rhs_skeletal(p, y + i * (ARC_NSP + 1), dydt + i * (ARC_NSP + 1));
}

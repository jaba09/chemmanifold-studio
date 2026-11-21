/* ARC_GRI30_NOx22 direct chemistry for one cell; see arc22_core.h. */
#include <math.h>
#include <string.h>
#include "arc22_core.h"
#include "arc22_kernel.h"

#define N ARC22_NSP
#define NE (ARC22_NSP + 1)          /* equations: 22 species + T */
#define RU 8314.46261815324         /* J/kmol/K, as the kernel */

static const char *arc22_names[N] = {"H2", "H", "O", "O2", "OH", "H2O", "HO2", "H2O2", "CH4", "CH3", "CO",
                                     "CO2", "CH2O", "CH3OH", "C2H2", "C2H4", "C2H6", "N2", "NO", "NO2",
                                     "N2O", "HCN"};
/* C, H, O, N atoms (same as the kernel's E_ODE table) */
static const double arc22_el[N][4] = {
    {0, 2, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}, {0, 0, 2, 0}, {0, 1, 1, 0}, {0, 2, 1, 0}, {0, 1, 2, 0},
    {0, 2, 2, 0}, {1, 4, 0, 0}, {1, 3, 0, 0}, {1, 0, 1, 0}, {1, 0, 2, 0}, {1, 2, 1, 0}, {1, 4, 1, 0},
    {2, 2, 0, 0}, {2, 4, 0, 0}, {2, 6, 0, 0}, {0, 0, 0, 2}, {0, 0, 1, 1}, {0, 0, 2, 1}, {0, 0, 1, 2},
    {1, 1, 0, 1}};
static const double atomic_W[4] = {12.011, 1.008, 15.999, 14.007};   /* Cantera's C H O N */
enum { iH2O = 5, iO2 = 3, iCO2 = 11, iN2 = 17 };

static double W[N];
static int W_ready = 0;

static void init_W(void)
{
    int k, e;
    if (W_ready) return;
    for (k = 0; k < N; k++) {
        W[k] = 0.0;
        for (e = 0; e < 4; e++) W[k] += arc22_el[k][e] * atomic_W[e];
    }
    W_ready = 1;
}

const char *arc22_name(int k) { return (k >= 0 && k < N) ? arc22_names[k] : ""; }
double arc22_W(int k) { init_W(); return (k >= 0 && k < N) ? W[k] : 0.0; }

void arc22_default_options(arc22_options *o)
{
    o->rtol = 1e-4;
    o->atol = 1e-9;
    o->atol_T = 1e-3;
    o->T_freeze = 200.0;
    o->T_quiet = 500.0;
    o->max_steps = 100000;
    o->project = 1;
    o->method = 1;
    o->jac_reuse = 8;
}

double arc22_h_mass(const double *Y, double T)
{
    double cp[N], h[N], s = 0.0;
    int k;
    init_W();
    arck_thermo_cp_h(T, cp, h);
    for (k = 0; k < N; k++) s += Y[k] * h[k] / W[k];
    return s;
}

void arc22_rhs(double p, const double *y, double *dydt)
{
    double c[N], w[N], cp[N], h[N], sYW = 0.0, rho, cpm = 0.0, q = 0.0, T = y[N];
    int k;
    init_W();
    if (T < 200.0) T = 200.0;
    if (T > 5000.0) T = 5000.0;
    for (k = 0; k < N; k++) sYW += y[k] / W[k];
    if (sYW < 1e-12) sYW = 1e-12;
    rho = p / (RU * T * sYW);
    for (k = 0; k < N; k++) c[k] = rho * y[k] / W[k];
    arck_wdot(T, c, w, NULL, 0);
    arck_thermo_cp_h(T, cp, h);
    for (k = 0; k < N; k++) {
        cpm += y[k] * cp[k] / W[k];
        q += h[k] * w[k];
        dydt[k] = w[k] * W[k] / rho;
    }
    dydt[N] = -q / (rho * cpm);
}

/* finite-difference Jacobian J[i][j] = d f_i / d y_j (column by column, as the OpenFOAM ARC solver) */
static void jacobian(double p, const double *y, const double *f0, double J[NE][NE])
{
    double yy[NE], f1[NE];
    int i, j;
    memcpy(yy, y, sizeof yy);
    for (j = 0; j < NE; j++) {
        const double y0 = yy[j];
        const double hj = (j == N) ? 1e-6 * (y0 > 300.0 ? y0 : 300.0) : 1e-7 * (fabs(y0) > 1e-9 ? fabs(y0) : 1e-9);
        yy[j] = y0 + hj;
        arc22_rhs(p, yy, f1);
        yy[j] = y0;
        for (i = 0; i < NE; i++) J[i][j] = (f1[i] - f0[i]) / hj;
    }
}

/* LU with partial pivoting of A (in place); returns 0 if singular */
static int lu_decompose(double A[NE][NE], int piv[NE])
{
    int i, j, k, m;
    for (k = 0; k < NE; k++) {
        double amax = fabs(A[k][k]);
        m = k;
        for (i = k + 1; i < NE; i++)
            if (fabs(A[i][k]) > amax) { amax = fabs(A[i][k]); m = i; }
        if (amax == 0.0 || !isfinite(amax)) return 0;
        piv[k] = m;
        if (m != k)
            for (j = 0; j < NE; j++) { double t = A[k][j]; A[k][j] = A[m][j]; A[m][j] = t; }
        for (i = k + 1; i < NE; i++) {
            const double l = A[i][k] / A[k][k];
            A[i][k] = l;
            if (l != 0.0)
                for (j = k + 1; j < NE; j++) A[i][j] -= l * A[k][j];
        }
    }
    return 1;
}

static void lu_solve(double A[NE][NE], const int piv[NE], double *b)
{
    int i, j;
    for (i = 0; i < NE; i++) {
        double t;
        if (piv[i] != i) { t = b[i]; b[i] = b[piv[i]]; b[piv[i]] = t; }
        for (j = 0; j < i; j++) b[i] -= A[i][j] * b[j];
    }
    for (i = NE - 1; i >= 0; i--) {
        for (j = i + 1; j < NE; j++) b[i] -= A[i][j] * b[j];
        b[i] /= A[i][i];
    }
}

static void elements(const double *Y, double el[4])
{
    int k, e;
    for (e = 0; e < 4; e++) el[e] = 0.0;
    for (k = 0; k < N; k++)
        for (e = 0; e < 4; e++) el[e] += arc22_el[k][e] * Y[k] / W[k];
}

/* two-pass projection onto the element totals el0 by changing CO2 (C), H2O (H), N2 (N) and O2 (rest of O) */
static double project(double *Y, const double el0[4])
{
    double fix = 0.0;
    int pass, e;
    for (pass = 0; pass < 2; pass++) {
        double el[4], dC, dH, dO, dN, nCO2, nH2O, nN2, nO2;
        elements(Y, el);
        if (pass == 0)
            for (e = 0; e < 4; e++)
                if (el0[e] > 0.0 && fabs(el[e] - el0[e]) / el0[e] > fix) fix = fabs(el[e] - el0[e]) / el0[e];
        dC = el0[0] - el[0]; dH = el0[1] - el[1]; dO = el0[2] - el[2]; dN = el0[3] - el[3];
        nCO2 = dC; nH2O = 0.5 * dH; nN2 = 0.5 * dN; nO2 = 0.5 * (dO - 2.0 * nCO2 - nH2O);
        Y[iCO2] += nCO2 * W[iCO2];
        Y[iH2O] += nH2O * W[iH2O];
        Y[iN2] += nN2 * W[iN2];
        Y[iO2] += nO2 * W[iO2];
    }
    return fix;
}

/* Shampine's L-stable ROS4 (Hairer & Wanner II, also Numerical Recipes 'stiff'); autonomous system */
#define GAM (1.0 / 2.0)
#define A21 2.0
#define A31 (48.0 / 25.0)
#define A32 (6.0 / 25.0)
#define C21 (-8.0)
#define C31 (372.0 / 25.0)
#define C32 (12.0 / 5.0)
#define C41 (-112.0 / 125.0)
#define C42 (-54.0 / 125.0)
#define C43 (-2.0 / 5.0)
#define B1 (19.0 / 9.0)
#define B2 (1.0 / 2.0)
#define B3 (25.0 / 108.0)
#define B4 (125.0 / 108.0)
#define E1 (17.0 / 54.0)
#define E2 (7.0 / 36.0)
#define E3 0.0
#define E4 (125.0 / 108.0)

/* ROS34PW2 (Rang & Angermann 2005): 4 stages, order 3 with embedded order 2, L-stable, and a W-method,
 * i.e. it keeps its order with an approximate Jacobian, so one Jacobian serves several steps. */
static const double PW_g = 4.3586652150845900e-01;
static const double PW_a[4][4] = {{0, 0, 0, 0},
                                  {8.7173304301691801e-01, 0, 0, 0},
                                  {8.4457060015369423e-01, -1.1299064236484185e-01, 0, 0},
                                  {0, 0, 1.0, 0}};
static const double PW_c[4][4] = {{0, 0, 0, 0},
                                  {-8.7173304301691801e-01, 0, 0, 0},
                                  {-9.0338057013044082e-01, 5.4180672388095326e-02, 0, 0},
                                  {2.4212380706095346e-01, -1.2232505839045147e+00, 5.4526025533510214e-01, 0}};
static const double PW_b[4] = {2.4212380706095346e-01, -1.2232505839045147e+00, 1.5452602553351020e+00,
                               4.3586652150845900e-01};
static const double PW_bh[4] = {3.7810903145819369e-01, -9.6042292212423178e-02, 0.5, 2.1793326075422950e-01};

static double h_guess = 0.0;   /* last accepted step size, used as the next cell's first try */

int arc22_advance(const arc22_options *o, double *Yio, double T, double p, double dt, arc22_info *info)
{
    double y[NE], f[NE], J[NE][NE], A[NE][NE], g1[NE], g2[NE], g3[NE], g4[NE], yt[NE], ft[NE], ynew[NE];
    double el0[4], Y[N], Y0[N], yerr[NE], t = 0.0, h, sumY = 0.0;
    int piv[NE], i, j, k, need_jac = 1, steps = 0, jac_age = 0, jac_fresh = 0;
    arc22_info dummy;
    if (!info) info = &dummy;
    memset(info, 0, sizeof *info);
    info->T_out = T;
    init_W();
    if (!(dt > 0.0) || !(T > 0.0)) { info->status = 1; return 1; }
    if (T < o->T_freeze) { info->status = 1; return 1; }

    for (k = 0; k < N; k++) {
        Y[k] = Yio[k] > 0.0 ? Yio[k] : 0.0;
        sumY += Y[k];
    }
    if (sumY <= 0.0) { info->status = 1; return 1; }
    for (k = 0; k < N; k++) Y0[k] = Y[k] /= sumY;   /* Fluent's yk sum to 1 up to round-off */
    elements(Y, el0);
    for (k = 0; k < N; k++) y[k] = Y[k];
    y[N] = T;
    arc22_rhs(p, y, f);

    /* quiet cold cell: the whole change over dt is far below the tolerance -> one explicit Euler step */
    if (o->T_quiet > 0.0 && T < o->T_quiet) {
        double r = 0.0;
        for (i = 0; i < NE; i++) {
            const double sc = (i == N) ? o->atol_T + o->rtol * T : o->atol + o->rtol * fabs(y[i]);
            const double q = fabs(f[i]) * dt / sc;
            if (q > r) r = q;
        }
        if (r < 1e-2) {
            for (i = 0; i < NE; i++) ynew[i] = y[i] + dt * f[i];
            for (k = 0; k < N; k++) Y[k] = ynew[k] > 0.0 ? ynew[k] : 0.0;
            if (o->project) info->elem_fix = project(Y, el0);
            info->hrr = -(arc22_h_mass(Y, T) - arc22_h_mass(Y0, T)) / dt;
            for (k = 0; k < N; k++) Yio[k] = Y[k] > 0.0 ? Y[k] : 0.0;
            info->T_out = ynew[N];
            info->status = 2;
            return 2;
        }
    }

    h = (h_guess > 0.0 && h_guess < dt) ? h_guess : dt;
    if (h < 1e-12 * dt) h = 1e-12 * dt;
    while (t < dt) {
        double err = 0.0, fac, gam = (o->method == 0) ? GAM : PW_g, order = (o->method == 0) ? 4.0 : 3.0;
        int ok;
        if (steps >= o->max_steps) break;
        if (t + h > dt) h = dt - t;
        if (need_jac) {
            jacobian(p, y, f, J);
            info->n_jac++;
            need_jac = 0;
            jac_age = 0;
            jac_fresh = 1;
        }
        for (i = 0; i < NE; i++) {
            for (j = 0; j < NE; j++) A[i][j] = -J[i][j];
            A[i][i] += 1.0 / (gam * h);
        }
        ok = lu_decompose(A, piv);
        if (ok && o->method == 0) {          /* Shampine ROS4, needs the exact Jacobian */
            for (i = 0; i < NE; i++) g1[i] = f[i];
            lu_solve(A, piv, g1);
            for (i = 0; i < NE; i++) yt[i] = y[i] + A21 * g1[i];
            arc22_rhs(p, yt, ft);
            for (i = 0; i < NE; i++) g2[i] = ft[i] + C21 * g1[i] / h;
            lu_solve(A, piv, g2);
            for (i = 0; i < NE; i++) yt[i] = y[i] + A31 * g1[i] + A32 * g2[i];
            arc22_rhs(p, yt, ft);
            for (i = 0; i < NE; i++) g3[i] = ft[i] + (C31 * g1[i] + C32 * g2[i]) / h;
            lu_solve(A, piv, g3);
            for (i = 0; i < NE; i++) g4[i] = ft[i] + (C41 * g1[i] + C42 * g2[i] + C43 * g3[i]) / h;
            lu_solve(A, piv, g4);
            for (i = 0; i < NE; i++) {
                ynew[i] = y[i] + B1 * g1[i] + B2 * g2[i] + B3 * g3[i] + B4 * g4[i];
                yerr[i] = E1 * g1[i] + E2 * g2[i] + E3 * g3[i] + E4 * g4[i];
            }
        } else if (ok) {                     /* ROS34PW2: (I - h g J) k_i = h f(y + sum a_ij k_j) + h J sum c_ij k_j */
            double *kk[4];
            int s, m;
            kk[0] = g1; kk[1] = g2; kk[2] = g3; kk[3] = g4;
            for (s = 0; s < 4; s++) {
                double v[NE];
                if (s == 0) memcpy(ft, f, sizeof ft);
                else {
                    for (i = 0; i < NE; i++) {
                        yt[i] = y[i];
                        for (m = 0; m < s; m++) yt[i] += PW_a[s][m] * kk[m][i];
                    }
                    arc22_rhs(p, yt, ft);
                }
                for (i = 0; i < NE; i++) {
                    v[i] = 0.0;
                    for (m = 0; m < s; m++) v[i] += PW_c[s][m] * kk[m][i];
                }
                for (i = 0; i < NE; i++) {
                    double jv = 0.0;
                    if (s > 0)
                        for (j = 0; j < NE; j++) jv += J[i][j] * v[j];
                    kk[s][i] = ft[i] + jv;
                }
                lu_solve(A, piv, kk[s]);   /* A = (I - h g J)/(h g), so k = A^-1 (f + J v) / g */
                for (i = 0; i < NE; i++) kk[s][i] /= gam;
            }
            for (i = 0; i < NE; i++) {
                ynew[i] = y[i];
                yerr[i] = 0.0;
                for (s = 0; s < 4; s++) {
                    ynew[i] += PW_b[s] * kk[s][i];
                    yerr[i] += (PW_b[s] - PW_bh[s]) * kk[s][i];
                }
            }
        }
        if (ok) {
            for (i = 0; i < NE; i++) {
                double sc = (i == N) ? o->atol_T + o->rtol * fmax(fabs(y[i]), fabs(ynew[i]))
                                     : o->atol + o->rtol * fmax(fabs(y[i]), fabs(ynew[i]));
                double q = fabs(yerr[i]) / sc;
                if (!(q <= 1e300)) q = 1e300;   /* NaN or inf */
                if (q > err) err = q;
            }
            if (!(ynew[N] > 150.0 && ynew[N] < 6000.0)) err = 1e300;
        } else {
            err = 1e300;
        }
        if (err <= 1.0) {
            t += h;
            steps++;
            memcpy(y, ynew, sizeof y);
            arc22_rhs(p, y, f);
            jac_age++;
            jac_fresh = 0;
            if (o->method == 0 || jac_age >= o->jac_reuse) need_jac = 1;
            if (t < dt) h_guess = h;
            fac = 0.9 * pow(err > 1e-10 ? err : 1e-10, -1.0 / order);
            if (fac > 4.0) fac = 4.0;
            h *= fac;
        } else {
            info->n_reject++;
            if (!jac_fresh) need_jac = 1;   /* first suspect an old Jacobian */
            fac = (err < 1e300) ? 0.9 * pow(err, -1.0 / order) : 0.1;
            if (fac < 0.1) fac = 0.1;
            if (fac > 0.5) fac = 0.5;
            if (!jac_fresh && err < 1e300) fac = 1.0;   /* retry the same h with a fresh Jacobian */
            else h *= fac;
            if (h < 1e-14 * dt + 1e-20) break;
        }
    }
    info->n_steps = steps;
    if (t < dt * (1.0 - 1e-12)) {   /* failed: leave the cell unreacted */
        info->status = -1;
        h_guess = 0.0;
        return -1;
    }
    for (k = 0; k < N; k++) Y[k] = y[k] > 0.0 ? y[k] : 0.0;
    if (o->project) info->elem_fix = project(Y, el0);
    for (k = 0; k < N; k++) Y[k] = Y[k] > 0.0 ? Y[k] : 0.0;
    /* heat release over dt at fixed T: -(h(Y_new,T) - h(Y_old,T))/dt, positive when exothermic */
    info->hrr = -(arc22_h_mass(Y, T) - arc22_h_mass(Y0, T)) / dt;
    for (k = 0; k < N; k++) Yio[k] = Y[k];
    info->T_out = y[N];
    info->status = 0;
    return 0;
}

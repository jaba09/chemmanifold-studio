/* ARC_GRI30_NOx22: analytically reduced GRI-Mech 3.0 (22 ODE + 21 LQSSA species).
 *
 * Plain C, no dependencies. Units are Cantera's: kmol, m3, kg, J, K, Pa.
 * Species order: arc_species_name(0..ARC_NSP-1); the first ARC_NODE are the
 * transported species, the rest are the quasi-steady radicals.
 */
#ifndef ARC_GRI30_NOX22_H
#define ARC_GRI30_NOX22_H

#ifdef __cplusplus
extern "C" {
#endif

#define ARC_N_ODE 22
#define ARC_N_QSS 21
#define ARC_N_SP 43

const char* arc_species_name(int k);
double arc_species_W(int k);           /* kg/kmol */
/* number of C, H, O, N atoms of species k in el[4] */
void arc_species_elements(int k, double el[4]);

/* molar enthalpy h [J/kmol] and cp [J/kmol/K] of species k at T */
void arc_species_h_cp(int k, double T, double* h, double* cp);

/* Production rates [kmol/m3/s] of the 22 ODE species from their
 * concentrations c[22] at T, p; the 21 QSS concentrations come from the
 * linearized QSSA solve and are returned in xq (may be NULL). */
void arc_wdot(double T, double p, const double* c, double* wdot, double* xq);

/* Skeletal-mechanism production rates for all 43 species from c43 (no QSSA);
 * for testing against Cantera. */
void arc_wdot_skeletal(double T, const double* c43, double* wdot43);

/* Constant-pressure adiabatic ODE: y = (Y[22], T), dydt same layout. */
void arc_rhs(double p, const double* y, double* dydt);

/* Elements (kmol of C, H, O, N per kg) of the mass fractions Y[22]. */
void arc_elements(const double* Y, double el[4]);

/* Two-pass projection of Y[22] onto the element totals el0 by changing
 * CO2, H2O, O2 and N2 (keeps every Y >= 0 where possible). */
void arc_project(double* Y, const double el0[4]);

/* Vectorized forms for validation (n states of n_eq values each) and the full
 * 43-species skeletal ODE y = (Y[43], T) without QSSA. */
void arc_rhs_many(double p, int n, const double* y, double* dydt);
void arc_rhs_skeletal(double p, const double* y, double* dydt);
void arc_rhs_skeletal_many(double p, int n, const double* y, double* dydt);

/* arc_rhs on the original unrolled kernel (arc_kernel_original.cpp, C++17). */
void arc_rhs_original(double p, const double* y, double* dydt);

#ifdef __cplusplus
}
#endif

#endif

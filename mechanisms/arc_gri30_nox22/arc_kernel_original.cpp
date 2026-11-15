/* arc_rhs on the original ARC_GRI30_NOx22 kernel (original/arc_gri30_nox22.hpp, Javier's deliverable header:
 * fully unrolled LQSSA + rates, 8.7 us per call against 26 us for the table-driven arc_wdot of this directory;
 * production rates agree to 2e-8 relative on 400 hot A1r states). Same ODE as arc_rhs: constant-pressure,
 * y = (Y[22], T); the thermo (h, cp) and molecular weights come from arc_gri30_nox22.c, the rate-level element
 * projection of the header is off (arcChemStep projects Y after each step). */
#include "original/arc_gri30_nox22.hpp"
extern "C" {
#include "arc_gri30_nox22.h"
}

extern "C" void arc_rhs_original(double p, const double* y, double* dydt)
{
    const int N = ARC_N_ODE;
    const double RU = 8314.462618;
    double T = y[N];
    double sYW = 0;
    for (int k = 0; k < N; k++) sYW += y[k] / arc_species_W(k);
    double rho = p / (RU * T * sYW);
    double c[ARC_N_ODE], w[ARC_N_ODE];
    for (int k = 0; k < N; k++) c[k] = rho * y[k] / arc_species_W(k);
    arc_gri30_nox22::evaluate_qss(T, c, w, nullptr, false);
    double cp = 0, q = 0;
    for (int k = 0; k < N; k++) {
        double h, cpk;
        arc_species_h_cp(k, T, &h, &cpk);
        cp += y[k] * cpk / arc_species_W(k);
        q += h * w[k];
        dydt[k] = w[k] * arc_species_W(k) / rho;
    }
    dydt[N] = -q / (rho * cp);
}

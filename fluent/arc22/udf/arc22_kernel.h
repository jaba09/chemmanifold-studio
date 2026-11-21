/* ARC_GRI30_NOx22 plain-C rate kernel, see arc22_kernel.c (generated). */
#ifndef ARC22_KERNEL_H
#define ARC22_KERNEL_H
#define ARCK_N_ODE 22
#define ARCK_N_QSS 21
void arck_wdot(const double T, const double* c_ode, double* wdot_ode, double* c_qss_out, const int project);
void arck_thermo_cp_h(const double T, double* cp_mole, double* h_mole);
#endif

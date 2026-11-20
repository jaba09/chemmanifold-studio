/* ARC_GRI30_NOx22 direct chemistry for one cell: constant-pressure adiabatic ODE of the 22 transported
 * species + T, integrated with an L-stable Rosenbrock method, then element projection onto CO2/H2O/O2/N2.
 * Default ROS34PW2 (Rang & Angermann 2005, order 3(2), W-method: the finite-difference Jacobian is reused
 * for up to jac_reuse steps, ~5x cheaper on burner cells); option method = 0 is Shampine's ROS4 (order
 * 4(3), fresh Jacobian every step, as OpenFOAM's Rosenbrock34).
 * Plain C99, no Fluent dependency, so it can be tested outside Fluent (fluent/arc22/tests).
 * Units: kg, m, s, K, Pa, kmol (Cantera's).
 */
#ifndef ARC22_CORE_H
#define ARC22_CORE_H

#ifdef __cplusplus
extern "C" {
#endif

#define ARC22_NSP 22

typedef struct {
    double rtol;          /* relative tolerance (default 1e-4, as the OpenFOAM ARC run)                */
    double atol;          /* absolute tolerance on mass fractions (default 1e-9); T uses atol_T       */
    double atol_T;        /* absolute tolerance on T [K] (default 1e-3)                               */
    double T_freeze;      /* cells colder than this are not advanced (default 200 K, Fluent's minimum) */
    double T_quiet;       /* below this T a cell whose change over dt is far below the tolerance gets */
                          /* one explicit step instead of the implicit solve (default 500 K; 0 = off) */
    int max_steps;        /* Rosenbrock steps per call at most (default 100000)                        */
    int project;          /* 1 = element projection after the step (default 1)                        */
    int method;           /* 1 = ROS34PW2 W-method, Jacobian reused (default); 0 = Shampine ROS4        */
    int jac_reuse;        /* ROS34PW2: accepted steps per Jacobian at most (default 8; 1 = every step) */
} arc22_options;

typedef struct {
    int status;           /* 0 advanced, 1 frozen (T < T_freeze), 2 quiet (explicit), -1 failed       */
    int n_steps;          /* accepted Rosenbrock steps                                                 */
    int n_reject;         /* rejected steps                                                            */
    int n_jac;            /* Jacobian evaluations                                                      */
    double T_out;         /* temperature after dt [K]                                                  */
    double hrr;           /* mean heat release rate over dt [W/kg] (sum h_k * dY_k / dt, sign: >0 exo) */
    double elem_fix;      /* largest relative element correction the projection applied              */
} arc22_info;

const char *arc22_name(int k);             /* Cantera/CHEMKIN name, e.g. "CH4" */
double arc22_W(int k);                     /* kg/kmol */
void arc22_default_options(arc22_options *o);

/* Advances Y[22] (mass fractions, overwritten) from temperature T at pressure p [Pa, absolute] over dt
 * [s]. Returns info->status. On failure Y is left unchanged (frozen chemistry for this call). */
int arc22_advance(const arc22_options *o, double *Y, double T, double p, double dt, arc22_info *info);

/* Right-hand side y = (Y[22], T) -> dy/dt, for tests. */
void arc22_rhs(double p, const double *y, double *dydt);

/* Mixture enthalpy [J/kg] of (Y, T), for tests. */
double arc22_h_mass(const double *Y, double T);

#ifdef __cplusplus
}
#endif
#endif

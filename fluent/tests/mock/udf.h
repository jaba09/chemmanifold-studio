/* Minimal stand-in for Fluent's udf.h, only to compile-check and smoke-test chemmanifold_udf.c
   outside Fluent (fluent/tests/run_tests.sh). Not used when building inside Fluent. */
#ifndef MOCK_UDF_H
#define MOCK_UDF_H
#include <stdio.h>
#ifndef RP_HOST
#define RP_HOST 0
#endif
#ifndef RP_NODE
#define RP_NODE 0
#endif
typedef int cell_t;
typedef struct { double udm[16]; double rho; } Thread;
typedef struct Particle Particle;
typedef struct Material Material;
typedef struct Domain Domain;
extern int N_UDM, N_ITER, myid;
extern double CURRENT_TIME;
#define I_AM_NODE_ZERO_P (myid == 0)
#define Message printf
#define Message0 printf
#define C_UDMI(c, t, i) ((t)->udm[i])
#define C_R(c, t) ((t)->rho)
#define PRF_GRSUM1(x) (x)
#define PRF_GRHIGH1(x) (x)
#define PRF_GRLOW1(x) (x)
double RP_Get_Real(const char *name);
Domain *Get_Domain(int id);
Material *mixture_material(Domain *d);
int mixture_specie_index(Material *m, char *name);
#define DEFINE_EXECUTE_ON_LOADING(name, libname) void name(char *libname)
#define DEFINE_ON_DEMAND(name) void name(void)
#define DEFINE_ADJUST(name, d) void name(Domain *d)
#define DEFINE_CHEM_STEP(name, c, t, p, num_p, n_spe, dt, pres, temp, yk) \
    void name(cell_t c, Thread *t, Particle *p, int num_p, int n_spe, double *dt, double *pres, \
              double *temp, double *yk)
#endif

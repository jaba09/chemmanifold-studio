/* Drives the UDF hooks the way Fluent would, with the mock udf.h: load, self-test, a few
   iterations of chemistry steps over a fake mesh, and the monitor. */
#include <stdlib.h>
#include <string.h>
#include "udf.h"

int N_UDM = 7, N_ITER = 0, myid = 0;
double CURRENT_TIME = 0.0;
static const char *fluent_names[] = {"h2", "h", "o", "o2", "oh", "h2o", "ho2", "h2o2", "ch2", "ch2<s>",
                                     "ch3", "ch4", "co", "co2", "hco", "ch2o", "ch3o", "n2"};
double RP_Get_Real(const char *name) { (void)name; return 101325.0; }
Domain *Get_Domain(int id) { (void)id; return (Domain *)1; }
Material *mixture_material(Domain *d) { (void)d; return (Material *)1; }
int mixture_specie_index(Material *m, char *name)
{
    int i;
    (void)m;
    for (i = 0; i < 18; i++)
        if (strcmp(fluent_names[i], name) == 0) return i;
    return -1;
}

void chemmanifold_on_load(char *libname);
void chemmanifold_selftest(void);
void chemmanifold_monitor(Domain *d);
void user_chem_step(cell_t c, Thread *t, Particle *p, int num_p, int n_spe, double *dt, double *pres,
                    double *temp, double *yk);

int main(void)
{
    Thread cells[200];
    int it, i, k;
    chemmanifold_on_load("libudf");
    chemmanifold_selftest();
    for (it = 1; it <= 3; it++) {
        N_ITER = it;
        chemmanifold_monitor(NULL);
        for (i = 0; i < 200; i++) {
            double yk[18] = {0}, T = 300.0 + 1800.0 * i / 199.0, dt = 2e-5, pres = 0.0, z = 0.02 + 0.06 * (i % 5) / 4;
            yk[11] = z; yk[3] = 0.21 * (1 - z); yk[17] = 0.79 * (1 - z);
            if (T > 1200) { yk[13] = 0.05; yk[5] = 0.04; yk[3] -= 0.07; yk[11] -= 0.02; }
            for (k = 0; k < 18; k++) if (yk[k] < 0) yk[k] = 0;
            cells[i].rho = 101325.0 / (287.0 * T);
            user_chem_step(i, &cells[i], NULL, 0, 18, &dt, &pres, &T, yk);
        }
    }
    chemmanifold_monitor(NULL);
    printf("cell 150: ood_any %g flags %g manifold %.3f data %.3f Z %.4f HRR %.3g W/m3 substeps %g\n",
           cells[150].udm[0], cells[150].udm[1], cells[150].udm[2], cells[150].udm[3], cells[150].udm[4],
           cells[150].udm[5], cells[150].udm[6]);
    return 0;
}

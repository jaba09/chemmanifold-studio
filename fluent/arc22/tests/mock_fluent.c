/* Drives the ARC22 UDF hooks the way Fluent would, with the stand-in udf.h of fluent/tests/mock:
   load, self-test, a few iterations of chemistry steps over a fake mesh (species in a shuffled Fluent
   order, N2 last), and the monitor. */
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "udf.h"

int N_UDM = 3, N_ITER = 0, myid = 0;
double CURRENT_TIME = 0.0;
/* Fluent order of fluent/arc22/mechanism/arc22_chem.inp */
static const char *fluent_names[] = {"h2", "h", "o", "o2", "oh", "h2o", "ho2", "h2o2", "ch4", "ch3", "co", "co2",
                                     "ch2o", "ch3oh", "c2h2", "c2h4", "c2h6", "no", "no2", "n2o", "hcn", "n2"};
double RP_Get_Real(const char *name) { (void)name; return 101325.0; }
Domain *Get_Domain(int id) { (void)id; return (Domain *)1; }
Material *mixture_material(Domain *d) { (void)d; return (Material *)1; }
int mixture_specie_index(Material *m, char *name)
{
    int i;
    (void)m;
    for (i = 0; i < 22; i++)
        if (strcmp(fluent_names[i], name) == 0) return i;
    return -1;
}

void arc22_on_load(char *libname);
void arc22_selftest(void);
void arc22_monitor(Domain *d);
void arc22_chem_step(cell_t c, Thread *t, Particle *p, int num_p, int n_spe, double *dt, double *pres,
                     double *temp, double *yk);

int main(void)
{
    static Thread cells[300];
    int it, i, k, bad = 0;
    arc22_on_load("libudf");
    arc22_selftest();
    for (it = 1; it <= 3; it++) {
        N_ITER = it;
        arc22_monitor(NULL);
        for (i = 0; i < 300; i++) {
            /* CH4 (index 8) / air (o2 3, n2 21) mixtures from 300 to 2200 K, some with burnt products */
            double yk[22] = {0}, T = 300.0 + 1900.0 * i / 299.0, dt = (it == 3) ? 0.1 : 2e-5, pres = 0.0, s = 0.0;
            double z = 0.01 + 0.08 * (i % 5) / 4;
            yk[8] = z; yk[3] = 0.233 * (1 - z); yk[21] = 0.767 * (1 - z);
            if (T > 1200) { yk[11] = 0.05; yk[5] = 0.04; yk[3] -= 0.07; yk[8] -= 0.02; yk[10] = 0.01; yk[4] = 1e-3; }
            for (k = 0; k < 22; k++) { if (yk[k] < 0) yk[k] = 0; s += yk[k]; }
            for (k = 0; k < 22; k++) yk[k] /= s;
            cells[i].rho = 101325.0 / (287.0 * T);
            arc22_chem_step(i, &cells[i], NULL, 0, 22, &dt, &pres, &T, yk);
            s = 0.0;
            for (k = 0; k < 22; k++) { if (!(yk[k] >= 0.0 && yk[k] <= 1.0)) bad++; s += yk[k]; }
            if (fabs(s - 1.0) > 1e-9) bad++;
        }
    }
    arc22_monitor(NULL);
    printf("cell 250: HRR %.3g W/m3, steps %g, element fix %.2g; invalid outputs: %d\n", cells[250].udm[0],
           cells[250].udm[1], cells[250].udm[2], bad);
    return bad != 0;
}

/* oodmap model.txt < cells.txt > ood.txt
   cells.txt: N then per line T p Y1..Y18 (model order). Out: T Z h flags manifold_ratio data_ratio */
#include <stdio.h>
#include <stdlib.h>
#include "chemmanifold_core.h"
int main(int argc, char **argv) {
    char err[512]; cm_model *m = cm_load(argv[1], err, 512);
    if (!m) { fprintf(stderr, "%s\n", err); return 1; }
    cm_options o; cm_default_options(&o);
    int n, ns = cm_n_species(m); if (scanf("%d", &n) != 1) return 1;
    for (int i = 0; i < n; i++) {
        double T, p, Y[64]; cm_info inf = {0};
        if (scanf("%lf %lf", &T, &p) != 2) return 1;
        for (int k = 0; k < ns; k++) if (scanf("%lf", &Y[k]) != 1) return 1;
        cm_ood(m, &o, Y, T, p, &inf);
        printf("%g %g %g %u %g %g\n", T, inf.Z, cm_enthalpy(m, Y, T), inf.flags, inf.manifold_ratio, inf.data_ratio);
    }
    return 0;
}

/*
 * Standalone check of the UDF core outside Fluent:
 *     cc -O2 -o cm_selftest cm_selftest.c ../udf/chemmanifold_core.c -lm
 *     ./cm_selftest chemmanifold_model.txt chemmanifold_tests.txt
 */
#include <stdio.h>
#include <time.h>

#include "../udf/chemmanifold_core.h"

int main(int argc, char **argv)
{
    char err[512], report[512];
    cm_model *m;
    cm_options o;
    cm_info info;
    int fail, i, k;
    double Y[CM_MAX_SPECIES], t0;
    if (argc < 3) {
        fprintf(stderr, "usage: %s chemmanifold_model.txt chemmanifold_tests.txt\n", argv[0]);
        return 2;
    }
    m = cm_load(argv[1], err, sizeof err);
    if (!m) {
        fprintf(stderr, "%s\n", err);
        return 2;
    }
    printf("model %s: %d species, dt %.3g-%.3g s, OOD tables %s\n", cm_arch(m), cm_n_species(m),
           cm_dt_min(m), cm_dt_max(m), cm_has_ood(m) ? "yes" : "no");
    fail = cm_selftest(m, argv[2], report, sizeof report);
    printf("%s\n", report);

    /* timing: one dt_max step (with OOD checks) on an air/fuel mixture at 1500 K */
    cm_default_options(&o);
    t0 = (double)clock();
    for (i = 0; i < 2000; i++) {
        for (k = 0; k < cm_n_species(m); k++) Y[k] = 0.0;
        Y[3] = 0.20; Y[11] = 0.05; Y[cm_n_species(m) - 1] = 0.75;   /* O2, CH4, N2 in GA18 order */
        cm_advance(m, &o, Y, 1500.0, 101325.0, cm_dt_max(m), &info);
    }
    printf("%.1f us per cell call\n", ((double)clock() - t0) / CLOCKS_PER_SEC / 2000 * 1e6);
    cm_free(m);
    return fail != 0;
}

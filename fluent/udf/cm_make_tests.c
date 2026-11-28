/* Write chemmanifold_tests.txt (the cm_selftest file) for any model the core loads, e.g. arch moe_top2.
   Usage: cm_make_tests model.txt states.txt tests.txt
   states.txt: N Ns, then N lines "dt P T Y_1..Y_Ns". Each case is run through cm_advance with the default
   options (exactly what cm_selftest does) and written as "dt P T Y.. T_out Y_out.. flags mr dr Z n_sub hrr".
   The reference is this standalone build of the same core; scripts/29_export_moe_tests.py checks it against
   the numpy model before the file is written, so the plug-in's on-load selftest then catches a wrong
   library, model or build on the target machine. */
#include <stdio.h>
#include <stdlib.h>
#include "chemmanifold_core.h"
int main(int argc, char **argv)
{
    char err[256];
    cm_model *m;
    FILE *in, *out;
    int N, Ns, i, k;
    if (argc != 4) { fprintf(stderr, "usage: cm_make_tests model.txt states.txt tests.txt\n"); return 1; }
    m = cm_load(argv[1], err, sizeof err);
    if (!m) { fprintf(stderr, "load: %s\n", err); return 1; }
    in = fopen(argv[2], "r"); out = fopen(argv[3], "w");
    if (!in || !out || fscanf(in, "%d %d", &N, &Ns) != 2 || Ns != cm_n_species(m)) return 2;
    fprintf(out, "CHEMMANIFOLD_TESTS 1 %d %d\n", N, Ns);
    for (i = 0; i < N; i++) {
        double dt, P, T, Y0[CM_MAX_SPECIES], Y[CM_MAX_SPECIES];
        cm_options o; cm_info info;
        if (fscanf(in, "%lf %lf %lf", &dt, &P, &T) != 3) return 3;
        for (k = 0; k < Ns; k++) { if (fscanf(in, "%lf", &Y0[k]) != 1) return 4; Y[k] = Y0[k]; }
        cm_default_options(&o);
        cm_advance(m, &o, Y, T, P, dt, &info);
        fprintf(out, "%.17g %.17g %.17g", dt, P, T);
        for (k = 0; k < Ns; k++) fprintf(out, " %.17g", Y0[k]);
        fprintf(out, " %.17g", info.T_out);
        for (k = 0; k < Ns; k++) fprintf(out, " %.17g", Y[k]);
        fprintf(out, " %u %.17g %.17g %.17g %d %.17g\n", info.flags, info.manifold_ratio, info.data_ratio,
                info.Z, info.n_sub, info.hrr);
    }
    fclose(out); fclose(in);
    cm_free(m);
    return 0;
}

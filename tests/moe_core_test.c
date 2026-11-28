/* Parity driver for the MoE branch of fluent/udf/chemmanifold_core.c (COVLOOP stage 0).
   Usage: moe_core_test model.txt states.txt out.txt
   states.txt: N, then N lines "T dt Y_1..Y_Ns"; out.txt: N lines "flags T_out Y_out(1..Ns)" (one cm_step,
   h from cm_enthalpy) followed by "manifold_ratio data_ratio" from cm_advance. */
#include <stdio.h>
#include <stdlib.h>
#include "chemmanifold_core.h"
int main(int argc, char **argv)
{
    char err[256];
    cm_model *m = cm_load(argv[1], err, sizeof err);
    FILE *in = fopen(argv[2], "r"), *out = fopen(argv[3], "w");
    int N, i, k, Ns;
    if (!m) { fprintf(stderr, "load: %s\n", err); return 1; }
    Ns = cm_n_species(m);
    if (fscanf(in, "%d", &N) != 1) return 2;
    for (i = 0; i < N; i++) {
        double T, dt, Y[64], Yo[64], To, Ya[64];
        cm_options o; cm_info info;
        if (fscanf(in, "%lf %lf", &T, &dt) != 2) return 3;
        for (k = 0; k < Ns; k++) if (fscanf(in, "%lf", &Y[k]) != 1) return 4;
        if (cm_step(m, Y, T, 101325.0, cm_enthalpy(m, Y, T), dt, Yo, &To) != 0) To = -1;
        cm_default_options(&o); o.T_freeze = 0; o.max_substeps = 1000;
        for (k = 0; k < Ns; k++) Ya[k] = Y[k];
        cm_advance(m, &o, Ya, T, 101325.0, dt, &info);
        fprintf(out, "%u %.17g", info.flags, To);
        for (k = 0; k < Ns; k++) fprintf(out, " %.17g", Yo[k]);
        fprintf(out, " %.17g %.17g\n", info.manifold_ratio, info.data_ratio);
    }
    fclose(out);
    cm_free(m);
    return 0;
}

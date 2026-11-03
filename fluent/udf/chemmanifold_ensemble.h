/*
 * A set of ChemManifold surrogates used as one model (docs/ENSEMBLE-ROADMAP.md).
 *
 * The ensemble file (chemmanifold_ensemble.txt, written by scripts/make_ensemble.py) lists member
 * model files (each an ordinary chemmanifold_model.txt from stage 12) and how to combine them:
 *
 *   blend mean   every member advances the cell; the result is the mean of their mass fractions
 *                (deep ensemble). The members' spread of T_out is returned as a disagreement signal.
 *   blend gate   each member owns a box in (T, c), with c = Yc / Yc_eq(Z) the normalised progress
 *                variable (Yc = sum of the listed species, Yc_eq from an adiabatic-equilibrium table in Z).
 *                The box edges are softened over a width: weights fall linearly to 0 across it, and are
 *                normalised to sum 1. Only members with a weight > 0 are evaluated, so a cell inside one
 *                box costs one network; a cell in an overlap costs two.
 *
 * Every member conserves elements and enthalpy, so a convex combination of their outputs does too;
 * T is solved from the blended Y at the cell's enthalpy with the first member's NASA-7 tables.
 * The gate reads the input state only.
 */
#ifndef CHEMMANIFOLD_ENSEMBLE_H
#define CHEMMANIFOLD_ENSEMBLE_H

#include "chemmanifold_core.h"

#ifdef __cplusplus
extern "C" {
#endif

#define CME_MAX_MEMBERS 16
#define CME_MAX_ZTAB 256

#define CME_BLEND_MEAN 0
#define CME_BLEND_GATE 1

/* Extra bit in cm_info.flags (outside CM_OOD_ANY): the gate found no member for the state and
 * fell back to equal weights. */
#define CME_NO_MEMBER 0x800

typedef struct cm_ensemble cm_ensemble;

/* Load an ensemble file; member paths are relative to the file's directory. NULL on failure. */
cm_ensemble *cme_load(const char *path, char *err, int errlen);
void cme_free(cm_ensemble *e);

int cme_n_members(const cm_ensemble *e);
int cme_n_species(const cm_ensemble *e);
const char *cme_species_name(const cm_ensemble *e, int k);
int cme_blend(const cm_ensemble *e);

/* Member i (owned by the ensemble: do not cm_free it). Member 0's species, NASA tables and dt range
 * stand for the ensemble (all members are checked to have the same species at load). */
cm_model *cme_member(const cm_ensemble *e, int i);

/* 1 if the file at path is an ensemble file (starts with chemmanifold_ensemble), else 0. */
int cme_is_ensemble_file(const char *path);

/* Gate weights of a state (sum 1); returns the number of members with weight > 0. Also gives Z and c. */
int cme_weights(const cm_ensemble *e, const double *Y, double T, double *w, double *Z, double *c);

/* OOD checks: the union of the flags of the members the gate uses (all members for blend mean). */
void cme_ood(const cm_ensemble *e, const cm_options *o, const double *Y, double T, double P, cm_info *info);

/* Advance Y in place over dt, as cm_advance. info->flags is the union of the used members' flags.
 * spread_T (may be NULL) receives the standard deviation of the members' T_out (0 for one member). */
int cme_advance(const cm_ensemble *e, const cm_options *o, double *Y, double T, double P, double dt,
                cm_info *info, double *spread_T);

#ifdef __cplusplus
}
#endif
#endif

/*
 * ChemManifold surrogate inference in plain C (no Fluent dependency).
 *
 * Mirrors chemmanifold/models.py and chemmanifold/physics.py: Box-Cox + z-score encoding,
 * the ResNet-FiLM or Phy-ChemNODE network, the abundance-weighted null-space projection and the
 * NASA-7 Newton temperature solver, plus out-of-distribution (OOD) checks against the training
 * data. The model file is written by scripts/12_export_fluent.py.
 *
 * All arrays use the model's species order (the mechanism's order). The Fluent wrapper
 * (chemmanifold_udf.c) maps Fluent's species onto it.
 */
#ifndef CHEMMANIFOLD_CORE_H
#define CHEMMANIFOLD_CORE_H

#ifdef __cplusplus
extern "C" {
#endif

#define CM_MAX_SPECIES 64
#define CM_MAX_ELEMENTS 8
#define CM_MAX_HIDDEN 512
#define CM_MAX_LATENT 32
#define CM_MAX_NAME 32

/* Bits of cm_info.flags. Bits 0-5 are OOD checks; the rest describe what the step did. */
#define CM_OOD_T        0x001  /* T outside the training T range (+- T_margin) */
#define CM_OOD_TZ       0x002  /* T outside the training T range of this mixture-fraction band */
#define CM_OOD_P        0x004  /* |P / P_ref - 1| > p_tol */
#define CM_OOD_SPECIES  0x008  /* some Box-Cox species value outside the training range (+- y_margin) */
#define CM_OOD_MANIFOLD 0x010  /* VQ-PCA reconstruction residual above its training 99.9% quantile */
#define CM_OOD_DATA     0x020  /* distance to nearest training landmark above its training 99.9% quantile */
#define CM_OOD_ANY      0x03f
#define CM_DT_CAPPED    0x040  /* dt needed more than max_substeps: chemistry advanced less than dt */
#define CM_FROZEN       0x080  /* T < T_freeze: not advanced (and no OOD bits set) */
#define CM_INVALID      0x100  /* non-finite surrogate output: state returned unchanged */
#define CM_DT_SCALED    0x200  /* dt < dt_min: increment over dt_min scaled linearly to dt */
#define CM_OOD_SKIPPED  0x400  /* OOD cell not advanced (ood_action = 1) */

typedef struct cm_model cm_model;

typedef struct {
    double T_freeze;      /* K; cells colder than this are not advanced (0 = advance all) */
    int max_substeps;     /* surrogate steps per call at most; dt beyond max_substeps*dt_max is cut */
    int ood_action;       /* 0 = flag only, 1 = do not advance cells with any OOD bit set */
    double T_margin;      /* K, tolerance on the T range checks */
    double y_margin;      /* tolerance on the species range check, in Box-Cox standard deviations */
    double p_tol;         /* relative pressure tolerance */
    int check_ood;        /* 0 skips the OOD checks (faster) */
} cm_options;

typedef struct {
    unsigned flags;
    int n_sub;              /* surrogate steps taken */
    double dt_sub;          /* their size [s] */
    double Z;               /* Bilger mixture fraction of the input */
    double manifold_ratio;  /* VQ-PCA residual / threshold (> 1 is off-manifold) */
    double data_ratio;      /* nearest-landmark distance / threshold (> 1 is far from data) */
    double hrr;             /* heat release rate per unit mass [W/kg] = -sum h_f,k dY_k/dt */
    double T_out;           /* temperature after the step [K] */
} cm_info;

void cm_default_options(cm_options *o);

/* Load a model file. Returns NULL on failure and writes a message into err. */
cm_model *cm_load(const char *path, char *err, int errlen);
void cm_free(cm_model *m);

int cm_n_species(const cm_model *m);
const char *cm_species_name(const cm_model *m, int k);
const char *cm_arch(const cm_model *m);
double cm_dt_min(const cm_model *m);
double cm_dt_max(const cm_model *m);
int cm_has_ood(const cm_model *m);

/* Mixture enthalpy [J/kg] of (Y, T) from the model's NASA-7 tables. */
double cm_enthalpy(const cm_model *m, const double *Y, double T);

/* Temperature [K] of (Y, h) by Newton iteration from T_init, as the training physics layer. */
double cm_temperature(const cm_model *m, const double *Y, double h, double T_init);

/* One surrogate step exactly as Surrogate.forward: (Y, T, P, h, dt) -> (Y_out, T_out). */
int cm_step(const cm_model *m, const double *Y, double T, double P, double h, double dt,
            double *Y_out, double *T_out);

/* OOD checks of a state; fills info->flags (OOD bits), Z, manifold_ratio and data_ratio. */
void cm_ood(const cm_model *m, const cm_options *o, const double *Y, double T, double P, cm_info *info);

/* Advance Y (in place) over dt at constant pressure and enthalpy, sub-stepping inside the
 * trained dt range. T is the input temperature. Returns 0 on success (including frozen and
 * skipped cells) and -1 if the surrogate output was invalid (Y is then left unchanged). */
int cm_advance(const cm_model *m, const cm_options *o, double *Y, double T, double P, double dt,
               cm_info *info);

/* Run the test vectors written by scripts/12_export_fluent.py (chemmanifold_tests.txt) with the
 * default options. Writes a one-paragraph report; returns the number of failed cases, or -1 if
 * the file cannot be read. */
int cm_selftest(const cm_model *m, const char *path, char *report, int len);

#ifdef __cplusplus
}
#endif
#endif

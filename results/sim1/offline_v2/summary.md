# Offline stage 18 benchmark vs protocol v2 (sim1, 21 Nov 2026)

Stage 18 (`scripts/18_offline_benchmark.py`) on the C3 state set: 218 Cantera states (6 families, state seed 12345), 2500 steps of 2e-5 s, surrogate alone and hybrid; 36 models (10 ensembles through the C ensemble code). Full tables: `benchmark.md`; per model: `offline_vs_protocol_v2.csv`; Spearman of every metric/family: `cfd_check.csv`.

Spearman rank correlation over the 20 models with a valid protocol v2 S (tix2_s1 invalid; models without their own protocol v2 run, e.g. tix2c_s0-2 and the C3/C3b repeats, are in the CSV without S). p = two-sided, n = 20.

| offline metric (all families) | rho vs S | p | rho vs flame dT | p | rho vs abs ignition shift | p |
|---|---|---|---|---|---|---|
| hybrid_dT_10ms | +0.36 | 0.115 | +0.43 | 0.061 | +0.13 | 0.572 |
| hybrid_inc_CO | -0.35 | 0.132 | -0.33 | 0.154 | -0.12 | 0.609 |
| alone_dT_10ms | +0.33 | 0.156 | +0.33 | 0.158 | +0.31 | 0.186 |
| alone_inc_OH | +0.32 | 0.164 | +0.32 | 0.162 | +0.33 | 0.156 |
| hybrid_dT_end | +0.32 | 0.171 | +0.35 | 0.130 | +0.11 | 0.645 |
| hybrid_fp_OH | +0.31 | 0.177 | +0.32 | 0.175 | +0.52 | 0.019 |
| alone_fp_OH | +0.31 | 0.179 | +0.32 | 0.166 | +0.59 | 0.007 |
| alone_drift100 | +0.29 | 0.213 | +0.31 | 0.185 | +0.25 | 0.287 |
| alone_rad_OH_1ms | +0.27 | 0.257 | +0.24 | 0.304 | +0.29 | 0.218 |
| alone_score | +0.24 | 0.308 | +0.28 | 0.237 | +0.41 | 0.073 |
| alone_dT_1ms | +0.22 | 0.352 | +0.18 | 0.443 | +0.35 | 0.127 |
| hybrid_inc_T | -0.20 | 0.405 | -0.14 | 0.548 | -0.19 | 0.421 |
| alone_rad_OH_10ms | +0.17 | 0.466 | +0.24 | 0.307 | +0.25 | 0.283 |
| hybrid_score | +0.17 | 0.482 | +0.21 | 0.380 | +0.26 | 0.267 |
| alone_inc_CO | -0.16 | 0.490 | -0.07 | 0.772 | -0.35 | 0.128 |
| alone_dT_end | +0.15 | 0.519 | +0.20 | 0.409 | +0.31 | 0.189 |
| alone_inc_H | -0.15 | 0.527 | -0.21 | 0.366 | +0.38 | 0.100 |
| hybrid_inc_OH | +0.14 | 0.548 | +0.13 | 0.574 | +0.40 | 0.083 |
| hybrid_drift100 | +0.14 | 0.562 | +0.19 | 0.415 | +0.04 | 0.863 |
| alone_fp_H | +0.14 | 0.569 | +0.05 | 0.840 | +0.30 | 0.204 |
| alone_inc_T | +0.12 | 0.627 | +0.20 | 0.387 | -0.00 | 0.990 |
| hybrid_inc_H | -0.11 | 0.631 | -0.16 | 0.490 | +0.27 | 0.242 |
| hybrid_rad_H_1ms | -0.11 | 0.640 | -0.06 | 0.801 | +0.32 | 0.176 |
| hybrid_dT_1ms | +0.09 | 0.701 | +0.08 | 0.753 | +0.32 | 0.176 |
| hybrid_rad_OH_1ms | +0.07 | 0.762 | +0.05 | 0.835 | +0.31 | 0.186 |
| hybrid_rad_OH_10ms | +0.06 | 0.791 | +0.15 | 0.514 | +0.18 | 0.459 |
| hybrid_fp_H | -0.04 | 0.880 | -0.12 | 0.622 | +0.41 | 0.072 |
| alone_ood_start | +0.03 | 0.914 | -0.01 | 0.967 | +0.56 | 0.010 |
| hybrid_ood_start | +0.03 | 0.914 | -0.01 | 0.967 | +0.56 | 0.010 |
| hybrid_ode_share | +0.02 | 0.925 | -0.02 | 0.950 | +0.59 | 0.007 |
| alone_fp_T | -0.01 | 0.970 | +0.04 | 0.875 | +0.25 | 0.296 |
| alone_rad_H_1ms | +0.00 | 0.995 | +0.05 | 0.826 | +0.40 | 0.079 |
| hybrid_fp_T | +0.00 | 0.995 | +0.07 | 0.758 | -0.27 | 0.250 |

Strongest single offline predictor of S: hybrid_dT_10ms (rho +0.36, p 0.115). With n = 20, |rho| > 0.44 is significant at p < 0.05.

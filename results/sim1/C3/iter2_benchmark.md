# Offline benchmark on Cantera states

218 states (equilibrium 40, cooled 36, lean_hot 40, vitiated 37, partial 28, flamelet 37), homogeneous constant-(p, h) reactors, 2500 steps of 2e-05 s (50 ms), state seed 12345. Physics only: no CFD state is used.

Columns: dT = mean |T_model - T_Cantera| [K] at 10 ms and at the end; drift = share off by > 100 K; inc = one-step relative error of the chemical increment (sum|err| / sum|true|, non-equilibrium states); rad = median |log10(Y_model/Y_Cantera)| at 1 ms (0.3 = x2, 1 = x10); fp = equilibrium states after the horizon: |T - T_eq| [K] and median |log10(Y/Y_eq)|. Seeds: mean [min, max]. Score = mean rank over inc_T, inc_OH, rad_OH_1ms, rad_H_1ms, fp_T, fp_OH, dT_10ms, dT_end (lower is better).

## Surrogate alone (as in Fluent)

| model | seeds | score | dT_10ms | dT_end | drift100 | inc_T | inc_OH | inc_H | rad_OH_1ms | rad_H_1ms | fp_T | fp_OH | fp_H | failed | ood_start |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| parent | 1 | 1.88 | 25 | 74 | 22% | 32% | 14% | 37% | 0.08 | 0.13 | 129 | 0.69 | 1.18 | 0.00 | 15% |
| iter2 | 1 | 2.50 | 32 | 116 | 29% | 47% | 15% | 38% | 0.13 | 0.19 | 50 | 0.47 | 1.16 | 0.00 | 11% |
| iter2_s1 | 1 | 2.75 | 55 | 97 | 24% | 68% | 11% | 32% | 0.11 | 0.19 | 82 | 0.51 | 0.91 | 0.00 | 11% |
| iter2_s2 | 1 | 2.88 | 33 | 82 | 33% | 30% | 17% | 32% | 0.12 | 0.20 | 63 | 0.99 | 1.54 | 0.00 | 11% |

## Hybrid (flagged steps to Cantera, as OpenFOAM userChemStep)

| model | seeds | score | dT_10ms | dT_end | drift100 | inc_T | inc_OH | inc_H | rad_OH_1ms | rad_H_1ms | fp_T | fp_OH | fp_H | failed | ode_share |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| parent | 1 | 1.62 | 17 | 39 | 14% | 15% | 9% | 14% | 0.06 | 0.10 | 36 | 0.60 | 1.01 | 0.00 | 20% |
| iter2 | 1 | 2.50 | 17 | 61 | 19% | 26% | 9% | 15% | 0.10 | 0.12 | 39 | 0.47 | 1.29 | 0.00 | 15% |
| iter2_s1 | 1 | 2.75 | 38 | 66 | 18% | 22% | 6% | 8% | 0.09 | 0.16 | 27 | 0.54 | 1.35 | 0.00 | 16% |
| iter2_s2 | 1 | 3.12 | 22 | 64 | 21% | 16% | 11% | 8% | 0.08 | 0.13 | 46 | 0.71 | 1.50 | 0.00 | 17% |

## States in each model's own data (surrogate alone, not flagged at the start)

| model | states | dT_10ms | dT_end | drift100 | inc_T | inc_OH | inc_H | rad_OH_1ms | rad_H_1ms | fp_T | fp_OH | fp_H |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| parent | 186 | 18 | 73 | 20% | 17% | 11% | 20% | 0.07 | 0.12 | 132 | 0.68 | 1.04 |
| iter2_s1 | 193 | 45 | 80 | 21% | 25% | 7% | 11% | 0.11 | 0.19 | 82 | 0.51 | 0.91 |
| iter2_s2 | 193 | 21 | 80 | 32% | 17% | 12% | 11% | 0.11 | 0.19 | 63 | 0.99 | 1.54 |
| iter2 | 193 | 31 | 118 | 26% | 28% | 10% | 21% | 0.13 | 0.19 | 50 | 0.47 | 1.16 |

## Per family (surrogate alone, mean over seeds)

| model | family | dT 10 ms | dT end | drift | inc T | inc OH | rad OH 1 ms | rad H 1 ms |
|---|---|---|---|---|---|---|---|---|
| parent | equilibrium | 28 | 129 | 30% | - | - | 0.08 | 0.16 |
| parent | cooled | 40 | 112 | 28% | 70% | 24% | 0.06 | 0.24 |
| parent | lean_hot | 0.19 | 0.62 | 0% | 21% | 15% | 0.46 | 0.41 |
| parent | vitiated | 17 | 128 | 35% | 227% | 33% | 0.23 | 0.36 |
| parent | partial | 76 | 68 | 46% | 80% | 4% | 0.02 | 0.03 |
| parent | flamelet | 6.15 | 11 | 0% | 5% | 9% | 0.03 | 0.04 |
| iter2 | equilibrium | 7.34 | 50 | 15% | - | - | 0.17 | 0.29 |
| iter2 | cooled | 63 | 171 | 33% | 139% | 21% | 0.20 | 0.36 |
| iter2 | lean_hot | 0.15 | 1.85 | 2% | 34% | 6% | 0.29 | 0.33 |
| iter2 | vitiated | 78 | 312 | 54% | 307% | 32% | 0.21 | 0.25 |
| iter2 | partial | 38 | 146 | 68% | 124% | 5% | 0.04 | 0.08 |
| iter2 | flamelet | 13 | 40 | 14% | 6% | 11% | 0.01 | 0.03 |
| iter2_s1 | equilibrium | 22 | 82 | 15% | - | - | 0.23 | 0.32 |
| iter2_s1 | cooled | 45 | 85 | 22% | 63% | 19% | 0.07 | 0.14 |
| iter2_s1 | lean_hot | 0.55 | 0.55 | 0% | 56% | 22% | 0.27 | 0.43 |
| iter2_s1 | vitiated | 148 | 196 | 49% | 416% | 25% | 0.17 | 0.16 |
| iter2_s1 | partial | 132 | 228 | 57% | 212% | 3% | 0.04 | 0.08 |
| iter2_s1 | flamelet | 9.60 | 29 | 11% | 5% | 7% | 0.01 | 0.02 |
| iter2_s2 | equilibrium | 19 | 63 | 25% | - | - | 0.41 | 0.53 |
| iter2_s2 | cooled | 28 | 73 | 44% | 135% | 23% | 0.09 | 0.27 |
| iter2_s2 | lean_hot | 5.97 | 0.78 | 2% | 79% | 19% | 0.34 | 0.45 |
| iter2_s2 | vitiated | 49 | 236 | 65% | 266% | 35% | 0.25 | 0.27 |
| iter2_s2 | partial | 114 | 100 | 64% | 64% | 5% | 0.02 | 0.07 |
| iter2_s2 | flamelet | 5.98 | 29 | 8% | 3% | 15% | 0.02 | 0.03 |


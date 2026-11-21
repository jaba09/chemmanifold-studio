# Offline benchmark on Cantera states

218 states (equilibrium 40, cooled 36, lean_hot 40, vitiated 37, partial 28, flamelet 37), homogeneous constant-(p, h) reactors, 2500 steps of 2e-05 s (50 ms), state seed 12345. Physics only: no CFD state is used.

Columns: dT = mean |T_model - T_Cantera| [K] at 10 ms and at the end; drift = share off by > 100 K; inc = one-step relative error of the chemical increment (sum|err| / sum|true|, non-equilibrium states); rad = median |log10(Y_model/Y_Cantera)| at 1 ms (0.3 = x2, 1 = x10); fp = equilibrium states after the horizon: |T - T_eq| [K] and median |log10(Y/Y_eq)|. Seeds: mean [min, max]. Score = mean rank over inc_T, inc_OH, rad_OH_1ms, rad_H_1ms, fp_T, fp_OH, dT_10ms, dT_end (lower is better).

## Surrogate alone (as in Fluent)

| model | seeds | score | dT_10ms | dT_end | drift100 | inc_T | inc_OH | inc_H | rad_OH_1ms | rad_H_1ms | fp_T | fp_OH | fp_H | failed | ood_start |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| parent | 1 | 2.00 | 25 | 74 | 22% | 32% | 14% | 37% | 0.08 | 0.13 | 129 | 0.69 | 1.18 | 0.00 | 15% |
| iter1_s1 | 1 | 2.00 | 25 | 69 | 24% | 68% | 11% | 32% | 0.10 | 0.17 | 49 | 0.54 | 1.22 | 0.00 | 10% |
| iter1 | 1 | 3.00 | 45 | 85 | 27% | 43% | 15% | 37% | 0.11 | 0.17 | 101 | 0.50 | 1.01 | 0.00 | 10% |
| iter1_s2 | 1 | 3.00 | 25 | 77 | 32% | 31% | 17% | 30% | 0.13 | 0.19 | 79 | 1.03 | 1.20 | 0.00 | 10% |

## Hybrid (flagged steps to Cantera, as OpenFOAM userChemStep)

| model | seeds | score | dT_10ms | dT_end | drift100 | inc_T | inc_OH | inc_H | rad_OH_1ms | rad_H_1ms | fp_T | fp_OH | fp_H | failed | ode_share |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| parent | 1 | 1.75 | 17 | 39 | 14% | 15% | 9% | 14% | 0.06 | 0.10 | 36 | 0.60 | 1.01 | 0.00 | 20% |
| iter1_s1 | 1 | 2.38 | 18 | 54 | 18% | 21% | 6% | 7% | 0.09 | 0.15 | 30 | 0.53 | 1.13 | 0.00 | 11% |
| iter1_s2 | 1 | 2.75 | 19 | 49 | 21% | 17% | 11% | 7% | 0.10 | 0.13 | 14 | 0.99 | 1.20 | 0.00 | 16% |
| iter1 | 1 | 3.12 | 30 | 57 | 18% | 24% | 9% | 15% | 0.10 | 0.12 | 56 | 0.46 | 1.14 | 0.00 | 14% |

## States in each model's own data (surrogate alone, not flagged at the start)

| model | states | dT_10ms | dT_end | drift100 | inc_T | inc_OH | inc_H | rad_OH_1ms | rad_H_1ms | fp_T | fp_OH | fp_H |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| iter1_s1 | 197 | 20 | 64 | 21% | 23% | 7% | 10% | 0.10 | 0.19 | 49 | 0.54 | 1.22 |
| iter1_s2 | 197 | 24 | 69 | 31% | 19% | 12% | 10% | 0.13 | 0.22 | 79 | 1.03 | 1.20 |
| parent | 186 | 18 | 73 | 20% | 17% | 11% | 20% | 0.07 | 0.12 | 132 | 0.68 | 1.04 |
| iter1 | 197 | 42 | 77 | 25% | 27% | 10% | 21% | 0.11 | 0.17 | 101 | 0.50 | 1.01 |

## Per family (surrogate alone, mean over seeds)

| model | family | dT 10 ms | dT end | drift | inc T | inc OH | rad OH 1 ms | rad H 1 ms |
|---|---|---|---|---|---|---|---|---|
| parent | equilibrium | 28 | 129 | 30% | - | - | 0.08 | 0.16 |
| parent | cooled | 40 | 112 | 28% | 70% | 24% | 0.06 | 0.24 |
| parent | lean_hot | 0.19 | 0.62 | 0% | 21% | 15% | 0.46 | 0.41 |
| parent | vitiated | 17 | 128 | 35% | 227% | 33% | 0.23 | 0.36 |
| parent | partial | 76 | 68 | 46% | 80% | 4% | 0.02 | 0.03 |
| parent | flamelet | 6.15 | 11 | 0% | 5% | 9% | 0.03 | 0.04 |
| iter1 | equilibrium | 78 | 101 | 30% | - | - | 0.15 | 0.26 |
| iter1 | cooled | 48 | 171 | 42% | 152% | 26% | 0.22 | 0.32 |
| iter1 | lean_hot | 0.23 | 0.25 | 5% | 25% | 11% | 0.28 | 0.44 |
| iter1 | vitiated | 85 | 98 | 35% | 329% | 32% | 0.13 | 0.17 |
| iter1 | partial | 53 | 149 | 50% | 101% | 4% | 0.06 | 0.04 |
| iter1 | flamelet | 11 | 13 | 5% | 6% | 9% | 0.01 | 0.03 |
| iter1_s1 | equilibrium | 7.61 | 49 | 18% | - | - | 0.20 | 0.35 |
| iter1_s1 | cooled | 11 | 46 | 22% | 68% | 18% | 0.08 | 0.19 |
| iter1_s1 | lean_hot | 0.90 | 0.71 | 0% | 32% | 13% | 0.19 | 0.34 |
| iter1_s1 | vitiated | 78 | 197 | 46% | 395% | 24% | 0.22 | 0.14 |
| iter1_s1 | partial | 56 | 117 | 57% | 212% | 3% | 0.06 | 0.09 |
| iter1_s1 | flamelet | 9.41 | 23 | 11% | 5% | 8% | 0.01 | 0.02 |
| iter1_s2 | equilibrium | 30 | 79 | 28% | - | - | 0.42 | 0.61 |
| iter1_s2 | cooled | 17 | 57 | 44% | 115% | 24% | 0.08 | 0.26 |
| iter1_s2 | lean_hot | 2.48 | 1.20 | 5% | 86% | 23% | 0.34 | 0.45 |
| iter1_s2 | vitiated | 62 | 197 | 65% | 220% | 36% | 0.33 | 0.35 |
| iter1_s2 | partial | 41 | 121 | 54% | 78% | 5% | 0.03 | 0.03 |
| iter1_s2 | flamelet | 5.02 | 21 | 3% | 3% | 13% | 0.02 | 0.04 |


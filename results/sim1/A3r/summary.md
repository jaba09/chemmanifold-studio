# A3r: cheap 2-step LeFoam flame with wall radiation, and stage 19 gate against R2 with radiation

11 Nov 2026, 13:50-15:55 CET, sim1, 4 ranks, about 1.75 s per LTS iteration. Same as A3 (`results/sim1/A3/summary.md`):
2-step Westbrook-Dryer CH4/air, LeFoam + constantLewis, LTS, Fluent DI start (CH4, O2, H2O, CO, CO2, N2). Plus the
radiation of A1r (`openfoam/quemadorUnico/enable_radiation.sh`: fvDOM, transparent gas, black walls, zero total flux on
Fluent's zero-flux walls, hood non-radiative), warm-started from the converged intensities. Settled at iteration 4000:
domain Tmax 2230 K, range 0.8 K over iterations 3000-4000. Then stage 19 (`--label A3r_wd2_lefoam_rad`). Only statistics
leave this step.

Note: the ray-solver tolerance was still 1e-4 in this run (the A1r stall fix came later). This is less of a concern under
LTS, where the radiation is re-solved every 10 of 4000 iterations from a slowly changing field.

## Statistics (reacting cells T > 600 K): A3r vs R2 with radiation (A1r, DI, mean state at 0.1875 s)

| Quantity | A3r p1 / p50 / p99 | R2rad p1 / p50 / p99 | A3 (no radiation) p50 |
|---|---|---|---|
| chi [1/s] | 1.8e-4 / 7.6e-3 / 3.0 | 1.8e-4 / 6.9e-3 / 2.9 | 1.9e-3 |
| strain [1/s] | 26 / 125 / 613 | 28 / 126 / 603 | 144 |
| psi | -0.012 / 0.383 / 0.75 | -0.049 / 0.363 / 0.751 | 0.101 |
| tau_cell [s] | 9.1e-6 / 4.6e-5 / 4.1e-4 | 9.1e-6 / 4.5e-5 / 4.1e-4 | 9.2e-5 |

Fluent DI (stage 19 on the corrected `.dat.h5`): psi p50 0.42, p99 0.758.

## Gate (stage 19 `compare`, factor 2 on p1/p50/p99, psi within 0.05)

| Reference | check | result | p1 | p50 | p99 |
|---|---|---|---|---|---|
| R2rad DI | chi at Z_st | pass | x1.62 | x0.97 | x1.23 |
| R2rad DI | tau_cell | pass | x1.00 | x1.02 | x1.00 |
| R2rad DI | strain at Z_st | pass | x0.90 | x0.90 | x0.85 |
| R2rad DI | psi | **pass** | +0.038 | +0.020 | -0.001 |
| Fluent DI | psi (A3r) | pass | -0.025 | -0.033 | -0.008 |
| Fluent DI | psi (R2rad) | fail (just) | -0.062 | -0.053 | -0.007 |

**A3r passes against R2 with radiation on every check, including psi, which failed by +0.04..+0.11 without radiation.**
Its psi is even closer to Fluent's than R2rad's. Age is not compared (the A1r case has no age function object).

Consequences for the next tix exploration (stage 20 from these statistics):
- The tau_cell band of hot cells is 9 us .. 0.41 ms with median 45 us (A3 without radiation: 9.5 us .. 0.2 ms,
  median 92 us).
- psi up to 0.75 is needed. tix2 already had burnt_relaxation.psi_max 0.80 and envelope psi_max 0.85, set from Fluent's psi.

Files: `stats.json`, `stats.png` (A3r), `R2rad_stats.json`, `gate_vs_R2rad.md`, `gate_vs_fluent.md`.

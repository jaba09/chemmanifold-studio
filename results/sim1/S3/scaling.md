# sim1 S3: smoke and scaling test

9 Nov 2026, 22:15-23:10 CET, sim1 (16 vCPU virtual Haswell, 1 thread per core, 62 GB), OpenFOAM v2412 (conda),
MPICH 4.3.2.

**Case.** Corrected burner (`openfoam/quemadorUnico`: top `outlet-lab` and chimney `wall-fff-fluid-exhaust`
open, r = 0.14 m side `outlet-lab-026` an adiabatic wall), mesh built from the corrected
`quemadorUnicoTesis_60KCells-GA18--ID.cas.h5` (63,087 cells, 5 deg wedge), GA18 (18 species),
`rhoReactingBuoyantLeFoam` with `constantLewis` (Sct 0.7). Start: converged Fluent DI field
(`.dat.h5`, 8572 it) mapped with `fluent_dat_to_foam.py` (Tmax 2087.5 K). Transient: Euler, fixed dt 2e-5 s,
PIMPLE 1 outer / 2 pressure correctors. DI: `ode` seulex, rtol 1e-5, atol 1e-10.
Timing: mean wall s/step over steps 11-50 (50-step runs) or 4-15 (15-step weight tests), nothing else running.

## Results (s/step)

| Run | Ranks | Decomposition | s/step |
|---|---|---|---|
| GA18 DI | 4 | scotch, cellWeight 25 for T > 800 K | 11.92 |
| GA18 DI | 8 | same | 8.77 |
| GA18 DI | 16 | same | 5.87 |
| GA18 DI | 4 | scotch, cellWeight 5 for T > 500 K | 12.13 |
| GA18 DI | 8 | same | 6.79 |
| GA18 DI | 12 | same | 5.13 |
| GA18 DI | 16 | same | 4.53 |
| Flow only (chemistry off) | 4 | 25 / 800 K | 1.17 |
| Flow only (chemistry off) | 16 | 25 / 800 K | 0.85 |
| userChemStep ood8_s0, pure | 4 | 25 / 800 K | 2.64 |

Weight tests at 16 ranks (T cut / weight -> s/step): 800/1 7.33, 800/3 4.74, 800/8 4.93, 800/25 5.87,
800/100 10.37, 1200/60 7.60, 400/6 5.78, 500/5 4.53, 500/8 4.53. Scotch's partitions are not smooth in the
weight, so differences under about 0.3 s/step are noise.

## Findings

- **Selftest 60/60** (ood8_s0: max |dY| 5e-16, max |dT| 2e-12 K vs PyTorch). Pure mode runs on the LeFoam
  solver; OOD under 1 % of advanced cells in the first 50 steps.
- **DI is slower than the roadmap assumed** (8 s/step on 2 ranks there; 12 s/step on 4 ranks here). Chemistry is
  about 10.7 s of the 11.9 s on 4 ranks.
- **The old weight (25 above 800 K) over-weights the hot cells on this flame.** The cold and warm cells cost more
  relative to the hot ones than the weight assumes: chemistry work grows from about 43 core-s/step on 4 ranks to about
  80 on 16. A weight of 5 above 500 K is about 25 % faster at 8-16 ranks. All sim1 runs now use 500 K / 5
  (`server/sim1/make_transient.sh`, override with TCUT/WEIGHT).
- **The flow solve does not scale** (1.17 -> 0.85 s/step from 4 to 16 ranks; about 4,000 cells per rank at 16, with
  18 species equations). The MPI transport makes no difference (FI_PROVIDER tcp, shm or unset: within 0.1 s).
- The surrogate's 2.64 s/step is mostly flow (1.2 s) and the per-cell surrogate cost on 4 ranks; it is 4.5x faster
  than DI at 4 ranks.

## Gate G0 and the rank decision

- Selftest passes, DI and surrogate both run with LeFoam: **pass**.
- DI at 8 ranks is 6.8 s/step, above the roadmap's 4 s/step threshold, so A1 would move to 16 ranks (4.5 s/step,
  12.6 h). Instead, **A1 runs on 12 ranks** (5.1 s/step, about 14.3 h for 10,000 steps). That costs about 1.7 h,
  and the other 4 cores run A2 and then A3 alongside it rather than after it.
- Measured s/step vs the roadmap estimates: DI about 1.5x slower per core. Surrogate (2.6 s on 4 ranks) is in the
  estimated range. A protocol v2 candidate (about 3,750 steps) costs about 2.7 h on 4 ranks, not 1.25 h. The B phase
  (6 runs) is about 6-8 h at 3 slots.

Scripts: `server/sim1/make_transient.sh`, `write_cell_weight.py`, `s3_scaling.sh`. Run dirs: `/opt/ofb/runs/s3/`.

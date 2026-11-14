# A3: cheap 2-step LeFoam flame and stage 19 flow statistics

Run 10 Nov 01:52-03:37 CET, 4 ranks, about 1.45 s/iteration. Corrected case, rhoReactingBuoyantLeFoam + constantLewis
(Sct 0.7), 2-step Westbrook-Dryer CH4/air (openfoam/timescale/reactions.2step, Fluent's methane-air-2step data),
LTS (localEuler, maxCo 0.5), from the Fluent GA18 DI field (CH4, O2, H2O, CO, CO2, N2 kept; the rest goes into N2).
Settled at iteration 4000: domain Tmax 2231-2232 K over iterations 3000-4000 (range 1.3 K; flat at about 2231 K since
iteration 1000). Then stage 19 (`scripts/19_flow_statistics.py case ... --time 4000 --label A3_wd2_lefoam`), reacting
cells T > 600 K (16,546 of 63,087). Only statistics leave this step.

| Quantity | p1 | p50 | p99 |
|---|---|---|---|
| chi | 4.6e-06 | 0.00189 | 0.995 |
| strain | 13.2 | 144 | 533 |
| age | 1.95 | 2.99 | 4.09 |
| psi | -0.0072 | 0.101 | 0.546 |
| theta | 0.461 | 0.886 | 1.08 |
| tau_conv | 0.000236 | 0.00105 | 0.00454 |
| tau_diff | 9.54e-05 | 0.00295 | 0.025 |
| tau_cell | 9.54e-06 | 9.17e-05 | 0.000197 |

Units: chi, strain 1/s; age, tau s; psi, theta dimensionless. The age is computed on the LTS flux field, so it is the steady-flow age, not the time since start.

**tau_cell band:** the hot-cell tau_cell is 9.5 us (p1) to 92 us (p50) and 197 us (p99). The old-case
band was 10 to 80 us, so the upper end is about 2.5x higher on the corrected LeFoam case, with the same lower edge. The gate
against R2's DI statistics (stage 19 `compare`) waits for A1.

Files: stats.json, stats.png (here); per-cell cells.npz on sim1 in data/timescale/A3_wd2_lefoam (not committed).

# ISANN with ARC_GRI30_NOx22: isann_arc22b

Run `/opt/ofb/run/isann_arc22b`: protocol v2 flame base (A1r state at 0.1 s, LeFoam + wall radiation), 0.1-0.15 s on 8 ranks; DI on the ARC kernel (libuserChemStepArc) until the daemon publishes a network, then the network in the cells it does not flag OOD or untrusted. Parent: `/opt/ofb/isann/parent_arc22b` (physics only; parent_arc22 = skel43 labels projected to 22 species, parent_arc22b = ARC labels). Reference: the ARC22 DI flame (`/opt/ofb/runs/arc22/flame`, same base; it crashed at 0.185 s, so 0.1-0.15 s is complete). Protocol v2 flame scores (`openfoam/protocol/score_protocol.py`, window 100.05-150 ms; ranks differ: the protocol's s/step are on 4 ranks, this run 8). Every CFD state is a diagnostic, never training data for the a priori models (ISANN's own online pairs are its method).

## Protocol v2 flame window (100-150 ms)

| metric | isann_arc22b vs ARC22 DI | earlier run (ISANN_ARC22) vs ARC22 DI | isann_arc22b vs GA18 DI (A1r) | ARC22 DI vs GA18 DI (A1r) | GA18 isann_v6 (pure) vs GA18 DI |
|---|---|---|---|---|---|
| flame mean abs dT (T > 1600 K) [K] | 5.2 | 7.3 | 31.9 | 33.3 | 5.8 |
| flame bias dT [K] | +1.9 | +0.3 | -31.1 | -33.0 | +3.6 |
| hot-cell mean abs dT [K] | 6.7 | 14.6 | 21.3 | 23.5 | 6.1 |
| hot-cell p95 abs dT [K] | 21 | 53 | 61 | 61 | 16 |
| hot volume ratio run/ref | 1.006 | 0.990 | 0.973 | 0.967 | 0.995 |
| OH L1 (hot cells) | 4.6% | 6.5% | 13.7% | 12.6% | 11.2% |
| OH total ratio | 1.01 | 0.99 | 1.06 | 1.05 | 0.97 |
| CO L1 (hot cells) | 11.0% | 13.4% | 11.9% | 7.2% | 14.3% |
| CO total ratio | 1.01 | 1.06 | 0.94 | 0.93 | 0.93 |
| HRR ratio (GA18 rates on each state) | 1.09 | 1.01 | 1.01 | 0.93 | 0.88 |
| DI (ODE) share reported by the solver | – | – | – | – | 0.0% |
| s per step | 6.47 | 5.87 | 6.47 | 11.15 | 2.09 |

## NOx in the hot cells, ISANN ARC22 vs ARC22 DI (volume-weighted, T > 600 K in either)

| species | total ratio mean (min-max) | L1 mean | L1 last 10 ms | earlier run: ratio / L1 mean / L1 last 10 ms |
|---|---|---|---|---|
| NO | 0.839 (0.686-1.000) | 23.4% | 35.8% | 1.288 / 47.6% / 76.0% |
| NO2 | 1.595 (0.890-2.225) | 80.4% | 120.0% | 3.146 / 250.3% / 115.7% |
| N2O | 1.759 (1.000-2.339) | 96.3% | 98.4% | 2.392 / 157.0% / 183.0% |
| HCN | 1.164 (0.830-1.606) | 53.1% | 80.7% | 4.299 / 343.4% / 759.7% |

20 common snapshots.

## Outlet NOx, mean over 0.1-0.15 s (weighted averages of the outletNOx function objects)

**outlet-lab** (250 / 250 samples)

| field | ISANN ARC22 | ARC22 DI | ratio |
|---|---|---|---|
| C2H2 | 3.18e-65 | 4.459e-64 | 0.071 |
| CO | 2.509e-17 | 2.502e-17 | 1.003 |
| CO2 | 2.238e-08 | 2.233e-08 | 1.002 |
| HCN | 1.807e-70 | 6.097e-70 | 0.296 |
| N2O | 9.503e-30 | 2.912e-29 | 0.326 |
| NO | 5.047e-52 | 1.612e-51 | 0.313 |
| NO2 | 1.121e-62 | 1.444e-61 | 0.078 |
| T | 305.5 | 305.5 | 1.000 |

**wall-fff-fluid-exhaust** (250 / 250 samples)

| field | ISANN ARC22 | ARC22 DI | ratio |
|---|---|---|---|
| C2H2 | 1.087e-59 | 2.939e-59 | 0.370 |
| CO | 1.037e-05 | 1.037e-05 | 1.000 |
| CO2 | 0.01749 | 0.01749 | 1.000 |
| HCN | 2.364e-60 | 6.195e-60 | 0.382 |
| N2O | 1.124e-26 | 3.102e-26 | 0.362 |
| NO | 1.384e-42 | 3.572e-42 | 0.387 |
| NO2 | 1.16e-44 | 1.183e-43 | 0.098 |
| T | 357.9 | 357.9 | 1.000 |

## ISANN rounds

Gate on held-out online pairs: one-step T MAE and 0D 2 ms rollout mean |dT| against the reference chemistry (current network -> candidate).

| round | step | why | online / replay pairs | one-step T MAE [K] | rollout mean [K] | failed rollouts | result |
|---|---|---|---|---|---|---|---|
| 1 | 5154 | saturated grid (new boxes 1.99% over 25 steps) | 17443 / 52329 | 1.39 -> 0.17 | 63.3 -> 2.6 | 52 -> 0 | accepted, v1 from step 5470 |
| 2 | 5572 | 7449 new pairs | 24892 / 60000 | 0.16 -> 0.12 | 1.9 -> 1.9 | 0 -> 1 | rejected |
| 3 | 6175 | 12969 new pairs | 37861 / 60000 | 0.16 -> 0.08 | 5.4 -> 1.7 | 9 -> 0 | accepted, v2 from step 6873 |

Final version: 2; daemon log: `/opt/ofb/run/isann_arc22b/isann/daemon.log`.

## DI share and cost (isann_report.py)

See `isann/isann_isann_arc22.md` and `.png`.
- label: isann_arc22b
- steps: 7500
- t_ms: 150
- di_phase_steps: 469
- first_switch_ms: 109.4
- ga18_share_total: 0.5113
- ga18_share_network_phase: 0.3984
- s_per_step_di_phase: 11.43
- s_per_step_network_phase: 5.945
- speedup_network_phase: 1.923
- wall_h: 4.841
- stored_pairs_end: 73785
- candidates: 18763579

## GA18 ISANN for context

- ISANN run 1 (GA18, 30 Oct, lit start 0-50 ms, 2 ranks, parent ood7): six accepted networks of 12 rounds; flame (T > 1600 K) mean |T - T_DI| 2.0-3.4 K at 25-50 ms, OH error 33-90 %; GA18 share 0.14-0.5 % of the hot cells with the network; 7.9 s/step DI, 4.2 s/step with the network (openfoam/isann/README.md).
- isann_v6 (that run's last network, frozen, pure mode) under protocol v2: column 4 above.

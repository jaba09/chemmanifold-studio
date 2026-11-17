# ISANN with ARC_GRI30_NOx22 (sim1, 17 Nov 2026)

Run `/opt/ofb/run/isann_arc22`: protocol v2 flame base (A1r state at 0.1 s, LeFoam + wall radiation), 0.1-0.15 s on 8 ranks; DI on the ARC kernel (libuserChemStepArc) until the daemon publishes a network, then the network in the cells it does not flag OOD or untrusted. Parent: `/opt/ofb/isann/parent_arc22` (configs/ch4_arc22.yaml, physics only, skel43 labels projected to 22 species). Reference: the ARC22 DI flame (`/opt/ofb/runs/arc22/flame`, same base; it crashed at 0.185 s, so 0.1-0.15 s is complete). Protocol v2 flame scores (`openfoam/protocol/score_protocol.py`, window 100.05-150 ms; ranks differ: the protocol's s/step are on 4 ranks, this run 8). Every CFD state is a diagnostic, never training data for the a priori models (ISANN's own online pairs are its method).

## Protocol v2 flame window (100-150 ms)

| metric | ISANN ARC22 vs ARC22 DI | ISANN ARC22 vs GA18 DI (A1r) | ARC22 DI vs GA18 DI (A1r) | GA18 isann_v6 (pure) vs GA18 DI |
|---|---|---|---|---|
| flame mean abs dT (T > 1600 K) [K] | – | 34.2 | 33.3 | 5.8 |
| flame bias dT [K] | – | -33.7 | -33.0 | +3.6 |
| hot-cell mean abs dT [K] | – | 33.8 | 23.5 | 6.1 |
| hot-cell p95 abs dT [K] | – | 96 | 61 | 16 |
| hot volume ratio run/ref | – | 0.957 | 0.967 | 0.995 |
| OH L1 (hot cells) | – | 17.9% | 12.6% | 11.2% |
| OH total ratio | – | 1.05 | 1.05 | 0.97 |
| CO L1 (hot cells) | – | 14.2% | 7.2% | 14.3% |
| CO total ratio | – | 0.99 | 0.93 | 0.93 |
| HRR ratio (GA18 rates on each state) | – | 0.93 | 0.93 | 0.88 |
| DI (ODE) share reported by the solver | – | – | – | 0.0% |
| s per step | – | 5.87 | 11.15 | 2.09 |

## NOx in the hot cells, ISANN ARC22 vs ARC22 DI (volume-weighted, T > 600 K in either)

| species | total ratio mean (min-max) | L1 mean | L1 last 10 ms |
|---|---|---|---|
| NO | 1.288 (1.000-1.637) | 47.6% | 76.0% |
| NO2 | 3.146 (0.996-7.912) | 250.3% | 115.7% |
| N2O | 2.392 (1.000-4.454) | 157.0% | 183.0% |
| HCN | 4.299 (0.953-9.206) | 343.4% | 759.7% |

20 common snapshots.

## Outlet NOx, mean over 0.1-0.15 s (weighted averages of the outletNOx function objects)

**outlet-lab** (250 / 0 samples)

| field | ISANN ARC22 | ARC22 DI | ratio |
|---|---|---|---|
| C2H2 | 2.026e-65 | – | – |
| CO | 2.533e-17 | – | – |
| CO2 | 2.249e-08 | – | – |
| HCN | 1.596e-70 | – | – |
| N2O | 5.938e-30 | – | – |
| NO | 3.345e-52 | – | – |
| NO2 | 4.505e-63 | – | – |
| T | 305.6 | – | – |

**wall-fff-fluid-exhaust** (250 / 0 samples)

| field | ISANN ARC22 | ARC22 DI | ratio |
|---|---|---|---|
| C2H2 | 6.81e-60 | – | – |
| CO | 1.037e-05 | – | – |
| CO2 | 0.01749 | – | – |
| HCN | 1.493e-60 | – | – |
| N2O | 7.015e-27 | – | – |
| NO | 8.778e-43 | – | – |
| NO2 | 4.394e-45 | – | – |
| T | 357.9 | – | – |

## ISANN rounds

Gate on held-out online pairs: one-step T MAE and 0D 2 ms rollout mean |dT| against the reference chemistry (current network -> candidate).

| round | step | why | online / replay pairs | one-step T MAE [K] | rollout mean [K] | failed rollouts | result |
|---|---|---|---|---|---|---|---|
| 1 | 5148 | saturated grid (new boxes 1.96% over 25 steps) | 15755 / 47265 | 1.24 -> 0.15 | 99.5 -> 27.0 | 65 -> 25 | accepted, v1 from step 5280 |
| 2 | 5380 | 11470 new pairs | 27225 / 60000 | 0.34 -> 0.14 | 110.0 -> 24.6 | 42 -> 16 | accepted, v2 from step 5463 |
| 3 | 5565 | 10378 new pairs | 37603 / 60000 | 0.14 -> 0.11 | 53.5 -> 5.6 | 23 -> 9 | accepted, v3 from step 5721 |
| 4 | 5826 | 7892 new pairs | 45495 / 60000 | 0.12 -> 0.09 | 21.7 -> 5.3 | 18 -> 7 | accepted, v4 from step 6015 |
| 5 | 6117 | 6511 new pairs | 52006 / 60000 | 0.09 -> 0.09 | 15.1 -> 15.1 | 18 -> 18 | rejected |
| 6 | 6291 | 2913 new pairs | 54919 / 60000 | 0.11 -> 0.08 | 18.5 -> 15.3 | 20 -> 11 | accepted, v5 from step 7052 |
| 7 | 7156 | 16183 new pairs | 71102 / 60000 | 0.12 -> 0.07 | 56.0 -> 20.3 | 29 -> 18 | accepted, v6 from step 7375 |

Final version: 6; daemon log: `/opt/ofb/run/isann_arc22/isann/daemon.log`.

## DI share and cost (isann_report.py)

See `isann/isann_isann_arc22.md` and `.png`.
- label: isann_arc22
- steps: 7500
- t_ms: 150
- di_phase_steps: 279
- first_switch_ms: 105.6
- ga18_share_total: 0.3132
- ga18_share_network_phase: 0.226
- s_per_step_di_phase: 13.85
- s_per_step_network_phase: 7.21
- speedup_network_phase: 1.922
- wall_h: 5.518
- stored_pairs_end: 96668
- candidates: 11443436

## GA18 ISANN for context

- ISANN run 1 (GA18, 30 Oct, lit start 0-50 ms, 2 ranks, parent ood7): six accepted networks of 12 rounds; flame (T > 1600 K) mean |T - T_DI| 2.0-3.4 K at 25-50 ms, OH error 33-90 %; GA18 share 0.14-0.5 % of the hot cells with the network; 7.9 s/step DI, 4.2 s/step with the network (openfoam/isann/README.md).
- isann_v6 (that run's last network, frozen, pure mode) under protocol v2: column 4 above.

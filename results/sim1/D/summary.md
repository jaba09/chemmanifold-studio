# Phase D: ISANN on the radiation reference (label isann, CFD-adapted)

sim1, 21 Nov 2026. Driver `server/sim1/d_isann.sh`, criteria `openfoam/isann/isann_D_tix2c.yaml` (run 1 criteria; parent
tix2c_s0 = member 0 of P_tix2c, the ITERML parent; 4 LeFoam ranks + 4 training threads). ISANN is the one method that
trains on the run's own GA18 (DI) pairs, so every model here is labelled `isann`.

- Leg 1 (ignition, protocol v2 lean start with radiation, 0-25 ms, 09:33-11:31 CET): DI phase 401 steps (8 ms, forced at
  max_steps), then networks v1-v3 (rounds 1-5, 3 accepted).
- Leg 2 (flame, A1r state at 0.1 s to 0.15 s, 11:35-13:45 CET): continued leg 1's archive and rounds, v3 loaded at the
  first step (no DI phase); rounds 6-12, 5 accepted (v4-v8). max_rounds 12 reached at 140.8 ms. GA18 share of the hot
  cells 3.7 % over the leg. Rounds and per-window shares: `isann_ign/`, `isann_flame/`.
- Final network v8 (33,159 online + 60,000 replay pairs; held-out one-step |dT| 0.044 K, OH 16 %, parent 0.73 K / 59 %),
  run in protocol v2 pure as `isann_D` (13:45-16:48 CET).

| Run | S | F (flame abs dT) | I (ignition) | C | drift [K/10 ms] | s/step (flame, 4 ranks) |
|---|---|---|---|---|---|---|
| **isann_D (v8, pure)** | **1.04** | 1.04 (5.2 K) | 0.67 (-0.2 ms) | 0.15 | +0.4 | 1.94 |
| isann_D online (the ISANN run itself) | 1.03* | 1.03 (5.2 K) | 0.00 | 0.24 | +0.3 | 2.11 |
| ISAT 1e-4 (E2) | 0.67 | | | | | |
| isann_v6 (old reference) | 1.16 | | | | | |
| P_tix2c (best physics-only) | 2.00 | 1.60 (8.0 K) | 2.00 (-0.6 ms) | 0.15 | | 3.66 |

\* flagged not valid by score_v2 only because the online run has no pure-mode OOD count (GA18 handles OOD cells); the
ignition of the online leg is on GA18 until 9.4 ms, so its I = 0 is by construction.

Flame abs dT against A1r (K, T > 1600 K):

| t [ms] | isann_D | isann_D online | isann_v6 | P_tix2c |
|---|---|---|---|---|
| 102.5 | 2.6 | 3.9 | 4.4 | 5.8 |
| 110 | 4.8 | 4.8 | 5.7 | 7.3 |
| 120 | 5.4 | 4.8 | 5.8 | 7.8 |
| 130 | 5.5 | 5.3 | 6.0 | 8.4 |
| 140 | 5.6 | 5.5 | 6.1 | 8.7 |
| 150 | 5.9 | 5.8 | 6.3 | 8.9 |

Reading: ISANN from the same physics-only parent as ITERML halves S (2.00 -> 1.04), with flat error growth (+0.4 K/10 ms)
and the fastest flame step of all networks (1.94 s/step, no OOD in pure mode). It sits just above the target (S 1) and
above ISAT 1e-4 (0.67), and it is CFD-adapted: trained on this flame's DI pairs, scored on the same flame.
Daemon fixes used here (in this branch): DI steps from the run's first step; current network = last accepted round;
header-only pair files skipped.

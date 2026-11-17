# C3: ITERML v2 on the radiation reference (tix2h family; iteration 0 = P_tix2c)

Settings frozen before the run: `configs/iterml/iterml_v2_tix2h.yaml`; driver `openfoam/iterml/iterml_v2.py`;
decisions in `DECISIONS.md`. Accept if the iteration's ensemble S < best S x 0.9. Stop at S <= 1, 2 rejections in a
row, or 6 iterations. CFD states are only seeds of Cantera exploration (never training pairs).

| Iteration | parent | collection (ign / flame legs) | seeds | seeded pairs | train pairs | gate (10 ms alone, parent 25.4 K) | S (F, I, C) | flame abs dT | ignition | decision |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 (P_tix2c) | - | - | - | - | 662,188 | - | 2.00 (1.60, 2.00, 0.15) | 8.0 K | -0.6 ms | baseline |
| 1 | 0 | 10.6 ms (15k-state cap) / 18 ms (model lost: OOD > 10 %) | 11,440 | 405,184 | 1,018,750 | s0 45.3 K FAIL, s1 25.5, s2 25.5 | 2.22 (2.22, 1.33, 0.14) | 11.1 K | +0.4 ms | rejected |

Iteration 1: ignition improved from -0.6 to +0.4 ms, but the flame got worse (8.0 -> 11.1 K, drift +1.3 K/10 ms), and
one repeat (s0) failed the offline gate. Iteration 2 restarts from iteration 0 (16 Nov 03:27 CET).

# C3: ITERML v2 on the radiation reference (tix2h family; iteration 0 = P_tix2c)

Settings frozen before the run: `configs/iterml/iterml_v2_tix2h.yaml`; driver `openfoam/iterml/iterml_v2.py`;
decisions in `DECISIONS.md`. Accept if the iteration's ensemble S < best S x 0.9. Stop at S <= 1, 2 rejections in a
row, or 6 iterations. CFD states are only seeds of Cantera exploration (never training pairs).

| Iteration | parent | collection (ign / flame legs) | seeds | seeded pairs | train pairs | gate (10 ms alone, parent 25.4 K) | S (F, I, C) | flame abs dT | ignition | decision |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 (P_tix2c) | - | - | - | - | 662,188 | - | 2.00 (1.60, 2.00, 0.15) | 8.0 K | -0.6 ms | baseline |
| 1 | 0 | 10.6 ms (15k-state cap) / 18 ms (model lost: OOD > 10 %) | 11,440 | 405,184 | 1,018,750 | s0 45.3 K FAIL, s1 25.5, s2 25.5 | 2.22 (2.22, 1.33, 0.14) | 11.1 K | +0.4 ms | rejected |

| 2 | 0 | 10.6 ms (15k-state cap) / 18 ms (model lost: OOD > 10 %) | 11,296 | 405184 | 1018750 | s0 32.1 K, s1 55.3 K FAIL, s2 33.1 K | 2.15 (2.15, 0.67, 0.15) | 10.7 K | +0.2 ms | rejected |

Iteration 1: ignition improved from -0.6 to +0.4 ms, but the flame got worse (8.0 -> 11.1 K, drift +1.3 K/10 ms), and
one repeat (s0) failed the offline gate. Iteration 2 restarted from iteration 0 (17 Nov 03:27 CET).

Iteration 2: ignition within target (+0.2 ms, I 0.67, the first a-priori-family ensemble to meet it since P_tix2h), but
flame abs dT 10.7 K (drift +1.8 K/10 ms) against 8.0 K for P_tix2c; one repeat (s1) failed the offline gate.

## Result: STOP after 2 rejections in a row (frozen rule, 17 Nov 16:32 CET). Best = iteration 0, P_tix2c (S 2.00).

What C3 showed:
1. **CFD-seeded physics exploration fixes the ignition term**: P_tix2c -0.6 ms -> iteration 1 +0.4 ms -> iteration 2
   +0.2 ms (on target). The seeds from the lean-start collection (the cells where the model and the shadow GA18 step
   disagree) are what the a-priori exploration missed.
2. **It costs flame accuracy every time** (8.0 K -> 11.1 / 10.7 K, with 3x more drift). The seeded pairs (about 40 %
   of the training set, capped at 35 % by the frozen rule) shift the warm-started networks away from the flame states.
   In both iterations one of the three repeats failed the offline gate (45-55 K vs the parent's 25 K).
3. So the ITERML loop trades one error for another instead of reducing S, and its frozen rules stop it. Changes worth
   testing (would need new frozen settings): a lower seeded share (e.g. 15-20 %), training from scratch instead of
   warm starts (warm fine-tuning was unstable here, as in the old reference), or seeding only the ignition leg.
4. Best physics-only model on the radiation reference: **P_tix2c, S 2.00** (flame 8.0 K, ignition -0.6 ms), against
   **ISAT 1e-4, S 0.67 at the same cost** (results/sim1/E2/long.md).

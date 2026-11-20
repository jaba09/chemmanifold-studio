# C3b: ITERML v2b (20 % seeded share, repeats from scratch): stopped, no model accepted

Settings `configs/iterml/iterml_v2b_tix2c.yaml` (frozen 17 Nov 23:20 CET), log `DECISIONS.md`. Iteration 0 = P_tix2c (S 2.00).
Stopped by the frozen rule (2 rejections in a row) on 19 Nov 21:59 CET. Best stays **P_tix2c, S 2.00**.

| Iteration | data | offline gate (dT10 ens / s1 / s2, parent 25.4 K) | S | flame abs dT | ignition | drift [K/10 ms] | decision |
|---|---|---|---|---|---|---|---|
| 0 P_tix2c | a-priori tix2c | - | 2.00 | 8.0 K | -0.6 ms | - | baseline |
| 1 | + 188,121 seeded (C3 iter 1 seeds) | 17.1 / 21.8 / 24.2 K, all pass | 6.86 | 34.3 K | **0.0 ms** | +25.5 | rejected |
| 2 | + 188,121 seeded (C3 iter 2 seeds) | 15.3 / 37.7 / 34.2 K, all pass | 16.80 | 84.0 K | +0.4 ms | +65.1 | rejected |

Training: 300 epochs from scratch, best epochs 290-298, val loss 0.0031-0.0040 (17-18 h per iteration, 3 repeats in parallel).

## Flame abs dT against A1r (K, T > 1600 K)

| t [ms] | P_tix2c | C3_iter1 (warm, 35 %) | C3b_iter1 | C3b_iter2 |
|---|---|---|---|---|
| 102.5 | 5.8 | 6.1 | **1.7** | 2.1 |
| 110 | 7.3 | 7.9 | **2.1** | 3.1 |
| 120 | 7.8 | 12.9 | **2.2** | 3.7 |
| 130 | 8.4 | 11.7 | 21.8 | 17.6 |
| 140 | 8.7 | 12.4 | 73.7 | 207.0 |
| 150 | 8.9 | 13.5 | 121.6 | 294.2 |

## Reading

- Up to about 122 ms the from-scratch ensembles are the most accurate networks so far: flame abs dT 1.7-2.2 K
  (iteration 1), 3-4x better than P_tix2c, CO/OH within 2-3 %; iteration 1 also hits the DI ignition time exactly.
- From about 125 ms both fail the same way: the error starts in the rich core (Z-rich zone bias -6 K at 125 ms ->
  -304 K at 135 ms, iteration 1) and the nozzle zone, then spreads into the flame. Iteration 2 also lights spurious heat
  release outside the flame (HRR outside 0.07 -> 31, a hot spot on the axis at 25-30 mm). The offline gate (10-step
  rollouts on 40 states) passed for every repeat, so it does not see this slow, coupled rich-side drift.
- The same failure in two independent iterations (different seeds and data) points to the recipe (from scratch with
  20 % seeded pairs) rather than chance: the warm-started C3 models kept the parent's rich-side behaviour and drifted
  only 1.3 K/10 ms.
- Possible next steps (not started): a longer offline/coupled gate on rich-core states; warm-start from a C3b repeat;
  or a short "rich-core" seeded leg. Waiting for Javier.

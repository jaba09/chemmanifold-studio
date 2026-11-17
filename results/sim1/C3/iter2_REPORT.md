# ITERML iteration 2

Updated 2026-11-17 16:32 CET.

- **collect**: done=2026-11-17 06:29 CET, ign_reason=15494 states stored (max 15000), ign_steps=533, ign_stored=15529, flame_reason=model lost: OOD share > 10% for 51 steps, flame_steps=5906, flame_stored=13299
- **seeds**: done=2026-11-17 06:31 CET, n_seeds=11296
- **explore**: done=2026-11-17 06:52 CET, seeded_pairs=405184
- **train**: done=2026-11-17 10:02 CET, s0={'best_val_loss': 0.006947313171941998, 'best_epoch': 37, 'wall_time_s': 10794.1}, s1={'best_val_loss': 0.0068233825885155005, 'best_epoch': 39, 'wall_time_s': 10781.3}, s2={'best_val_loss': 0.009971143041168922, 'best_epoch': 33, 'wall_time_s': 11285.0}
- **bench**: done=2026-11-17 10:07 CET, report=/opt/ofb/iterml_v2/iter2/bench/benchmark.md, dT10_parent=25.42, dT10_iter2=32.08, dT10_iter2_s1=55.27, dT10_iter2_s2=33.11, gate_iter2=pass, gate_iter2_s1=fail, gate_iter2_s2=pass
- **eval**: done=2026-11-17 16:32 CET, score=/home/ubuntu/chemmanifold-studio/results/sim1/C3/C3_iter2/score_v2.json

# ITERML seeds

Caught states: 28828; seed candidates 21805; after radius dedup (r = 0.1134): **11296 seeds** standing for 21805 states.

| regime | seeds | weight | T median K | Z median | psi median |
|---|---|---|---|---|---|
| 10 PaSR | 2575 | 4654 | 731 | 0.014 | 0.09 |
| 11 relaxation | 4971 | 10906 | 1850 | 0.056 | 0.08 |
| 12 ignition | 2276 | 3956 | 1353 | 0.080 | 0.11 |
| 13 cooling | 1474 | 2289 | 768 | 0.061 | 0.70 |

| flag | seeds |
|---|---|
| bin+err | 4132 |
| ood | 2168 |
| bin | 1917 |
| ood+err | 1640 |
| drift | 735 |
| err | 704 |

Shadow checks: 7172, failed 928 (12.9 %). Rollouts drifted: 889 (sentinels 680 of 1614).
Lean (Z < Z_st = 0.055) share of seeds: 46 %.

Seeds are starting points for Cantera reactors (stage 4 `pasr.seeded`); no state here is a training pair.


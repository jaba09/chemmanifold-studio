# ITERML iteration 1

Updated 2026-11-17 03:27 CET.

- **collect**: done=2026-11-16 18:31 CET, ign_reason=15454 states stored (max 15000), ign_steps=531, ign_stored=15492, flame_reason=model lost: OOD share > 10% for 58 steps, flame_steps=5911, flame_stored=13591
- **seeds**: done=2026-11-16 18:33 CET, n_seeds=11440
- **explore**: done=2026-11-16 18:54 CET, seeded_pairs=405184
- **train**: done=2026-11-16 21:52 CET, s0={'best_val_loss': 0.005691235398541778, 'best_epoch': 40, 'wall_time_s': 10530.5}, s1={'best_val_loss': 0.006600521704521531, 'best_epoch': 39, 'wall_time_s': 10567.6}, s2={'best_val_loss': 0.006450746385834171, 'best_epoch': 40, 'wall_time_s': 10579.8}
- **bench**: done=2026-11-16 21:57 CET, report=/opt/ofb/iterml_v2/iter1/bench/benchmark.md, dT10_parent=25.42, dT10_iter1=45.29, dT10_iter1_s1=25.47, dT10_iter1_s2=25.46, gate_iter1=fail, gate_iter1_s1=pass, gate_iter1_s2=pass
- **eval**: done=2026-11-17 03:27 CET, score=/home/ubuntu/chemmanifold-studio/results/sim1/C3/C3_iter1/score_v2.json

# ITERML seeds

Caught states: 29083; seed candidates 22095; after radius dedup (r = 0.1134): **11440 seeds** standing for 22095 states.

| regime | seeds | weight | T median K | Z median | psi median |
|---|---|---|---|---|---|
| 10 PaSR | 2657 | 4748 | 730 | 0.014 | 0.10 |
| 11 relaxation | 5066 | 11100 | 1846 | 0.056 | 0.08 |
| 12 ignition | 2271 | 3988 | 1353 | 0.080 | 0.11 |
| 13 cooling | 1446 | 2259 | 781 | 0.060 | 0.69 |

| flag | seeds |
|---|---|
| bin+err | 4269 |
| ood | 2195 |
| bin | 1964 |
| ood+err | 1524 |
| drift | 809 |
| err | 679 |

Shadow checks: 7218, failed 911 (12.6 %). Rollouts drifted: 979 (sentinels 761 of 1613).
Lean (Z < Z_st = 0.055) share of seeds: 47 %.

Seeds are starting points for Cantera reactors (stage 4 `pasr.seeded`); no state here is a training pair.


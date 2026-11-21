# C2: ignition-focused physics-only exploration from tix2h (tix2c)

15-16 Nov 2026, sim1, at most 8 cores. G2 decision (Javier, 15 Nov): tix2h is the parent family, ignition first.

**Exploration** (`configs/burner_openfoam_tix2c.yaml` = tix2h + ignition-focused changes; physics only, Cantera states):
- jet-induction mixing layer (regime 17): 150 runs (tix2h: 30), hot side = lean products Z 0.02-0.04 at 1200-1700 K
  against the cold CH4 jet: 162,600 pairs (tix2h: 31,680);
- vitiated ignition: 400 starts (tix2h: 160) on lean products;
- stage 23 committee round 1 from the tix2h s0-s2 models: 15,000 candidate states from 3,000 Cantera starts above
  800 K (3 ms rollouts). 2,654 were over the spread/drift threshold (10 K or x1.4 OH/H/CO), and the top 1,500 became
  Cantera trajectories: 35,856 pairs (regime 21);
- total 662,188 training pairs (tix2h: 388,128).

**Training:** 3 repeats (resnet_film, 300 epochs). They were restarted after the tmux crash of 15 Nov, and are now
resumable. The rollout-loss phase took about 210-640 s per epoch, because there are many more trajectories than in
tix2h. Registry: `burner_openfoam_tix2c[_s1,_s2]-resnet_film-20261115-*`. Offline T MAE (s0/s1/s2): tier 3
67.1/9.3/17.0 K, cooled 6.1/3.6/2.5 K, mixing 9.2/9.4/3.2 K, held-out flamelet coverage 95.9 %.

**CFD score: P_tix2c** = mean ensemble of the 3 repeats (selftest passed). Protocol v2 pure on A1r/A2r with radiation,
4 ranks. There were 2 shadow-DI FPE retries in the ignition phase (1.5 and 7.5 ms), handled by the runner.

| Model | S | F (flame abs dT) | I (ignition shift) | C | L1 OH / CO (flame) | OOD (flame) | drift [K/10 ms] | s/step |
|---|---|---|---|---|---|---|---|---|
| **P_tix2c** | **2.00** | 1.60 (8.0 K) | 2.00 (-0.6 ms) | 0.15 | 10.2 % / 5.9 % | 2.6 % | +0.5 | 3.66 |
| P_tix2h (parent family) | 2.97 | 2.97 (14.9 K) | 0.67 (+0.2 ms) | 0.61 | 23.4 % / 6.8 % | 0.8 % | +0.7 | 3.95 |
| P_mix (ood8 + tix2h, 6) | 2.05 | 2.05 (10.3 K) | 2.00 (-0.6 ms) | 0.50 | 18.9 % / 5.9 % | 7.0 % | +0.5 | 7.12 |
| P0_ood8 | 2.67 | 1.55 (7.8 K) | 2.67 (-0.8 ms) | 0.48 | 18.3 % / 4.4 % | 8.9 % | +0.1 | 4.09 |
| ISAT tol 1e-4 (E2, reference) | 0.67 | 0.18 (0.9 K) | 0.67 (-0.2 ms) | 0.01 | 0.8 % / 0.3 % | - | +0.2 | 3.65 |

**Findings**
1. **P_tix2c is the best physics-only model (S 2.00)**, at the cost of a 3-member ensemble. It beats its parent family
   by 33 % and P_mix (6 members, twice the cost) slightly.
2. **The ignition-focused data improved the flame, not the ignition.** Flame abs dT fell from 14.9 to 8.0 K and OH L1
   from 23 % to 10 %, but ignition moved from +0.2 ms (on target) to -0.6 ms. The induction-layer and committee states
   fill the lean, hot, partially mixed region where the flame sits, and that improved the flame. The ignition delay
   of the lean-start test is set by a few cells whose induction chemistry the networks still get early.
3. Ignition is the term that limits every physics-only model (I 2.0-2.7 except P_tix2h). ISAT 1e-4 still meets all
   targets at the same cost: the bar for C3.

**Next (C3):** ITERML iteration 0 = **P_tix2c**, as the frozen settings provide when C2 beats P_tix2h (S 2.00 vs
2.97). The parent members are tix2c s0-s2.

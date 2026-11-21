# sim1 campaign summary (9–21 Nov 2026)

This campaign was the full roadmap in `docs/SIM1-ROADMAP.md`, run on the OpenStack VM sim1 (16 cores). It stopped on 21 Nov 2026, when Javier chose to keep P_tix2c as the best physics-only model and write up. Every number below comes from the linked result files.

## 1. Reference flame (gates G1, A-phase)

| Step | Result | File |
|---|---|---|
| A1 R2, LeFoam constantLewis, corrected outlets, no radiation | **G1 failed**: V(T>1500) 54.8 vs Fluent 18.25 cm3 | `A1/G1.md` |
| Diagnosis | Fluent's DO model with transparent gas still has wall radiation. The pot bottom radiates about 25 W/rad (about 45 % of the fuel power). Imposing Fluent's wall T cut the hot volume 54.5 → 28 cm3 in 14 ms. | `A1w/wall_T_check.md` |
| A1r = R2 with fvDOM wall radiation (transparent gas, black walls, zero total flux on adiabatic walls) | **G1 passed**: V 19.95 vs 18.25 cm3, Tmax 2121 vs 2087.5 K, base 1.39 vs 1.15 mm, mean hot abs dT 52 K | `A1r/G1.md` |
| A2r ignition reference (lean phi 0.5 start) | DI ignites at 2.4 ms | `A2/summary.md` |
| A3r 2-step statistics gate | passes chi, tau, strain and psi. Hot tau_cell: p1 9 µs, p50 45 µs, p99 0.41 ms | `A3r/summary.md` |
| A4r steady LTS with radiation, from the Fluent field | settled at 3000 iterations, **passes G1**: V 19.62 cm3, Tmax 2117.7 K, abs dT 47.6 K; 17.6 h on 8 cores (without radiation the LTS run drifted to 60 cm3) | `A4r/summary.md` |

**Rule from now on:** every OpenFOAM burner reference needs wall radiation (`openfoam/quemadorUnico/enable_radiation.sh`, fvDOM tolerance 1e-6, hood baffle non-radiative).

## 2. Surrogates under protocol v2 (S = max(F, I, C), S ≤ 1 meets every target)

Pure mode, 4 ranks. Ignition is scored 0–25 ms against A2r; the flame is scored over 50 ms from A1r at 0.1 s. Targets: flame abs dT 5 K, ignition shift 0.3 ms, CO/OH within ×1.4.

| Model | S | Flame abs dT | Ignition shift | s/step | Notes | File |
|---|---|---|---|---|---|---|
| **ISAT tol 1e-4** (reference method) | **0.67** | 0.9 K | −0.2 ms | 3.65 | first method to meet every target | `E2/long.md` |
| isann_v6 (CFD-adapted, reference only) | 1.16 | 5.8 K | −0.2 ms | 2.1 | trained on DI data (ISANN exception) | `B/ranking_v2.md` |
| **P_tix2c** (mean of 3 tix2c) | **2.00** | 8.0 K | −0.6 ms | 3.66 | **best physics-only model** | `C2/summary.md` |
| P_mix (3 ood8 + 3 tix2h) | 2.05 | 10.3 K | −0.6 ms | 7.12 | | `B/G2.md` |
| tix2h_s0 | 2.35 | 11.8 K | +0.6 ms | 2.0 | best single network | `B/ranking_v2.md` |
| P0 (3 ood8) | 2.67 | 7.8 K | −0.8 ms | 4.1 | | `B/G2.md` |
| P_tix2h (3 tix2h) | 2.97 | 14.9 K | +0.2 ms | 4.0 | | `B/G2.md` |
| ISAT tol 1e-3 | 3.33 | 2.9 K | −1.0 ms | 2.96 | | `E2/long.md` |
| P_tix2all (3 tix2) | 4.47 | 22.3 K | −0.4 ms | 4.0 | | `B/G2.md` |
| Single models in phase B | 4.6–14.1 | | | ~2 | tix2_s1 crashed alone | `B/ranking_v2.md` |

Findings:
1. **Ensembles always beat their family mean and stabilise every member**, but each member costs about 1 s/step. Repeats of the same recipe that share the same error (tix2) gain nothing in flame accuracy.
2. **All physics-only models ignite early from the lean start**, except P_tix2h. The ignition-focused exploration in C2 (more jet-induction states plus a committee round) improved the flame (14.9 → 8.0 K) but not ignition.
3. **CFD-seeded physics exploration (ITERML, C3)** fixes ignition (−0.6 → +0.2 ms) but costs flame accuracy (8 → 11 K). One of three warm-started repeats failed the offline gate in each iteration. C3 stopped after 2 rejections (S 2.22, 2.15). See `C3/progress.md`.
4. **From-scratch training with a 20 % seeded share (C3b)** gave the most accurate networks so far up to about 122 ms: flame 1.7–2.2 K, CO/OH within 2–3 %, ignition exactly on DI. After that, a slow cold drift in the rich core under the nozzle spreads into the flame (S 6.86, 16.80). The 10-step offline gate cannot see this drift. See `C3b/summary.md`.

## 3. Cost (phase E, 200 steps from A1r, 4 ranks)

| Case | s/step | Chemistry speed-up vs DI | Hot abs dT after 4 ms |
|---|---|---|---|
| Flow + radiation only | 1.32 | – | – |
| GA18 DI | 13.63 | 1.0× | 0 |
| DI with Treact 600 K | 12.62 | 1.1× | 0.26 K |
| ISAT 1e-3 / 1e-4 / 1e-5 | 2.92 / 3.73 / 6.89 | 7.7× / 5.1× / 2.2× | 1.41 / 0.85 / 0.67 K |
| tix2h_s0 | 2.05 | 16.9× | 4.68 K |
| P_mix | 8.95 | 1.6× | 3.08 K |

- Chemistry is about 90 % of a DI step. The flow plus radiation floor caps any chemistry method at about 10× on the whole step.
- DI's cost sits in the 14.6k hot cells, so a cold-cell cutoff saves only 8 %.
- ISAT's table settles in under 1 ms (about 2,900 leaves at 1e-4, 89–90 % retrieves).
- **On GA18 (18 species), at matched accuracy, ISAT beats every network.** A network pays off only if it reaches about ISAT 1e-4 accuracy at single-network cost, or for larger mechanisms (GRI-3.0: ISAT's table grows with (n_species+2)², while a network's cost barely changes). See `E/cost.md` and `E2/long.md`.

## 4. Open items (not started)

- A longer coupled gate on rich-core states, plus warm-starting from a C3b repeat. This is the most promising route to beat P_tix2c.
- Phase D: ISANN on the radiation reference, needed to revise the ISANN vs ITERML paper.
- ISAT and ISANN with GRI-3.0 / ARC22, running in their own threads.
- sim1 disk: about 11 GB free. Phase B/E field snapshots in `/opt/ofb/runs` (52 GB) can be trimmed, keeping scores and logs, once Javier OKs it.

Operational lessons: run long jobs as systemd user units, not inside tmux (the tmux server segfaulted on 15 Nov and killed every session). Make every training resumable (`07_train --resume`). Each protocol v2 candidate leaves about 1.2–1.6 GB once cleaned.

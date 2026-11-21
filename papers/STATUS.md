# Paper plan and status (TODO list)

Started 16 Nov 2026 (Spain time, CET) from Javier's approved 8-paper list. This file is the single
place that tracks every paper: what exists, where it lives, what blocks it and what is next.
Update it whenever a draft or a result changes.

**Standing rules for every paper**

- Training data of the surrogate comes **only** from physics-based exploration of the thermochemical
  space. CFD/DI states may be used as seeds (ITERML), for diagnosis and for evaluation, never as
  training pairs. The single exception is ISANN, where training on the run's own DI pairs is the
  method itself; ISANN models must always be labelled "CFD-adapted".
- Every CFD number before 5 Nov 2026 was produced on the burner case with the **wrong outlets**
  (side open, top and chimney closed) and, before 10 Nov, **without wall radiation**. Papers must use
  the corrected case (protocol v2: LeFoam + constantLewis + fvDOM wall radiation, A1r/A2r references)
  or say explicitly which case a number comes from.
- sim1 campaign closed 21 Nov 2026: summary `results/sim1/SUMMARY.md` (branch `claude/project-thread-mq77al`, commit 53d6f21; Library `chemmanifold/sim1/SUMMARY.md`). **Best physics-only model = P_tix2c (S 2.00, flame 8.0 K, ignition -0.6 ms, 3.66 s/step).**
- Reference for "good enough" in the CFD: **ISAT 1e-4, protocol v2 score S = 0.67** (flame 0.9 K,
  ignition -0.2 ms, 3.65 s/step on 4 ranks, ~3.7x faster than GA18 DI). Every surrogate paper must
  state where it stands against it.
- English, elsarticle LaTeX (unless a journal needs otherwise), figures from scripts in the paper folder.

## Overview

Suggested order: **1, 2, 5 first**, then 3, 7, 6, 4, 8.

| # | Working title | Target journal | Status | Draft location | Blocking |
|---|---|---|---|---|---|
| 1 | Physics-only exploration of the thermochemical space for neural chemistry surrogates | Combustion and Flame (alt. Energy and AI) | **Outline** (this PR) | `papers/p1-physics-exploration/OUTLINE.md` | Coverage results done (ood8 + tix2c); ready to draft |
| 2 | ISANN vs ITERML: where should a surrogate's training data come from? | Combustion and Flame (alt. Energy and AI) | **Draft v1** (protocol v1, old outlets) + revision outline (this PR) | `papers/isann-vs-iterml/` on PR #20 (branch `claude/project-thread-uzvup8`); outline `papers/p2-isann-vs-iterml/OUTLINE.md` | All results in (phase D: isann_D S 1.04); ready to revise draft v1 |
| 3 | State Y(t+dt) vs increment dY, dT network outputs | Combustion and Flame | **Draft v0** | `papers/y-vs-dy/` on PR #23 (branch `claude/project-thread-6ik60m`) | Per-species weighted dY loss test; rerun on corrected case |
| 4 | One network or several? Single ANN vs ensemble / mixture of experts | Combustion and Flame | **Draft v0** (3 Nov) | `papers/single-vs-multiple-ann/` on branches 04fho7, mq77al, ... | Ensemble research (PR #21); add protocol v2 C4 results (P0, P_mix, P_tix2h) and repeat variance |
| 5 | A CFD evaluation protocol for chemistry surrogates (offline benchmarks do not predict CFD ranking) | Combustion and Flame or Combust. Theory Model. (alt. Energy and AI) | **Outline** (this PR) | `papers/p5-cfd-protocol/OUTLINE.md` | Spearman done, n = 20 (no offline metric predicts S); ready to draft |
| 6 | Same flame, two codes: OpenFOAM vs Fluent differences | Combust. Theory Model. or Flow Turb. Combust. | Material only | results in Library `fluent-vs-openfoam-simple/`, `comparacion-T-openfoam-fluent/`, sim1 A1/A1r G1 | Fluent F1/F2/F3 reruns at dt 1e-4; write outline |
| 7 | 22-species ARC from GRI-Mech 3.0 in a laminar burner | Combustion and Flame or Fuel | **Two drafts** (Claude Docs) | https://claude.ai/artifact/RjFHRJUX3q3qmztavmHjWT and https://claude.ai/artifact/RpamXr1iSLYWMr9eVUakDh | Same-code OpenFOAM GRI-53 leg (~06 CET Tue 17 Nov); ARC ignition leg (Tue); choose one draft |
| 8 | Reduced mechanism and coverage-hole exploration methods | later | Ideas only | memory `reduced-mechanism`, hole methods doc https://claude.ai/artifact/W8RXBwYEJpXiqN8THz4Eb7 | Hole methods M1-M7 runs (PR #27) |

## Per paper

### 1. Physics-only thermochemical-space exploration (core methods paper)
- Story: how to build training data for a chemistry surrogate from the mechanism and the stream
  physics alone (flamelets, strain, 0D, PaSR, recirculation, unsteady flamelets, equilibrium tails,
  vitiated ignition, burnt relaxation, flow-statistics bounding, hole sets, committee sampling), and
  how CFD may steer it (OOD/hole maps) without ever becoming training data.
- Next: see `p1-physics-exploration/OUTLINE.md` section "Missing results".

### 2. ISANN vs ITERML
- Draft v1 exists (abstract and all sections; iteration 2 as negative result). All its CFD numbers
  are protocol v1 on the old-outlet case.
- New since the draft: ISANN v6 on protocol v2 S 1.16 (best surrogate, CFD-adapted); ITERML iteration
  3 and the automatic rules (`openfoam/iterml/rules.py`); ITERML v2 on the corrected case done (C3:
  ignition fixed -0.6 -> +0.2 ms but flame 8 -> 11 K, stopped after 2 rejections, S 2.22 / 2.15;
  C3b from-scratch with 20 % seeded share: flame 1.7-2.2 K and ignition on DI up to ~122 ms, then a
  rich-core cold drift, S 6.86 / 16.80, invisible to the 10-step offline gate). Phase D (ISANN on R2)
  still missing.
- Next: see `p2-isann-vs-iterml/OUTLINE.md`.

### 3. Y(t+dt) vs dY, dT outputs
- Draft v0 on PR #23. Finding: dY output is as good in the flame but CO x8-30 and OH x2.5-15 in lean
  burnt gas 600-1600 K, because the loss on physical increments ignores tiny minor-species increments.
- Next: per-species relative weighting of the dY loss (proposed, not run); rerun both on the corrected
  case; cite ISAT 1e-4 as the bar.

### 4. Single ANN vs ensemble / MoE
- Draft v0 from 3 Nov (old case). Protocol v2 C4 now gives the strongest evidence: ensembling is the
  biggest single gain (P0 2.67 vs members 4.67-14.14; P_mix 2.05 best physics-only), but costs ~2-3.5x
  per step. Repeat spread (1.7-9.5 in S) is larger than family differences.
- Next: wait for the ensemble research to finish (Javier's TODO), then update with C4 and C2.

### 5. CFD evaluation protocol for chemistry surrogates
- Story: one-step and offline errors do not rank surrogates the way the CFD does; a fixed, versioned
  CFD protocol (ignition phase + flame phase, single score S, pure mode, repeats) does, and ISAT gives
  the reference line.
- Next: see `p5-cfd-protocol/OUTLINE.md`.

### 6. OpenFOAM vs Fluent
- Material: OpenFOAM species diffusion is Sc = 1 (rho D = mu) vs Fluent kinetic theory; Fluent DO
  radiation radiates from the pot bottom even with transparent gas (+25 W/rad, ~45 % of fuel power);
  outlet BCs; Fluent dt <= 1e-4 needed (dt 1e-3 gives an artificial lift-off); steady pseudo-transient
  artefact (Tmax 3100 K). After fixes OpenFOAM vs Fluent GA18 hot |dT| ~48-52 K.
- Next: outline after papers 1, 2, 5.

### 7. ARC 22 from GRI-Mech 3.0
- Two drafts kept on purpose (Javier, 15 Nov). Final burner numbers filled: ARC (OpenFOAM) vs Fluent
  GRI hot |dT| 38.6 K against a 48.8 K code-to-code baseline; NO max 2.48e-4 vs 2.47e-4.
- Next: add OpenFOAM GRI-53 same-code leg and the ignition leg, then merge into one draft.

### 8. Reduced mechanism + hole-exploration methods
- Later. Depends on M1-M7 runs and the DRGEP -> QSSA roadmap.

## Change log
- 2026-11-16: file created; outlines for papers 1, 2 and 5 added.
- 2026-11-21: phase D done (isann_D S 1.04 vs ITERML C3 2.22/2.15, same parent family).
- 2026-11-21: sim1 offline_v2 (n = 20 Spearman, tix2c regime coverage) added; phase D started.
- 2026-11-21: coverage ablation (paper 1) and offline-vs-v2 Spearman (paper 5) added under papers/data/; phase D and the sim1-only benchmarks asked of the sim1 thread.
- 2026-11-21: sim1 campaign results added (P_tix2c S 2.00, C3/C3b, cost study).

# ChemManifold research report

As of 8 Nov 2026. Living version (Claude Doc): https://claude.ai/artifact/PDFXzqjrPVGDx3cCoCgsHv

## Executive summary

The goal of this project is to replace the stiff ODE integration of CH4/air chemistry (GA18 mechanism, 18 species) inside a CFD solver with a trained neural network (ANN surrogate) that jumps a cell's state from t to t + dt in one cheap call. After 18 days (21 Oct to 8 Nov 2026), we have surrogates that reproduce the burner flame temperature within 2 to 4 K of direct integration (DI) over 50 ms in a transient OpenFOAM run, at roughly half the cost per step. No surrogate is yet robust everywhere, and the reference flame itself turned out to be less solid than we thought.

**What worked**

- A physics-only exploration of the thermochemical space (0D reactors, PaSR ensembles, steady and unsteady flamelets, heat loss, recirculation, equilibrium tails, vitiated ignition, burnt-gas relaxation) is enough to train a ResNet-FiLM network that holds the flame. The best a priori model, ood8, gives a flame error of 3.4 K at 50 ms when 1.6 % of cells fall back to GA18.
- Online learning (ISANN, the one place where training on the run's own DI pairs is allowed) gave the best pure result: 2.1 K flame error over 25 to 50 ms with no GA18 fallback.
- The ITERML loop (CFD states used only as starting states for new physics exploration) reached 3.3 K pure in iteration 1 and removed the early nozzle ignition.
- Averaging three independently trained networks (deep ensemble P0) cut the pure flame error of ood8 from 24 K to 4.4 K and its out-of-sample share from 58 % to 0.4 %, at 2.9 times the cost.

**What did not work**

- Every pure a priori model ignites the fuel jet too early (about 1 ms before DI) or too late, and lean burnt gas keeps CO and OH errors of 2 to 30 times.
- Offline certification and the offline Cantera benchmark do not predict the CFD ranking. Training noise between repeats is as large as the differences between the top models.
- Equilibrium fixed-point and relative radical losses improved one-step chemistry but made the coupled flame worse (constant cold bias of 7 to 24 K).
- dt as an input over a wide range (1 us to 50 ms), increment outputs (dY), and chaining fixed-timestep models all made the flame worse.
- Phy-ChemNODE (latent neural ODE) was unstable on this flame.

**Big caveats.** All CFD results before 5 Nov 2026 used a Fluent case with wrong outlet boundary conditions. Separately, the OpenFOAM DI flame that served as the reference for most tests differs strongly from Fluent DI (mean |dT| 418 to 552 K in hot cells), most likely because OpenFOAM's species diffusion uses Sc = 1. The surrogate-vs-DI comparisons are internally consistent (same solver, same case), but the reference flame is not the Fluent flame.

## 1. Goal and problem statement

The main goal is to embed the chemistry into an ANN so that a CFD simulation integrates chemistry faster, without losing the flame. In a finite-rate reacting solver with operator splitting, each cell's chemistry step solves a stiff ODE system at constant pressure and enthalpy:

```latex
\frac{dY_k}{dt} = \frac{W_k\,\dot{\omega}_k(Y, T, p)}{\rho}, \qquad h(Y, T) = \text{const}, \qquad p = \text{const}, \qquad t \in [t_n, t_n + \Delta t]
```

The surrogate replaces this integration with a map F(Y, T, p, dt) giving Y(t + dt) in one call. T is recovered from enthalpy by the CFD solver, so element conservation and the energy balance stay with the solver.

**Why it matters.** With GA18 and Cantera CVODES, one cell step of 10 to 100 us costs 590 to 900 us of CPU on one core, against about 155 us for the surrogate (measured 24 Oct). In the OpenFOAM burner, DI costs 5.0 s per flow step against 1.9 s for a pure surrogate run.

**Target system.**

| Item | Value |
| --- | --- |
| Mechanism | GA18: 18 species, 92 reactions, no C2 and no N chemistry |
| Flame | Non-premixed CH4/air laminar-like burner, 2D axisymmetric, about 63k cells, about 340 W |
| Streams | CH4 and air at 300 K, 1 atm; air O2 = 0.21 by mole (Y_O2 0.233, Z_st about 0.055) |
| State ranges | T 300 to about 2120 K, mixture fraction Z 0 to 1 |
| Chemistry step | Fluent's tau_cell = 0.1 min(t_diffusion, t_convection); hot cells 1 us to 0.6 ms in OpenFOAM DI |
| CFD codes | Fluent 2026 R1 Student (Javier's PC, 4 cores), OpenFOAM v2412 (cloud, 4 cores) |

The research question underneath, in Javier's words, is a procedure to (1) explore the physically feasible thermochemical space of a given kinetics system and (2) represent that data with machine learning, so the surrogate is built from the chemistry and the boundary physics, not from a particular CFD solution.

## 2. Ground rules and caveats

Three rules shaped every experiment, and two caveats limit what the CFD numbers mean.

**Rules**

1. **Training data comes only from physics-based exploration** (rule set 27 Oct). Coverage gaps are fixed by changing the exploration (bounds, starting states, heat-loss model, reactor types), never by training on Fluent or OpenFOAM DI states. Training on the run's own DI pairs was explicitly allowed only for ISANN (30 Oct); ISANN models are labelled as CFD-adapted in the registry. ITERML uses CFD states only as starting states for new physics exploration, and the CFD state itself is excluded from training.
2. **Periodic DI shadow checks** (rule set 29 Oct). Every surrogate run integrates a sample of cells with GA18 now and then, spread over T x Z x (inside/out of sample) bins, and saves the comparison. These data are for comparison only.
3. **Per-cell dt.** The dt the surrogate must handle is the chemistry step per cell (tau_cell), not the global flow step. During runs we store a histogram of tau_cell, not the values.

**Caveats**

- **Wrong outlets before 5 Nov 2026.** The Fluent case used until then had the top outlet and the chimney closed and the side open. Javier corrected it on 5 Nov (top and chimney open, side a wall). Every CFD result dated before 5 Nov, in Fluent and in OpenFOAM, used the wrong outlets. Near the burner the Fluent flame barely changed (mean |dT| 4 K under the pot), so relative comparisons between surrogates and DI on the same case remain meaningful, but absolute flame data are not those of the real burner.
- **OpenFOAM DI is not Fluent DI.** On identical meshes, the old OpenFOAM DI flame is a lifted hot pocket with 5 times the volume above 1500 K (mean |dT| 552 K in hot cells). After the outlet fix, OpenFOAM is bistable (start-dependent), and even its attached state differs from Fluent (418 K). The likely cause is OpenFOAM's species diffusion, rho D_k = mu + mu_t for all species (Sc = 1). Surrogate tests compare against the OpenFOAM DI run of the same case, so they measure surrogate error, not agreement with Fluent.

## 3. Methods

The pipeline (scripts 00 to 22 in this repository) explores the space with Cantera, builds (state, dt, state after dt) pairs, trains a network, certifies it offline, exports it to a C file read by a Fluent UDF or an OpenFOAM library, and scores it in CFD against DI.

### 3.1 Exploration of the thermochemical space

Each pair carries a regime label. The regimes were added one by one, each in response to a failure seen in CFD.

| Regime | What it samples | Added because |
| --- | --- | --- |
| 0 | 0D adiabatic ignition from mixtures over Z and progress | Base pipeline (21 to 23 Oct) |
| 1 | PaSR: static same-Z mixing ensembles | Base pipeline |
| 2 | Steady counterflow flamelet states, strain 0.6 to about 1200 1/s | Base, widened in the strain exploration (29 Oct) |
| 3 | 0D wall-cooled gas, heat-loss fraction psi up to 0.85 toward 300 K | 27 % of Fluent hot cells were out of sample (27 Oct) |
| 4 | Recirculation: hot products mixed into pure fuel or air | Products mixed into the jets collapsed (28 Oct) |
| 5 | Unsteady flamelets: extinction, reignition, cooling, strain jumps | Strain exploration (29 Oct) |
| 6 | 0D equilibrium tails (30 ms) | Flame core 35 K cold, OH 2x (ood1, 29 Oct) |
| 7 | Vitiated ignition | Early jet ignition near the nozzle (ood4, 30 Oct) |
| 8 | Burnt-gas relaxation, then a lean set | Radicals pumped into lean burnt gas (ood7, ood8, 30 Oct) |
| 9 | Equilibrium as a fixed point, perturbed equilibrium | Near-equilibrium radical errors (eqfp, 30 Oct) |
| 10 to 14 | Seeded dynamic PaSR (IEM), relaxation, ignition, cooling, flamelets from CFD starting states | ITERML (1 Nov) |

The timescale variant (tix1, 5 Nov) bounds the exploration with flow statistics (Z, psi, scalar dissipation, strain, tau_cell) from a cheap 2-step-chemistry flame, checked against DI statistics. Only statistics pass to the exploration, never states.

### 3.2 Networks

- **ResNet-FiLM** (the workhorse): residual MLP whose layers are modulated by dt and pressure (FiLM), predicting Box-Cox-scaled outputs; latent dimension 8 to 12 chosen by VQ-PCA. Trained with a short rollout (pushforward) loss.
- **Phy-ChemNODE**: a latent neural ODE with physics layers (float64). Tested several times and dropped as unstable.
- **Variants tried**: dt as an input over a wide range with per-dt loss; increment outputs dY and dT; fixed-point and relative radical losses; deep ensembles (mean of 3 repeats) and gated experts; five fixed-dt models chained in a ladder.

### 3.3 Coupling to CFD

- **Fluent**: DEFINE_CHEM_STEP UDF (fluent/udf, C core chemmanifold_core.c), self-test of 60 cases, OOD flags in UDMs and a monitor CSV.
- **OpenFOAM v2412**: userChemStep library using the same C core, with an optional GA18 fallback for out-of-sample cells (hybrid mode), DI shadow sampling, tau_cell histogram and a T_freeze below which cold cells are skipped.
- **Out-of-distribution (OOD) detection**: input-state checks against T-Z boxes, species bounds and the distance to data landmarks. In hybrid mode an OOD cell is integrated by GA18 instead.

### 3.4 Evaluation

- **Offline certification** (tiers 1 to 3): one-step R2 and T error, 0D ignition delay and final T, cooled-gas and mixing tests.
- **Stage 17 local stability**: closed-loop 0D rollouts from sampled hot DI cells.
- **Stage 18 offline benchmark**: 218 to 440 Cantera states (equilibrium, cooled, lean hot, vitiated, partial, flamelet), 2500 steps of 20 us, with 3 training repeats per model.
- **CFD protocol v1** (30 Oct): OpenFOAM transient from a lit start (lean phi 0.5 burnt gas at 1480 K), dt 2e-5 s, scored in two phases: start-up 0 to 5 ms (ignition time) and flame 25 to 100 ms (mean |dT| for T > 1600 K, drift, OH/CO/H errors, heat release, GA18 share). **Pure mode** (no GA18 fallback) is the headline, because Fluent has no hybrid mode.
- **Steady test 6b** (5 to 6 Nov): local-time-stepping run from a converged DI field with the chemistry step equal to tau_cell, scored after 1500 iterations against a DI run of the same start.

## 4. Timeline

The work moved through five phases: pipeline (21 to 23 Oct), Fluent coupling (24 to 28 Oct), the OpenFOAM OOD loop (28 to 31 Oct), learning strategies (30 Oct to 3 Nov) and the reference and timescale checks (5 to 7 Nov). Dates are in Spain time; listed oldest first so it reads as a story.

| Date (2026) | Step | One-line outcome |
| --- | --- | --- |
| 21 Oct | Pipeline scripts 01 to 10 from the ChemManifold Studio spec, H2/air test | Works; ResNet-FiLM drifts on long equilibrium tails |
| 22 Oct | OpenFOAM conversion of the Fluent burner (PR #1); CH4/GRI-3.0 trial | Case converted; GRI-3.0 rollouts collapse to 280 K |
| 23 Oct | Switch to Fluent; sample the burner flame with GA18 (PR #2) | ResNet-FiLM certified (tier 3 tau error 9 %); Phy-ChemNODE unstable |
| 24 to 26 Oct | Fluent UDF, OOD tracking, GA18 DI case (PRs #3 to #5) | Surrogate 155 us vs CVODES 590 to 900 us per cell step |
| 27 Oct | First Fluent surrogate run (PR #6) | UDF compiles, self-test 60/60; 27 % of hot cells OOD rising to 50 % in 19 steps |
| 27 to 28 Oct | Non-adiabatic and recirculation explorations, model registry (PR #7) | Cooled-gas error 277 K to 5.9 K; mixing 50 K to 15 K, but no single winner |
| 28 to 29 Oct | OpenFOAM DI and pure surrogate runs (PRs #8, #9) | Tmax right, flame base creeps to nozzle, hot-cell error 75 to 97 K |
| 29 Oct | Coverage-gap map (PR #10), strain exploration and stage 17 (PR #11), unity-Lewis config (PR #12) | OOD on DI 23 % to 0 to 7 %; one-step increment error still 50 to 80 % |
| 29 to 31 Oct | OOD-driven loop, ood1 to ood8 (PR #17) | Best ood8 hybrid 3.4 K at 50 ms; early nozzle ignition traced to radicals in lean start gas |
| 30 Oct | Critical review; CFD protocol v1 (PR #13); offline benchmark with repeats (PR #14) | Benchmark does not predict CFD; training noise as large as model gaps |
| 30 to 31 Oct | Equilibrium fixed point and radical loss (PR #15) | Better one-step radicals, worse coupled flame (cold bias) |
| 30 Oct to 1 Nov | ISANN online learning (PRs #16, #18), LTS steady test, article draft | Best result: v6 pure 2.1 K; LTS within DI's own drift |
| 1 to 2 Nov | ITERML loop and automatic rules (PR #19); ISANN vs ITERML paper (PR #20) | iter1 3.3 K pure; iter2 worse (6.6 K); iter3 fixes ignition and CO but OH x2.3 |
| 2 Nov | ISANN with dY, dT outputs | Flame as good, lean burnt gas CO x8 to 30 |
| 2 to 3 Nov | Ensemble vs single ANN roadmap, E0 to E4 (PR #21) | P0 deep ensemble pure 4.4 K vs single 24 K, 2.9x cost |
| 3 Nov | Y(t+dt) vs dY paper draft (PR #23); rented-server guide (PR #22); reduced-mechanism brainstorm | Drafts and plans only |
| 5 Nov | Timescale roadmap (tix1); outlet BC error found; OpenFOAM vs Fluent T maps | tix1 lean CO x2 vs ood8 x22, flame 28 to 34 K vs 23 K; references found inconsistent |
| 5 to 6 Nov | OpenFOAM with corrected outlets | OpenFOAM bistable; neither state matches Fluent |
| 6 Nov | Five fixed-dt models and ladder test (PR #24) | Ladder worse (67 K or flame lost) than single tix1 (35 K) |
| 6 to 7 Nov | Why Fluent and OpenFOAM differ: simple coflow flame | Sc = 1 gives a lifted, superadiabatic flame; Lewis-number solvers give an attached steady flame |

## 5. Results

The best surrogate for the transient flame is ISANN v6 (2.1 K pure), followed by ITERML iter1 (3.3 K pure), ood8 hybrid (3.4 K) and the P0 ensemble (4.4 K pure); ood8 alone in pure mode gives 24 K. "Flame error" is the mean absolute difference between surrogate and DI temperature over cells above 1600 K. All rows in 5.1 to 5.3 used the old (wrong) outlets; 5.4 says which case each row used.

### 5.1 Fluent era (a priori models, old outlets)

| Trial | Test | Key number | Verdict |
| --- | --- | --- | --- |
| burner_fluent_air (ResNet-FiLM) | Fluent transient from DI state, dt 4e-5 s | 27 % of hot cells OOD at step 0, 50 % by step 19 | Bad: drift out of sample |
| Rich-weighted retrain | Closed-loop 0D | Much worse than parent | Discarded |
| Non-adiabatic exploration | Cooled-gas test, 9 cases | Mean T MAE 277 K down to 5.9 K | Good |
| Recirculation exploration | Products mixed into jets | 50 K down to 15 K, but cooled gas 13.5 K and rich Z 0.088 60 to 140 K low | Mixed |
| Non-adiabatic, pure, OpenFOAM transient | 50 ms vs DI | Tmax 2043 vs 2041 K; hot-cell error 75 to 97 K; OH x2; flame base creeps to nozzle | Bad |
| Strain exploration (05a0ee02) | Stage 17 on DI cells | OOD 0 %, 10 ms error 13 K (was 36 K); one-step increment error 67 % | Partly good |

### 5.2 OpenFOAM OOD loop (a priori models, transient, old outlets)

| Model | Mode | Flame error | Other | Verdict |
| --- | --- | --- | --- | --- |
| unityle (iteration 1) | Hybrid | About 35 K cold in the flame core | OH x2, CO x1.4; GA18 0.3 to 1.4 % | Bad |
| ood1 | Hybrid | 3 to 6 K at 25 to 50 ms | GA18 0.1 to 1 % | Good |
| ood1 | Pure (protocol v1) | 8 K at 10 to 17 ms, then -71 K at 32.5 ms | Ignites 1.6 ms early; OH x4 to 20 | Bad |
| ood2 (dt 1 us to 50 ms) | Hybrid | 15 K | Wide dt range | Bad |
| ood3 (+ per-dt loss) | Hybrid | 24 to 57 K | GA18 0.8 % | Bad |
| ood5 | Hybrid | Lean burnt gas cools | | Discarded |
| ood8 | Hybrid + GA18 in induction cells | 3.4 K at 50 ms | GA18 1.6 % | Best a priori |
| ood8 | Pure | 24 K | Ignition 1.37 vs 2.45 ms; OH and CO x5; OOD 58 % | Bad |
| eqfp8 (fixed-point + radical loss) | Hybrid | 13.3 K, constant -13 K bias | Best one-step shadow error (T 4 %, OH 1 %) | Bad in CFD |
| eqfp8_fp / eqfp8_low / eqfp_scratch | Hybrid | 7.3 / 13.2 / 24 K | GA18 14 / 3.8 / 11 % | Bad |
| Phy-ChemNODE (ood7n, 6 substeps) | Hybrid | 38 K at 25 ms | 2-substep version: ignition delay +1100 % | Bad |

### 5.3 Learning strategies (transient, old outlets)

| Trial | Mode | Flame error | Other | Verdict |
| --- | --- | --- | --- | --- |
| ISANN run 1 (online, DI start) | Hybrid | 2 to 3.4 K at 25 to 50 ms | OH 33 to 90 %; GA18 0.14 to 0.5 %; 4.2 vs 7.9 s/step | Good |
| ISANN v6 | Pure | 2.1 K | Ignition 2.2 vs 2.6 ms (+251 K at 2.5 ms); OH x0.55 | Best overall |
| ISANN3 (restart from v6) | Hybrid | About v6 | 0/5 retrains accepted; misses early ignition | Neutral |
| ISANN2 (no DI phase) | Hybrid | 7 to 12.6 K | Start-up 47 K | DI phase is worth it |
| ISANN LTS steady | Hybrid | 40 to 48 K | Smaller than DI's own drift (100 K); CO x2.7; GA18 5 to 7 % | Inconclusive |
| ISANN with dY, dT outputs | Hybrid | 1.3 to 3.7 K | Lean burnt gas CO x8 to 30, OH x2.5 to 15; GA18 5x run 1 | Bad for minor species |
| ITERML iter1 | Pure | 3.3 K | Early ignition gone, ignition 0.6 ms late; CO x1.66 rising | Good |
| ITERML iter2 | Pure | 6.6 K | CO x6.4 in cooled lean gas; benchmark ranked it better | Bad |
| ITERML iter3 (2 training repeats) | Pure | 3.1 K | Ignition and CO fixed; OH x2.2 to 2.55; score 2.45 to 2.52 vs 2.22 | Rejected by rules |
| P0 deep ensemble (3 x ood8) | Pure | 4.4 K | OOD 0.4 % vs 58 %; ignition 1.55 vs 2.45 ms; 2.9x cost | Partial go |
| P1 gated experts, warm start | Offline | 31 vs 25 K at 10 ms | Warm fine-tuning degrades rollouts | No-go |
| P1 gated experts, from scratch | Offline, 3 repeats | 29/58 K vs ood8 37/78 K | Ranges overlap | Inconclusive |

### 5.4 Timescale-bounded exploration and fixed dt (steady test 6b)

| Trial | Case | Flame error | Other | Verdict |
| --- | --- | --- | --- | --- |
| ood8, pure | Old outlets | 23 K | Lean CO x21.7; OOD 28 to 37 % | Reference |
| tix1, pure, 3 training repeats | Old outlets | 28 to 34 K | Lean CO x1.5 to 2.9; OOD 1 to 4 % | Better minor species, worse flame T |
| tix1, pure | Corrected outlets | 35 K | Lean CO x0.89; OOD 4 to 5 % | Good on lean gas |
| ood8, pure | Corrected outlets | 33 K | Lean CO x8; OOD 55 to 66 % | Bad on lean gas |
| Ladder 1e-4 + 1e-5 | Corrected outlets | 67 K | Lean CO x64; OOD about 70 % | Bad |
| Ladder + 1e-6 | Corrected outlets | Flame mostly lost (-711 K) | 1e-6 model one-step error 85 to 156 % | Bad |

### 5.5 Reference flame checks

| Check | Result |
| --- | --- |
| OpenFOAM DI vs Fluent DI, old outlets | Lifted pocket vs attached sheet; 88.6 vs 18.2 cm3 above 1500 K; mean hot-cell difference 552 K |
| OpenFOAM DI, corrected outlets | Two states depending on the start; the attached one is still 418 K from Fluent |
| Fluent transport | Flame nearly laminar (median mu_t/mu 0.01); DO radiation inactive (absorption 0) |
| Simple coflow flame, OpenFOAM | Sc = 1: lifted, 2230 to 2380 K, 448 cm3, never steady. Unity Lewis: 2216 K, 39 cm3. Constant Lewis: 2107 K, 37 cm3. Both steady |
| Simple coflow flame, Fluent | Pending (Javier's PC went offline) |

## 6. Negative results, honestly

Most of what we tried did not improve the coupled flame, and several fixes that looked right offline made it worse. These are the ones a reviewer should hear about.

1. **Offline quality does not predict CFD quality.** ood1 had the worst tier-3 error (59.8 K) but the best early CFD result; ood4 had the best tier 3 (10.6 K) and 14.5 K in CFD. The stage 18 benchmark rank correlation with CFD fell from 0.68 (218 states) to 0.28 (440 states). It ranked ITERML iter2 better than iter1 (22.9 vs 31.8 K) when the CFD said the opposite. It only flags clearly bad models such as Phy-ChemNODE.
2. **Training noise is as large as the model differences.** Three training repeats of ood1 spread 33 to 60 K, and of ood6 22 to 62 K, in the 10 ms benchmark error. Most single-run rankings in sections 5.2 and 5.3 are therefore not statistically settled.
3. **Pure a priori models fail at ignition and in lean burnt gas.** The fuel jet ignites about 1 ms early near the nozzle, because the network pumps OH and H into the hot lean start gas (OH 10 to 17 times, H about 1000 times DI). Fixing the start-gas radicals (regime 8) was necessary but not sufficient. ood8 pure gives 24 K with 58 % of cells out of sample.
4. **Physically motivated losses hurt the coupled flame.** The equilibrium fixed-point and relative radical losses cut one-step errors (OH 2.5 times closer) but produced a steady cold bias of 7 to 24 K and up to 14 % GA18 fallback.
5. **dt as a wide-range input hurts.** ood2 and ood3 (dt 1 us to 50 ms) were 15 and 24 to 57 K, against 3 to 6 K for ood1 at a few fixed strides. tix1 (dt 10 to 840 us) improved lean CO but was worse in the flame (28 to 34 vs 23 K).
6. **Chaining fixed-dt models fails.** The 1e-6 s model's one-step increment errors were 85 to 156 %, and errors add up over 2 to 5 calls per cell. The ladder lost the flame.
7. **Increment outputs (dY, dT) hurt minor species.** A loss on physical increments ignores tiny radical increments: lean burnt gas CO 8 to 30 times DI.
8. **ITERML is not monotone.** Iteration 2 was worse than iteration 1 (6.6 vs 3.3 K) because a seeding bug gave it no new pairs and an absolute CO threshold (5e-5) hid a CO excess of 100 times in cooled lean gas. Iteration 3 fixed ignition and CO but not OH and was rejected by the codified rules. The automatic rerun was stopped on 2 Nov before it was scored.
9. **The early-warning checks miss problems.** OOD flags and shadow DI checks did not catch the early nozzle ignition in ISANN3 or ITERML; the generic multi-step sentinel is not selective (21 % flagged).
10. **Warm-start fine-tuning degrades rollouts.** Gated experts and fine-tuned controls started from ood8 were worse than ood8 itself.
11. **Phy-ChemNODE never became stable** on this 18-species flame (ignition +260 % at tier 2, +1100 % in CFD).
12. **The reference is the weakest link.** The OpenFOAM DI flame used as truth for every OpenFOAM test is a different flame from Fluent DI, with wrong outlets until 5 Nov, and probably wrong species diffusion (Sc = 1). Our surrogate numbers measure fidelity to that reference, not to the physical burner.
13. **Speed is not yet a clear win.** At 40 us the surrogate is 4 to 6 times cheaper per cell than CVODES, but at a 1 ms step it is slower (surrogate 4.1 ms per cell with 25 substeps, CVODES 1.6 ms). The P0 ensemble costs 2.9 times a single network. Most of DI's cost in the burner is in 41k cold cells that a temperature cutoff would also skip.

## 7. Lessons learned

1. **Score in coupled CFD, in pure mode, for at least 50 ms.** Offline metrics are useful only to throw out clearly bad models. 25 ms is too short: ood6 looked fine at 25 ms and drifted to 23 K by 47 ms.
2. **Always train more than one repeat.** Rank models on the mean of 2 to 3 training repeats, and accept a new model only if it beats the best by more than the spread (the elitism rule coded in ITERML).
3. **The remaining error is near-equilibrium chemistry precision, not coverage.** Once regimes 3 to 8 were in, out-of-sample shares on DI states were a few percent, yet OH and CO errors stayed large in hot lean gas, where tiny radical increments drive slow relaxation.
4. **Small one-step errors are not enough; their sign and accumulation matter.** A bias of a few percent in the radical increment, repeated every 20 us, produces early ignition or cold flames. Tests must look at multi-step behaviour per region (start gas, jet induction zone, flame, lean burnt gas).
5. **Averaging independent networks works.** The deep ensemble reduced error and out-of-sample drift at once, and the members' disagreement predicts the error (rank correlation 0.67 to 0.83 at 1 ms), so it can serve as a built-in OOD signal.
6. **Some DI is cheap insurance.** A 1 to 2 % GA18 fallback (hybrid) turns 24 K into 3.4 K for ood8. ISANN's initial DI phase was worth keeping (7 to 12.6 K without it vs 2 to 3.4 K with it). Fluent has no hybrid mode, though, so pure performance is what counts there.
7. **Use a narrow dt range matched to the flame.** Hot-cell tau_cell sits mostly at 10 to 80 us; spreading data over 1 us to 50 ms dilutes it.
8. **Physics-only exploration can reach the flame.** ITERML iter1 (3.3 K pure) is close to ISANN v6 (2.1 K pure), which learned from the run's own DI data. The methodology rule costs little accuracy.
9. **Verify the reference before tuning against it.** We spent most of the CFD effort against an OpenFOAM flame that later proved to differ from Fluent and from the corrected case. Check boundary conditions, transport model and steadiness first.
10. **Infrastructure matters.** Cloud jobs die after 2 h and containers restart when idle, so every run was made resumable and relaunched by a supervisor. Training is about 60 % of an iteration's time; more cores for parallel training repeats would help before any GPU.

## 8. Open questions and next steps

The first job is to fix the reference flame; only then is it worth re-ranking surrogates.

**Open questions**

- Does the Fluent simple coflow flame (runs F1 unity Lewis and F2 burner transport) confirm that Sc = 1 is what separates OpenFOAM from Fluent?
- Which reference should the papers use: Fluent DI of the corrected case, or OpenFOAM DI with a Lewis-number species diffusion solver?
- Do the best models (ISANN v6, ITERML iter1, P0, tix1) keep their ranking on the corrected outlets and corrected transport?
- Is the ignition error a coverage problem (jet induction states never sampled) or a precision problem (radical increments)?
- Is NO a goal? GA18 has no N chemistry, so NO would need a larger mechanism or a separate model.
- Can the surrogate beat a tuned Fluent ISAT, which is what reviewers will compare against?

**Next steps (recommended order)**

1. Finish the Fluent F1/F2 simple-flame runs on Javier's PC.
2. If confirmed, rerun the OpenFOAM burner DI with the constant-Lewis solver (rhoReactingBuoyantLeFoam) and the corrected outlets, and check it converges to one state that matches Fluent.
3. Re-score the leading models on that reference with protocol v1 (pure, 50 to 100 ms, 2 training repeats each), plus the steady test 6b.
4. Run the best candidates in Fluent itself (transient, dt 4e-5 s, then steady with tau_cell), since Fluent is the target code.
5. Combine what worked: a P0 ensemble built from ITERML iter1 or tix1 repeats, with dt restricted to the flame's 10 to 80 us band.
6. Target the jet induction zone: more vitiated and partially mixed ignition starting states in the physics exploration, and a sentinel test on ignition delay.
7. Add an ISAT baseline and a cost study at matched accuracy, including cold-cell skipping for DI.
8. Finish the three paper drafts (ISANN vs ITERML, PR #20; Y vs dY, PR #23; single vs multiple ANN, PR #21) after step 3, because their numbers rest on the old reference.

**Repository housekeeping.** PRs #18 to #24 are still open. Two items are stale: ITERML's automatic rerun was stopped before it was scored, and the trials-summary doc predates the outlet correction.

## Sources

- Repository: merged PRs #2 to #17, open PRs #18 to #24.
- Project files: chemmanifold/RESULTS.md, chemmanifold/REGISTRY.md, propuestas-mejora.md, isann/INFORME-ISANN.md, isann/lts/LTS-REPORT.md, isann/delta-output/REPORT-ISANN-DY.md, iterml/STATUS.md, ensemble/ROADMAP.md, equilibrio-punto-fijo/RESUMEN.md, benchmark/, bucle-ood/, protocolo-cfd/, timescale/, ladder/compare_final.json, fluent-vs-openfoam-simple/.
- Earlier write-ups (Claude artifacts): All trials so far, in headlines; CFD timescale roadmap; fixed-timestep ladder results; exploration story infographic; reduced-mechanism brainstorm.
- Project notes kept between threads (21 Oct to 7 Nov 2026).

# Paper 1 outline: physics-only exploration of the thermochemical space

**Working title.** Exploring the physically accessible thermochemical space of a combustion mechanism to
train neural chemistry surrogates without CFD data.

**Target.** Combustion and Flame (methods paper); alternative Energy and AI.

**One-sentence claim.** A surrogate can be trained entirely from the mechanism and the physics of the
streams (no CFD states), provided the exploration covers not only flame structures but also the
"quiet" states a real flame visits (diluted and cooled lean products, near-equilibrium relaxation at
the flow time step, vitiated induction); CFD may tell the exploration *where* to look, never *what*
the answer is.

## 1. Introduction
- Chemistry is 90 % of the DI step in the burner (phase E: 13.6 s/step DI vs 1.3 s flow only).
- Surrogates in the literature are trained on flamelets, on canonical reactors or on CFD data; the last
  is circular when the same CFD is the test.
- Contribution: (i) a catalogue of physics-only data sources ("regimes") with what each covers;
  (ii) a way to measure coverage on any CFD solution and turn holes into new exploration without using
  the states; (iii) evidence of which regimes matter, measured in the CFD.

## 2. Problem setting
- Mechanism GA18 (18 species), non-premixed CH4/air, 1 atm, T 300-~2120 K, Z 0-1, Z_st ~0.055 (air
  O2 0.21 by mole).
- Map to learn: (T, Y, dt) -> (T, Y)(t + dt), dt = per-cell chemistry step (Fluent tau_cell), not the flow step.
- Network: ResNet-FiLM (dt as FiLM context), the same for every data set; OOD detection on the
  trained input box/grid.

## 3. Exploration sources (the core of the paper)
One subsection per source, each with one figure (Library `chemmanifold/exploracion/figures/01-11`):

| Regime | Source | What it covers |
|---|---|---|
| 2 | Steady flamelets, strain sweep 0.6-1200 1/s, adiabatic + radiating | flame structure, extinction side |
| 5 | Unsteady flamelets (extinction, reignition, cooling, strain jumps) | transient flame states |
| 0 | 0D adiabatic reactors from Sobol seeds (stage 1) | ignition / burnout paths |
| 3 | 0D wall-cooled reactors | heat-loss states (psi > 0) |
| 1 | PaSR / same-Z mixing ensemble | partially reacted mixtures |
| 4 | Recirculation into pure streams | product-stream mixing |
| 6 | Equilibrium tails (30 ms) | near-equilibrium precision |
| 7 | Vitiated ignition | jet induction in hot lean gas (fixes early nozzle ignition partly) |
| 8 | Burnt-gas relaxation (+ lean set) | lean product relaxation |
| 9 | Equilibrium fixed point | drift of the map at equilibrium |
| tix | Flow-statistics bounding (stage 19: Z, psi, chi, strain, tau_cell PDFs from a cheap one-step flame) | ranges only, no states |
| 15-19 | Hole sets M1, M4-M6 (lean dilution-cooling parcels, relaxation at flame dt, jet induction layer, hot-wall heat gain) | measured holes |
| 21 | Committee sampling (disagreement of model rollouts, no CFD) | model-driven adaptive sampling |

- dt sampling: fixed strides vs dt_range; tau_cell histogram from the CFD as a *distribution*, never values.
- Deduplication (grid cap + radius) and capping per regime.

## 4. Measuring coverage on a CFD solution without using it
- Stage 16 OOD/hole map in (Z, psi, progress, strain); stage 21 a-priori one-tau step.
- Worked example: Fluent GA18 DI (corrected case): main hole Z 0.005-0.035, T 600-950 K; psi < 0 is an
  OpenFOAM Sc = 1 artefact, not a real hole (so do not explore it). This is a methods result in itself.
- Rule: the map only changes exploration bounds and seeds; it is reported, never trained on.

## 5. Results
5.1 Coverage: share of the corrected-case DI hot mass inside the data, per regime added (ablation).
5.2 Offline: one-step and 0D rollout errors vs Cantera on held-out physics states (stage 18).
5.3 CFD, protocol v2 pure mode (paper 5's protocol): families ood8 -> tix1 -> tix2 -> tix2h -> tix2c,
    with 3 training repeats each and their ensembles. Final ranking (sim1 SUMMARY.md): **P_tix2c S 2.00
    best physics-only** (flame 8.0 K, ignition -0.6 ms), P_mix 2.05, tix2h_s0 2.35 (best single), P0 2.67,
    P_tix2h 2.97. The C2 ignition-focused exploration (jet induction + committee round) improved the
    flame 14.9 -> 8.0 K but not ignition; all physics-only models except P_tix2h ignite early.
5.4 What each regime fixed, with the trial that showed it: vitiated ignition and burnt relaxation (early
    nozzle ignition caused by radicals pumped into the hot lean start gas, `odeAbove` proof);
    wide dt_range hurts the flame at the flow step (ood3); equilibrium tails (flame core cold near nozzle).
5.5 Against ISAT 1e-4 (S 0.67): honest gap, ~9x in flame error for the best model (8.0 vs 0.9 K);
    on GA18 ISAT wins at matched accuracy, a network only pays off for larger mechanisms (cost study).

## 6. Discussion
- Remaining error is near-equilibrium precision and induction timing, not coverage.
- Repeat spread is as large as family differences: report repeats or ensembles, never single seeds.
- Limits: one mechanism, one burner, 1 atm; generality to another case is the main reviewer risk.

## 7. Conclusions

## Figures (planned)
1. Z-T scatter of all regimes (from `fuentes_Z_T.png`, regenerate for the final data set).
2. One panel per regime (existing 11 figures, merged into 2 multi-panel figures).
3. Coverage map of the Fluent DI solution with holes (corrected case).
4. Ablation bar chart: coverage + protocol v2 S per family, with repeat spread.
5. Flame |dT| vs time for best families and ISAT 1e-4.

## Missing results (to run before writing)
- [x] Coverage ablation per regime of the ood8 data (regimes 0-8) on the corrected Fluent GA18 DI:
      `papers/data/coverage/coverage_ood8.md`. Strict coverage is nearly complete (94 % of hot mass within 0.5);
      dense (Z, T) coverage goes 7 % (flamelets) -> 60 % (+0D) -> 74 % (+PaSR) -> 97 % (+burnt relaxation);
      only burnt relaxation cannot be replaced. tix2c on the A1r DI (`results/sim1/offline_v2/a1r_regime_coverage.md`): 0 of 44k hot cells beyond
      the OOD threshold; nearest regimes dilution cooling (15) 29 % of hot volume, flamelets 17 %, committee (21)
      14 %, vitiated 9 %; dilution cooling dominates 600-1400 K (the old hole), vitiated 1400-1800 K.
- [x] P_tix2c (C2) protocol v2 score: S 2.00 (`results/sim1/C2/summary.md`).
- [ ] Hole sets M1-M7 (PR #27) trained and scored with 3 seeds.
- [ ] Offline stage 18 numbers for the same families, same state set.
- [ ] Regenerate the regime figures for the final data set (figures/make_figs.py).

# Paper 5 outline: a CFD evaluation protocol for chemistry surrogates

**Working title.** Judging a chemistry surrogate where it is used: a fixed CFD protocol, and why
offline errors do not rank surrogates.

**Target.** Combustion and Flame (short communication or full paper); alternatives Combustion Theory
and Modelling, Energy and AI.

**Claim.** One-step errors, offline 0D rollouts and single training runs do not predict how a
surrogate behaves in a CFD run. A fixed, versioned protocol (ignition phase + established-flame phase,
pure mode, repeats, one normalised score S, ISAT as the reference line) does, at a cost of a few hours
per candidate.

## 1. Introduction
- Surrogate papers report test-set MAE or a priori errors; a posteriori CFD tests differ per paper in
  start state, duration, mode (hybrid fallback hides errors) and metric.
- Evidence from this project that the usual numbers mislead (sections 4-5).

## 2. Test case
Laminar buoyant CH4/air burner, GA18, OpenFOAM v2412 rhoReactingBuoyantLeFoam + constantLewis
(Sct 0.7) + fvDOM wall radiation, corrected outlets, dt 2e-5 s, 4 ranks. DI references A1r (flame,
0.1-0.2 s) and A2r (ignition 0-25 ms), validated against Fluent (gate G1: V(T>1500) 19.95 vs 18.25 cm3,
Tmax 2121 vs 2087.5 K, base 1.39 vs 1.15 mm).

## 3. The protocol (v2; v1 kept as history)
- Phases: ignition 0-25 ms from a lean lit start vs A2r; flame 50 ms from A1r at 0.1 s vs A1r snapshots.
- **Pure mode is mandatory** (no DI fallback; commercial codes such as Fluent have none). Hybrid mode only
  as a diagnostic; it hid ood1's errors in v1 (hybrid 5 K vs pure 69 K).
- Metrics: flame-cell |dT| (T > 1600 K), drift K/10 ms, ignition time (domain Tmax > 1600 K), CO/OH total
  ratios and volume-weighted L1 for OH, CO, CH4, H, V(T > 1500), flame base/tip, zone split (reactive,
  lean burnt, rich, nozzle box classified on the DI state), OOD share, s/step.
- Score S = max(F, I, C): F = flame |dT| / 5 K, I = ignition shift / 0.3 ms, C = |ln CO, OH ratio| / ln 1.4.
  S <= 1 means every target met. Validity: run must reach the end time.
- Versioning rule: change a number -> new version; reports of different versions are not compared.
- Shadow-DI comparison data saved with every run (standing rule), stratified in T x Z x OOD bins.

## 4. Results: what the protocol reveals
4.1 Reference line: ISAT 1e-4 S 0.67 (0.9 K, -0.2 ms, 3.65 s/step, ~3.7x DI); ISAT 1e-3 S 3.33 (good
    flame, ignition 1.0 ms early); DI Treact cutoff only 1.1x.
4.2 Surrogates (G2 + C4 + C2 tables): best physics-only P_tix2c 2.00, P_mix 2.05, tix2h_s0 2.35, P0 2.67; CFD-adapted
    ISANN v6 1.16; none meets all targets; networks 3-15x worse in flame than ISAT 1e-4.
4.3 Repeat variance: same data, same architecture, three seeds: S 2.35 / 5.26 / 10.58 (tix2h),
    4.67 / 7.72 / 14.14 (ood8). Single-seed rankings are noise.
4.4 Ignition is the term that separates methods (ISAT 1e-3 and most networks fail only there).
4.5 Hybrid mode masks errors (v1: ood1 hybrid vs pure).

## 5. Offline benchmark vs CFD ranking
- Stage 18 (physics-only Cantera states, 2500 x 2e-5 s rollouts): ranking stable within itself but
  Spearman with CFD 0.28-0.68 (v1), 0.62-0.77 only when driven by one clearly bad model; ITERML iteration 2
  ranked better offline (22.9 vs 31.8) and was worse in CFD.
- One-step test-set error: ISANN round 1 was 18x better in one step but drifted -60..-110 K in 0D.
- C3b: the 10-step offline gate passed networks that were the best in CFD to 122 ms and then drifted
  (S 6.86 / 16.80): a strong example for the paper that short offline checks miss slow coupled drift.
- What offline tests are good for: rejecting clearly bad models (Phy-ChemNODE worst in both).

## 6. Cost of the protocol and a cheaper screen
Protocol v2 ~2.7 h per candidate on 4 ranks; proposal: offline screen -> 5 ms ignition + short flame
leg -> full protocol for survivors; LTS steady state (A4r passes G1) as a cheaper flame reference.

## 7. Recommendations (checklist for surrogate papers)
Pure mode, ignition + flame phases, >= 2-3 training repeats or ensembles, ISAT/TDAC line at the same
ranks, report s/step with chemistry share, version the protocol.

## Missing results
- [x] Spearman of stage 18 vs protocol v2 S, 6 models in the cloud (`papers/data/offline_v2/spearman_v2.md`):
      composite rho 0.43 alone / 0.71 hybrid, not significant; ood8_s2 worst offline, best single physics model
      in the CFD. Full set done on sim1 (`results/sim1/offline_v2/summary.md`, branch mq77al 2d9f97e, n = 20 models with
      valid S, 36 benchmarked): **no offline metric predicts S** (best hybrid dT_10ms rho +0.36, p 0.12); only the
      ignition shift correlates (fp_OH rho +0.59, p 0.007; OOD-at-start share +0.56). Headline result of section 5.
- [ ] Short-screen correlation (5 ms ignition + 10 ms flame vs full S).
- [x] P_tix2c score: S 2.00.
- [ ] ISANN v6 repeat.
- [ ] Optional: same protocol on Fluent (pure mode is its only mode) to show code portability.

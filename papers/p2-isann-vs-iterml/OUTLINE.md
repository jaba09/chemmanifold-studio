# Paper 2 outline: ISANN vs ITERML (revision plan for draft v1)

**Existing draft.** `papers/isann-vs-iterml/isann_vs_iterml.tex` on PR #20 (branch
`claude/project-thread-uzvup8`), copy in Library `chemmanifold/comparacion-isann-iterml/paper/`.
Title: "Where should the training data of a neural chemistry surrogate come from? Online learning from
the simulation vs physics-only seeded exploration". Target Combustion and Flame.

**Claim (keep).** Both schemes use the simulation to close the coverage gap of an a priori network.
ISANN trains on the run's DI pairs (CFD-adapted model); ITERML uses CFD states only as seeds of new
Cantera explorations (model stays a physics model of the mechanism). Physics-only seeding works only as
well as the error detector that picks the seeds.

## Why a revision is needed
- All CFD numbers in v1 are **protocol v1 on the old-outlet case without wall radiation**. They must be
  replaced by protocol v2 numbers on the corrected case, or the paper must state it is a v1 study.
- The decision to drop iteration 2 and restart iteration 3 from iteration 1 was a manual judgment
  (Javier's objection, 1 Nov). Since then the rules are codified (`openfoam/iterml/rules.py`: score S,
  elitism with 2 seeds, stopping rule). The revised paper should present the **automatic** ITERML.

## Revised structure (sections of v1 kept unless noted)
1. Introduction (keep).
2. Common elements: network, a priori exploration, OOD + shadow checks, dedup, test case (**update to
   corrected case + radiation**), evaluation protocol (**v2, cite paper 5**), offline benchmark.
3. ISANN (keep method). Add: GRI/ARC22 ISANN if the thread "Run ISANN with GRI-Mech 3.0" finishes
   (second mechanism answers the generality question).
4. ITERML. Rewrite: seeds only, seed state excluded; seeded regimes 10-14; seed dedup at three levels;
   **codified acceptance** (S, elitism, stop at S <= 1 / 2 rejections / 6 iterations); generic
   stratified relative-error sentinels (replace the CO floor that hid iteration 2's error).
5. Results.
   5.1 Information taken from the CFD (keep table: pairs vs seeds, share of CFD-derived data).
   5.2 Protocol v2 scores: ISANN v6 S 1.16 (5.8 K, -0.2 ms); a priori parent P_tix2c S 2.00;
       ITERML v2 warm-started (C3): ignition fixed (-0.6 -> +0.2 ms) but flame 8 -> 11 K, S 2.22 / 2.15,
       stopped after 2 rejections, one of 3 repeats failed the offline gate each iteration;
       ITERML from scratch with 20 % seeded share (C3b): flame 1.7-2.2 K, CO/OH 2-3 %, ignition on DI up
       to ~122 ms, then a slow cold drift in the rich core under the nozzle (S 6.86 / 16.80) that the
       10-step offline gate cannot see. ISAT 1e-4 S 0.67 as the line.
   5.3 Ignition (mirror-image errors in v1: ISANN early, ITERML late; check if it survives v2).
   5.4 Species and HRR in lean burnt gas (iteration 2 negative result: CO x6.4 under the 5e-5 floor).
   5.5 Generality away from the burner: offline benchmark (ISANN v6 alone best there too, 1.75).
   5.6 Cost (s/step; ISANN DI phase cost; ITERML ~11-12 h per iteration on 8 cores).
   5.7 Development history (v1 iterations 1-3, old case) moved to an appendix with the decisions log.
6. Discussion: CFD-adapted vs physics model; what the detector must see; when each scheme is admissible.
7. Conclusions.

## Missing results
- [x] C3 / C3b: ITERML v2 on the corrected case done (`results/sim1/C3/progress.md`, `C3b/summary.md`).
- [ ] Optional: longer coupled gate on rich-core states + warm start from a C3b repeat (sim1 open item,
      most promising route to beat P_tix2c).
- [ ] Phase D: ISANN on R2 (A1r) from a physics-only parent of the tix2h family, so both schemes share a parent
      (fixes the "different parents" caveat of v1: ood7 vs ood8).
- [ ] Two training seeds for each final model (fairness).
- [ ] Same offline benchmark state set for all models (v1 used 440 vs 218 states).

## Fairness caveats to keep in the text
Parents, ranks, seeds and benchmark sets must match; ISANN uses DI during its learning phase (its cost
and its CFD dependence must be shown next to its accuracy).

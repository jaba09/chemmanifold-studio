# sim1 run roadmap

As of 9 Nov 2026, 20:30 CET. Plan only: nothing here has been launched.

sim1 is Javier's OpenStack VM: Ubuntu 24.04, 16 CPUs, 62 GB RAM, 88 GB free disk, OpenFOAM v2412,
Python env `/opt/ofb/ml` (Cantera 3.2.0, PyTorch 2.9.1 CPU), `userChemStep` and `tauCellHistogram`
built. Claude drives it through Remote Control (tmux session `claude`, folder
`/home/ubuntu/chemmanifold-studio`). It has no 2-hour task limit and is not reclaimed when idle, so
long runs can go in tmux or under `nohup` with a resumable supervisor.

This plan starts from section 8 of the research report (`docs/RESEARCH-REPORT.md`, PR #25): **fix the
reference flame first, then re-rank the surrogates on it, then improve them.**

## 0. Ground rules for every run here

1. **No training on CFD or DI data.** A priori models learn only from the physics-based exploration.
   CFD states may be used as starting states for new physics exploration (ITERML, seed state itself
   excluded) or for flow statistics (timescales, strain), never as training pairs. The single
   exception is ISANN, which is labelled `isann` (CFD-adapted) in the registry.
2. **DI comparison data is always saved.** Every surrogate run keeps its shadow-DI checks on a
   diverse (T, Z) stratified subset of cells, and the comparison files are kept with the run.
3. **Corrected case only:** top and chimney open, r = 0.14 m side a wall (`openfoam/quemadorUnico`
   from branch `claude/ga18-realistic-diffusion`). Everything before 5 Nov used wrong outlets.
4. **Realistic species diffusion only:** solver `rhoReactingBuoyantLeFoam` with `constantLewis`
   (per-species Le from Cantera, Sct 0.7). The stock solver's Sc = 1 is what made the old OpenFOAM
   flame differ from Fluent.
5. **Rank in pure mode** (no GA18 fallback, as in Fluent), over at least 50 ms, on the mean of at least
   2 training repeats. Accept a new model only if it beats the best by more than the repeat spread
   (the ITERML elitism rule).
6. All times given to Javier in Spain time (CET).

## 1. Summary of the plan

| # | Run | Needs | Cores | Wall time (est.) | Decides |
|---|---|---|---|---|---|
| S | Set up sim1 for this plan, smoke and scaling test | inputs bundle, integration branch | 16 | 2 h | real s/step, rank count per run |
| A1 | Reference flame, time-accurate DI (R2) | S | 8 | 7 to 9 h | **gate G1**: is the OpenFOAM flame now the Fluent flame? |
| A2 | Ignition DI reference (0 to 25 ms from the lean start) | S | 4 | 1 h | ignition reference for protocol v2 |
| A3 | Cheap 2-step flame + flow statistics (stage 19) | S | 4 | 2 to 3 h | dt band and bounds for the timescale exploration |
| B | Re-score existing models on R2 (pure, protocol v2) | A1, A2 | 12 (3 x 4) | 4 to 5 h | **gate G2**: which family is the parent |
| C1 | tix2: timescale exploration from R2 statistics, 3 repeats, narrow-dt variant | A3 | 12 | 8 to 10 h | does R2-bounded exploration beat ood8? |
| C2 | Ignition-focused exploration (more induction states) | code change | 8 | 6 to 8 h | is the ignition error coverage or precision? |
| C3 | ITERML automatic rerun on R2 from iteration 0 | A1, A2, B | 16 | 1 to 1.5 days | best physics-only model |
| C4 | P0 ensemble of the best family, CFD | B or C | 4 | 3 to 4 h | ensemble gain on the new reference |
| D | ISANN on R2 (CFD-adapted, labelled) | A1 | 8 | 5 to 6 h | online-learning comparison for the paper |
| E | Cost study: DI, DI with T cutoff, ISAT (TDAC), surrogate | A1, best model | 8 | 4 h | speed-up at matched accuracy |
| F | Refresh the three paper drafts | B to E | 2 | Python only | papers on the new reference |

Total: about 4 to 6 days of sim1 wall time if run in the order below, with two or three jobs side by
side most of the time.

The time estimates assume a sim1 core is about as fast as the cloud cores used so far (DI 8 s/step on
2 ranks, surrogate 2 to 4 s/step on 2 ranks, training from scratch about 3.5 h on 4 threads). Step S
measures the real numbers, and the table gets updated then.

## 2. What is running elsewhere

- **Javier's PC (WSL), thread "Rerun burner in OpenFOAM with realistic diffusion":** LTS (pseudo-steady)
  run of the corrected burner with `rhoReactingBuoyantLeFoam` + `constantLewis`. At iteration 2200 it
  was close to Fluent (Tmax 2115 vs 2088 K, hot volume 19.8 vs 18.2 cm3, flame base 6.9 vs 1.1 mm).
  At 3000 it had drifted (S-shaped sheet, 2203 K, 58 cm3) and was still changing: it looks like a
  flame that wanders under local time stepping. About 15 s per iteration; left running overnight, to
  be checked at about iteration 7000 on 10 Nov.
- **sim1 does not duplicate that run.** It runs the time-accurate version (A1), which the PC thread
  offered as option 2, because the transient protocol needs a time-accurate reference anyway and the
  Fluent simple flame already showed buoyant flicker (12.5 Hz).
- **Fluent stays on the PC** (Ansys Student, 4 cores). The Fluent checks of the best surrogate
  (report step 4) come after gate G2 or C3 and are not part of this plan.

## 3. Step S: set up sim1 for the plan (about 2 h, needs Javier once)

**S1. Code.** Most of the needed code sits on unmerged branches. Build one integration branch
`sim1/base` from `main` plus, in this order:

| Branch | What it brings |
|---|---|
| `claude/ga18-realistic-diffusion` | corrected outlets, `rhoReactingBuoyantLeFoam`, `constantLewis`, `compare_fluent.py`, `fluent_dat_to_foam.py` |
| `claude/project-thread-ol9roa` (PR #22) | `server/` setup and supervisor scripts (already copied to sim1, not committed) |
| `claude/project-thread-zpo3kx` (PR #16 follow-up, #18) | ISANN code, `startActive`, `relabel_dt`, `model.output` |
| `claude/project-thread-d8k91y` (PR #19) | ITERML, `rules.py`, `iterml_auto.yaml`, seeded regimes 10 to 14 |
| `claude/project-thread-04fho7` (PR #21) | ensemble model files in `userChemStep`, stage 18 sticky-OOD fix |
| `claude/project-thread-q4nf3a` | stages 19 to 21 (flow statistics, stats to config, tau_cell a-priori) |

Conflicts are expected in `userChemStep.C`, `07_train.py` and `models/registry.jsonl`. This is done in
the cloud, pushed, then pulled on sim1. Rebuild `userChemStep`, `tauCellHistogram` and
`rhoReactingBuoyantLeFoam` on sim1 after the pull.

**S2. Inputs.** sim1 has no access to the project Library. Two bundles are needed:

- `chemmanifold/servidor/server-inputs.tgz` (396 MB, already in the Library): base case, benchmark
  models and seeds, `handoff-ood7`, `handoff-ood8` (ITERML iteration 0 data).
- `chemmanifold/sim1/sim1-extra.tgz` (71 MB, new): the corrected Fluent case `.cas.h5` and its
  converged DI `.dat.h5`, plus model files ood8 seeds 0 to 2, ISANN v6 and tix1 seed 0.

`server-di-reference.tgz` is **not** needed: it holds the old stock-OpenFOAM DI snapshots, which this
plan replaces.

**Javier, once:** download both files from the Library to the Mac, then in Terminal:

```bash
scp -i ~/.ssh/javier-key.pem ~/Downloads/server-inputs.tgz ~/Downloads/sim1-extra.tgz ubuntu@<sim1 floating IP>:~/
```

Also run `gh auth login` once on sim1 (or add a deploy key), so results (reports, JSON, PNG; never
raw fields) can be pushed to a results branch and reach the cloud threads.

Models that were **not** kept and must be retrained if wanted: ITERML iter1 and iter3, tix1 seeds 1
and 2, the P1 expert sets. The plan does not need them: ITERML restarts from iteration 0 on the new
reference (C3), and tix is rebuilt from the new statistics (C1).

**S3. Smoke and scaling test.** 50 DI steps of the corrected case with `rhoReactingBuoyantLeFoam` at
4, 8 and 16 ranks (weighted scotch, cell weight 25 above 800 K), and 50 steps with `userChemStep`
(ood8, selftest 60/60) at 4 ranks. Output: s/step table that replaces the estimates in section 1.

**Gate G0:** the selftest passes, DI and surrogate both run with the LeFoam solver, and the measured
s/step is within 2x of the estimates. If DI at 8 ranks is slower than about 4 s/step, A1 moves to 16
ranks and B waits for A1.

## 4. Phase A: the reference flame (first priority)

### A1. Time-accurate DI reference "R2" (8 ranks, 7 to 9 h)

- Case: corrected outlets, `rhoReactingBuoyantLeFoam` + `constantLewis`, GA18 DI (`ode` seulex, rtol
  1e-5, atol 1e-10, as in Fluent).
- Start: the converged corrected Fluent field, mapped with `fluent_dat_to_foam.py` (cell order kept).
- Time stepping: Euler, fixed dt 2e-5 s, the protocol's chemistry step. (Fluent showed that dt 1e-3
  produces a false lift-off; 2e-5 is well below the 1e-4 limit found there.)
- Length: 0.1 s to settle, then 0.1 s of statistics (10,000 steps). Snapshots every 2.5 ms during
  the statistics window, mean and RMS of T, U, Y via `fieldAverage`, `tau_cell` histogram on.
- Resumable supervisor in tmux; `writeInterval` every 100 steps with `purgeWrite`, plus the 2.5 ms
  snapshots kept. Disk: about 40 snapshots x 60k cells x 25 fields, under 3 GB.

**Gate G1 (needs Javier's look).** Compare the R2 mean field with Fluent DI using `compare_fluent.py`.
Proposed pass criteria: Tmax within 50 K of 2088 K, V(T > 1500 K) within 30 % of 18.2 cm3, flame base
within 3 mm of Fluent's, mean hot-cell |dT| well below the old 418 K (target under 100 K), and the
flame position stable over the 0.1 s window (flicker is fine; a drifting base is not).

- **Pass:** R2 becomes the reference for all OpenFOAM scoring. Phases B to E go ahead.
- **Fail, close:** run one more variant before re-scoring anything, for example mixture-averaged
  diffusion instead of constant Le, or a finer start-up dt.
- **Fail, far:** stop OpenFOAM scoring and move model ranking to Fluent on the PC (pure mode, dt 4e-5
  s), keeping sim1 for exploration and training only. This is Javier's call.

The PC's LTS run is the cross-check: if it settles near Fluent too, the steady test 6b can be kept
(rebuilt on that state); if it keeps wandering, 6b is retired and the transient protocol is the only
CFD test.

### A2. Ignition DI reference (4 ranks, about 1 h, parallel with A1)

Protocol v1 scored the start-up (0 to 5 ms) from the lean phi 0.5 burnt-gas start at 1480 K, which
is where every pure a priori model ignites too early or too late. Keep that test, but on the new
solver: DI from the same lean start, 0 to 25 ms, writes every 0.5 ms to 5 ms then every 2.5 ms.

### Protocol v2 (defined by A1 + A2, small code change in `openfoam/protocol/`)

1. **Ignition phase:** lean start, 0 to 25 ms, scored against A2 (ignition time from Tmax > 1600 K,
   nozzle-box bias at 2 to 5 ms, as before).
2. **Flame phase:** start from the R2 snapshot at t = 0.1 s, run 50 ms, scored against R2 snapshots
   0.1 to 0.15 s (flame |dT| for T > 1600 K, drift per 10 ms, OH/CO/CH4/H, HRR, hot volume,
   lean-burnt-gas CO and OH, OOD share, s/step).
3. Score S from `openfoam/iterml/rules.py` (max of flame dT / 5 K, ignition delay / 0.3 ms, CO/OH log
   ratio / ln 1.4), so ITERML's acceptance rule and the ranking use the same number.

Cost per candidate: about 3,750 surrogate steps, roughly 1.25 h on 4 ranks.

### A3. Cheap 2-step flame and flow statistics (4 ranks, 2 to 3 h, parallel with A1)

Repeat the timescale-roadmap steps 1 to 3 on the new solver: a 2-step (methane-air-2step) LeFoam
flame from the Fluent start, stage 19 statistics (Z, chi with the Lewis-number diffusivities,
strain, gas age, tau_cell), and the gate against R2's DI statistics once A1 has them. Only
statistics leave this step, never states.

Decides: the tau_cell band for the exploration. Earlier, hot-cell tau_cell sat at 10 to 80 us; the
LeFoam flame is thinner, so this may shift.

## 5. Phase B: re-score what we already have (after G1)

Run protocol v2 in pure mode for every model already on sim1, three runs at a time on 4 ranks each:

| Run | Model | Why |
|---|---|---|
| B1 to B3 | ood8 seeds 0, 1, 2 | best a priori family; 3 repeats give the spread |
| B4 | P0 = mean of ood8 seeds 0 to 2 | ensemble cut ood8's pure error from 24 to 4.4 K on the old reference |
| B5 | tix1 seed 0 | best lean-burnt-gas CO on the corrected outlets (x0.89) |
| B6 | ISANN v6 (info only, labelled `isann`) | trained online on the old reference; shows how much it transfers |

About 4 to 5 h wall for all six (B4 costs about 2.9x a single model).

**Gate G2.** Pick the parent family by mean S over its repeats. Expected questions answered here:
does ood8 still ignite early with the new transport? Does P0 still remove the out-of-sample drift?
Did the old ranking survive the new reference (report open question 3)?

## 6. Phase C: improve, physics-only (after G2, partly earlier)

### C1. tix2: exploration bounded by R2 statistics (12 cores, 8 to 10 h)

- Stage 20 turns the A3 statistics into a config (`configs/burner_openfoam_tix2.yaml`), then the
  full pipeline (stages 0 to 7) with 3 training repeats in parallel (4 threads each).
- Variant tix2n: same data but pairs restricted to the flame's own dt band (from A3, expected about
  10 to 80 us), following lesson 7 and the tix1 finding that spreading over 10 to 840 us cost flame
  accuracy. Another 3 repeats.
- **Variant tix2h (added 2026-11-10, coverage holes):** the same stage-20 config plus the
  physics-only hole sets of `chemmanifold/holes.py` (regimes 15-19: lean dilution-cooling parcels,
  dynamic multi-stream PaSR, jet induction mixing layer, hot-wall heating, near-equilibrium
  relaxation at the flame's dt), regime 0 scaled by 0.7, `burnt_relaxation_lean.psi_min` clipped to
  0. Built by `scripts/24_add_hole_sets.py --base configs/burner_openfoam_tix2.yaml --out
  configs/burner_openfoam_tix2h.yaml --data-dir ../data/openfoam_tix2h`. Another 3 repeats. The hole
  sets add about 1 h of stage 4 on 12 workers. Why: the Fluent DI solution keeps 59 % of its hot mass
  at Z < 0.0275 (mostly 600-950 K), where ood8 and tix1 are 20-100 times thinner than elsewhere.
- Scored with protocol v2 (6 runs, about 4 h wall at 3 slots; 9 with tix2h).
- Can start as soon as A3 is done; it does not need G1 to train, only to be scored.

Decides: whether timescale bounding plus a narrow dt band beats ood8 in pure mode (flame and lean
CO/OH together).

### C2. Ignition-focused exploration (8 cores, 6 to 8 h)

- Code change first (cloud): extend regime 12 with more vitiated and partially mixed CH4/air/product
  states at 800 to 1700 K covering the jet induction zone, plus an ignition-delay sentinel in the
  offline checks (0D ignition delay vs Cantera on a fixed set of jet-like mixtures).
- Physics-only data on top of the parent family's data, 3 repeats from scratch (warm fine-tuning
  degraded rollouts before, so no warm start).
- Scored on protocol v2's ignition phase first (cheap, 25 ms); full protocol only if it passes.
- This step can run before G1, because it does not use the CFD reference to build its data.

Decides report open question 4: if more induction states fix the ignition time, the error was
coverage; if not, it is radical-increment precision and the next work is on the loss or the outputs.

### C2b. Committee rounds on the C1 winner (M3, 12 cores, 2 to 3 h per round)

- `scripts/23_committee_sampling.py --round k --models <the 3 seeds' chemmanifold_model.txt>`: the
  seeds roll out 3000 Cantera starts from the a-priori data; states where they disagree or drift from
  Cantera (10 K, x1.4 on OH/H/CO) start new Cantera trajectories (regime 21). Then stages 5-7 for 3
  seeds again (warm start not used). 2 to 3 rounds; stop when the score quantiles stop falling.
- Physics only: the candidate states come from the surrogates run on Cantera starts, not from a CFD run.

### C3. ITERML automatic rerun on R2 (16 cores, 1 to 1.5 days)

- Parent: iteration 0 = best family from G2 (ood8 unless B says otherwise).
- Frozen rules (`configs/iterml/iterml_auto.yaml`): CFD states as seeds only (state excluded,
  three-level dedup including against earlier iterations), seeded pairs capped at 35 % with the
  newest iteration at least half of it, relative CO/OH floor 1e-7, 2 training repeats per iteration,
  elitism on the protocol v2 score, stop at S <= 1, 2 rejections in a row or 6 iterations.
- Code change: point collection and evaluation runs at the LeFoam solver and protocol v2.
- Per iteration about 4 to 5 h on sim1 (collection 1 to 2 h, seeded exploration about 1 h, 2 trainings
  in parallel, 2 pure evaluations in parallel). `DECISIONS.md` logs every accept or reject.

Decides: the best physics-only model on the new reference, and whether ITERML improves monotonically
when the rules are frozen (it did not on the old reference: iter1 3.3 K, iter2 6.6 K, iter3 rejected).

### C4. P0 ensemble of the best family (4 cores, 3 to 4 h)

Average the 2 to 3 repeats of whichever family wins C1 or C3, with member disagreement as the OOD
signal, one pure protocol v2 run. Decides whether the ensemble gain holds on the new reference and
gives the input for the single-vs-multiple-ANN paper.

## 7. Phase D: ISANN on R2 (8 cores, 5 to 6 h, after G1)

Online learning on the new reference, which is the one place training on the run's own DI pairs is
allowed. Same design as run 1 (DI phase first, dedup store, warm start from the a priori parent,
rollout gate), parent = the G2 family, run 0 to 50 ms of the flame phase plus the ignition phase.
Labelled `isann` in the registry. Then one pure run of the final ISANN model for the ISANN vs ITERML
comparison. Can share sim1 with C1 or C3 (it needs 4 ranks plus 4 training threads).

## 8. Phase E: cost at matched accuracy (8 cores, about 4 h)

From one R2 snapshot, 200 steps on the same 4 ranks each, timed per cell:

1. GA18 DI (seulex), as the baseline.
2. DI with a temperature cutoff (`Treact` around 600 K), since most of DI's cost was in 41k cold cells.
3. ISAT through OpenFOAM's TDAC (tabulation tolerance 1e-3, 1e-4, 1e-5), the baseline reviewers will
   ask for.
4. The best surrogate from C, single and P0.

Error measured against step 1 on the same cells. Decides whether the surrogate's speed-up survives
a fair comparison (report negative result 13). The Fluent ISAT comparison stays on the PC.

## 9. Phase F: papers (Python only)

After B to E, regenerate the figures and tables of the three drafts (ISANN vs ITERML, PR #20; Y vs
dY, PR #23; single vs multiple ANN, PR #21) on the new reference, and update the research report.
The Y vs dY paper needs one extra pair of ISANN runs (state vs increment output) on R2, about 10 h
on 8 cores, only if Javier still wants that paper.

## 10. Suggested order on the calendar

| When (CET) | Slot 1 (8 cores) | Slot 2 (4 cores) | Slot 3 (4 cores) |
|---|---|---|---|
| Day 1 | S, then A1 starts | A2, then A3 | C2 code change in the cloud |
| Day 1 night | A1 | C2 data + training | C2 training |
| Day 2 | A1 ends, **G1** | C1 exploration | C1 training |
| Day 2 night | B (3 x 4 ranks across slots) | | |
| Day 3 | **G2**, C3 starts (all 16) | | |
| Day 4 | C3 | | |
| Day 5 | C3 ends; D | C4 | E |
| Day 6 | F, report update | | |

Gates G1 and G2 need Javier: each is a short report with the comparison figures and a
recommendation. Everything between gates runs without waiting, and failed runs are diagnosed and
retried automatically, within the rules in section 0.

## 11. Not planned for sim1 (parked)

- Reduced mechanism from GRI 3.0 (brainstorm doc): waiting on Javier's answers (is NO a goal, which
  reference mechanism).
- Fixed-dt ladder and wide-dt models: closed, both made the flame worse.
- dY outputs with per-species loss weights: only if the Y vs dY paper needs it.
- Fluent runs: on the PC.

## 12. Operational notes

- One thread drives sim1 through Remote Control at a time. Parallel jobs run inside that one
  session (supervisor scripts with slots), not in separate threads.
- Layout on sim1: code in `~/chemmanifold-studio`, runs in `/opt/ofb/runs/<phase>/<run>`, inputs in
  `~/inputs`, results reports under `results/sim1/<phase>/` on a results branch.
- If sim1 is shut off or rebooted, Javier restarts the link: `ssh` in, `tmux new -s claude`,
  `cd chemmanifold-studio`, `claude remote-control`. All runs are resumable from their last write.
- Keep at least 20 GB free: purge intermediate writes, keep only the scoring snapshots.

## 13. Queued: A4r, steady LTS check with radiation (added 2026-11-14)

From the PC thread's report (GA18 LTS + LeFoam/constantLewis, no radiation: settled at iteration ~9000 with V(T>1500)
60 cm3 = 3.3x Fluent, flame base and peak T on Fluent's). A1r showed the missing piece is the wall radiation.
A4r = that same steady LTS run plus `enable_radiation.sh`, from the Fluent DI start:
`server/sim1/a4r_lts.sh <A1r prepared case> /opt/ofb/runs/A4r_lts 8`.

- Settles when V(T>1500) changes < 3 % and Tmax < 10 K between two 1000-iteration checks (min 3000, hard stop 12000).
- Cost: 8 ranks; the PC did 13-15 s per LTS iteration on 8 WSL cores without radiation. Starting from the Fluent field
  it should settle well before the PC's 9000 iterations: estimate 3000-5000 iterations, 8-20 h.
- Pass = the G1 limits against Fluent (V within 30 %, Tmax within 50 K, base within 3 mm, mean hot |dT| < 100 K).
  Decides whether the steady test 6b can be rebuilt on an LTS state (hours instead of a day of DI per check).
- Report: `results/sim1/A4r/summary.md`. Low priority: run in a free 8-core slot, after the current C4 scoring.

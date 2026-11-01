# ITERML roadmap: iterative physics-seeded surrogate loop

Requested by Javier on 2026-11-01 (09:23 Spain time). Status: go-ahead given 09:28; code S0-S5 written
(section 10); short test run S6 done 10:01 (results in project files iterml/prueba-corta/).
Written in English; all times in Spain time (CET).

## 1. The idea in one paragraph

ITERML repeats one cycle until the CFD run with the surrogate is good enough:
explore the thermochemical space with physics reactors, train the network, run the
burner with the network while watching for out-of-distribution (OOD) cells and
checking a spread-out sample of cells against direct integration (DI, GA18), keep the
states where the network is OOD or wrong, stop the run once enough of them are kept,
and use those states as **starting points (seeds) for new physics-based exploration**
(PaSR, 0D reactors, relaxation, flamelets). The network is then retrained on the old
plus the new physics data, and the burner is run again.

### The rule that separates ITERML from ISANN

| | ISANN (done, 2026-10-30) | ITERML (this plan) |
|---|---|---|
| What the CFD states are used for | training pairs (state, dt, DI result) | **seeds only**: they say *where* to explore |
| Where the training pairs come from | DI integration of CFD cells | Cantera physics reactors started from or around the seeds |
| Is the CFD state itself in the training set? | yes | **never** (flagged `excluded` in the pairs file) |
| Registry label | `isann` (CFD-adapted) | `iterml-iterK` (a priori + seeded exploration) |

The DI comparison of a diverse cell sample (standing rule of 2026-10-29) is kept in
every run and saved, but it is used only to decide which states become seeds and to
score the model. It is never training data.

## 2. The loop

```
 iter 0:  ood8 exploration + model (already done, best a priori model so far)
   |
   v
 [A] CFD collection run (OpenFOAM burner, lit start, dt 2e-5 s)
       network in every cell; OOD cells -> GA18 (hybrid) or network (pure), see 4.2
       shadow DI on a stratified sample every N steps   -> shadowDI.csv (kept, comparison)
       OOD states + states with large shadow error      -> seed store (deduplicated)
       stop when a stop criterion of 5.1 fires
   |
   v
 [B] seed processing (new script 19_iterml_seeds.py)
       merge processors and snapshots, deduplicate, describe each seed by its flame
       features (Z, psi, progress c, strain, tau_cell, radical excess), assign a regime
   |
   v
 [C] seeded physics exploration (stage 04, new seeded sets, regimes 10-14)
       Cantera reactors started from / around the seeds; seed states excluded
   |
   v
 [D] training: warm start from the previous model on old + new pairs (replay)
   |
   v
 [E] gates: offline benchmark (stage 18) + registry card (stage 15)
   |
   v
 [F] evaluation run: CFD protocol v1, PURE mode, 0-50 ms (100 ms for the final model)
       outer stop criteria of 5.2 met?  yes -> done   no -> back to [A] with the new model
```

## 3. What is reused (nothing here is rebuilt from scratch)

| Need | Existing piece | Change needed |
|---|---|---|
| Step 1, exploration from flame features | stages 00-04, regimes 0-8, config `burner_openfoam_ood8.yaml` | none; ood8 is iteration 0 |
| Network in OpenFOAM, OOD checks | `openfoam/userChemStep` (`oodFallback`, `odeInduction`) | add `iterml` collection dictionary (6, step S1) |
| Diverse DI checks | userChemStep `shadowEvery` / `shadowPerBin` (bins T x Z x inside/OOD), `shadow_report.py` | add error thresholds that flag a seed |
| Not storing repeated points | ISANN `isannStore.H` grid cap + landmark radius (61-93x reduction) | reuse as is for the seed store |
| Where the gaps are | stage 16 `16_coverage_gaps.py` (Z, psi, c, strain per cell) | reuse its feature code in step [B] |
| dt seen by the chemistry | `tauCellHistogram`, `dtHistogram.csv` | keep the histogram per run; it sets the dt of the seeded reactors |
| Warm-start training | `training.init_from`, `patience`, `07_train.py --seed --tag` | none |
| Model gate | stage 18 offline benchmark (3 min/model) | add the run's seeds (relaxed by Cantera) as an extra held-out state set |
| Documentation | stage 15 registry, cards, `models/REGISTRY.md` | lineage field `parent`, tag `iterml-iterK` |
| Final score | CFD protocol v1 (`openfoam/protocol`, pure mode, 100 ms, phases start / flame) | none |
| Long runs in the container | `run_hyb.sh` / `resume_hyb.sh`, supervisor relaunch after the 2 h task limit | one supervisor script for the whole loop |

## 4. Stages in detail

### 4.1 [A] What a seed is, and how it is caught

A cell state is written to the seed store when at least one of these holds:

1. **OOD**: the userChemStep OOD flags (manifold ratio, data ratio, element/Z checks)
   fire, as today in `puntos_ood.csv`.
2. **Large error vs DI** on a shadow-checked cell (one step, same dt):
   `|T_ann - T_DI| > max(1 K, 0.3 |dT_DI|)`, or for OH, H, O, CO:
   `|Y_ann - Y_DI| > max(5e-5, 0.3 |dY_DI|)` (the ISANN trust thresholds, which
   already worked). Checked cells that pass are kept too, as `pass` rows, so the
   comparison data are complete.
3. **Bin flag**: a (T, Z) bin whose shadow failure rate goes above 20 % marks all its
   cells for the next 5 steps (with the grid cap this adds only a few new seeds) so
   the store also holds states *around* the failing ones, not only the checked cell.

Shadow sampling follows the standing rule: stratified over T x Z x inside/OOD bins,
`shadowPerBin` cells per bin every `shadowEvery` steps, never a random draw that
clusters in the far field. Default: every 25 steps, 3 per bin (ISANN used 10 / 2).

Known blind spot (ISANN3, 2026-10-31): OOD and one-step shadow checks both missed the
early ignition at the nozzle, because each single step looks fine and the error builds
over many steps. ITERML adds a **multi-step sentinel**: every 100 steps, 20 cells of the
induction bins (T 900-1700 K, low c, Z near stoichiometric) are copied and integrated
with GA18 for 25 steps alongside the network; a drift above 50 K in T or 2x in OH makes
the start state a seed with flag `drift`.

### 4.2 [A] Hybrid or pure collection run

- **Recommended: hybrid for collection** (OOD cells go to GA18). The states the run
  visits stay close to what the burner really does, so seeds are relevant and the run
  does not blow up in the first iterations. The ignition fix of `odeInduction` is
  switched OFF in collection runs, so the network's own induction errors show up.
- **Pure** runs are used for evaluation [F], since Fluent has no hybrid mode. If the
  pure run drifts in a region the hybrid run never shows (as ood1 pure did after
  20 ms), seeds are also collected from the pure evaluation run (same store, flag
  `pure`).

### 4.3 [A] When to stop a collection run (inner stop)

Stop at the first of:

| Criterion | Value (first guess) | Why |
|---|---|---|
| Seed store saturated | < 2 % new grid boxes over the last 100 steps, and >= 1500 seeds | more steps give the same states |
| Enough seeds | 6000 deduplicated seeds | stage 04 cost grows with seeds; ~3-4 h of Cantera at most |
| Model clearly lost | OOD share > 10 % of hot cells for 50 steps | further states are produced by a broken run |
| Divergence | NaN, T < 250 K or T > 2600 K anywhere, or Courant blow-up | |
| Time limit | 25 ms simulated (protocol start + early flame) | flame phase is scored in [F] |

### 4.4 [B] Seed processing (new `scripts/19_iterml_seeds.py`)

1. Merge per-processor files and snapshots; drop exact duplicates; apply the grid cap
   and landmark radius (0.05) in the same scaled space the model uses.
2. Compute the flame features of each seed (code from stage 16): Z (Bilger), psi
   (heat-loss fraction towards T_wall; psi < 0 allowed and flagged), progress c,
   strain and chi when written, tau_cell, and the radical excess
   `r = Y_OH / Y_OH,eq(Z, h)`.
3. Assign each seed to a seeded regime (table in 4.5) with simple rules on (c, T, psi, r).
4. Write `seeds.npz` + `seeds.csv` and `seeded_exploration.yaml` (the config block for
   stage 04), plus `seeds_report.md` with counts per regime, Z-T maps and the share of
   seeds that come from OOD, error, drift and pure flags.

### 4.5 [C] Seeded physics exploration (stage 04, new sets)

Each seed only fixes the **starting point**; the pairs come from Cantera with GA18. To
explore around the seed and not just at it, every seed spawns `k` jittered starts:
element-conserving perturbation of radicals (x 10^u, u in +-0.5), psi +- 0.05, and
Z moved by mixing with a small share of either inlet stream.

| Regime | Seeds that go here | Physics run from the seed |
|---|---|---|
| 10 seeded PaSR (new, dynamic) | mixing layer, psi < 0, cells between flame and streams | PaSR with IEM mixing: particles = seed cluster + inlet streams; mixing time from the strain / tau_cell of the cluster (log range x 0.3-3), residence 1-50 ms |
| 11 seeded relaxation | burnt gas with radical excess (r far from 1), near-equilibrium errors | regime 8 started at the seed composition, radical perturbations, t up to 20 ms |
| 12 seeded ignition | induction cells (c < 0.3, T 900-1700 K), drift seeds | 0D autoignition + regime 7 vitiated mixing with a share of the opposite stream |
| 13 seeded cooling | psi > 0.5, cells near walls / hood | regime 3 cooling reactor at tau_q 1 ms-1 s |
| 14 seeded flamelet | high strain or chi seeds | unsteady flamelet at the seed's strain, strain jump x 0.3-3 (deferred: the store does not record strain yet) |

Pairs use the dt range of the run's tau_cell histogram (as `dt_range`), so the
network learns the steps it is really asked for. The seed state itself is never
paired, and any pair that starts within 1e-8 (max |dY|) of a seed is dropped before saving, so not
even a numerical copy of a CFD state reaches training.
A cap keeps seeded pairs at <= 35 % of the training set, so the a priori exploration
still dominates and old regions are not forgotten.

### 4.6 [D] Training

- Warm start from the previous model (`training.init_from`), lr 1e-4, 40 epochs,
  patience 8, replay of all earlier pairs: ~35 min on 2 threads (measured for eqfp8).
- Every third iteration, or when the warm-started model fails the gate, train from
  scratch on the same data (~3-3.5 h) to avoid locking into the parent (seen with eqfp).
- No relative-radical loss: it caused the coupled cold bias in the eqfp line.
- Scalers are kept from iteration 0 unless the new data leave their range by > 5 %.

### 4.7 [E] Gates and registry

A new model goes to the CFD only if, on the offline benchmark (stage 18, alone and
hybrid), it is not worse than its parent by more than the seed spread measured on
2026-10-30 (dT_10ms +- 15 K), and it is better on the new held-out set made of
**this iteration's seeds relaxed by Cantera** (comparison only). Every model is
registered with stage 15 (`--status candidate`, parent id, iteration, seed counts per
regime). Rejected models get `--status discarded` with the reason.

### 4.8 [F] Evaluation

CFD protocol v1, pure mode, 0-50 ms each iteration (DI reference exists to 67.5 ms;
the last model gets the full 100 ms after extending DI). Scored: start phase (ignition
time, nozzle bias) and flame phase (mean flame |dT| T > 1600 K, drift K/10 ms, OH / CO /
CH4 / H L1, V(T > 1500), GA18/OOD share, s/step).

## 5. Stop criteria

### 5.1 Inner (one collection run): table in 4.3.

### 5.2 Outer (the whole ITERML loop): stop when the pure evaluation run meets all of

| Metric (pure, 25-50 ms) | Target | Reference values |
|---|---|---|
| Mean flame abs(dT) vs DI | <= 5 K | ood8 hybrid 3.4 K, ISANN v6 pure 2.1 K, ood1 pure 68.8 K |
| Flame drift | <= 2 K / 10 ms | ood1 pure +20 K / 10 ms |
| Ignition time vs DI | within 0.3 ms | ood8 alone ~1.5 ms early |
| OH total | within x0.7-1.4 of DI | ISANN v6 pure x0.55 |
| OOD share of hot cells | < 1 % | |
| Shadow pass rate | >= 95 % in every T x Z bin | |

Or stop and report when: two iterations in a row improve the flame |dT| by less than
10 %, or after 6 iterations, or when an iteration makes the pure score worse twice in
a row (then the seeded exploration is the problem, not the amount of data).

## 6. Data layout and formats

All under `/mnt/project-files/chemmanifold/iterml/iterK/` (K = 1, 2, ...), large raw
files in the container under `/opt/ofb/iterml/iterK/`:

| File | Content |
|---|---|
| `seeds_raw/processorN.csv` | one row per caught state: `step, time, cell, x, y, volume, T, P, Y_<18 species>, strain, tau_cell, flags (ood, err, bin, drift, pure), manifold_ratio, data_ratio, err_T, err_OH, err_H, err_O, err_CO, bin` |
| `seeds.npz` / `seeds.csv` | deduplicated seeds: the columns above + `Z, psi, c, r_OH, regime, weight` (number of states merged into it) |
| `shadowDI.csv` | every shadow check (pass and fail): state, network result, DI result, dt, bin. Comparison data, kept as the standing rule asks |
| `sentinel.csv` | multi-step sentinel tracks (25 steps network vs GA18) |
| `dtHistogram.csv` | tau_cell histogram of the run |
| `seeded_exploration.yaml` | stage 04 config block written by step [B] |
| `pairs_seeded.npz` | new pairs: as the other `pairs_*.npz`, plus `regime` 10-14, `seed_id`, `excluded` |
| `model/` | `model.pt`, `chemmanifold_model.txt`, `model_card.json`, `config_used.yaml` |
| `benchmark/` | stage 18 output incl. the seed held-out set |
| `eval/` | protocol v1 report and metrics |
| `ITER-REPORT.md` | one page: seeds per flag and regime, new coverage, training, gate, CFD scores, decision for the next iteration |

A loop-level `ITERML-STATUS.md` holds one line per iteration with the table of 5.2.

## 7. Work plan

| Step | What | Effort | Compute |
|---|---|---|---|
| S0 | this roadmap; `configs/iterml/iterml.yaml` with all thresholds of sections 4-5 | done / 1 h | none |
| S1 | userChemStep `iterml` dictionary: seed store (reuse `isannStore.H`), error flag, bin flag, sentinel, stop file read by the supervisor | 4-6 h | compile + 50-step test |
| S2 | `scripts/19_iterml_seeds.py` (merge, dedup, features, regime rules, yaml) | 3-4 h | minutes |
| S3 | stage 04 seeded sets (regimes 10-14), jitter, `excluded` flag, cap | 5-7 h | test on 200 seeds |
| S4 | stage 18 seed held-out set; stage 15 lineage fields | 2 h | minutes |
| S5 | `openfoam/iterml/run_iterml.sh` supervisor: A -> F, resumable, relaunch after the 2 h task limit | 3 h | |
| S6 | dry run of one full iteration on a short window (5 ms collection, 500 seeds, 10 epochs) | | ~2 h |
| S7 | iterations 1..N | | see below |

Estimated cost of one real iteration on this 4-core container: collection run 25 ms
hybrid ~1.5-2 h, seed exploration 1-3 h, warm-start training ~35 min (3.5 h when from
scratch), benchmark 5 min, pure evaluation 50 ms ~3 h. So **~6-9 h per iteration** and
1.5-3 days for 4-6 iterations. With a 32-64 core machine the collection and evaluation
runs could go in parallel with the next exploration and 3 training seeds per
iteration, which would also tell real improvement from seed noise.

## 8. Open choices for Javier

1. **How seeds feed the exploration**: DECIDED 2026-11-01 09:27 by Javier, option (a).
   (a) full seed state as reactor start, seed itself excluded from training
   (recommended, it is what "seeds for PaSR" means and it reaches states like psi < 0
   that the a priori bounds cannot);
   (b) only the seed's flame features (Z, psi, c, strain) are passed on, and reactors
   start from a priori states with those features: stricter with the a priori rule,
   but it may miss exactly the compositions where the model fails.
2. Starting model: ood8 as iteration 0 (recommended, saves a 3-4 h exploration) or a
   fresh flame-feature exploration.
3. Go-ahead for S1-S6 (code + a ~2 h dry run), then for the first real iteration.

## 9. Risks

- **Seeded data crowd out the rest** and the model gets worse far from the burner's
  current solution: the 35 % cap and the old-data replay are there for this; the
  offline benchmark on a priori states catches it.
- **Circularity**: seeds come from the burner solution, so the model is tuned to this
  burner. This is acceptable for the thesis only if stated; the a priori model and the
  ITERML model will be reported side by side.
- **Seed noise vs real gain**: one training seed per iteration cannot rank close models
  (spread 22-62 K on the benchmark). Use 3 seeds for the last two iterations at least.
- **Container limits**: runs die when no harness task is running; the supervisor must
  run as a background task and resume from the last write.

## 10. Implementation (2026-11-01)

| Piece | File | Notes |
|---|---|---|
| Collection mode | `openfoam/userChemStep` (`isann` dictionary, `startActive true`, new `sentinel`), `openfoam/iterml/setup_collect.sh` | reuses the ISANN store: reasons 1 OOD, 2 untrusted bin, 3 shadow check, 4 sentinel; status gains `sentinel,new_boxes` |
| Seeds | `scripts/19_iterml_seeds.py` | network one-step via the UDF C core vs the stored GA18 step, 0D sentinel rollouts, radius dedup, flame features, regime rules; `comparison.csv` keeps every check |
| Seeded exploration | `chemmanifold/seeded.py`, stage 4 `--only seeded` (`pasr.seeded`) | regimes 10-13, jitter, cumulative 35 % cap; stage 5 reads `pairs_seeded*.npz` |
| Settings | `configs/iterml/iterml.yaml` | every threshold of sections 4-5 |
| Driver | `openfoam/iterml/iterml.py run --iter K [--dry]` | collect -> seeds -> explore -> train (5, 7, 12, 15) -> bench (18) -> eval (protocol v1 pure) -> report; resumable via `iterK/state.json` |

# Roadmap: iterative coverage exploration (COVLOOP) with an ARC22 mixture-of-experts surrogate

Requested by Javier on 2026-11-23 (14:38 Spain time, CET). Status: **plan only**, nothing launched.
Written in English; all times are Spain time (CET, UTC+1).

Inputs read for this plan: the Gemini paper draft "A C1-smooth sparse Top-2 Mixture-of-Experts
chemistry integrator ..." (2026-11-20, uploaded as `several-ANNs_variable-dt_dY-Y_final.pdf`), the
Gemini chat "Somers–de Goey 2D flame setup" (uploaded PDF, 8 pages), and the earlier roadmaps and
results in this repository (ITERML, ENSEMBLE, SIM1, the hole-exploration methods, the ARC22 DI runs,
the CFD protocol).

---

## 1. The procedure in one paragraph

COVLOOP starts from a **general** sampling of the thermochemical space that uses only the
mechanism, the inlet streams, the pressure and a temperature range, with no model of any flame. A
mixture-of-experts (MoE) network is trained on it and used in OpenFOAM. During each run, out-of-distribution
(OOD) checks and shadow direct integration (DI) on a spread-out sample of cells mark the bins of
the thermochemical space where the network cannot be trusted. Those bins are the **holes**; the
share of the run's reacting mass that sits in trusted bins is the **coverage**. The states found in
the holes are used as **starting points** for new physics-based sampling, the network is trained
again on the old plus the new physics data, and the cycle repeats until coverage stops improving.

```
 step 1  general sampling (no flame assumptions)  ->  MoE training (dt in, dY out)
            |
            v
 step 2  OpenFOAM run, Case A and Case B (hybrid: OOD cells -> ARC22 DI)
            |
            v
 step 3  OOD + shadow DI  ->  untrusted bins  ->  holes, coverage C_k
            |
            v
 step 4  hole states = starting points for new physics sampling  ->  retrain
            |
            v
 step 5  coverage improved?  yes -> back to step 2     no (plateau) -> stop, final evaluation
```

### 1.1 Rules (fixed for the whole study)

| Rule | What it means in practice |
|---|---|
| R1. No flame-specific assumptions in sampling | No heat-loss or heat-gain models (no cooling reactors, no wall temperatures, no psi-based enthalpy targets, regimes 15/17/18 of `holes.py` are off). No jet-induction or entrainment mixing models (M5 off). No flamelets tuned to a burner (strain from a CFD run, etc.). |
| R2. Never train on DI data | DI results (the hybrid fallback, the shadow checks, the DI reference runs) are **never** training pairs. CFD/DI states are used only as starting points for physics sampling, and the starting state itself is flagged `excluded`. Same rule as ITERML ([javier-methodology]); ISANN stays a separate method. |
| R3. Network | MoE in the style of the Gemini paper: state-only router, top-2 smooth gate, dt as an input to the experts, increment dY as the output (rate form dY = dt * R). |
| R4. CPU only | Training and inference on CPU (PyTorch CPU for training, plain C++ / BLAS for inference inside OpenFOAM). No GPU code paths. |
| R5. Mechanism | ARC_GRI30_NOx22 (22 transported species, 21 QSS species, from GRI-Mech 3.0). Training labels come from the ARC22 kernel itself, not from the 43-species skeleton plus projection. |
| R6. Solver | OpenFOAM v2412, `rhoReactingBuoyantLeFoam` with constant Lewis numbers (the Sc = 1 stock diffusion is known to be wrong, see the simple-flame study). |
| R7. Standing comparison rule | Every run keeps a stratified shadow-DI sample and saves it (comparison data, never training). |

What R1 still allows (my reading; Javier to confirm, see section 11, choice Q1):
sampling the enthalpy dimension **as a box** (initial temperature drawn over a range at a given
mixture fraction), random composition perturbations, generic random-pair mixing of samples that
already exist (a property of any diffusing flow, not of one burner), and relaxation towards
equilibrium. These place states in the space without saying *why* a flame would be there.

---

## 2. What we learned before that shapes this plan

| Earlier result | Consequence here |
|---|---|
| ITERML (Nov 1) and C3/C3b on sim1 (Nov 16-19): CFD-seeded sampling fixed ignition but each iteration cost flame accuracy; warm-started repeats failed the offline gate 1 time in 3; from-scratch repeats drifted after ~120 ms | Train **from scratch** every iteration (2 repeats), cap the share of seeded pairs **per bin** instead of globally, and use long sentinels (section 5.3). |
| Stopping on the CFD score (rules.py S) mixed coverage and accuracy and stopped after 2 rejections | COVLOOP stops on a **coverage plateau**; the CFD score is the final evaluation only, plus a no-regression guard. |
| The 10-step offline gate was blind to slow drift (C3b), and one-step shadow checks missed the early nozzle ignition (ITERML) | Multi-step sentinels (25-200 steps) are part of step 3; a bin is trusted only if both one-step and multi-step checks pass. |
| ISANN-ARC22: one-step T MAE 0.14 K but 0D 2 ms rollouts 53 K; NOx errors invisible until NO, NO2, N2O, HCN were added to the trust bins | Trust criteria include NOx species from the start, with the floors that worked (section 5.2), and training uses a rollout loss. |
| ARC22 parent a: closed-loop minor-species drift (H2O2, C2H6) in lean, cooled states; labels from the ARC kernel fixed nothing by themselves, rollout loss (parent b) did | Rollout loss on by default; per-expert output scaling (paper section 2.5) targets exactly this trace-species problem. |
| Our own dY,dT ISANN test (Nov 2): flame fine, lean burnt gas CO/OH much worse than Y(t+dt) | The paper's fix for trace species (per-cluster local output scaling, shifted Box-Cox floor) must be in from day 1; gate G0 checks lean burnt gas explicitly. |
| ood3 (Oct 29): a very wide dt range (1 us-50 ms) hurt the flame at the 2e-5 s flow step | dt range set from the run's own dt histogram (p0.5-p99.5), sampled with the histogram's density, rate formulation. |
| Hole methods M1-M7 (Nov 10): main hole of the burner was warm lean gas Z < 0.035, 600-950 K, caused by heat loss | Under R1 these holes must now be reached from **starting points** (step 4), not by a heat-loss model. This is the scientific test of the method. |
| Paper reference points: ISAT 1e-4 S 0.67 on GA18; best physics-only network P_tix2c S 2.00; ISANN-ARC22 run 2 flame 5.2 K | Final comparison bars (section 8). |

The Gemini paper is an unreviewed draft with placeholder authors; its numbers come from a small
premixed autoignition dataset (45.7k states, dt 0.2-5 us, GRI-Mech 3.0). We take its design, not its
numbers. Our dt range is wider (about 3 decades instead of 1.4) and our space includes non-premixed
mixing, so its claims must be re-shown here.

---

## 3. The two cases

### Case A: our classical non-premixed burner (exists)

- Geometry, mesh and boundary conditions of `openfoam/quemadorUnico` with the corrected outlets
  (top and chimney open, side wall), wall radiation by fvDOM (transparent gas, 256 rays) and the pot
  walls at the frozen temperature profile used in the ARC22 extension to 0.3 s.
- ARC22 DI reference: `/opt/ofb/runs/arc22` on sim1, flame leg to 0.3 s (fields
  `results/sim1/ARC22/fields/`) and the ignition leg 0-25 ms (ignition 2.8 ms). The GRI-53 same-code
  run (ending tonight, ETA ~23:30 CET Mon 23 Nov) is the check of ARC22 itself.
- Two legs per run, as in ITERML v2: **ignition leg** 0-25 ms from the lean lit start, and **flame
  leg** 25 ms from a settled flame state.

### Case B: Somers–de Goey 2D laminar premixed slit burner (to build)

From the uploaded chat (values to be checked against the original paper, L.M.T. Somers and
L.P.H. de Goey, Combust. Sci. Technol. 108 (1995), before the case is frozen):

| Item | Value |
|---|---|
| Domain | planar 2D half domain, 1 cell deep (`empty` front/back), x 0-6 mm, y 0-40 mm (the 12-16 mm canonical box extended to 40 mm so that thermal NO has 10-12 ms of residence time) |
| Inlet | y = 0, x 0-2 mm (4 mm full slit), CH4/air phi = 1.0, 298 K, Poiseuille u = 1.1 m/s [1 - (x/2 mm)^2] |
| Burner rim and side wall | y = 0, x 2-6 mm and x = 6 mm: no slip, zero species flux, isothermal 298 K |
| Axis | x = 0 symmetry plane |
| Outlet | y = 40 mm, 1 atm, zero gradient / inletOutlet |
| Mesh | 20-25 um cells across the flame (about 20 cells per 0.43 mm flame thickness), stretched to 150 um outside and to ~0.5 mm above y = 10 mm; ~35-45k cells |
| Start | fresh reactants for x <= 2 mm, y <= 5 mm; burnt gas elsewhere from an HP equilibrium of the **major C/H/O species plus N2 only**, with NO, NO2, N2O, HCN set to zero (the chat warns that equilibrium NO, ~2000 ppm, poisons the slow rim region for many flow-through times) |
| Steady state | ~1.5-2 flow-through times; the cone is ~5-7 mm high |
| Expected regimes | cooled rim foot (heat loss, quenching, NO to NO2 by HO2), quasi-1D flank, negatively curved tip, adiabatic post-flame plume with slow thermal NO |

Case B is a good test of R1: its rim heat loss and curvature are exactly the things the general
sampling is not allowed to model. Variants in the chat (phi = 0.75 second run; rich slit with air
co-flow for a double flame) are **not** part of this plan unless Javier asks (Q4).

Case B checks before it can be used (gate G1): grid independence of the cone height on 2 meshes,
flank burning velocity vs the 1D ARC22 flame speed (Cantera, ARC22 vs GRI already within 1.3 %),
burnt T vs adiabatic, and a short LTS-vs-transient check.

---

## 4. Step 1: general sampling (iteration 0)

Inputs only: the ARC22 mechanism, the inlet streams of both cases (CH4, air, premixed phi = 1.0
reactant), p = 1 atm and a temperature box 298-2400 K. Mixture fraction Z (Bilger) spans 0-1; the
premixed reactant is the point Z = 0.055.

| Set | What it does | Share (first guess) |
|---|---|---|
| G1 homogeneous reactors | Adiabatic constant-pressure reactors, Latin hypercube over (Z, T0): Z log-spaced in 0-1 with extra density around Z_st, T0 298-1800 K; integrated through ignition to equilibrium, states taken by arc length | 40 % |
| G2 equilibrium and relaxation | HP equilibrium over the (Z, h) box, then relaxation from perturbed equilibrium (radicals scaled 0.1-10x, majors +/-3 %) | 15 % |
| G3 composition perturbations | Around G1/G2 states: multiplicative noise on majors (+/-3 %) and radicals (+/-0.25 decade), enthalpy box shift +/-65 K, element-conserving projection (the paper's off-manifold set) | 20 % |
| G4 generic mixing | Random pairs of existing states (any set, any Z), mixed at a random fraction, then reacted; no stream or flow model | 15 % |
| G5 low-temperature mixtures | Frozen and slowly reacting mixtures 298-950 K over all Z, some with up to 12 % products from G1 | 10 % |

Labels: for every state, **several dt** drawn log-uniformly from the dt range (initially 1 us-1 ms
from the 2026-10-29 tau_cell histogram; refined after the first run), with 2-3 dt per state. The
ARC22 kernel (Rosenbrock, relTol 1e-8 for labels) gives Y(t + dt); the target is dY. Sampling code:
existing stages 01-04 with a new config `configs/covloop_general.yaml` that switches off regimes
5-8, 15-21 (flamelets tied to burner strain, heat loss, jet mixing) and adds G4/G5 if the existing
`pasr` options cannot express them.

Size: aim at 300-500k states (0.6-1.5M pairs). The paper used 41k states for a much narrower space.

---

## 5. Steps 2-3: the run, the holes and the coverage

### 5.1 Coverage grid (case-independent)

Each cell state is placed in a bin of a fixed grid built from quantities any state has:

| Axis | Bins |
|---|---|
| Mixture fraction Z (Bilger) | 12 bins, log-spaced 1e-3 to 1 plus a bin for Z < 1e-3, refined around Z_st |
| Temperature T | 300-2400 K in 100 K bins (21) |
| Progress c = (Y_CO2 + Y_CO) / (same at HP equilibrium of this Z and h) | 5 bins |
| Enthalpy excess dh = h - h_mix(Z) (a measurement, not a model) | 3 bins: below -50 kJ/kg, near zero, above +50 kJ/kg |

About 3800 bins, of which only a few hundred are ever visited. Case B lives almost on one Z
column; the same grid works for both cases. The dt axis is kept apart (section 5.4).

Only reacting cells count: T > 450 K or c between 0.02 and 0.98. Each cell is weighted by its
mass, and runs are averaged over the written times of the leg.

### 5.2 What makes a bin untrusted (a hole)

A bin is a **hole** if any of the following is true over the leg:

1. **OOD**: more than 5 % of its mass is flagged by the MoE trust gate (local PCA residual of the
   chosen expert above gamma * q0.995, gamma = 2.4) or by the existing data-density check.
2. **One-step shadow error**: every N = 25 steps, 3 cells per visited bin are copied and integrated
   with ARC22 DI over the same dt. The bin fails if more than 10 % of its checks fail
   `|T_ann - T_DI| > max(1 K, 0.3 |dT_DI|)`, or for OH, CO, H, O
   `|Y_ann - Y_DI| > max(5e-5, 0.3 |dY_DI|)`, or for NO, NO2, N2O, HCN the same with floors
   3e-6, 2e-7, 5e-8, 2e-6 (the ISANN-ARC22 values). A bin needs at least 6 checks to be judged;
   fewer = **unverified**.
3. **Multi-step sentinel**: every 100 steps, 2 cells per visited bin are copied and integrated for
   25 and 200 steps alongside the network (frozen flow, same dt). The bin fails if T drifts more
   than 20 K or OH/CO/NO more than 1.5x.

Unverified bins count as **not trusted** in the coverage number (so coverage can only rise by
real checks), and the shadow sampler gives them priority in the next run.

### 5.3 Coverage metric

```
C = sum over bins b of  m_b * 1[b trusted]   /   sum over bins b of  m_b
```

with m_b the time-averaged reacting mass in bin b. Reported per case and leg, and also:

- **C_data**: the same sum with "trusted" replaced by "in-distribution" (data coverage only,
  model-independent);
- **C_ref**: C computed on the fixed ARC22 DI reference snapshots by one-step and sentinel checks
  offline (an a-priori evaluation, never training). It has a fixed denominator, so it shows
  whether a rise of C is real or only because the network's own run moved into easier states.
- **hole list**: bins sorted by m_b, with Z, T, c, dh, and which test failed.

Headline number per iteration: **C = mass-weighted mean of C over the four legs** (A ignition,
A flame, B start-up, B steady), with each case weighted 1/2.

### 5.4 dt coverage

The chemistry dt that OpenFOAM passes to the plug-in (deltaT for transient runs, the local deltaT
for LTS runs) and tau_cell = 0.1 min(t_diff, t_conv) are both kept **as histograms only**
(`dtHistogram.csv`, `tauCellHistogram`). dt coverage = share of reacting cell-steps whose dt is
inside the training dt range. Below 99 %, the next iteration widens the range to the run's
p0.5-p99.5.

### 5.5 Runs in step 2

- **Collection runs are hybrid**: OOD cells go to ARC22 DI (`arcChemStep` kernel), so the run stays
  physical and the holes are real. DI results are written only to the comparison files.
- Same start, same length and same writes in every iteration, so C is comparable: Case A
  ignition 0-25 ms and flame 25 ms from the settled state; Case B start-up 0-10 ms from the patch
  start and 10 ms from its settled DI state.
- Inner stop of a leg: the ITERML table (seed store saturated, 6000 states, model lost, divergence,
  time limit).

---

## 6. Step 4: new sampling from the holes

1. **Collect** the states of every hole bin (OOD cells, failed shadow and sentinel cells, plus a
   sample of passing cells in the same bin), deduplicated at three levels as in ITERML
   (1 state per fine grid box in the run, radius within the iteration, radius against all earlier
   iterations). Hard cap 15000 starting states per iteration.
2. **Exclude** each starting state from training (flag `excluded`). Only the reactor results
   started from it can be training pairs.
3. **Generic operators**, the same ones as step 1, applied around each starting state:
   - S1 reactor from the state, with jitter (majors +/-3 %, radicals +/-0.25 decade, h +/-20 kJ/kg),
     integrated for 1-30 ms, states by arc length;
   - S2 relaxation to equilibrium from the state with radicals scaled 0.1-10x;
   - S3 random-pair mixing between starting states and between a starting state and the general
     set (random fraction), then reaction;
   - S4 perturbation cloud inside the hole bin (box over the observed species ranges in that bin,
     element-conserving projection), short integration.
   No operator uses a wall temperature, a heat-loss rate or a flow-derived mixing law. The heat-loss
   states of Case A's walls or Case B's rim are reached only because the starting states already
   carry their enthalpy.
4. **Labels** with several dt from the current dt range (ARC22 kernel).
5. **Balance**: per-bin cap so no hole bin holds more than 3x the median training density of
   trusted bins; overall seeded share at most 35 % of the training set.
6. **Train from scratch** on general + all seeded sets (2 repeats with different training seeds;
   the repeat spread is the noise level of the coverage test).

---

## 7. The network (MoE, dt in, dY out, CPU)

Adapted from the Gemini paper to ARC22:

| Part | Choice |
|---|---|
| Input features | T, and shifted Box-Cox of the 22 transported Y (lambda 0.1, floor 1e-10); p dropped (fixed 1 atm) |
| Router | state only (no dt), Linear(23, 64) - SiLU - Linear(64, K); router never sees dt so a changing time step cannot make cells switch expert |
| Partition | Jacobian-scaled k-means (stiffness weight alpha 4), K = 6 to start, re-clustered every iteration; K raised to 8-12 if a cluster's local PCA explains < 98 % or the hole list concentrates in one expert |
| Buffers | tangential overlap, theta 0.80, so neighbouring experts are trained on shared states |
| Gate | top-2 Hermite C1 gate, tau 2.5; interior cells evaluate one expert, boundary cells two |
| Experts | SiLU MLP 3 x 128, input = features + standardised log10(dt) |
| Output | rate R, dY = dt * R, with per-expert output scaling folded into the last layer |
| Training | stage 1A router on cluster labels, 1B experts on their buffered subsets, 2 joint fine tuning (global + local MSE, load balance) plus a **rollout loss** (24-step segments from 10 % of epochs, weight 0.5, as ARC22 parent b), CPU, 8 threads |
| Conservation | element null-space projection (C, H, O, N; 4 x 22), batched positivity cleanup, T from h by NASA-7 Newton (3 iterations) |
| Trust gate (also the OOD flag of step 3) | local 8-component PCA residual per expert, inter-expert discrepancy on boundary cells (L1 > 0.05), positivity (min Y < -5e-3) |
| Frozen cut-off | T < 450 K and c < 0.02: no chemistry (measured, can be switched off) |
| Inference in OpenFOAM | C++ inside the ARC22 chemistry plug-in (`openfoam/arcChemStep` + the `userChemStep` model loader), plain BLAS, new model file v3 (experts, router, PCA bases, scalings); parity with PyTorch < 1e-8 |

Single-ANN control (same data, parameter-matched) is trained once at iteration 0 and once at the
end, to place COVLOOP against the earlier single-network results and against paper 4 of the
paper plan (single vs several ANNs).

---

## 8. Gates, stop criterion and final evaluation

| Gate | When | Pass condition | If it fails |
|---|---|---|---|
| G0 code | after stage 0 | MoE trainer + C++ inference parity < 1e-8; OpenFOAM selftest; 0D ARC22 tests: ignition delay error < 5 % on 18 held-out cases, 2 ms rollouts T MAE < 20 K in lean burnt gas and cooled mixtures (our known weak spot) | fix code; nothing heavy starts |
| G1 references | Case B built | Case B ARC22 DI: grid-independent cone height (< 3 %), flank S_L within 5 % of 1D ARC22, steady to < 1 % in heat release over one flow-through; Case A reference fields present | fix case B; Case A can start alone |
| G2 iteration 0 | after the first runs | both cases run to the end of all legs in hybrid mode with OOD share < 30 %; C_0 and the hole list written | widen the general box (still R1), retrain |
| G3 per iteration | after each iteration | new C > old C + max(1 pp, 2 x repeat spread), C_ref does not fall, the pure-mode flame score of Case A does not get worse by more than its spread | count as "no improvement" |
| Stop | after G3 | **coverage plateau: 2 iterations in a row with no improvement**, or C >= 0.98 in both cases, or 8 iterations | go to final evaluation |
| Final | at stop | pure mode, both cases: Case A protocol v2 (ignition + 50 ms flame); Case B 20 ms from the start and 10 ms steady | report |

The plateau rule is the one Javier asked for (step 5). The 1 pp floor is a first guess; the repeat
spread at iteration 0 will tell whether it is above the noise.

Final comparison table (both cases, vs ARC22 DI): flame |dT| (T > 1500 K), ignition delay
(Case A) or cone height and flame position (Case B), OH, CO, NO, NO2, N2O, HCN L1, heat release,
OOD share, s/step and speed-up against DI, coverage C and C_ref. Bars: ISAT 1e-4 on Case A (S 0.67
with GA18; one ARC22 ISAT run would make this a same-mechanism bar, about 4 h on 8 ranks, Q5),
ISANN-ARC22 run 2 (CFD-adapted, flame 5.2 K), the single-ANN control.

---

## 9. Stages, run locations and cost

All heavy runs on **sim1** (16 cores, no 2 h cut) by default, per the run-location rule; the cloud
thread writes code, runs smoke tests and analyses; Javier's PC is not needed (no Fluent). To be
confirmed by Javier (decision card in the thread).

| Stage | Work | Where | Cost (estimate) |
|---|---|---|---|
| 0 | Code: `chemmanifold/moe.py` (trainer, export), dt-aware ARC22 labeller, `configs/covloop_general.yaml` + G4/G5 sets, `scripts/25_coverage.py` (grid, holes, C, C_data, C_ref), shadow + sentinel bins in the plug-in, model file v3 C++ loader, `openfoam/slitBurner/` case builder, `openfoam/covloop/covloop.py` driver with frozen rules | cloud | 2-3 thread-days, smoke tests only |
| 1 | Case B: coarse smoke (cloud, 4 cores, ~1 h), then 2 meshes x ARC22 DI to steady (LTS first, then 10 ms transient) | sim1, 8 ranks | ~1-1.5 days wall (unverified: ~40k cells at ~2-5 us flow steps) |
| 2 | G0 offline tests; iteration 0 general sampling (ARC22 labels) and 2 training repeats | sim1, 8 cores | sampling 4-8 h, training 4-8 h per repeat (paper: 8 min for 41k states; ours ~10x data and rollout loss) |
| 3 | Iteration k: 4 hybrid legs (A ignition, A flame, B start-up, B steady) | sim1, 2 x 8 ranks | ~6-10 h |
| 4 | Coverage + holes + seeded sampling + 2 trainings from scratch | sim1 | ~8-12 h |
| 5 | Repeat 3-4 until the plateau rule stops it | sim1 | ~14-22 h per iteration, 3-8 iterations: 2-7 days |
| 6 | Final evaluation (pure) + single-ANN control + report | sim1 + cloud | ~1 day |

sim1 is busy until the GRI-53 extension ends (~23:30 CET Mon 23 Nov); Case A can start at the
earliest Tue 24 Nov once stage 0 code passes G0. Every run is a resumable systemd user unit with an
automatic report, as in the C2/C3 campaigns, and nothing starts on sim1 without Javier's typed OK
in the thread.

---

## 10. Outputs

- `results/covloop/iterK/`: coverage tables (C, C_data, C_ref per case and leg), hole maps (Z-T and
  T-c projections), shadow and sentinel CSVs (comparison only), dt histograms, starting-state
  counts by operator, training summary, registry card (tag `covloop-iterK`).
- `results/covloop/SUMMARY.md`: coverage curve C_k vs iteration for both cases, which holes closed
  and which never did (and why: none of the generic operators reaches them), final evaluation table.
- Model files v3 for the final MoE and the single-ANN control in `models/` and the Library.
- Material for paper 1 (physics-only exploration; the claim becomes "a flame-agnostic start plus
  hole-seeded physics sampling reaches coverage X on two very different flames") and paper 4
  (single vs mixture of experts).

---

## 11. Open choices for Javier

| # | Question | Default in this plan |
|---|---|---|
| Q1 | Does R1 allow the enthalpy box, random-pair mixing (G4/S3) and relaxation, as written in 1.1? | yes |
| Q2 | Canonical 1D flames (freely propagating premixed, counterflow) in step 1? They are not tied to a burner but they are flame structures | **no** (stricter reading of R1); can be an ablation |
| Q3 | One shared training database and MoE for both cases, or one loop per case? | shared (tests generality; coverage still reported per case) |
| Q4 | Case B variants (phi = 0.75, rich slit with air co-flow) | not included |
| Q5 | ARC22 ISAT 1e-4 run on Case A as the same-mechanism bar | yes, at the end (~4 h, 8 ranks) |
| Q6 | Run location | sim1 for all heavy runs (decision card) |

---

## 12. Risks

| Risk | Handling |
|---|---|
| Holes caused by heat loss (Case A pot, Case B rim) are never closed without a heat-loss model | That is a valid result of the study. Step 4 starts from the hole states themselves, which already carry the enthalpy deficit; the hole list will show if a hole persists. |
| Coverage rises only because the hybrid run moves (moving target) | C_ref on fixed DI snapshots is reported every iteration and must not fall (G3). |
| Coverage noise larger than the 1 pp step | the threshold is max(1 pp, 2 x repeat spread). |
| Wide dt range hurts accuracy (as ood3) | rate form, dt range from the histogram, per-dt-band error report at G0. |
| MoE gate chatters in OpenFOAM at expert boundaries | C1 gate, buffers, and the count of expert switches per cell per 100 steps is logged. |
| dY output worsens lean burnt gas (our Nov 2 test) | per-expert scaling and Box-Cox floor; G0 tests lean burnt gas explicitly. |
| Case B cost higher than estimated | coarse smoke first; LTS for the steady state; reduce Ly to 25 mm if needed (thermal NO then partly cut). |
| sim1 Remote Control usage limits pause reports for a day | systemd units keep running; each stage writes its own report file. |
| Somers–de Goey values in the chat are not checked | check against the 1995 paper before G1. |

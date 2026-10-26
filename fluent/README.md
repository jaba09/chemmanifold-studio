# Using the surrogates in Ansys Fluent

This folder plugs the trained ResNet-FiLM or Phy-ChemNODE surrogate into Fluent's chemistry step.
Fluent then calls the network for each cell instead of integrating GA18 with its stiff ODE solver.
It also tracks which cells fall outside the sampled training space and helps you measure how well the
surrogate does against a direct-chemistry run.

```
fluent/
├── udf/
│   ├── chemmanifold_udf.c     Fluent hooks: DEFINE_CHEM_STEP, DEFINE_ADJUST monitor, load/reload/self-test
│   ├── chemmanifold_core.c    the surrogate in plain C (networks, physics layers, OOD checks)
│   └── chemmanifold_core.h
└── tests/
    ├── run_tests.sh           checks the C code outside Fluent (Linux, macOS, WSL)
    ├── cm_selftest.c          C core vs the PyTorch test vectors, plus timing
    ├── mock_fluent.c          drives the Fluent hooks through a stand-in udf.h
    └── mock/udf.h
scripts/12_export_fluent.py    trained model -> chemmanifold_model.txt + chemmanifold_tests.txt
scripts/13_fluent_compare.py   surrogate Fluent run vs reference Fluent run (direct GA18)
scripts/14_fluent_apriori.py   per-cell Cantera check of a Fluent solution + coverage maps
```

**Use ResNet-FiLM.** Phy-ChemNODE is supported in the same way, but it is not stable on this flame yet.
It ignites late and in one rich case it collapses to the 280 K solver bound (see `RESULTS.md`). The UDF
prints a warning when you load it.

## 1. Export the model

After training (stages 0–11), run:

```bash
python run_pipeline.py --from 12 --to 12 --arch resnet_film      # or: python scripts/12_export_fluent.py --arch resnet_film
```

This writes `data/08_fluent/resnet_film/`:

| File | What it is |
|---|---|
| `chemmanifold_model.txt` | weights, scalers, NASA-7 and element tables, OOD tables (one text file, ~5 MB) |
| `chemmanifold_tests.txt` | 60 cases computed with the PyTorch model that the compiled UDF checks itself against |
| `export_report.json` | trained dt range, fraction of validation states the OOD checks flag (about 0.1–0.3% by design), float32 vs float64 difference |

Copy the two `.txt` files into the folder Fluent runs in (next to the case file).

Optionally, check the C code on your machine before going into Fluent. This needs Linux, macOS or WSL with a C compiler:

```bash
fluent/tests/run_tests.sh data/08_fluent/resnet_film
```

## 2. Build the UDF in Fluent

Written for **Fluent 2020 R2 (20.2), double precision**, which is the version of the burner case. It
uses only the standard UDF API, so newer versions should work too.

1. Copy `fluent/udf/chemmanifold_udf.c`, `chemmanifold_core.c` and `chemmanifold_core.h` into the case folder.
2. Go to *User-Defined > Functions > Compiled…*. Add **both `.c` files** under *Source Files* and
   `chemmanifold_core.h` under *Header Files*. Click *Build*, then *Load* with the library name `libudf`.
   On Windows you need either Visual Studio (Build Tools) or the *Use Built-In Compiler* option that
   2020 R2 offers.
   The TUI equivalent is:
   ```
   /define/user-defined/compiled-functions compile libudf yes chemmanifold_udf.c chemmanifold_core.c "" chemmanifold_core.h ""
   /define/user-defined/compiled-functions load libudf
   ```
3. On load, the console prints `chemmanifold: loaded chemmanifold_model.txt (resnet_film, 18 species, …)`.

The old example UDF (the one with the `exp(-dt)` decay) must not be in the same library, because it
defines the same `user_chem_step` name.

## 3. Set up the case

The burner case already has *Species Transport*, *Laminar finite-rate* with *Stiff Chemistry Solver*,
and the hook `user_chem_step::libudf`, so most settings carry over.

| Where | Setting |
|---|---|
| *User-Defined > Memory* | **7** user-defined memory locations (the OOD fields below) |
| *User-Defined > Function Hooks* | *Chemistry Step*: `user_chem_step::libudf` (already set in the case) |
| | *Adjust*: `chemmanifold_monitor::libudf` (per-iteration OOD log) |
| | *Execute on Loading*: `chemmanifold_on_load::libudf` (optional: the hook also loads lazily) |
| *Species > Integration Parameters* | turn ISAT off (direct integration), so that every cell calls the hook |
| *User-Defined > Execute on Demand* | run `chemmanifold_selftest::libudf` once. It should print `selftest passed: 60/60 cases match PyTorch` |

Start from a burning solution, either your converged GA18 solution or a hot patch. The surrogate replaces
chemistry; it does not ignite a cold field any differently than GA18 would.

### Options: `chemmanifold.ini`

Put this optional file in the working folder. After you change it, run `chemmanifold_reload` on demand.

```ini
model = chemmanifold_model.txt     # model file (relative to the working folder)
tests = chemmanifold_tests.txt
log = chemmanifold_monitor.csv     # per-iteration OOD log
T_freeze = 600                     # K; colder cells are not advanced (CH4 chemistry is frozen there)
max_substeps = 50                  # surrogate steps per call at most
ood_action = 0                     # 0 = only flag OOD cells; 1 = also leave them unreacted
T_margin = 25                      # K, tolerance on the T range checks
y_margin = 0.25                    # tolerance on species ranges, in Box-Cox standard deviations
p_tol = 0.05                       # relative pressure tolerance around 1 atm
check_ood = 1                      # 0 skips the OOD checks (a little faster)
write_udm = 1
verbose = 0                        # 2 prints every cell call (debugging only)
```

## 4. What the hook does (model I/O)

For each cell, Fluent passes the mass fractions `yk` (18 species), the temperature, the pressure and
the chemistry time step `dt`. It expects the mass fractions after `dt` at constant pressure and
enthalpy. The UDF then does the following:

1. **Species mapping.** Fluent's species are matched to the model's by name. GA18 `CH2(S)` becomes
   Fluent's `ch2<s>`. If the names cannot be matched, the UDF falls back to the mechanism order
   (`h2 h o o2 oh h2o ho2 h2o2 ch2 ch2<s> ch3 ch4 co co2 hco ch2o ch3o n2`, which is the case's order)
   and prints a warning.
2. **Enthalpy.** h is computed from (Y, T) with the mechanism's NASA-7 polynomials, the same data that
   produced the training h, and is held constant.
3. **Encoding.** The network sees the same inputs as in training:
   * species: Box-Cox (λ = 0.1, ε = 1e-15), then z-scored with `mu_y`, `sigma_y`;
   * context: (T, P, h, log10 dt), z-scored with `ctx_mu`, `ctx_sigma`.
   * The models were trained at exactly 1 atm, so the pressure scaler has σ ≈ 1e-11 Pa. The UDF
     therefore always feeds the network the trained pressure. Otherwise a few Pa of pressure change in
     the CFD would push the input millions of standard deviations away. The real pressure is only used
     for the pressure OOD flag. If Fluent passes a gauge pressure, the operating pressure is added.
4. **Network.** ResNet-FiLM (input layer, 3 FiLM residual blocks, output increment) or Phy-ChemNODE
   (encoder → RK4 latent ODE with 2 substeps → decoder difference). All of it runs in double precision.
5. **Hard physics.** Box-Cox is inverted and clipped to [0, 1]. Then the abundance-weighted null-space
   projection runs (3 active-set passes), so element mass is conserved to round-off and Y ≥ 0. Finally,
   4 Newton iterations recover T from h for the next substep.
6. **Time step.** The model was trained on dt = 10, 20 and 40 µs.
   * For dt in that range or above, the UDF takes `n = ceil(dt / 40 µs)` equal steps.
   * Below 10 µs, it takes one 10 µs step and scales the increment by dt/10 µs. The scaled state still
     conserves elements and stays non-negative.
   * Above `max_substeps × 40 µs` (2 ms by default), the UDF caps the steps, so chemistry advances less
     than dt. Those cells are counted as `dt_capped`. In a steady run Fluent's chemistry dt is a pseudo
     time step, so check `mean_substeps` and `dt_capped` in the log. If many cells are capped, raise
     `max_substeps` (cost grows linearly) or lower the pseudo time step.

The cost is about 0.15 ms per surrogate step per cell on one core (gcc -O2). Cells below `T_freeze`
cost almost nothing.

### Expected CPU saving

Measured on one core of a 2.8 GHz Xeon, over 400 training states at T ≥ 600 K. The direct-chemistry
proxy is Cantera's CVODES constant-pressure reactor with Fluent's tolerances (rtol 1e-5, atol 1e-10),
timing only the integration. Fluent's own stiff solver was not timed.

| Chemistry dt | Direct GA18 (CVODES) | Surrogate, ResNet-FiLM (UDF core, with OOD checks) | Speed-up |
|---|---|---|---|
| 10 µs | 590 µs/cell (21 steps) | 160–210 µs/cell (1 step) | ~3–4× |
| 40 µs | 760 µs/cell (30 steps) | 155 µs/cell (1 step) | ~5× |
| 100 µs | 900 µs/cell (39 steps) | 430 µs/cell (3 steps) | ~2× |
| 1 ms | 1600 µs/cell (77 steps) | 4100 µs/cell (25 steps) | **0.4× (slower)** |

* The surrogate is a fixed-cost 40 µs step, while the cost of a stiff solver grows slowly with dt. So the
  saving exists only while Fluent's chemistry dt stays within about 10–100 µs. Check `mean_substeps`
  in the log: 1–2 means you are in the fast regime.
* Fluent with ISAT on (the default for stiff chemistry) can cut direct-chemistry cost by a further 10×
  or more in a steady flame, which can erase the gain. Compare against the setting you actually use.
* Chemistry is only part of each iteration. The wall-clock saving is 1 / ((1 − f) + f / s), where f is
  the share of iteration time spent in chemistry and s is the speed-up above. For example, f = 0.7
  and s = 5 give about 2.3× overall.
* The OOD checks add 5–30% to the surrogate's cost. Set `check_ood = 0` once you trust a run.
* The main levers for more speed are a model trained on larger dt (strides up to ~1 ms, so one call
  covers Fluent's step) and a smaller network. The 192-wide ResNet is ~0.23 M multiply-adds per step.

## 5. Is the model working outside the sampled space?

For each cell it advances, the UDF runs six checks. They use the training states that
`12_export_fluent.py` stored in the model file:

| Bit | Name | Fires when |
|---|---|---|
| 1 | `T` | T outside the training range (300–2076 K in the reference run) ± `T_margin` |
| 2 | `T_at_Z` | T outside the training T range of the cell's mixture-fraction band (32 bands, fine around Z_st), for example hotter than any training state at that Z |
| 4 | `pressure` | \|p/1 atm − 1\| > `p_tol` |
| 8 | `species` | any species outside its training range (Box-Cox units) ± `y_margin` |
| 16 | `manifold` | the state is off the training manifold: its VQ-PCA residual (4 clusters, d = latent dim) exceeds the 99.9% quantile of the training residuals |
| 32 | `data` | the state is far from all training states: its distance to the nearest of 1024 training landmarks exceeds the 99.9% quantile of the training distances |

Other bits describe what the step did: 64 `dt_capped`, 128 `frozen` (T < T_freeze, no checks), 256
`invalid` (non-finite output; the cell keeps its input state), 512 `dt_scaled` (dt < 10 µs), and
1024 `ood_skipped` (when `ood_action = 1`).

The checks use the same coordinates as stage 11 (Box-Cox z-scores of all species, plus z-scored T), so
`data_ratio > 1` corresponds roughly to stage 11's "not covered".

**User-defined memory:** these fields are available for contour plots under *User Defined Memory*.

| UDM | Field |
|---|---|
| 0 | `ood_any`: 1 if any check fired. Contour this first. |
| 1 | `ood_flags`: the bitmask above. For example, 48 = manifold + data. |
| 2 | `manifold_ratio` (> 1 = off-manifold) |
| 3 | `data_ratio` (> 1 = far from the training data) |
| 4 | mixture fraction Z (Bilger) |
| 5 | heat release rate [W/m³] of the surrogate step, −ρ Σ h°f,k ΔY_k / dt |
| 6 | surrogate steps used for the cell |

**Per-iteration log:** the `chemmanifold_monitor` adjust hook prints one line per iteration. It also
appends a row to `chemmanifold_monitor.csv` with these columns: `iteration, flow_time, cells,
advanced, frozen, ood_skipped, invalid, dt_capped, dt_scaled, mean_substeps, ood_any, ood_T,
ood_T_at_Z, ood_pressure, ood_species, ood_manifold, ood_data, ood_fraction,
max_manifold_ratio, max_data_ratio`. The counts refer to the chemistry calls of the previous iteration,
summed over all compute nodes.

How to read it:
* An `ood_fraction` around 0.1–1% of the advanced cells is the noise level of the 99.9% thresholds.
* Persistent clusters in the UDM 0 contour show where the CFD visits states that were never sampled.
  Common places are the flame base near the burner rim, cooled states near the walls, and the rich
  core. Compare the error maps of stage 13 with these regions.
* A region that keeps growing during the iterations is the warning sign.
* To cover such states, retrain with more seeds there. Useful knobs are `envelope.z_knots`/`u_knots`,
  `heat_loss_max`, and `pasr.dh_range`.

## 6. How good is the surrogate in Fluent?

**A-posteriori, against direct chemistry (stage 13).** This is the definitive test.

1. Run the same case twice:
   * the reference: GA18 with the stiff ODE solver (set the *Chemistry Step* hook to `none`);
   * the surrogate run: with the hook.
   Converge both from the same initial solution.
2. Export each with *File > Export > Solution Data…*: type **ASCII**, location **Cell Center**,
   delimiter comma. Include:
   * *Temperature*, *Absolute Pressure* and the mass fractions of **all 18 species**;
   * *Cell Volume* and *Density*;
   * for the surrogate run also *User Defined Memory 0–6*;
   * if you want heat-release metrics, the heat of reaction field in both runs.
3. Run:
   ```bash
   python scripts/13_fluent_compare.py --ref ref.csv --run surrogate.csv --label resnet [--hrr-col <column name>]
   ```
   It writes `data/08_fluent/compare_resnet/compare.json` and `compare.png`:
   * T MAE / RMSE / max and volume-weighted MAE, overall, in hot cells, and separately in cells
     flagged OOD vs not flagged (this tells you whether the flags point at the errors);
   * peak T and its location;
   * NRMSE per species;
   * total and peak heat release;
   * flame length (furthest axial point on the axis with Z ≥ Z_st);
   * conditional means ⟨T|Z⟩, ⟨Y_CO|Z⟩, ⟨Y_OH|Z⟩ and ⟨Y_CO2|Z⟩;
   * a map of the T error with the OOD region outlined.

**A-priori, cell by cell (stage 14).** This one needs no second Fluent run:

```bash
python scripts/14_fluent_apriori.py --run surrogate.csv --label resnet --cells 3000 [--dt 4e-5]
```

It samples cells (T ≥ 600 K) from any export and advances each one over dt with both Cantera (GA18)
and the surrogate, using the UDF's own sub-stepping. It reports the single-step T error, the
heat-release error and the Box-Cox increment R², split by flagged/not flagged and covered/not covered.
It also plots the error against the distance to the training data, which shows whether the error grows
outside the sampled space. Running it on the reference export shows how well the training data covers
the true flame, before you trust any surrogate run.

What to expect, from the certification of the full training run (RESULTS.md):
* ResNet-FiLM's single step matches to 0.02 K MAE.
* In closed loop it ignites on time but settles 30–45 K low near stoichiometric. In the rich case
  (Z = 0.08) it is 155 K low.
* So in Fluent, look first at the peak temperature and at ⟨T|Z⟩ just rich of Z_st.

## Assumptions and limits

* Fluent 2020 R2, double precision, cell-based laminar finite-rate (or EDC) with the stiff-chemistry
  `DEFINE_CHEM_STEP` hook. UDMs are written only for cell calls. Under PDF transport, where particles
  call the hook, the step works but no UDMs are written.
* The API calls used are `mixture_material`, `mixture_specie_index`, `RP_Get_Real("operating-pressure")`,
  `C_UDMI`, `C_R`, `PRF_GRSUM1` and `PRF_GRHIGH1`. Nothing version-specific beyond these.
* Every compute node reads the model file from the working folder, which works for local parallel
  runs and shared cluster file systems.
* The model is valid for this flame only: CH4/air with GA18, air with Y_O2 = 0.21 by mass, 300 K
  streams, 1 atm. A different mechanism, stream or pressure needs a retrained model; the UDF refuses
  a model whose species count does not match.
* The counters are per process and are not thread-safe. They are statistics only, and Fluent's MPI
  parallelism (one process per core) is not affected.

## Reference run: GA18 burner case with Direct Integration

This reference run is the direct-GA18 Fluent solution that `scripts/13_fluent_compare.py` compares the surrogate run against.

Case: `quemadorUnicoTesis_60KCells-GA18--ID-UDF.cas.h5` (Fluent 20.2), from
`burner-simulation.zip`. That original file is not committed.

The Direct Integration base case (the original with the chem-step UDF unhooked) is committed at
[`fluent/cases/quemadorUnicoTesis_60KCells-GA18--DI.cas.h5`](cases/quemadorUnicoTesis_60KCells-GA18--DI.cas.h5)
(1.6 MB). It is the output of the command below, so you can open it in Fluent directly and skip that step.

| File | What it does |
|---|---|
| `fluent_chem_settings.py` | Reads the chemistry settings out of a `.cas.h5`; `--di-copy` writes a copy with the chem-step UDF unhooked |
| `ga18_di.jou` | Fluent journal: unhook the UDF, keep DI tolerances, initialise and ignite, iterate |

```bash
python fluent_chem_settings.py quemadorUnicoTesis_60KCells-GA18--ID-UDF.cas.h5 \
    --di-copy quemadorUnicoTesis_60KCells-GA18--DI.cas.h5
```

### What the case is set to (read from the file)

| Setting | Value in the case |
|---|---|
| Solver | pressure-based, coupled, steady with pseudo-transient (auto pseudo-time step 0.148 s), 2D axisymmetric, double precision, 12 partitions, 63,087 cells |
| Turbulence | k-ω SST |
| Turbulence-chemistry interaction | laminar finite-rate (`species/reaction-model "finite-rate"`; EDC off) |
| Stiff chemistry | on (`stiff-chem-seg? #t`) |
| Integration method | ISAT **off** (`species/isat? #f`), which is Direct Integration |
| Chem-step UDF | **hooked**: `udf/chem-step-fcn "user_chem_step::libudf"`, compiled from `/home/acubero/BSHsan-IAcomb/quemadorUnico-GA18/UDF.c` (source not in the zip) |
| ODE tolerances | rtol 1e-5, atol 1e-10 |
| Minimum chemistry temperature | 200 K |
| Chemistry agglomeration / dimension reduction | off / off |
| Mechanism | GA18 via Chemkin import: 18 species, 92 reactions (h2 h o o2 oh h2o ho2 h2o2 ch2 ch2(s) ch3 ch4 co co2 hco ch2o ch3o n2) |
| Transport | kinetic-theory diffusivity, thermal diffusion on |
| Iterations stored | 20,000 |

In the Rampant variables, the `(rp-react? #f)`-style flags at the top of the list are not the
active models; the active ones are in the `(case-config ...)` block (react on, 18 species, axi,
energy, k-ω). `species/kinetics/use-isat? #t` belongs to the Chemkin-CFD solver, which is off.

### What has to change for DI

Only one thing: **unhook the DEFINE_CHEM_STEP UDF.** ISAT is already off, so Fluent's integrator
is set to DI; it just never runs, because a hooked chem-step function replaces it in every cell.
In the GUI: *Define → User Defined → Function Hooks → Chemistry Step → none*. In the TUI:
`/define/user-defined/function-hooks/chemistry-step "none"`. The `--di-copy` case has this already.

If `libudf` is not compiled next to the case, Fluent prints a "library not found" error on read
and carries on; with the hook set to none nothing uses it.

### DI settings

* **Tolerances.** rtol 1e-5 / atol 1e-10 are reasonable for a steady flame and are kept.
  Loosening rtol to 1e-4 gives a modest speed-up; tighten atol (1e-12) only if you care about
  trace species such as CH2 or CH3O.
* **Minimum chemistry temperature.** 200 K means every cell is integrated, including the 300 K
  fuel in the pot and the coflow air, which together are most of the mesh. 400 K skips those cells and changes nothing that
  burns. It is left commented out in the journal so a first DI run matches the case as it is.
* **Chemistry agglomeration.** Off now. Turning it on (default tolerance 0.02) groups cells with
  similar composition and temperature and is usually the biggest DI speed-up for steady cases.
* **Initialisation.** Best: read the converged data of the UDF run and continue with DI. From
  scratch: hybrid initialisation, then patch T = 2000 K in `fff-fluid-mixing` (the annulus
  r 0.05–0.075 m, x 0–0.085 m where the fuel leaving the pot meets the coflow air), then iterate.
  If it struggles, converge a cold flow first with volumetric reactions off, then switch them on
  and patch.

### Why the current run is slow

* Every iteration integrates 18-species, 92-reaction chemistry in all 63k cells (no ISAT, no
  agglomeration, minimum chemistry temperature 200 K). Two thirds of the mesh (41,843 cells) is
  the fuel pot `fff-fluid-fuel` (x 0–0.05 m, r 0–0.05 m), which is mostly cold CH4, and another
  9,737 cells are the cold exterior air, so most of that chemistry work is spent on gas that does
  not react.
* That work is done by the UDF. Its source is not in the zip, so its cost is unknown; if it calls
  an external model or prints per cell, it could dominate the run time.
* 20,000 iterations are requested; with the pseudo-transient solver a steady flame usually needs
  far fewer, so use residuals plus a peak-temperature or CO monitor to stop earlier.

### What was verified and what was not

Verified from the file: every setting in the table above, and that the `--di-copy` case differs
from the original only in the 23 bytes of the chem-step entry.
Not tested: Fluent was not available, so neither the journal nor the edited case has been run.
The TUI lines marked `prompt` in the journal follow the 20.2 TUI layout and should be checked once
interactively.

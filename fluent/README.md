# Fluent GA18 burner case: running with Direct Integration

Case: `quemadorUnicoTesis_60KCells-GA18--ID-UDF.cas.h5` (Fluent 20.2), from
`burner-simulation.zip`. The case file is not committed.

| File | What it does |
|---|---|
| `fluent_chem_settings.py` | Reads the chemistry settings out of a `.cas.h5`; `--di-copy` writes a copy with the chem-step UDF unhooked |
| `ga18_di.jou` | Fluent journal: unhook the UDF, keep DI tolerances, initialise and ignite, iterate |

```bash
python fluent_chem_settings.py quemadorUnicoTesis_60KCells-GA18--ID-UDF.cas.h5 \
    --di-copy quemadorUnicoTesis_60KCells-GA18--DI.cas.h5
```

## What the case is set to (read from the file)

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

## What has to change for DI

Only one thing: **unhook the DEFINE_CHEM_STEP UDF.** ISAT is already off, so Fluent's integrator
is set to DI; it just never runs, because a hooked chem-step function replaces it in every cell.
In the GUI: *Define → User Defined → Function Hooks → Chemistry Step → none*. In the TUI:
`/define/user-defined/function-hooks/chemistry-step "none"`. The `--di-copy` case has this already.

If `libudf` is not compiled next to the case, Fluent prints a "library not found" error on read
and carries on; with the hook set to none nothing uses it.

## DI settings

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

## Why the current run is slow

* Every iteration integrates 18-species, 92-reaction chemistry in all 63k cells (no ISAT, no
  agglomeration, minimum chemistry temperature 200 K). Two thirds of the mesh (41,843 cells) is
  the fuel pot `fff-fluid-fuel` (x 0–0.05 m, r 0–0.05 m), which is mostly cold CH4, and another
  9,737 cells are the cold exterior air, so most of that chemistry work is spent on gas that does
  not react.
* That work is done by the UDF. Its source is not in the zip, so its cost is unknown; if it calls
  an external model or prints per cell, it could dominate the run time.
* 20,000 iterations are requested; with the pseudo-transient solver a steady flame usually needs
  far fewer, so use residuals plus a peak-temperature or CO monitor to stop earlier.

## What was verified and what was not

Verified from the file: every setting in the table above, and that the `--di-copy` case differs
from the original only in the 23 bytes of the chem-step entry.
Not tested: Fluent was not available, so neither the journal nor the edited case has been run.
The TUI lines marked `prompt` in the journal follow the 20.2 TUI layout and should be checked once
interactively.

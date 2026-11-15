# ARC22: OpenFOAM DI burner flame with ARC_GRI30_NOx22 (22 transported + 21 QSS species)

15 Nov 2026, sim1, 8 ranks, systemd user unit `sim1-arc` (`server/sim1/arc_run.sh`). Status: **running** (results below are
filled in when the legs finish).

Case: the usual corrected-outlets burner, rhoReactingBuoyantLeFoam + constantLewis (Sct 0.7) + fvDOM wall radiation,
Euler dt 2e-5 s, protocol v2 bases. Chemistry: `openfoam/arcChemStep` (22 species, empty reaction list; per-cell
constant-pressure ODE of Y[22] + T, element projection onto CO2/H2O/O2/N2 after each step).

- flame leg: DI ARC from the A1r (GA18 DI + radiation) state at 0.1 s to 0.2 s, writes every 2.5 ms.
  GA18-only species CH2, CH2(S), HCO, CH3O (QSS in the ARC) dropped; the 8 new species start at 0 (Ydefault).
- ignition leg: DI ARC 0-25 ms from the lean start (protocol v2 ignition phase), vs A2r.

## Benchmark: Fluent DI with full GRI-Mech 3.0

Javier supplied a Fluent DI solution of the same corrected burner with full GRI-Mech 3.0 (53 species). It is the main
benchmark for this run. Its `.cas.h5` is on sim1 (`~/inputs/sim1-extra/fluent-gri/`); the mesh is identical to the GA18
case (all 38 mesh datasets equal), species order h2 ... c3h8 ch2cho ch3cho n2 (53). The `.dat.h5` is in the cloud thread,
so **the cell-by-cell GRI comparison is done in the cloud**, from the per-cell files in `fields/` (row i = OpenFOAM cell
i = Fluent cell i+1; float32, `np.savez_compressed`; `server/sim1/arc_fields.py`):

- `arc22_mean_0.15-0.2.npz`: time mean of the 0.15-0.2 s snapshots: T, Ux, Ur, Y of the 22 ARC species, x, r, V
- `arc22_t0.2.npz`: the same at 0.2 s
- `a1r_mean_0.1-0.1875.npz`: A1r (GA18 DI) mean 0.1-0.1875 s, T, Ux, Ur, 18 GA18 Y (pushed 15 Nov)
- provisional, as soon as 0.15 s exists: `arc22_t0.15.npz`, `arc22_mean_0.125-0.15.npz`

On sim1, `arc_meanfield.py` also takes the GRI solution (`--fluent Fluent_GRI <dat> <cas>`) whenever its `.dat.h5` is
placed next to the `.cas.h5`.

## Mechanism file

An ARC_GRI30_NOx22 mechanism already existed on sim1: `~/arc_gri30/arc_gri30_nox22.hpp` (Javier's deliverable:
unrolled C++17 header, plus `ARC_GRI30_NOx22_deliverables.zip`, the report sources and a torch version) and
`/tmp/libarc_gri30_nox22.so`. The repo version (`mechanisms/arc_gri30_nox22`, rebuilt from the report) gives the same
production rates: max relative difference 2e-8 per species over 400 hot A1r cells (no rate-level projection in either).
The original header is 3x faster per call (8.7 vs 26 us), so it is now the default kernel
(`mechanisms/arc_gri30_nox22/original`, `arcChemStepCoeffs { kernel original; }`; `rebuilt` still works). States after one
flow step agree to 4e-5 between the two kernels (ODE tolerance level).

## Build and smoke tests

- v2412 build fix: `ODESystem::derivatives/jacobian` and `ODESolver::solve` take no `li` argument.
- OpenFOAM accepts the empty reaction list (`StandardChemistryModel: Number of species = 22 and reactions = 0`).
- Ydefault covers every patch: all walls including the hood baffle (`wall-hood`, `wall-hood-shadow`, mappedWall) are in
  group `wall`. Mass-fraction sum after dropping the 4 GA18 species: off by 1.3e-8.
- First smoke (seulex 1e-5 / 1e-12, rebuilt kernel): loads, no FPE, Tmax 2121.3 K vs A1r 2123.0 K after 10 steps, but
  **~100 s/step** (GA18 DI: 7.6 s/step). Causes found and fixed:
  1. N2 had Tlow 300 K (GRI value) in `thermo.compressibleGas`; the cold wall-side cells sit at 299.99 K, so janafThermo
     printed ~15k warnings per step (75 MB of log in 10 steps). Now Tlow 200 K, as in the GA18 case.
  2. Integrator settings (`openfoam/arcChemStep/bench`, OpenFOAM ODE solvers on 400 hot A1r cells, one flow step,
     errors vs seulex 1e-9 / 1e-16):

     | solver, relTol / absTol (on Y) | rhs calls per cell-step | max rel. error OH / NO / HCN | max dT |
     |---|---|---|---|
     | seulex 1e-5 / 1e-12 (first smoke) | 873 | 1e-5 / 7e-6 / 2e-5 | < 0.01 K |
     | seulex 1e-4 / 1e-12 | 472 | 2e-5 / 8e-6 / 2e-4 | 0.01 K |
     | Rosenbrock34 1e-5 / 1e-12 | 580 | 1e-5 / 3e-6 / 5e-6 | < 0.01 K |
     | Rosenbrock34 1e-4 / 1e-12 | 363 | 1e-4 / 8e-6 / 9e-6 | < 0.01 K |
     | **Rosenbrock34 1e-4 / 1e-9 (used)** | **222** | **1.2e-4 / 8e-6 / 6e-5** | 0.01 K |
     | Rosenbrock34 1e-4 / 1e-8 | 180 | 1.2e-4 / 9e-6 / 9e-5 | 0.01 K |

     absTol 1e-9 on Y is still ~10x tighter than GA18's 1e-10 kmol/m3 (about Y 1e-8 in the hot gas).
  3. T-only rate-constant cache in the rebuilt C core (bit-identical; 22 of the 24 FD-Jacobian calls are at the same T).
  4. Original unrolled kernel (above).
  5. Hot-cell decomposition weight 5 instead of GA18's 25 (ARC hot/cold cost ratio is ~5); no measurable change on its own.
- Result: **11.2 s/step** on 8 ranks (machine load ~19 on 16 cores: C2 training, E2 on 4 ranks), first step 46 s.
  Early flame: Tmax 2121.4 / 2119.4 K at 0.1002 / 0.1004 s vs A1r 2123.0 / 2123.0 K.

## GRI-Mech 3.0 in OpenFOAM (queued)

Same burner, full GRI-Mech 3.0 (53 species, 325 reactions, the mechanism of the Fluent GRI DI case), standard
OpenFOAM DI (ode/seulex 1e-10/1e-5), from the A1r state at 0.1 s (`server/sim1/gri_case.sh`); queue unit `sim1-gri`
(`server/sim1/gri_queue.sh`, started by Javier 15 Nov 20:33 CET): ARC flame leg -> GRI flame leg 0.1-0.15 s -> ARC
ignition leg + scoring. Fixes: Tlow 200 K for all 53 species; 13 header lines of the Fluent-extracted therm.foam.dat
re-padded to 80 columns (chemkinToFoam refused them; values unchanged).

Cost per step (CPU seconds of the master rank, machine load ~20 on 16 cores):

| Mechanism | species / reactions | s/step, 8 ranks |
|---|---|---|
| GA18 (A1r) | 18 / 92 | 7.6 |
| ARC_GRI30_NOx22 (this run) | 22 transported + 21 QSS / 262 | 12.4 (13.1 wall) |
| GRI-Mech 3.0 | 53 / 325 | ~23-28 (smoke: 93 s/step on 2 ranks, steps 2-6) |

## Outputs

- snapshots: `/opt/ofb/runs/arc22/{flame,ign}/snap/arc22_{flame,ign}_t*.csv` (foam_snapshot.py now adds the ARC species
  columns ch3oh, c2h2, c2h4, c2h6, no, no2, n2o, hcn at the end of each table when present)
- outlet NOx: `postProcessing/outletNOx_{outlet-lab,wall-fff-fluid-exhaust}` (phi-weighted T, NO, NO2, N2O, HCN, CO, CO2,
  C2H2 every 10 steps)
- scoring: `server/sim1/arc_report.sh` (protocol v2 flame vs A1r, ignition vs A2r, as phaseB.sh; `arc_meanfield.py`:
  mean field over 0.15-0.2 s vs A1r mean 0.1-0.1875 s and Fluent, NOx maxima) -> this directory

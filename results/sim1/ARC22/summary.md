# ARC22: OpenFOAM DI burner flame with ARC_GRI30_NOx22 (22 transported + 21 QSS species)

15 Nov 2026, sim1, 8 ranks, systemd user unit `sim1-arc` (`server/sim1/arc_run.sh`). Status: flame leg done (stopped at 0.1874 s, see below); GRI-Mech 3.0 OpenFOAM leg running; ARC ignition leg queued.

Case: the usual corrected-outlets burner, rhoReactingBuoyantLeFoam + constantLewis (Sct 0.7) + fvDOM wall radiation,
Euler dt 2e-5 s, protocol v2 bases. Chemistry: `openfoam/arcChemStep` (22 species, empty reaction list; per-cell
constant-pressure ODE of Y[22] + T, element projection onto CO2/H2O/O2/N2 after each step).

- flame leg: DI ARC from the A1r (GA18 DI + radiation) state at 0.1 s to 0.2 s, writes every 2.5 ms.
  GA18-only species CH2, CH2(S), HCO, CH3O (QSS in the ARC) dropped; the 8 new species start at 0 (Ydefault).
- ignition leg: DI ARC 0-25 ms from the lean start (protocol v2 ignition phase), vs A2r.

## Flame leg results (16 Nov)

**The leg stopped at 0.1874 s (step 4375 of 5000), not because of the chemistry.** An axis gas cell under the pot bottom
(x = 50 mm, r = 0.4 mm) went from 299.7 K to negative T in one step: the same cell and almost the same time as the
near-axis fvDOM/axis runaway that ended A1r at 0.18754 s (results/sim1/A1r/G1.md). Domain Tmin was a smooth 299.7 K
and Tmax steady at 2106 K until then. Last clean write 0.185 s: the statistics window is **0.15-0.185 s** (15 snapshots).
Extending to 0.2 s would need that cell fixed first (e.g. radiation every step, or a restart from 0.185 s with a floor).

Protocol v2 flame report vs A1r (GA18 DI, 0.1-0.15 s; `flame/arc22_flame/protocol_report.md`): flame cells (T > 1600 K)
are **33 K cooler** on average (abs dT 33.3 K, bias -33.0 K; 36 K in the last 10 ms, drifting +2 K per 10 ms), hot-cell
p95 abs dT 61 K, V(T>1500) x0.97, OH L1 13 % (total x1.05), CO L1 7 % (x0.93), H L1 28 % (x1.20), GA18 heat release
evaluated on the state x0.93. Cost 11.15 s/step on 8 ranks.

Mean field (`meanfield.txt`; per-cell mean of the snapshots; V for the full revolution):

| Metric | ARC22 0.15-0.185 s | A1r 0.1-0.1875 s | Fluent GA18 |
|---|---|---|---|
| V(T > 1500 K) [cm3] | 18.79 (snapshots 18.33-19.36) | 19.94 | 18.25 |
| Tmax [K] | 2104.4 | 2121.4 | 2087.5 |
| Flame base x(T > 1500 K) [mm] | 1.39 | 1.39 | 1.15 |
| x(OH max) [mm] | 17.6 | 15.9 | 15.1 |
| OH max | 0.00346 | 0.00333 | 0.00328 |
| CO max | 0.0510 | 0.0599 | 0.0532 |
| Axis Tmax [K] | 1398 | 1472 | 1437 |
| Mean hot abs(dT) vs Fluent GA18, volume-weighted [K] | 45.9 | 51.6 | - |
| L1 OH / CO vs Fluent GA18 (hot) | 20 % / 8 % | 26 % / 13 % | - |

NOx and C2 species (max mass fraction, mean field 0.15-0.185 s): NO 2.48e-4, NO2 4.0e-5, N2O 6.1e-6, HCN 1.46e-4,
C2H2 0.0155, C2H4 0.0025, C2H6 0.0014, CH3OH 8.7e-5. NO is still rising slowly (mean field 0.1-0.185 s: 2.09e-4).

**Outlet NOx is not meaningful in this run:** both outlets still carry the initial gas after 87 ms (exhaust CO2 constant
at 0.0175, NO ~1e-41; `outlet_nox.txt`), so the outlet residence time is far longer than the leg. NOx is compared
inside the domain (maxima, hot-cell L1 against Fluent GRI in the cloud).

Field files for the cloud comparison: `fields/arc22_mean_0.15-0.185.npz`, `fields/arc22_t0.185.npz` (plus the
provisional `arc22_t0.15.npz`, `arc22_mean_0.125-0.15.npz` and `a1r_mean_0.1-0.1875.npz`).

## ARC22 vs GRI-Mech 3.0, same code (first window, 16 Nov 20:40)

OpenFOAM, same case, both from the A1r state at 0.1 s, per-cell mean of the snapshots 0.1025-0.125 s
(`fields/arc22_mean_0.1025-0.125.npz` vs `fields/gri53_mean_0.1025-0.125.npz`; hot = T > 1000 K in either,
volume-weighted over the full revolution):

| Metric | ARC22 | GRI-Mech 3.0 |
|---|---|---|
| V(T > 1500 K) [cm3] | 19.58 | 19.53 |
| Tmax [K] | 2112 | 2111 |
| x(OH max) [mm] | 20.4 | 20.1 |
| OH / CO max | 0.00347 / 0.0544 | 0.00349 / 0.0566 |
| NO / NO2 / N2O / HCN max | 1.67e-4 / 1.45e-5 / 9.6e-7 / 8.1e-5 | 1.67e-4 / 1.30e-5 / 9.7e-7 / 6.8e-5 |
| C2H2 / CH3OH max | 0.0122 / 7.1e-5 | 0.0114 / 7.3e-5 |

Hot cells: mean abs(dT) 1.5 K (volume-weighted), bias +0.4 K, max abs(dT) 11 K. L1 ARC vs GRI (total ARC/GRI):
OH 0.9 % (0.994), CO 2.0 % (0.982), H 2.7 % (0.974), CH4 0.3 % (1.000), NO 7.7 % (1.064), NO2 3.1 % (1.001),
N2O 12.4 % (1.091), HCN 18.2 % (1.182), C2H2 7.4 % (1.073).

So the ARC flame is the GRI flame to within 1.5 K: the -33 K offset of both from GA18 (A1r) is GA18 vs GRI chemistry.
NOx: NO within 6 % in total; HCN (+18 %) and N2O (+9 %) are the weakest species.

### Final window 0.125-0.15 s (GRI leg completed 17 Nov 05:24)

`compare_of_gri.md` (`fields/arc22_mean_0.125-0.15.npz` vs `fields/gri53_mean_0.125-0.15.npz`, 11 snapshots each):
V(T > 1500 K) 19.48 vs 19.46 cm3, Tmax 2108 vs 2107 K, hot-cell mean abs(dT) 3.2 K (volume-weighted), bias +1.2 K,
max 17 K. L1 (total ARC/GRI): OH 1.5 % (0.994), CO 3.4 % (0.971), CO2 0.4 %, H 3.6 %, CH4 0.4 %, CH3OH 3.2 %,
NO 7.6 % (1.039), NO2 4.0 % (0.981), C2H2 8.9 % (1.088), HCN 20.6 % (1.206), **N2O 34 % (1.27; max 2.6e-6 vs 1.1e-6)**.
At 0.15 s instantaneous: abs(dT) 4.1 K, NO total 1.026, N2O 1.31, HCN 1.21.
The ARC-GRI gap grows slowly with time (abs(dT) 1.5 K at 0.1025-0.125 s, 3.2 K at 0.125-0.15 s; N2O L1 12 % -> 34 %):
N2O (N2O-intermediate route) and HCN (prompt route) are where the reduction is weakest; NO itself stays within 4-6 %.

Cost per step on 8 ranks (same case): GA18 7.6 s, ARC22 11.2 s, GRI-Mech 3.0 30 s (2500 steps in 20.9 h).

## Benchmark: Fluent DI with full GRI-Mech 3.0

Javier supplied a Fluent DI solution of the same corrected burner with full GRI-Mech 3.0 (53 species). It is the main
benchmark for this run. Its `.cas.h5` is on sim1 (`~/inputs/sim1-extra/fluent-gri/`); the mesh is identical to the GA18
case (all 38 mesh datasets equal), species order h2 ... c3h8 ch2cho ch3cho n2 (53). The `.dat.h5` is in the cloud thread,
so **the cell-by-cell GRI comparison is done in the cloud**, from the per-cell files in `fields/` (row i = OpenFOAM cell
i = Fluent cell i+1; float32, `np.savez_compressed`; `server/sim1/arc_fields.py`):

- `arc22_mean_0.15-0.185.npz`: time mean of the 0.15-0.185 s snapshots: T, Ux, Ur, Y of the 22 ARC species, x, r, V
- `arc22_t0.185.npz`: the same at 0.185 s (last clean write)
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

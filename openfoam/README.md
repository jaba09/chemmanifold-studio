# OpenFOAM case from the Fluent single-flame burner

The Fluent case `quemadorUnicoTesis_60KCells-GA18--ID-UDF.cas.h5` (Fluent 20.2) rebuilt for OpenFOAM
(openfoam.com, tested with v2412), plus the tools that did the conversion and an OpenFOAM counterpart
of the `DEFINE_CHEM_STEP` UDF.

```
openfoam/
├── tools/
│   ├── fluent_h5_to_foam.py          .cas.h5 2D axisymmetric mesh -> OpenFOAM wedge polyMesh
│   ├── fluent_cas_settings.py        .cas.h5 settings -> BC summary + the embedded Chemkin files
│   └── chemkin_transport_to_foam.py  Chemkin tran.dat -> Sutherland coefficients for chemkinToFoam
├── quemadorUnico/                    the case (Allrun builds the mesh from the .cas.h5)
└── userChemStep/                     DEFINE_CHEM_STEP as an OpenFOAM chemistry solver library
```

## Running

```bash
# OpenFOAM (openfoam.com) environment sourced; python3 with numpy and h5py
cd openfoam/quemadorUnico
./Allrun /path/to/quemadorUnicoTesis_60KCells-GA18--ID-UDF.cas.h5 4     # 4 = MPI ranks
```

Without OpenFOAM installed, `quemadorUnico/run_on_my_computer.sh` does everything on any x86_64
Linux or Windows WSL machine: it installs v2412 from conda-forge into `~/openfoam-burner` (no sudo),
then runs `Allrun`. `--resume` continues a stopped run and `--results` reconstructs the latest save
for ParaView (`burner.foam`).

`Allrun` converts the mesh, runs `checkMesh`, converts the mechanism with `chemkinToFoam`, copies
`0.orig` to `0`, ignites with `setFields`, then runs `rhoReactingBuoyantFoam` in parallel.
`fluentMeshToFoam` is not used because it only reads ASCII `.msh`/`.cas`; the converter reads the
HDF5 mesh directly. `chemkin/transportProperties` is committed, so Cantera is only needed to refit it.

## What the Fluent case contains, and how it maps

| Fluent | OpenFOAM |
|---|---|
| 2D axisymmetric (x = axis, gravity -9.8 in x) | 5° wedge about the x axis, `g = (-9.8 0 0)` |
| Pressure-based, steady | `rhoReactingBuoyantFoam` with local time stepping (`ddt localEuler`) |
| k-ω SST | `kOmegaSST` |
| Species transport, laminar finite-rate, stiff chemistry, ODE rtol 1e-5 / atol 1e-10 | `combustionModel laminar`, `ode` + `seulex` with the same tolerances |
| Mechanism imported from Chemkin (GA18, 18 species, 92 reactions, CH4/air) | the Chemkin files Fluent stored in the .cas, via `chemkinToFoam`: all 92 reactions convert |
| Kinetic-theory viscosity | Sutherland fits to the same Lennard-Jones data (max error 4.9 %, 300–2500 K) |
| `inlet-fuel`: mass flow 6.735e-6 kg/s CH4, 300 K | `flowRateInletVelocity`, 6.735e-6 × 5/360 kg/s |
| `inlet-coflow-fff-fluid-mixing`: mass flow 5.7675e-5 kg/s air, 300 K | `flowRateInletVelocity`, 5.7675e-5 × 5/360 kg/s |
| `inlet-coflow-fff-fluid-exterior`: 0.05 m/s air, 300 K | `surfaceNormalFixedValue` |
| `outlet-lab:026` (r = 0.14 m side): pressure outlet 0 Pa gauge, backflow air 300 K | fixed `p_rgh` + `inletOutlet` (patch `outlet-lab-026`); Fluent's gauge pressure excludes the hydrostatic head, so fixing `p` on this vertical boundary would drive a spurious through-flow |
| Turbulence at inlets: 5 % intensity, viscosity ratio 10 | fixed k = 1.5 (0.05 U)², ω = k / (10 ν) |
| `wall-disk`: 300 K | `fixedValue` |
| `wall-pot-fff-fluid-exhaust`, `-mixing`: convection, h = 15, Tinf = 323 K | `externalWallHeatFluxTemperature` |
| `wall-hood` / `wall-hood-shadow`: coupled zero-thickness wall | `mappedWall` pair + `turbulentTemperatureCoupledBaffleMixed` |
| other walls: adiabatic | `zeroGradient` |
| `DEFINE_CHEM_STEP` = `user_chem_step::libudf` | `userChemStep` library, see below (the case runs with `ode` by default) |

Notes on the Fluent setup:

- The air streams set O2 = 0.21 with *species in mole fractions* on, so they are normal air. The case
  uses **Y_O2 = 0.233, Y_N2 = 0.767 by mass** (Z_st = 0.055). The first version of this case read the
  0.21 as a mass fraction; that was wrong.
- `outlet-lab` (top, r = 0.02–0.14 m) and `wall-fff-fluid-exhaust` (top of the chimney, r < 0.02 m)
  are **adiabatic walls**, so the only open boundary is the side at r = 0.14 m and the chimney is closed.

Known modelling differences:

- **Species diffusion.** Fluent used kinetic-theory mass diffusivities with thermal diffusion;
  `rhoReactingBuoyantFoam` uses unity Lewis number. The inlet jets are close to laminar
  (fuel jet Re ≈ 150), so this can shift the flame position and peak temperature.
- **Turbulent Schmidt number.** Fluent Sc_t = 0.7; OpenFOAM diffuses species with α_t (Pr_t = 0.85).
- **Initial state.** Fluent's data file was not supplied. The run starts from still air at 300 K with
  the fuel region under the pot already full of CH4 and the mixing annulus full of stoichiometric
  CH4/air products at 2000 K (`system/setFieldsDict`). Hot products hold no O2, so they light the
  flame without the 2690 K preheated-air peak that a 2000 K air patch gave. Filling that finely meshed, nearly stagnant region from the inlet takes
  tens of thousands of local-time-step iterations, so a hot patch alone cools before fuel arrives.
- **Thermo range.** N2 and CH3O have NASA fits starting at 300 K, the boundary temperature; the
  chemkinToFoam copy (`therm.foam.dat`) starts them at 200 K so cells a hair below 300 K do not
  print a warning each (which filled GBs of log).

## The DEFINE_CHEM_STEP hook in OpenFOAM

Fluent calls `DEFINE_CHEM_STEP(name, c, t, p, num_p, n_spe, dt, pres, temp, yk)` per cell and
expects the mass fractions after `dt`. In OpenFOAM the same hook is a chemistry solver:
`StandardChemistryModel` calls `solver.solve(c, T, p, deltaT, subDeltaT)` per cell with molar
concentrations and sets RR_i = W_i (c_i(dt) − c_i(0)) / dt. `userChemStep` converts c ↔ Y at the
cell density, so its `chemStep(yk, T, p, dt)` has the Fluent signature. Without a model file the body
is the Fluent manual example from the UDF (dY_k/dt = 1/N − Y_k).

With `userChemStepCoeffs/model` set, `chemStep` runs the ChemManifold surrogate through the same
plain-C core as the Fluent UDF (`fluent/udf/chemmanifold_core.c`; `Allwmake` copies it in), with
the same model files (`chemmanifold_model.txt`, `chemmanifold_tests.txt`) and options:

```
userChemStepCoeffs
{
    model        "chemmanifold_model.txt";   // omit for the Fluent manual example
    tests        "chemmanifold_tests.txt";   // optional: the 60-case self-test runs on load
    T_freeze     600;        // K; colder cells are not advanced
    maxSubsteps  50;         // 50 x 40 us = 2 ms of chemistry per call at most
    oodAction    0;          // 0 = only count cells outside the training data
    checkOOD     true;
    reportCalls  1000000;    // print counters (advanced, OOD by check, ...) every this many calls
    oodFallback  false;      // true: cells outside the training data are integrated with the
}                            //  ODE solver of odeCoeffs (hybrid surrogate + direct integration)
```

The surrogate is trained on dt = 10-40 us, so run it transient (`ddt Euler`, `deltaT 4e-5`), not
with local time stepping, whose chemistry dt reaches 10 ms.

```bash
cd openfoam/userChemStep && ./Allwmake        # -> $FOAM_USER_LIBBIN/libuserChemStep.so
```

Then in the case: `libs (userChemStep);` in `system/controlDict`, and `solver userChemStep;` in
`chemistryType` of `constant/chemistryProperties`. Tested with v2412: the species relax toward
1/N by the expected exp(−dt) factor per step.

Two details of the original `UDF.c`: index `ico = 13` is **CO2** in this mixture (CO is 12; the
order is H2 H O O2 OH H2O HO2 H2O2 CH2 CH2(S) CH3 CH4 CO CO2 HCO CH2O CH3O N2), and the
`Message0` call passes `i` first, so the printed `dt` and mass fractions are shifted.

## Parallel runs: balance the chemistry

Once the flame burns, the chemistry costs far more than the flow, and it sits in a few thousand
cells. A plain `scotch` split put most of them on one rank (9112 hot cells against 235-1593 on the
others), so the other ranks waited: about 19 s per iteration on 4 cores. Decomposing a burning
state with a cell weight (25 for T > 800 K, 1 elsewhere) brought it to about 10 s:

```
// system/decomposeParDict
method       scotch;
weightField  cellWeight;     // volScalarField in the time directory being decomposed
```

## OpenFOAM versions

- Tested with **openfoam.com v2412** (also on conda-forge: `micromamba create -n of -c conda-forge openfoam=2412`).
- Ubuntu 24.04's packaged **v1912** reads the case, but its `rhoReactingBuoyantFoam` produces
  spurious cell velocities from the first time step on this mesh, even cold and without gravity;
  `rhoReactingFoam` and v2412 do not. Use v2006 or newer.
- The Foundation releases (openfoam.org v10+) use different dictionaries (`physicalProperties`,
  `momentumTransport`, `foamRun`); this case is for openfoam.com.

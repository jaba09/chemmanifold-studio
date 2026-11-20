# ARC_GRI30_NOx22

Analytically reduced GRI-Mech 3.0 for CH4/air with NOx: 22 transported (ODE) species and 21 quasi-steady
radicals (linearized QSSA). Rebuilt from Javier's technical report (no mechanism file was supplied).

- `make_skeletal.py` -> `gri30_skel43.yaml`: gri30 minus AR, C3H7, C3H8, CH2CHO, CH3CHO, HCCOH, C2H, CH2CO,
  NH3, HCNN and every reaction that involves them (including the explicit-AR collider) = 43 species,
  262 reactions, as in the report.
- `gen_arc.py` -> `arc_gri30_nox22_data.h` (reaction / thermo tables); `arc_gri30_nox22.c/.h` the plain-C core:
  rate constants (Arrhenius, three-body, Troe / Lindemann falloff, reverse from NASA-7 equilibrium),
  LQSSA (directions with one QSS reactant are linear in it; the 11 bimolecular QSS-QSS directions are left
  out of the radical balances, exactly the report's 11 truncated channels), dense LU solve of the 21x21
  system, final rates from all 262 reactions, constant-pressure ODE rhs, element projection onto
  CO2/H2O/O2/N2.
- ODE species: H2 H O O2 OH H2O HO2 H2O2 CH4 CH3 CO CO2 CH2O CH3OH C2H2 C2H4 C2H6 N2 NO NO2 N2O HCN.
- QSS species: C CH CH2 CH2(S) HCO CH2OH CH3O C2H3 C2H5 HCCO N NH NH2 NNH HNO CN H2CN HCNO HOCN HNCO NCO.
- OpenFOAM: `openfoam/arcChemStep` (chemistry solver plug-in; the case lists only the 22 species and no reactions).
- Fluent: `fluent/arc22` (DEFINE_CHEM_STEP UDF with a plain-C copy of `original/arc_gri30_nox22.hpp`, 22-species CHEMKIN mixture files).
- Validation: `validation/` (ctypes wrapper `arcpy.py`, `ignition.py`, `lewis.py`, `flame1d.py`), results in
  `validation/VALIDATION.md`.

Build the shared library for the validation scripts:
`gcc -O2 -shared -fPIC -o /tmp/libarc.so arc_gri30_nox22.c -lm` and `export ARC_LIB=/tmp/libarc.so`.

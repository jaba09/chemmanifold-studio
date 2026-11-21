#!/usr/bin/env python3
"""Files for the GRI-Mech 3.0 (53 species) OpenFOAM burner case: the exact mechanism of Javier's Fluent GRI DI
case (chemkin/chem.foam.inp + therm.foam.dat, extracted from quemadorUnicoTesis_60KCells-GRI--ID.cas.h5 with
openfoam/tools/fluent_cas_settings.py), plus
  chemkin/transportProperties  Sutherland fits (300-2500 K) to Cantera gri30 pure-species viscosity
  case/speciesDiffusion        constantLewis, Sct 0.7: GA18 case values for its 18 species, the ARC22 values for
                               its 8 new ones, the rest from mechanisms/arc_gri30_nox22/validation/lewis.py --all
Run chemkinToFoam on sim1 to get constant/reactions and constant/thermo.compressibleGas (server/sim1/gri_case.sh)."""
import os
import numpy as np, cantera as ct
HERE = os.path.dirname(os.path.abspath(__file__))
GA18 = dict(H2=0.309, H=0.185, O=0.712, O2=1.084, OH=0.729, H2O=0.816, HO2=1.086, H2O2=1.081, CH2=0.995,
            **{"CH2(S)": 0.995}, CH3=1.014, CH4=0.870, CO=1.120, CO2=1.370, HCO=1.281, CH2O=1.290, CH3O=1.323,
            N2=1.151)
ARC_NEW = dict(CH3OH=1.332, C2H2=1.338, C2H4=1.346, C2H6=1.454, NO=1.126, NO2=1.221, N2O=1.367, HCN=1.298)
OTHER = dict(C=0.780, CH=0.683, CH2OH=1.334, C2H=1.329, C2H3=1.356, C2H5=1.477, HCCO=0.900, CH2CO=1.536,
             HCCOH=1.536, N=0.821, NH=0.692, NH2=0.707, NH3=0.919, NNH=1.156, HNO=1.127, CN=1.155, H2CN=1.314,
             HCNN=0.901, HCNO=1.403, HOCN=1.401, HNCO=1.402, NCO=1.398, C3H7=1.874, C3H8=1.869, CH2CHO=1.542,
             CH3CHO=1.553)
g = ct.Solution("gri30.yaml")
T = np.linspace(300, 2500, 111)
lines = ["FoamFile\n{\n    version     2.0;\n    format      ascii;\n    class       dictionary;\n    object      transportProperties;\n}\n"
         "// Sutherland fits to Cantera gri30 kinetic-theory viscosity, 300-2500 K (openfoam/gri30/make_case_files.py)\n"]
for s in g.species_names:
    mu = []
    for t in T:
        g.TPX = t, ct.one_atm, {s: 1}
        mu.append(g.viscosity)
    mu = np.array(mu)
    a, b = np.polyfit(1.0 / T, np.sqrt(T) / mu, 1)
    As, Ts = 1.0 / b, a / b
    err = np.max(np.abs(As * np.sqrt(T) / (1 + Ts / T) / mu - 1))
    lines.append('"%s"\n{\n    transport\n    {\n        As  %.6e;\n        Ts  %.4f;\n    }\n}\n// max fit error %.2f%%\n' % (s, As, Ts, 100 * err))
open(os.path.join(HERE, "chemkin", "transportProperties"), "w").write("\n".join(lines))
Le = {**OTHER, **ARC_NEW, **GA18}
with open(os.path.join(HERE, "case", "speciesDiffusion"), "w") as f:
    f.write("FoamFile\n{\n    version     2.0;\n    format      ascii;\n    class       dictionary;\n    location    \"constant\";\n"
            "    object      speciesDiffusion;\n}\n// GRI-Mech 3.0 burner case (openfoam/gri30/make_case_files.py): GA18 values kept for its 18 species,\n"
            "// ARC22 values for its 8 new species, the rest from validation/lewis.py --all (same method)\n\n"
            "model           constantLewis;\nSct             0.7;\n\nLe\n{\n")
    for s in g.species_names:
        if s in Le:
            f.write("    %-7s %.3f;\n" % (s, Le[s]))
    f.write("    default 1;      // AR (absent)\n}\n")
print("done")

#!/usr/bin/env python3
"""Write the OpenFOAM constant/ files of the ARC_GRI30_NOx22 burner case into case/:
reactions (22 species, no reactions: arcChemStep does the chemistry), thermo.compressibleGas
(GRI-Mech 3.0 NASA polynomials, Sutherland fits to GRI kinetic-theory viscosity as in
openfoam/tools/chemkin_transport_to_foam.py) and speciesDiffusion (constantLewis, Sct 0.7;
the Le of the species shared with GA18 are kept from the GA18 case so that only the
chemistry differs; the 8 new ones come from mechanisms/arc_gri30_nox22/validation/lewis.py)."""
import os
import numpy as np
import cantera as ct
HERE = os.path.dirname(os.path.abspath(__file__))
ODE = "H2 H O O2 OH H2O HO2 H2O2 CH4 CH3 CO CO2 CH2O CH3OH C2H2 C2H4 C2H6 N2 NO NO2 N2O HCN".split()
LE = dict(H2=0.309, H=0.185, O=0.712, O2=1.084, OH=0.729, H2O=0.816, HO2=1.086, H2O2=1.081,
          CH3=1.014, CH4=0.870, CO=1.120, CO2=1.370, CH2O=1.290, N2=1.151,          # GA18 case
          CH3OH=1.332, C2H2=1.338, C2H4=1.346, C2H6=1.454, NO=1.126, NO2=1.221,    # lewis.py (GRI)
          N2O=1.367, HCN=1.298)
g = ct.Solution("gri30.yaml")
out = os.path.join(HERE, "case")
hdr = lambda obj: ("FoamFile\n{\n    version     2.0;\n    format      ascii;\n    class       dictionary;\n"
                   "    location    \"constant\";\n    object      %s;\n}\n" % obj)
note = "// ARC_GRI30_NOx22 burner case, written by openfoam/arcChemStep/make_case_files.py\n"
with open(os.path.join(out, "reactions"), "w") as f:
    f.write(note + "// The 21 quasi-steady radicals are not transported; arcChemStep computes all rates.\n")
    f.write("elements 4 ( C H O N );\n\nspecies %d\n(\n%s\n);\n\nreactions\n{\n}\n\nTlow 200;\nThigh 3500;\n"
            % (len(ODE), "\n".join("    " + s for s in ODE)))
T = np.linspace(300, 2500, 221)
with open(os.path.join(out, "thermo.compressibleGas"), "w") as f:
    f.write(note + "// NASA-7 from Cantera gri30.yaml; Sutherland fit 300-2500 K to GRI pure-species viscosity\n\n")
    for s in ODE:
        sp = g.species(s); c = sp.thermo.coeffs
        mu = []
        for t in T:
            gg = ct.Solution("gri30.yaml"); gg.TPX = t, ct.one_atm, {s: 1}
            mu.append(gg.viscosity)
        mu = np.array(mu)
        a, b = np.polyfit(1.0 / T, np.sqrt(T) / mu, 1)
        As, Ts = 1.0 / b, a / b
        err = np.max(np.abs(As * np.sqrt(T) / (1 + Ts / T) / mu - 1))
        # Tlow 200 K for every species (GRI N2 says 300 K; the GA18 case uses 200 K with the same polynomials):
        # cold wall-side cells sit at 299.99 K and janafThermo warns for every cell and call below Tlow
        els = " ".join("%s %d;" % (e, sp.composition[e]) for e in ("C", "H", "O", "N") if sp.composition.get(e, 0))
        f.write('"%s"\n{\n    specie { molWeight %.6f; }\n    thermodynamics\n    {\n'
                '        Tlow %g;\n        Thigh %g;\n        Tcommon %g;\n'
                '        highCpCoeffs ( %s );\n        lowCpCoeffs ( %s );\n    }\n'
                '    transport { As %.6e; Ts %.4f; }   // max fit error %.2f %%\n'
                '    elements { %s }\n}\n\n'
                % (s, g.molecular_weights[g.species_index(s)], min(sp.thermo.min_temp, 200.0), sp.thermo.max_temp, c[0],
                   " ".join("%.9e" % v for v in c[1:8]), " ".join("%.9e" % v for v in c[8:15]),
                   As, Ts, 100 * err, els))
with open(os.path.join(out, "speciesDiffusion"), "w") as f:
    f.write(hdr("speciesDiffusion") + note +
            "// Le of the GA18 species kept from the GA18 case; new species from a Cantera GRI\n"
            "// counterflow flame by the same method (validation/lewis.py)\n\n"
            "model           constantLewis;\nSct             0.7;\n\nLe\n{\n")
    for s in ODE:
        f.write("    %-7s %.3f;\n" % (s, LE[s]))
    f.write("    default 1;\n}\n")
print("wrote", os.listdir(out))

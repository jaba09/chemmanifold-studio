#!/usr/bin/env python3
"""Write the COVLOOP Case B OpenFOAM case: Somers-de Goey 2D laminar premixed CH4/air slit burner, ARC22 DI.

Values from the 2026-11-23 Gemini chat (uploaded to the project), TO BE CHECKED against
L.M.T. Somers, L.P.H. de Goey, Combust. Sci. Technol. 108 (1995) before gate G1 (docs/COVERAGE-LOOP-ROADMAP.md s. 3):
  planar 2D half domain x 0-6 mm, y 0-40 mm (canonical 12-16 mm box extended for thermal NO), 1 cell deep;
  inlet y = 0, x 0-2 mm: CH4/air phi 1.0 at 298 K, Poiseuille u = umax (1 - (x/2 mm)^2), umax 1.1 m/s;
  rim y = 0, x 2-6 mm and side wall x = 6 mm: no slip, zero species flux, 298 K;
  axis x = 0 symmetry plane; outlet y = 40 mm at 1 atm;
  start: fresh reactants for x <= 2 mm, y <= 5 mm; burnt gas elsewhere = HP equilibrium of the MAJOR C/H/O
  species + N2 only (NO, NO2, N2O, HCN = 0, avoids the equilibrium-NO trap).
Solver rhoReactingBuoyantLeFoam (constant Lewis, openfoam/simpleFlame/solver), chemistry arcChemStep,
species/thermo/Lewis files from openfoam/arcChemStep/case. Laminar, no radiation, gravity -y.

Usage:  python3 make_case.py OUTDIR [--res 25e-6] [--phi 1.0] [--umax 1.1] [--Ly 0.040] [--lts] [--end 0.03]
        then:  cd OUTDIR && ./Allrun [nProcs]          (needs OpenFOAM v2412 + the solver and arcChemStep built)
"""
import argparse, os, shutil
import numpy as np
import cantera as ct

HERE = os.path.dirname(os.path.abspath(__file__))
ARC_CASE = os.path.join(HERE, "..", "arcChemStep", "case")
SPECIES = "H2 H O O2 OH H2O HO2 H2O2 CH4 CH3 CO CO2 CH2O CH3OH C2H2 C2H4 C2H6 N2 NO NO2 N2O HCN".split()
MAJORS = "H2 H O O2 OH H2O CO CO2 N2".split()   # kept from equilibrium in the burnt start; everything else = 0
NOX = ("NO", "NO2", "N2O", "HCN")


def hdr(cls, obj, loc):
    return ("/*--- COVLOOP Case B: Somers-de Goey slit burner, written by openfoam/slitBurner/make_case.py ---*/\n"
            "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class %s;\n    location \"%s\";\n    object %s;\n}\n\n"
            % (cls, loc, obj))


def states(phi):
    g = ct.Solution(os.path.join(HERE, "..", "..", "mechanisms", "arc_gri30_nox22", "gri30_skel43.yaml"))
    g.TP = 298.0, ct.one_atm
    g.set_equivalence_ratio(phi, "CH4", "O2:0.21, N2:0.79")
    fresh = {s: g.Y[g.species_index(s)] for s in SPECIES}
    g.equilibrate("HP")
    Tb = g.T
    burnt = {s: (g.Y[g.species_index(s)] if s in MAJORS else 0.0) for s in SPECIES}
    tot = sum(burnt.values())
    burnt = {s: v / tot for s, v in burnt.items()}
    return fresh, burnt, Tb


def n_cells(length, size):
    return max(1, int(round(length / size)))


def block_mesh(res, Ly):
    """Two x-blocks (slit 0-2 mm | rim 2-6 mm), multi-section grading in y. Sizes in m."""
    mm = 1e-3
    nx1 = n_cells(2 * mm, res)
    nx2a, nx2b = n_cells(0.5 * mm, res), max(4, n_cells(3.5 * mm, 3.5 * res))
    y1, y2 = 8 * mm, 12 * mm
    ny1 = n_cells(y1, res)
    ny2 = max(4, n_cells(y2 - y1, 2.5 * res))
    ny3 = max(4, n_cells(Ly - y2, 10 * res))
    gy = "((%g %d 1) (%g %d 6) (%g %d 3.3))" % (y1 / Ly, ny1, (y2 - y1) / Ly, ny2, (Ly - y2) / Ly, ny3)
    gx2 = "((%g %d 1) (%g %d 6))" % (0.5 / 4, nx2a, 3.5 / 4, nx2b)
    ny = ny1 + ny2 + ny3
    dz = res
    txt = hdr("dictionary", "blockMeshDict", "system") + f"""scale 1;

vertices
(
    (0     0  0) (0.002 0  0) (0.006 0  0)
    (0     {Ly} 0) (0.002 {Ly} 0) (0.006 {Ly} 0)
    (0     0  {dz}) (0.002 0  {dz}) (0.006 0  {dz})
    (0     {Ly} {dz}) (0.002 {Ly} {dz}) (0.006 {Ly} {dz})
);

blocks
(
    hex (0 1 4 3 6 7 10 9) ({nx1} {ny} 1) simpleGrading (1 {gy} 1)
    hex (1 2 5 4 7 8 11 10) ({nx2a + nx2b} {ny} 1) simpleGrading ({gx2} {gy} 1)
);

boundary
(
    inlet    {{ type patch;          faces ((0 1 7 6)); }}
    rim      {{ type wall;           faces ((1 2 8 7)); }}
    sideWall {{ type wall;           faces ((2 5 11 8)); }}
    axis     {{ type symmetryPlane;  faces ((0 6 9 3)); }}
    outlet   {{ type patch;          faces ((3 9 10 4) (4 10 11 5)); }}
    frontAndBack {{ type empty;      faces ((0 3 4 1) (1 4 5 2) (6 7 10 9) (7 8 11 10)); }}
);
"""
    return txt, (nx1 + nx2a + nx2b) * ny


def scalar_field(name, dims, internal, bc):
    s = hdr("volScalarField", name, "0") + "dimensions %s;\n\ninternalField uniform %.10g;\n\nboundaryField\n{\n" % (dims, internal)
    for patch, body in bc.items():
        key = '"%s"' % patch if any(c in patch for c in ".*|()") else patch   # regex patch names must be quoted
        s += "    %s\n    {\n%s    }\n" % (key, "".join("        %s\n" % l for l in body))
    return s + "}\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--res", type=float, default=25e-6, help="cell size in the flame zone [m]")
    ap.add_argument("--phi", type=float, default=1.0)
    ap.add_argument("--umax", type=float, default=1.1)
    ap.add_argument("--Ly", type=float, default=0.040)
    ap.add_argument("--end", type=float, default=0.03)
    ap.add_argument("--lts", action="store_true", help="steady state by local time stepping")
    a = ap.parse_args()
    out = a.out
    for d in ("0.orig", "constant", "system"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    fresh, burnt, Tb = states(a.phi)

    bm, nc = block_mesh(a.res, a.Ly)
    open(os.path.join(out, "system", "blockMeshDict"), "w").write(bm)

    # --- 0.orig
    Tw = 298.0
    wall_T = ["type fixedValue;", "value uniform %g;" % Tw]
    open(os.path.join(out, "0.orig", "T"), "w").write(scalar_field("T", "[0 0 0 1 0 0 0]", Tb, {
        "inlet": wall_T, "rim": wall_T, "sideWall": wall_T,
        "outlet": ["type inletOutlet;", "inletValue uniform %g;" % Tb, "value uniform %g;" % Tb],
        "axis": ["type symmetryPlane;"], "frontAndBack": ["type empty;"]}))
    for s in SPECIES:
        inl = fresh[s]
        body = {"inlet": ["type fixedValue;", "value uniform %.10g;" % inl],
                "rim": ["type zeroGradient;"], "sideWall": ["type zeroGradient;"],
                "outlet": ["type inletOutlet;", "inletValue uniform %.10g;" % burnt[s], "value uniform %.10g;" % burnt[s]],
                "axis": ["type symmetryPlane;"], "frontAndBack": ["type empty;"]}
        open(os.path.join(out, "0.orig", s), "w").write(scalar_field(s, "[0 0 0 0 0 0 0]", burnt[s], body))
    open(os.path.join(out, "0.orig", "Ydefault"), "w").write(scalar_field("Ydefault", "[0 0 0 0 0 0 0]", 0.0, {
        ".*": ["type zeroGradient;"], "axis": ["type symmetryPlane;"], "frontAndBack": ["type empty;"]}))
    open(os.path.join(out, "0.orig", "p"), "w").write(scalar_field("p", "[1 -1 -2 0 0 0 0]", 101325, {
        ".*": ["type calculated;", "value $internalField;"], "axis": ["type symmetryPlane;"],
        "frontAndBack": ["type empty;"]}))
    open(os.path.join(out, "0.orig", "p_rgh"), "w").write(scalar_field("p_rgh", "[1 -1 -2 0 0 0 0]", 101325, {
        ".*": ["type fixedFluxPressure;", "value $internalField;"],
        "outlet": ["type prghPressure;", "p uniform 101325;", "value $internalField;"],
        "axis": ["type symmetryPlane;"], "frontAndBack": ["type empty;"]}))
    U = hdr("volVectorField", "U", "0") + """dimensions [0 1 -1 0 0 0 0];

internalField uniform (0 0 0);

boundaryField
{
    inlet
    {
        type            codedFixedValue;
        value           uniform (0 0 0);
        name            poiseuilleSlit;
        code
        #{
            const vectorField& Cf = patch().Cf();
            const scalar umax = %g, R = 0.002;
            vectorField v(Cf.size(), Zero);
            forAll(Cf, i) { const scalar x = Cf[i].x()/R; v[i] = vector(0, umax*max(0.0, 1 - x*x), 0); }
            operator==(v);
        #};
    }
    "(rim|sideWall)" { type noSlip; }
    outlet { type pressureInletOutletVelocity; value uniform (0 0 0); }
    axis { type symmetryPlane; }
    frontAndBack { type empty; }
}
""" % a.umax
    open(os.path.join(out, "0.orig", "U"), "w").write(U)

    # --- setFields: fresh reactant box x <= 2 mm, y <= 5 mm
    sf = hdr("dictionary", "setFieldsDict", "system") + "defaultFieldValues ( );\n\nregions\n(\n    boxToCell\n    {\n" \
        "        box (-1 -1 -1) (0.002 0.005 1);\n        fieldValues\n        (\n            volScalarFieldValue T 298\n"
    sf += "".join("            volScalarFieldValue %s %.10g\n" % (s, fresh[s]) for s in SPECIES)
    sf += "        );\n    }\n);\n"
    open(os.path.join(out, "system", "setFieldsDict"), "w").write(sf)

    # --- constant
    for f in ("reactions", "thermo.compressibleGas", "speciesDiffusion"):
        shutil.copy(os.path.join(ARC_CASE, f), os.path.join(out, "constant", f))
    c = os.path.join(out, "constant")
    open(os.path.join(c, "g"), "w").write(hdr("uniformDimensionedVectorField", "g", "constant") +
                                          "dimensions [0 1 -2 0 0 0 0];\nvalue (0 -9.81 0);\n")
    open(os.path.join(c, "turbulenceProperties"), "w").write(hdr("dictionary", "turbulenceProperties", "constant") +
                                                            "simulationType laminar;\n")
    open(os.path.join(c, "combustionProperties"), "w").write(hdr("dictionary", "combustionProperties", "constant") +
                                                            "combustionModel laminar;\nlaminarCoeffs { }\n")
    open(os.path.join(c, "thermophysicalProperties"), "w").write(hdr("dictionary", "thermophysicalProperties", "constant") + """thermoType
{
    type            heRhoThermo;
    mixture         reactingMixture;
    transport       sutherland;
    thermo          janaf;
    energy          sensibleEnthalpy;
    equationOfState perfectGas;
    specie          specie;
}
inertSpecie         N2;
chemistryReader     foamChemistryReader;
foamChemistryFile   "<constant>/reactions";
foamChemistryThermoFile "<constant>/thermo.compressibleGas";
""")
    open(os.path.join(c, "chemistryProperties"), "w").write(hdr("dictionary", "chemistryProperties", "constant") + """chemistryType { solver arcChemStep; method standard; }
chemistry           on;
initialChemicalTimeStep 1e-08;
arcChemStepCoeffs
{
    kernel      original;
    solver      Rosenbrock34;
    absTol      1e-9;
    relTol      1e-4;
    T_freeze    0;
    project     true;
    reportCalls 0;
}
""")

    # --- system
    s = os.path.join(out, "system")
    if a.lts:
        timectl = "deltaT 1;\nendTime 20000;\nwriteControl timeStep;\nwriteInterval 500;\n"
        ddt = "localEuler"
        pimple = "    maxDeltaT 1e-4;\n    maxCo 0.5;\n    alphaTemp 0.05;\n    alphaY 0.05;\n    Yref { O2 0.1; CH4 0.1; }\n" \
                 "    rDeltaTSmoothingCoeff 0.02;\n    rDeltaTDampingCoeff 1;\n"
    else:
        timectl = ("deltaT 1e-7;\nendTime %g;\nadjustTimeStep yes;\nmaxCo 0.4;\nmaxDeltaT 1e-5;\n"
                   "writeControl adjustable;\nwriteInterval 5e-4;\n" % a.end)
        ddt = "Euler"
        pimple = ""
    open(os.path.join(s, "controlDict"), "w").write(hdr("dictionary", "controlDict", "system") + """application rhoReactingBuoyantLeFoam;
libs (arcChemStep);
startFrom latestTime;
startTime 0;
stopAt endTime;
%spurgeWrite 0;
writeFormat binary;
writePrecision 10;
timeFormat general;
timePrecision 8;
runTimeModifiable true;

functions
{
    minMaxT { type fieldMinMax; libs ("libfieldFunctionObjects.so"); fields (T U); writeControl timeStep; writeInterval 20; }
    #includeFunc flowRatePatch(name=inlet)
    #includeFunc flowRatePatch(name=outlet)
}
""" % timectl)
    open(os.path.join(s, "fvSchemes"), "w").write(hdr("dictionary", "fvSchemes", "system") + """ddtSchemes { default %s; }
gradSchemes { default Gauss linear; }
divSchemes
{
    default         none;
    div(phi,U)      Gauss linearUpwind grad(U);
    div(phi,Yi_h)   Gauss limitedLinear01 1;
    div(phi,K)      Gauss linear;
    div(phid,p)     Gauss limitedLinear 1;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
fluxRequired { default no; p_rgh; }
""" % ddt)
    open(os.path.join(s, "fvSolution"), "w").write(hdr("dictionary", "fvSolution", "system") + """solvers
{
    "rho.*"     { solver diagonal; }
    p_rgh       { solver GAMG; smoother GaussSeidel; tolerance 1e-8; relTol 0.01; }
    p_rghFinal  { $p_rgh; relTol 0; }
    "(U|h)"     { solver PBiCGStab; preconditioner DILU; tolerance 1e-8; relTol 0.1; }
    "(U|h)Final" { $U; relTol 0; }
    Yi          { solver PBiCGStab; preconditioner DILU; tolerance 1e-10; relTol 0; }
}
PIMPLE
{
    momentumPredictor yes;
    nOuterCorrectors 1;
    nCorrectors 2;
    nNonOrthogonalCorrectors 0;
%s}
""" % pimple)
    open(os.path.join(s, "decomposeParDict"), "w").write(hdr("dictionary", "decomposeParDict", "system") +
                                                         "numberOfSubdomains 8;\nmethod scotch;\n")
    allrun = """#!/bin/sh
# COVLOOP Case B (Somers-de Goey slit burner, ARC22 DI). ./Allrun [nProcs]
cd "${0%/*}" || exit 1
set -e
NP=${1:-8}
run() { log=log.$1; shift; echo "Running $* > $log"; "$@" > "$log" 2>&1 || { echo "  failed, see $log"; tail -20 "$log"; exit 1; }; }
run blockMesh blockMesh
run checkMesh checkMesh
rm -rf 0 && cp -r 0.orig 0
run setFields setFields
if [ "$NP" -gt 1 ]; then
    foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
    run decomposePar decomposePar -force
    run solver mpirun -np "$NP" rhoReactingBuoyantLeFoam -parallel
else
    run solver rhoReactingBuoyantLeFoam
fi
"""
    open(os.path.join(out, "Allrun"), "w").write(allrun)
    os.chmod(os.path.join(out, "Allrun"), 0o755)
    with open(os.path.join(out, "CASE_INFO.txt"), "w") as f:
        f.write("phi %g, umax %g m/s, Ly %g m, res %g m, cells ~%d, Tb(HP eq) %.1f K, %s\n" %
                (a.phi, a.umax, a.Ly, a.res, nc, Tb, "LTS" if a.lts else "transient"))
        f.write("fresh Y: " + ", ".join("%s %.5f" % (k, v) for k, v in fresh.items() if v > 0) + "\n")
        f.write("burnt start Y (majors only, NOx = 0): " + ", ".join("%s %.5f" % (k, v) for k, v in burnt.items() if v > 1e-6) + "\n")
    print(open(os.path.join(out, "CASE_INFO.txt")).read().strip())


if __name__ == "__main__":
    main()

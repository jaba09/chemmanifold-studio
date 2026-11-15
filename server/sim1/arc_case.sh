#!/bin/bash
# Turn a prepared GA18 burner case (corrected outlets, rhoReactingBuoyantLeFoam + constantLewis, fvDOM
# wall radiation) into the same case with ARC_GRI30_NOx22 chemistry (22 transported species, arcChemStep).
#   arc_case.sh <GA18 case> <time dir> <new case>
# - constant/: reactions (22 species, no reactions), thermo.compressibleGas (GRI NASA + Sutherland),
#   speciesDiffusion (Le of shared species unchanged), chemistryProperties solver arcChemStep.
# - <time dir>: the GA18-only species (CH2, CH2(S), HCO, CH3O: quasi-steady in the ARC) are removed
#   (their mass, < 1e-4, goes to the inert N2); the 8 new species start from Ydefault = 0 (written here).
# Needs: . /opt/ofb/ofenv.sh, libarcChemStep built (openfoam/arcChemStep/Allwmake).
set -e
SRC=$(realpath "${1:?GA18 case}"); T0=${2:?time dir}; DST=${3:?new case}
HERE=$(dirname "$(realpath "$0")"); REPO=$(realpath "$HERE/../.."); A=$REPO/openfoam/arcChemStep
[ -e "$DST" ] && { echo "$DST exists"; exit 1; }
mkdir -p "$DST"
cp -r "$SRC/constant" "$SRC/system" "$DST/"
[ -d "$SRC/chemkin" ] && cp -r "$SRC/chemkin" "$DST/"
cp -r "$SRC/$T0" "$DST/$T0"
cd "$DST"
rm -rf processor* constant/polyMesh/*.gz.orig 2>/dev/null || true
cp "$A/case/reactions" "$A/case/thermo.compressibleGas" "$A/case/speciesDiffusion" constant/
D() { foamDictionary -entry "$1" -set "$2" "$3" > /dev/null; }
D chemistryType/solver arcChemStep constant/chemistryProperties
foamDictionary -entry odeCoeffs -remove constant/chemistryProperties > /dev/null 2>&1 || true
cat >> constant/chemistryProperties <<'X'

// ARC_GRI30_NOx22 (openfoam/arcChemStep): per-cell constant-pressure ODE of 22 species + T,
// 21 radicals from the linearized QSSA, element projection after each step
arcChemStepCoeffs
{
    kernel          original;       // mechanisms/arc_gri30_nox22/original (unrolled, 3x faster per call than
                                    // the rebuilt tables; rates agree to 2e-8, states after a step to 4e-5)
    // GA18 DI used seulex 1e-10 / 1e-5 (on concentrations). For the ARC rhs (15-26 us, FD Jacobian of 24 calls)
    // seulex 1e-5/1e-12 costs 10.5 ms per hot cell and step; Rosenbrock34 1e-4/1e-9 about 2 ms (222 instead of
    // 873 rhs calls), with per-step errors against seulex 1e-9/1e-16 of at most 1.2e-4 (OH), 6e-5 (HCN, N2O),
    // 1e-5 (NO, CO) and 0.01 K (400 hot A1r cells, openfoam/arcChemStep/bench). absTol is on Y: GA18's 1e-10
    // kmol/m3 is about Y 1e-8 in the hot gas
    solver          Rosenbrock34;
    absTol          1e-9;
    relTol          1e-4;
    T_freeze        0;
    project         true;
    reportCalls     0;
}
X
grep -q 'arcChemStep' system/controlDict || \
    sed -i 's/^application .*/&\n\nlibs                (arcChemStep);/' system/controlDict
# outlet NOx: phi-weighted averages on the two outlets every 10 steps (postProcessing/outletNOx_*)
python3 - system/controlDict <<'PYX'
import re, sys
p = sys.argv[1]; s = open(p).read()
fo = ""
for patch in ("outlet-lab", "wall-fff-fluid-exhaust"):
    fo += '''
    outletNOx_%s
    {
        type            surfaceFieldValue;
        libs            ( "libfieldFunctionObjects.so" );
        writeControl    timeStep;
        writeInterval   10;
        writeFields     false;
        log             false;
        regionType      patch;
        name            %s;
        operation       weightedAverage;
        weightField     phi;
        fields          ( T NO NO2 N2O HCN CO CO2 C2H2 );
    }
''' % (patch, patch)
if "outletNOx_" not in s:
    i = s.index("functions")
    j = s.index("{", i)
    s = s[: j + 1] + fo + s[j + 1 :]
    open(p, "w").write(s)
PYX
# decomposition weight of the hot cells (cellWeight: 25 where T > 800 K, written for GA18). ARC costs about
# 3.1 ms per hot and 0.6 ms per cold cell and step (+ 0.08 ms flow), so hot cells get ARC_WEIGHT (default 5):
# with 25 the ranks holding cold gas got ~37k cells and set the pace
[ -f "$T0/cellWeight" ] && python3 - "$T0/cellWeight" "${ARC_WEIGHT:-5}" <<'PYX'
import re, struct, sys
p, w = sys.argv[1], float(sys.argv[2]); b = open(p, "rb").read()
m = re.search(rb"internalField\s+nonuniform\s+List<scalar>\s*(\d+)\s*\(", b)
if m and b"format      binary" in b:
    n = int(m.group(1)); i = m.end()
    v = struct.unpack("<%dd" % n, b[i:i + 8 * n])
    v = [w if x > 1.5 else x for x in v]
    b = b[:i] + struct.pack("<%dd" % n, *v) + b[i + 8 * n:]
    open(p, "wb").write(b); print("cellWeight: %d hot cells weighted %g" % (sum(x > 1.5 for x in v), w))
elif m:
    t = b.decode(); h, rest = t[:m.end()], t[m.end():]
    body, tail = rest.split(")", 1)
    open(p, "w").write(h + "\n".join(str(w) if float(x) > 1.5 else x for x in body.split()) + "\n)" + tail)
    print("cellWeight (ascii) reweighted to %g" % w)
PYX
# fields of the time dir
for s in CH2 'CH2(S)' HCO CH3O; do rm -f "$T0/$s" "$T0/$s.gz"; done
sed -e 's/^\(    object *\).*;/\1Ydefault;/' "$REPO/openfoam/quemadorUnico/0.orig/Ydefault" > "$T0/Ydefault"
# patches of this mesh that the template does not name (e.g. hood baffles) get zeroGradient via "wall"
echo "ARC case from $SRC time $T0 ($(date '+%F %T %Z'))" > arc_case_origin
echo "ready: $DST"

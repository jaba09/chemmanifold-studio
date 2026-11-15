#!/bin/bash
# Turn the prepared GA18 burner case (corrected outlets, rhoReactingBuoyantLeFoam + constantLewis, fvDOM wall
# radiation) into the same case with full GRI-Mech 3.0 (53 species, 325 reactions), the exact mechanism of Javier's
# Fluent GRI DI case (openfoam/gri30/chemkin), with standard OpenFOAM DI chemistry (ode/seulex 1e-10 / 1e-5, as the
# GA18 DI reference A1r; no TDAC/ISAT).
#   gri_case.sh <GA18 case> <time dir> <new case>
# - constant/: reactions + thermo.compressibleGas from chemkinToFoam (Tlow lowered to 200 K for every species: GRI
#   N2 etc. say 300 K and the cold wall-side cells sit at 299.99 K), speciesDiffusion from openfoam/gri30/case.
# - <time dir>: the 18 GA18 species keep their fields; the 35 others start from Ydefault = 0 (written here).
# - outlet NOx monitors and hot-cell decomposition weight GRI_WEIGHT (default 25) as in arc_case.sh.
# Needs: . /opt/ofb/ofenv.sh
set -e
SRC=$(realpath "${1:?GA18 case}"); T0=${2:?time dir}; DST=${3:?new case}
HERE=$(dirname "$(realpath "$0")"); REPO=$(realpath "$HERE/../.."); G=$REPO/openfoam/gri30
[ -e "$DST" ] && { echo "$DST exists"; exit 1; }
mkdir -p "$DST"
cp -r "$SRC/constant" "$SRC/system" "$DST/"
cp -r "$SRC/$T0" "$DST/$T0"
mkdir -p "$DST/chemkin"; cp "$G"/chemkin/* "$DST/chemkin/"
cd "$DST"
rm -rf processor* 2>/dev/null || true
chemkinToFoam chemkin/chem.foam.inp chemkin/therm.foam.dat chemkin/transportProperties \
    constant/reactions constant/thermo.compressibleGas > log.chemkinToFoam 2>&1 || { tail log.chemkinToFoam; exit 1; }
python3 - constant/thermo.compressibleGas <<'PYX'
import re, sys
p = sys.argv[1]; s = open(p).read()
n = 0
def low(m):
    global n
    if float(m.group(2)) > 200: n += 1; return m.group(1) + "200"
    return m.group(0)
s = re.sub(r"(Tlow\s+)([0-9.eE+-]+)", low, s)
open(p, "w").write(s); print("Tlow lowered to 200 K for %d species" % n)
PYX
cp "$G/case/speciesDiffusion" constant/
grep -q "Number of species\|^species" constant/reactions
# chemistry: standard OpenFOAM DI as the GA18 reference (ode / seulex absTol 1e-10 relTol 1e-5, from the base)
foamDictionary -entry chemistryType/solver -set ode constant/chemistryProperties > /dev/null
foamDictionary -entry odeCoeffs/solver -set seulex constant/chemistryProperties > /dev/null
foamDictionary -entry odeCoeffs/absTol -set 1e-10 constant/chemistryProperties > /dev/null
foamDictionary -entry odeCoeffs/relTol -set 1e-5 constant/chemistryProperties > /dev/null
# outlet NOx: phi-weighted averages on the two outlets every 10 steps (postProcessing/outletNOx_*)
python3 - system/controlDict <<'PYX'
import sys
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
    j = s.index("{", s.index("functions"))
    s = s[: j + 1] + fo + s[j + 1 :]
    open(p, "w").write(s)
PYX
# decomposition weight of the hot cells (base cellWeight: 25 where T > 800 K)
[ -f "$T0/cellWeight" ] && python3 - "$T0/cellWeight" "${GRI_WEIGHT:-25}" <<'PYX'
import re, struct, sys
p, w = sys.argv[1], float(sys.argv[2]); b = open(p, "rb").read()
m = re.search(rb"internalField\s+nonuniform\s+List<scalar>\s*(\d+)\s*\(", b)
if m and b"format      binary" in b:
    n = int(m.group(1)); i = m.end()
    v = [w if x > 1.5 else x for x in struct.unpack("<%dd" % n, b[i:i + 8 * n])]
    open(p, "wb").write(b[:i] + struct.pack("<%dd" % n, *v) + b[i + 8 * n:])
    print("cellWeight: %d hot cells weighted %g" % (sum(x > 1.5 for x in v), w))
PYX
sed -e 's/^\(    object *\).*;/\1Ydefault;/' "$REPO/openfoam/quemadorUnico/0.orig/Ydefault" > "$T0/Ydefault"
echo "GRI-Mech 3.0 case from $SRC time $T0 ($(date '+%F %T %Z'))" > gri_case_origin
echo "ready: $DST (53 species, 325 reactions, see log.chemkinToFoam)"

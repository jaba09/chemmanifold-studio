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
    solver          seulex;
    absTol          1e-12;
    relTol          1e-5;           // GA18 DI used seulex 1e-10 / 1e-5 (on concentrations)
    T_freeze        0;
    project         true;
    reportCalls     0;
}
X
grep -q 'arcChemStep' system/controlDict || \
    sed -i 's/^application .*/&\n\nlibs                (arcChemStep);/' system/controlDict
# fields of the time dir
for s in CH2 'CH2(S)' HCO CH3O; do rm -f "$T0/$s" "$T0/$s.gz"; done
sed -e 's/^\(    object *\).*;/\1Ydefault;/' "$REPO/openfoam/quemadorUnico/0.orig/Ydefault" > "$T0/Ydefault"
# patches of this mesh that the template does not name (e.g. hood baffles) get zeroGradient via "wall"
echo "ARC case from $SRC time $T0 ($(date '+%F %T %Z'))" > arc_case_origin
echo "ready: $DST"

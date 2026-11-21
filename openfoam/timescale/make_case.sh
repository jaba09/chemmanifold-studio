#!/bin/bash
# Build a cheap-flame LTS case for the timescale roadmap (step 1) from the GA18 base case.
#   make_case.sh <base case dir> <out dir> <2step|1step> [nprocs]
# Mesh, patches, boundary values and the lit start (phi 0.5 burnt gas at 1480 K in the gap and
# mixing zones) are copied unchanged; only the chemistry and the run controls change.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
BASE=$1; OUT=$2; MECH=$3; NP=${4:-2}
REPO_CASE=$HERE/../quemadorUnico
[ -d "$BASE/constant/polyMesh" ] || { echo "no base case at $BASE"; exit 1; }
rm -rf "$OUT"; mkdir -p "$OUT"
cp -r "$BASE/constant" "$BASE/system" "$OUT/"
mkdir "$OUT/0"
for f in "$BASE"/0/*; do
    n=$(basename "$f")
    case $n in CH4|O2|H2O|CO2|N2|T|U|p|p_rgh|k|omega|nut|alphat|Ydefault|cellWeight) cp "$f" "$OUT/0/";; esac
done
cp "$HERE/reactions.$MECH" "$OUT/constant/reactions"
cp "$HERE/controlDict.lts" "$OUT/system/controlDict"
cp "$REPO_CASE/system/fvSchemes" "$REPO_CASE/system/fvSolution" "$OUT/system/"
sed -i "s/^numberOfSubdomains.*/numberOfSubdomains $NP;/" "$OUT/system/decomposeParDict"
cp "$HERE/../../openfoam/quemadorUnico/system/tauCellHistogram" "$OUT/system/" 2>/dev/null || cp "$BASE/system/tauCellHistogram" "$OUT/system/"
# schemes and solver for the gas-age function object
python3 - "$OUT" <<'PY'
import re, sys
o = sys.argv[1]
f = o + "/system/fvSchemes"; t = open(f).read()
t = t.replace("div(phid,p)", "div(phi,age)    bounded Gauss upwind;\n    div(phid,p)", 1)
open(f, "w").write(t)
f = o + "/system/fvSolution"; t = open(f).read()
t = re.sub(r"(solvers\s*\{)", r"\1\n    age\n    {\n        solver          PBiCGStab;\n        preconditioner  DILU;\n        tolerance       1e-8;\n        relTol          0;\n    }\n", t, count=1)
open(f, "w").write(t)
PY
# the 1-step CH4^0.2 order makes the Jacobian singular at CH4 = 0 (seulex stops with an FPE): explicit RKF45
[ "$MECH" = 1step ] && sed -i 's/solver          seulex;/solver          RKF45;/' "$OUT/constant/chemistryProperties"
echo "case $OUT ready ($MECH, $NP ranks)"

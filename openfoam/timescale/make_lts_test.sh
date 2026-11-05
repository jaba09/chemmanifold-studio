#!/bin/bash
# Steady (LTS) test of the timescale roadmap (test 6b): the burner from the lit start with local time
# stepping, chemistry advanced over Fluent's tau_cell per cell (userChemStep dtMode tauCell).
#   make_lts_test.sh <base case> <run dir> <model dir> <pure|di> [nProcs] [endIter]
#   pure  surrogate in every cell (OOD cells only counted)
#   di    GA18 (ODE solver) in every hot cell, same tau_cell step: the reference for pure runs
# then: cd <run dir> && mpirun -np <nProcs> rhoReactingBuoyantFoam -parallel >> log.run 2>&1
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
BASE=${1:?base}; RUN=${2:?run dir}; MODEL=${3:?model dir}; MODE=${4:?pure or di}; NP=${5:-2}; END=${6:-4250}
"$HERE/../tools/setup_hybrid.sh" "$BASE" "$RUN" "$MODEL" "$NP" > /dev/null
cd "$RUN"
rm -rf processor*
cp "$HERE/../quemadorUnico/system/fvSchemes" "$HERE/../quemadorUnico/system/fvSolution" system/
for kv in "endTime $END" "deltaT 1" "writeControl timeStep" "writeInterval 250" "purgeWrite 0" "startFrom latestTime"; do
    set -- $kv; foamDictionary -entry "$1" -set "$2" system/controlDict > /dev/null
done
python3 - "$MODE" <<'PY'
import re, sys
mode = sys.argv[1]
f = "constant/chemistryProperties"; t = open(f).read()
extra = "    dtMode       tauCell;   // Fluent's steady stiff-chemistry step (timescale roadmap 6b)\n"
if mode == "pure":
    t = re.sub(r"oodFallback\s+true;[^\n]*", "oodFallback  false;      // pure surrogate: OOD cells are only counted", t)
else:
    extra += "    odeAbove     0;         // every hot cell on GA18 (reference)\n"
    t = re.sub(r"shadowEvery\s+50;", "shadowEvery  0;", t)
t = re.sub(r"(userChemStepCoeffs\s*\{)", r"\1\n" + extra, t, count=1)
open(f, "w").write(t)
PY
foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
decomposePar -force > log.decomposePar 2>&1
echo "ready: $RUN ($MODE, tauCell, $NP ranks, $END iterations)"

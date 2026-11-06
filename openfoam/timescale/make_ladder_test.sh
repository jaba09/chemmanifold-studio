#!/bin/bash
# Steady (LTS) test 6b with the LADDER of fixed-time-step surrogates (Javier, 2026-11-06): each cell's
# chemistry step tau_cell is rounded to the nearest multiple of the smallest model's dt and split
# greedily into calls of the models, largest first (1.36e-3 s = 1 x 1e-3 + 3 x 1e-4 + 6 x 1e-5).
#   make_ladder_test.sh <base case> <run dir> <main model dir> <nProcs> <endIter> <ladder model dir>...
# The main model (e.g. the 1e-5 one) gives the self-test; every ladder dir holds a
# chemmanifold_model.txt trained at one dt. Pure mode (OOD cells only counted), shadow DI check on.
# Same environment options as make_lts_test.sh (INIT, MAXCO, SMAX).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
BASE=${1:?base}; RUN=${2:?run dir}; MAIN=${3:?main model dir}; NP=${4:?nProcs}; END=${5:?endIter}
shift 5
[ $# -ge 2 ] || { echo "need at least two ladder model dirs"; exit 1; }
"$HERE/make_lts_test.sh" "$BASE" "$RUN" "$MAIN" pure "$NP" "$END"
cd "$RUN"
list=""
for d in "$@"; do
    n=ladder_$(basename "$d").txt
    cp "$d/chemmanifold_model.txt" "$n"
    list="$list \"$n\""
done
sed -i "0,/userChemStepCoeffs\s*{/s//userChemStepCoeffs\n{\n    ladder       ($list );   \/\/ fixed-dt models, tau_cell split largest first/" constant/chemistryProperties
# processor dirs copy constant/ by reference in v2412 (case-level constant); re-decompose to be safe
decomposePar -force > log.decomposePar 2>&1
echo "ladder: $list"

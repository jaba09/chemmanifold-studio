#!/bin/bash
# Turn a prepared burner case (mesh, GA18, LeFoam + constantLewis, field in an ASCII <time>/)
# into a time-accurate run case: Euler, fixed dt 2e-5 s, PIMPLE 1 outer / 2 pressure correctors,
# cellWeight-weighted scotch decomposition on NP ranks (TCUT/WEIGHT env, default T > 500 K -> 5).
#   make_transient.sh <prepared case> <new run dir> <NP> [time dir, default 0]
set -e
SRC=$(realpath "${1:?prepared case}"); RUN=${2:?run dir}; NP=${3:?ranks}; T0=${4:-0}
HERE=$(dirname "$(realpath "$0")")
[ -e "$RUN" ] && { echo "$RUN exists"; exit 1; }
mkdir -p "$RUN"
cp -r "$SRC/constant" "$SRC/system" "$SRC/chemkin" "$RUN/"
cp -r "$SRC/$T0" "$RUN/$T0"
# keep the species and flow fields only (Cx/Cy/Cz/C are the cell centres used for mapping)
cd "$RUN"
rm -f "$T0/C" "$T0/Cx" "$T0/Cy" "$T0/Cz"
D() { foamDictionary -entry "$1" -set "$2" "$3" > /dev/null; }
D ddtSchemes/default Euler system/fvSchemes
D startFrom latestTime system/controlDict
D startTime "$T0" system/controlDict
D deltaT 2e-5 system/controlDict
D writeControl timeStep system/controlDict
D writeFormat binary system/controlDict
D timePrecision 8 system/controlDict
D PIMPLE/nCorrectors 2 system/fvSolution
D numberOfSubdomains "$NP" system/decomposeParDict
grep -q weightField system/decomposeParDict || sed -i 's/^method .*/&\nweightField         cellWeight;     \/\/ 25 for T > 800 K (chemistry balance)/' system/decomposeParDict
grep -q '#include "tauCellHistogram"' system/controlDict || \
    sed -i '0,/^functions/{/^functions/{n;s/^{/{\n    #include "tauCellHistogram"/}}' system/controlDict
python3 "$HERE/write_cell_weight.py" "$T0" "${TCUT:-500}" "${WEIGHT:-5}"   # measured best on sim1 (S3); 800/25 was 30 % slower
decomposePar -force -time "$T0" > log.decomposePar 2>&1
echo "ready: $RUN ($NP ranks, from $T0)"

#!/bin/bash
# Move a decomposed run to another rank count at its latest write: reconstruct that time,
# rewrite cellWeight from its T, decompose for NP ranks. Stop the run first.
#   redecompose.sh <run dir> <np>
set -e
RUN=$(realpath "${1:?run dir}"); NP=${2:?ranks}; HERE=$(dirname "$(realpath "$0")")
. /opt/ofb/ofenv.sh
cd "$RUN"
T=$(ls processor0 | grep -E '^[0-9.e+-]+$' | sort -g | tail -1)
reconstructPar -time "$T" > log.reconstructPar 2>&1
foamDictionary -entry writeFormat -set ascii system/controlDict > /dev/null
foamFormatConvert -time "$T" > log.foamFormatConvert 2>&1
python3 "$HERE/write_cell_weight.py" "$T" "${TCUT:-500}" "${WEIGHT:-5}"
foamDictionary -entry writeFormat -set binary system/controlDict > /dev/null
foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
decomposePar -force -time "$T" > log.decomposePar 2>&1
find "$RUN/$T" -mindepth 1 -maxdepth 1 ! -name uniform -exec rm -rf {} +   # processor*/T/uniform links to it
echo "$(date '+%F %T %Z') redecomposed at $T for $NP ranks" >> supervisor.log

#!/bin/bash
# Compare the latest write of a decomposed burner run with the corrected Fluent DI solution.
#   progress.sh <run dir> [time]      -> <run dir>/progress/compare_<t>.txt and .png
# Reconstructs that one time into a scratch copy (serial, niced), so the running case is untouched.
RUN=$(realpath "${1:?run dir}"); HERE=$(dirname "$(realpath "$0")"); REPO=$(realpath "$HERE/../..")
DAT=${DAT:-$HOME/inputs/sim1-extra/fluent-corrected/quemadorUnicoTesis_60KCells-GA18--ID.dat.h5}
. /opt/ofb/ofenv.sh
T=${2:-$(ls "$RUN/processor0" | grep -E '^[0-9.e+-]+$' | sort -g | tail -1)}
W=/opt/ofb/runs/.progress_$(basename "$RUN"); rm -rf "$W"; mkdir -p "$W" "$RUN/progress"
cp -r "$RUN/constant" "$RUN/system" "$W/"
for p in "$RUN"/processor*; do mkdir -p "$W/$(basename $p)"; ln -s "$p/constant" "$W/$(basename $p)/constant"; cp -r "$p/$T" "$W/$(basename $p)/"; done
cd "$W"
foamDictionary -entry writeFormat -set ascii system/controlDict > /dev/null
nice -n 19 reconstructPar -time "$T" > log.rec 2>&1 || { tail -5 log.rec; exit 1; }
nice -n 19 foamFormatConvert -time "$T" > log.ffc 2>&1
nice -n 19 postProcess -func writeCellCentres -time "$T" > log.cc 2>&1
nice -n 19 postProcess -func writeCellVolumes -time "$T" > log.cv 2>&1   # compare_fluent needs <t>/V for volumes
nice -n 19 /opt/ofb/ml/bin/python "$REPO/openfoam/tools/compare_fluent.py" . "$T" "$DAT" \
    "$RUN/progress/compare_$T.png" --label "$(basename "$RUN") t=$T" > "$RUN/progress/compare_$T.txt" 2>&1
cat "$RUN/progress/compare_$T.txt"
cd /; rm -rf "$W"

#!/bin/bash
# Gate G1 material for A1 (R2): Fluent vs (a) the R2 mean field (fieldAverage, t = 0.1 .. T),
# (b) the final instantaneous field, (c) every kept snapshot from 0.1 s (drift series).
#   g1_report.sh <run dir> [final time]     -> <run dir>/g1/*.txt, *.png
# Reconstructs into a scratch copy (niced); the run dir is not touched.
RUN=$(realpath "${1:?run dir}"); HERE=$(dirname "$(realpath "$0")"); REPO=$(realpath "$HERE/../..")
DAT=${DAT:-$HOME/inputs/sim1-extra/fluent-corrected/quemadorUnicoTesis_60KCells-GA18--ID.dat.h5}
PY=/opt/ofb/ml/bin/python; N="nice -n ${NICE:-19}"
. /opt/ofb/ofenv.sh
TF=${2:-$(ls "$RUN/processor0" | grep -E '^[0-9.e+-]+$' | sort -g | tail -1)}
OUT=$RUN/g1; W=/opt/ofb/runs/.g1_$(basename "$RUN"); rm -rf "$W"; mkdir -p "$W" "$OUT"
cp -r "$RUN/constant" "$RUN/system" "$W/"
TIMES=$(ls "$RUN/processor0" | grep -E '^[0-9.e+-]+$' | sort -g | awk -v tf="$TF" '$1 >= 0.0999 && $1 <= tf + 1e-9')
for p in "$RUN"/processor*; do
    q=$W/$(basename "$p"); mkdir -p "$q"; ln -s "$p/constant" "$q/constant"
    for t in $TIMES; do cp -r "$p/$t" "$q/"; done
done
cd "$W"
foamDictionary -entry writeFormat -set ascii system/controlDict > /dev/null
foamDictionary -entry functions -set "{}" system/controlDict > /dev/null
for t in $TIMES; do
    $N reconstructPar -time "$t" > log.rec 2>&1 || { echo "reconstruct $t failed"; tail -5 log.rec; exit 1; }
    $N foamFormatConvert -time "$t" > log.ffc 2>&1
    rm -rf processor*/"$t"
done
$N postProcess -func writeCellCentres -time "$TF" > log.cc 2>&1
$N postProcess -func writeCellVolumes -time "$TF" > log.cv 2>&1
for t in $TIMES; do [ "$t" = "$TF" ] || cp "$TF/C" "$TF/V" "$t/"; done
# (a) mean field: a time dir "mean" whose T, U, Y are the fieldAverage means at TF
rm -rf mean; cp -r "$TF" mean
for f in "$TF"/*Mean; do b=$(basename "$f"); case $b in *Prime2Mean) ;; *) cp "$f" "mean/${b%Mean}";; esac; done
$N $PY "$REPO/openfoam/tools/compare_fluent.py" . mean "$DAT" "$OUT/compare_mean.png" --label "R2 mean 0.1-$TF s" \
    > "$OUT/compare_mean.txt" 2>&1
# (b) final instantaneous, (c) drift series
for t in $TIMES; do
    $N $PY "$REPO/openfoam/tools/compare_fluent.py" . "$t" "$DAT" "$OUT/snap_$t.png" --label "R2 t=$t" \
        > "$OUT/compare_$t.txt" 2>&1
    [ "$t" = "$TF" ] || rm -f "$OUT/snap_$t.png"
done
# T RMS from TPrime2Mean (for the flicker map)
cp "$TF/TPrime2Mean" "$OUT/TPrime2Mean_$TF" ; cp "$TF/C" "$OUT/C"; cp "$TF/V" "$OUT/V"
echo "$TF" > "$OUT/final_time"
cd /; rm -rf "$W"
echo "g1 material in $OUT"

#!/bin/bash
# Snapshots of a running protocol leg before it ends (run_protocol_v2.sh exports them only at the end), from a scratch
# copy of the decomposed writes; the run dir is not touched. Niced, 1 core.
#   arc_early.sh <run dir> <label> <out snap dir> [t0 [t1]]   (times written in processor0 within [t0, t1])
RUN=$(realpath "${1:?run dir}"); LAB=${2:?label}; OUTS=${3:?out dir}; T0=${4:-0}; T1=${5:-1e9}
HERE=$(dirname "$(realpath "$0")"); REPO=$(realpath "$HERE/../.."); PY=${PY:-/opt/ofb/ml/bin/python}
. /opt/ofb/ofenv.sh
S=$(dirname "$RUN")/.early_$(basename "$RUN"); rm -rf "$S"; mkdir -p "$S" "$OUTS"
cp -r "$RUN/constant" "$RUN/system" "$S/"
TIMES=$(ls "$RUN/processor0" | grep -E '^[0-9.e+-]+$' | sort -g | awk -v a="$T0" -v b="$T1" '$1 >= a - 1e-9 && $1 <= b + 1e-9')
for p in "$RUN"/processor*; do
    q=$S/$(basename "$p"); mkdir -p "$q"; ln -s "$p/constant" "$q/constant"
    for t in $TIMES; do [ -f "$p/$t/T" ] && cp -r "$p/$t" "$q/"; done
done
for t in $TIMES; do
    nice -n 19 $PY "$REPO/openfoam/tools/foam_snapshot.py" "$S" "$OUTS" --label "$LAB" --times "$t" --skip-existing
    rm -rf "$S/$t" "$S"/processor*/"$t"
done
rm -rf "$S" "$OUTS/.pp_$LAB"

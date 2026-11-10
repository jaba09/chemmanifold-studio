#!/bin/bash
# A3: cheap 2-step LeFoam flame (LTS) from the Fluent start, run until settled, then stage 19.
# Settled = at least 4000 iterations and domain Tmax range < 10 K over the last 1000 iterations
# (checked every 1000; hard stop at 15000). Resumable: rerun the same command.
#   a3_run.sh <case dir> <np>
CASE=$(realpath "${1:?case}"); NP=${2:-4}; HERE=$(dirname "$(realpath "$0")")
REPO=$(realpath "$HERE/../.."); PY=/opt/ofb/ml/bin/python
. /opt/ofb/ofenv.sh
cd "$CASE" || exit 1
foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
[ -d processor0 ] || decomposePar -force > log.decomposePar 2>&1
latest() { ls processor0 | grep -E '^[0-9.e+-]+$' | sort -g | tail -1; }
settled() {
    f=$(ls postProcessing/minMaxT/*/fieldMinMax.dat 2>/dev/null | sort -V | xargs cat 2>/dev/null)
    echo "$f" | awk -v L="$(latest)" '$1 !~ /#/ && $2 == "T" { t[$1] = $8 + 0 }
        END { n = 0; mn = 1e9; mx = 0; for (i in t) if (i + 0 > L - 1000) { n++; if (t[i] < mn) mn = t[i]; if (t[i] > mx) mx = t[i] }
              printf "Tmax range over last 1000 it: %.1f K (%d samples)\n", mx - mn, n > "/dev/stderr"; exit !(L >= 4000 && n > 50 && mx - mn < 10) }'
}
echo running > status
while true; do
    L=$(latest); L=${L:-0}
    if [ "$L" -ge 15000 ] || settled 2>> supervisor.log; then break; fi
    END=$((L - L % 1000 + 1000))
    foamDictionary -entry endTime -set $END system/controlDict > /dev/null
    echo "$(date '+%F %T %Z') leg to $END from $L" >> supervisor.log
    mpirun -np "$NP" rhoReactingBuoyantLeFoam -parallel >> log.run 2>&1 || {
        echo "$(date '+%F %T %Z') solver failed at $(latest)" >> supervisor.log; tail -30 log.run > crash_$(latest).txt
        [ "$(latest)" = "$L" ] && { echo "failed $L" > status; exit 1; }; }
done
T=$(latest); echo "$(date '+%F %T %Z') settled/stopped at $T; stage 19" >> supervisor.log
cd "$REPO" && $PY scripts/19_flow_statistics.py case "$CASE" --time "$T" --label A3_wd2_lefoam \
    --out "$REPO/data/timescale" > "$CASE/log.stage19" 2>&1 \
    && echo "completed $T" > "$CASE/status" || echo "stage19 failed $T" > "$CASE/status"

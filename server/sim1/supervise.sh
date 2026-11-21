#!/bin/bash
# Resumable supervisor for a decomposed transient run. Runs a list of legs; each leg sets
# endTime, writeInterval (time steps) and purgeWrite, then runs from the latest processor write.
# On a crash it restarts from the last write (up to MAX_RETRY times per leg in a row).
#   supervise.sh <run dir> <np> <end1:wi1:purge1> [<end2:wi2:purge2> ...]
# Status goes to <run dir>/supervisor.log; "completed" in <run dir>/status at the end.
RUN=$(realpath "${1:?run dir}"); NP=${2:?ranks}; shift 2
MAX_RETRY=${MAX_RETRY:-3}
. /opt/ofb/ofenv.sh
cd "$RUN" || exit 1
APP=$(foamDictionary -entry application -value system/controlDict)
log() { echo "$(date '+%F %T %Z') $*" >> supervisor.log; }
latest() { ls processor0 | grep -E '^[0-9.e+-]+$' | sort -g | tail -1; }
lt() { awk "BEGIN{exit !($1 < $2 - 1e-9)}"; }
echo running > status
for L in "$@"; do
    IFS=: read END WI PURGE <<< "$L"
    tries=0
    while lt "$(latest)" "$END"; do
        foamDictionary -entry endTime -set "$END" system/controlDict > /dev/null
        foamDictionary -entry writeInterval -set "$WI" system/controlDict > /dev/null
        foamDictionary -entry purgeWrite -set "$PURGE" system/controlDict > /dev/null
        foamDictionary -entry startFrom -set latestTime system/controlDict > /dev/null
        from=$(latest); log "leg end=$END wi=$WI purge=$PURGE from $from (try $tries)"
        mpirun -np "$NP" "$APP" -parallel >> log.run 2>&1
        rc=$?
        if [ $rc = 0 ] && [ "$(latest)" = "$from" ] && tail -3 log.run | grep -q '^Finalising'; then
            # reached END cleanly but END is not on the write grid (timeStep control): rerun the last
            # stretch writing on simulated time (multiples of END -> exactly at END)
            log "END not on the write grid; rerunning from $from with writeControl runTime"
            foamDictionary -entry writeControl -set runTime system/controlDict > /dev/null
            foamDictionary -entry writeInterval -set "$END" system/controlDict > /dev/null
            mpirun -np "$NP" "$APP" -parallel >> log.run 2>&1; rc=$?
            foamDictionary -entry writeControl -set timeStep system/controlDict > /dev/null
            foamDictionary -entry writeInterval -set "$WI" system/controlDict > /dev/null
        fi
        if lt "$(latest)" "$END"; then
            tries=$((tries + 1)); log "solver exited rc=$rc at $(latest)"
            tail -30 log.run > "crash_$(latest).txt"
            [ "$tries" -gt "$MAX_RETRY" ] && { echo "failed $(latest)" > status; log "giving up"; exit 1; }
            sleep 10
        fi
    done
done
log "completed $(latest)"; echo "completed $(latest)" > status

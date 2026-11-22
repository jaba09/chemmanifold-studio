#!/bin/bash
# Keeps the disk flat while the axis_ext.sh legs run: every 10 min, for each case, export every completed processor write
# to its snapshot CSV (foam_snapshot.py, niced, one time at a time) and then delete that write. The two newest writes are
# always kept (restart point and a write that may still be in progress). Stops when both legs have finished.
#   systemd-run --user --unit=sim1-axis-prune -p Nice=15 -p WorkingDirectory=/opt/ofb/arc22-src bash server/sim1/axis_prune.sh
REPO=$(realpath "$(dirname "$(realpath "$0")")/../.."); W=${W:-/opt/ofb/runs/arc22}; PY=${PY:-/opt/ofb/ml/bin/python}
. /opt/ofb/ofenv.sh
LOG=$W/axis_ext.log; say() { echo "$(date '+%F %T %Z') [prune] $*" >> "$LOG"; }
T_KEEP_FROM=${T_KEEP_FROM:-0.0}     # writes before this time are deleted without export (none by default)
prune() {   # <case> <label>
    local C=$1 L=$2 t csv
    [ -d "${C:?}/processor0" ] || return 0
    local times; times=$(ls "$C/processor0" | grep -E '^[0-9.]+$' | sort -g | head -n -2)
    for t in $times; do
        csv=$(printf "%s/snap/%s_t%07.2fms.csv" "$C" "$L" "$(awk -v t="$t" 'BEGIN{print t*1000}')")
        if [ ! -f "$csv" ]; then
            ( cd "$C" && nice -n 15 $PY "$REPO/openfoam/tools/foam_snapshot.py" . snap --label "$L" --times "$t" \
                  --skip-existing >> log.snapshots 2>&1 )
        fi
        if [ -f "$csv" ]; then
            rm -rf "${C:?}/${t:?}"
            for p in "$C"/processor*; do rm -rf "${p:?}/${t:?}"; done
            say "$L $t exported and pruned"
        else
            say "$L $t export failed, write kept"
        fi
    done
}
say "start"
while systemctl --user is-active -q sim1-axis-arc || systemctl --user is-active -q sim1-axis-gri; do
    systemctl --user is-active -q sim1-axis-arc && prune "$W/flame_ext" arc22_ext
    systemctl --user is-active -q sim1-axis-gri && prune "$W/gri/flame_ext" gri53_ext
    sleep 600
done
say "done (legs finished)"

#!/bin/bash
# L306 remedy (iii): extend the ARC and GRI-Mech 3.0 burner flames to T_END (default 0.3 s) with the radiation settings
# that removed the near-axis divergence (remedy ii-a: fvDOM nPhi = nTheta = 8, 256 rays, maxIter 10, solved every
# 10 steps). ARC continues /opt/ofb/runs/arc22/flame_ext (restarted from 0.185 s); GRI restarts from its 0.15 s write.
# Writes every 2.5 ms; snapshots (foam_snapshot.py) and field files for the common window T_AVG-T_END; NP ranks, one leg
# after the other. Run as a systemd user unit (after sim1-arc-ext has ended):
#   systemd-run --user --unit=sim1-axis-ext -p WorkingDirectory=/opt/ofb/arc22-src env NP=8 bash server/sim1/axis_ext.sh
set -e
REPO=$(realpath "$(dirname "$(realpath "$0")")/../.."); NP=${NP:-8}; T_END=${T_END:-0.3}; T_AVG=${T_AVG:-0.2}
W=${W:-/opt/ofb/runs/arc22}; PY=${PY:-/opt/ofb/ml/bin/python}; OUT=$REPO/results/sim1/ARC22/fields
. /opt/ofb/ofenv.sh
LOG=$W/axis_ext.log; say() { echo "$(date '+%F %T %Z') $*" | tee -a "$LOG"; }
latest() { ls "$1/processor0" | grep -E '^[0-9.e+-]+$' | sort -g | tail -1; }
lt() { awk "BEGIN{exit !($1 < $2 - 1e-9)}"; }
while systemctl --user is-active -q sim1-arc-ext; do sleep 60; done
say "start (NP $NP, to $T_END s, window $T_AVG-$T_END s)"

run_leg() {   # <case> <label>
    local C=$1 L=$2
    cd "$C"
    foamDictionary -entry startFrom -set latestTime system/controlDict > /dev/null
    foamDictionary -entry endTime -set "$T_END" system/controlDict > /dev/null
    foamDictionary -entry writeInterval -set 0.0025 system/controlDict > /dev/null
    if lt "$(latest "$C")" "$T_END"; then
        say "$L from $(latest "$C") s"
        mpirun -np "$NP" rhoReactingBuoyantLeFoam -parallel >> log.run 2>&1 || say "$L solver returned $?"
    fi
    say "$L reached $(latest "$C") s"
    $PY "$REPO/openfoam/tools/foam_snapshot.py" . snap --label "$L" --skip-existing > log.snapshots 2>&1 || say "$L snapshots returned $?"
    # disk: keep the latest processor write and the snapshots only
    local K; K=$(latest "$C")
    find . -maxdepth 1 -type d -regex '\./[0-9.e+-]+' -exec rm -rf {} +
    for p in processor*; do find "$p" -maxdepth 1 -type d -regex '.*/[0-9.e+-]+' ! -name "$K" -exec rm -rf {} +; done
    cd - > /dev/null
}

# ARC: flame_ext already carries the remedy settings
run_leg "$W/flame_ext" arc22_ext

# GRI: new case from the 0.15 s write of the GRI leg, same radiation settings, IDefault for the added rays
G=$W/gri/flame_ext
if [ ! -d "$G" ]; then
    S=$W/gri/flame; T0=$(latest "$S")
    mkdir -p "$G"; cp -r "$S/constant" "$S/system" "$S/chemkin" "$G/"
    for p in "$S"/processor*; do q=$G/$(basename "$p"); mkdir -p "$q"; cp -r "$p/constant" "$p/$T0" "$q/"; done
    cp "$W/flame_ext/constant/radiationProperties" "$G/constant/"
    for p in "$G"/processor*; do cp "$W/IDefault.processor" "$p/$T0/IDefault"; done   # uniform 300 K start for the added rays
    say "GRI case from $S at $T0 s"
fi
run_leg "$G" gri53_ext

# field files for the common window and the end state
for L in arc22_ext gri53_ext; do
    C=$W/flame_ext; [ "$L" = gri53_ext ] && C=$G
    $PY "$REPO/server/sim1/arc_fields.py" "$C/snap" "$L" "$T_AVG" "$T_END" "$OUT/${L}_mean_${T_AVG}-${T_END}.npz" >> "$LOG" 2>&1
    $PY "$REPO/server/sim1/arc_fields.py" "$C/snap" "$L" "$T_END" "$T_END" "$OUT/${L}_t${T_END}.npz" >> "$LOG" 2>&1
done
$PY "$REPO/server/sim1/compare_of_fields.py" "$OUT/arc22_ext_mean_${T_AVG}-${T_END}.npz" ARC22 \
    "$OUT/gri53_ext_mean_${T_AVG}-${T_END}.npz" GRI53 > "$REPO/results/sim1/ARC22/compare_of_gri_ext.md" 2>&1
say "done"

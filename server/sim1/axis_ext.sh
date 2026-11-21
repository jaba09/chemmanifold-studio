#!/bin/bash
# L306 remedy (iii): extend the ARC and GRI-Mech 3.0 burner flames to T_END (default 0.3 s) with the radiation settings
# that removed the near-axis divergence (remedy ii-a: fvDOM nPhi = nTheta = 8, 256 rays, maxIter 10, solved every
# 10 steps) plus remedy (ii-b), applied on 21 Nov at the restart times (ARC 0.205 s, GRI 0.15 s) with
# changeDictionary -parallel and server/sim1/axis_ext_changeDictionaryDict: qrRelaxation 0.2 and relaxation 0.5 in the
# T boundary conditions of the pot walls (the pot-top axis corner ran away at 0.2074-0.2276 s with (ii-a) alone), and,
# because that did not stop it, remedy (ii-c): the pot upper side + top (wall-pot-fff-fluid-exhaust, x = 85-200 mm) at
# a fixed temperature equal to its face values at the restart time (ARC 0.205 s, GRI 0.155 s). Passed 0.209 s cleanly.
# ARC continues /opt/ofb/runs/arc22/flame_ext (restarted from 0.185 s); GRI restarts from its 0.15 s write.
# Writes every 2.5 ms; snapshots (foam_snapshot.py) and field files for the common window T_AVG-T_END.
# LEG=arc | gri runs one leg on NP ranks (the two can run side by side, 16 cores approved on 21 Nov);
# LEG=fields waits for both legs and writes the field files and the comparison; LEG=all does everything in sequence.
#   systemd-run --user --unit=sim1-axis-arc -p WorkingDirectory=/opt/ofb/arc22-src env NP=8 LEG=arc bash server/sim1/axis_ext.sh
#   systemd-run --user --unit=sim1-axis-gri -p WorkingDirectory=/opt/ofb/arc22-src env NP=8 LEG=gri bash server/sim1/axis_ext.sh
#   systemd-run --user --unit=sim1-axis-fields -p WorkingDirectory=/opt/ofb/arc22-src env LEG=fields bash server/sim1/axis_ext.sh
set -e
REPO=$(realpath "$(dirname "$(realpath "$0")")/../.."); NP=${NP:-8}; LEG=${LEG:-all}; T_END=${T_END:-0.3}; T_AVG=${T_AVG:-0.2}
W=${W:-/opt/ofb/runs/arc22}; PY=${PY:-/opt/ofb/ml/bin/python}; OUT=$REPO/results/sim1/ARC22/fields
. /opt/ofb/ofenv.sh
LOG=$W/axis_ext.log; say() { echo "$(date '+%F %T %Z') [$LEG] $*" | tee -a "$LOG"; }
latest() { ls "$1/processor0" | grep -E '^[0-9.e+-]+$' | sort -g | tail -1; }
lt() { awk "BEGIN{exit !($1 < $2 - 1e-9)}"; }
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
if [ "$LEG" = arc ] || [ "$LEG" = all ]; then
    run_leg "$W/flame_ext" arc22_ext; touch "$W/.axis_done_arc"
fi

# GRI: new case from the 0.15 s write of the GRI leg, same radiation settings, IDefault for the added rays
G=$W/gri/flame_ext
if { [ "$LEG" = gri ] || [ "$LEG" = all ]; } && [ ! -d "$G" ]; then
    S=$W/gri/flame; T0=$(latest "$S")
    mkdir -p "$G"; cp -r "$S/constant" "$S/system" "$S/chemkin" "$G/"
    for p in "$S"/processor*; do q=$G/$(basename "$p"); mkdir -p "$q"; cp -r "$p/constant" "$p/$T0" "$q/"; done
    cp "$W/flame_ext/constant/radiationProperties" "$G/constant/"
    for p in "$G"/processor*; do cp "$W/IDefault.processor" "$p/$T0/IDefault"; done   # uniform 300 K start for the added rays
    say "GRI case from $S at $T0 s"
fi
if [ "$LEG" = gri ] || [ "$LEG" = all ]; then
    run_leg "$G" gri53_ext; touch "$W/.axis_done_gri"
fi
[ "$LEG" = arc ] || [ "$LEG" = gri ] && { say "leg done"; exit 0; }
until [ -f "$W/.axis_done_arc" ] && [ -f "$W/.axis_done_gri" ]; do sleep 300; done

# field files for the common window and the end state
for L in arc22_ext gri53_ext; do
    C=$W/flame_ext; [ "$L" = gri53_ext ] && C=$G
    $PY "$REPO/server/sim1/arc_fields.py" "$C/snap" "$L" "$T_AVG" "$T_END" "$OUT/${L}_mean_${T_AVG}-${T_END}.npz" >> "$LOG" 2>&1
    $PY "$REPO/server/sim1/arc_fields.py" "$C/snap" "$L" "$T_END" "$T_END" "$OUT/${L}_t${T_END}.npz" >> "$LOG" 2>&1
done
$PY "$REPO/server/sim1/compare_of_fields.py" "$OUT/arc22_ext_mean_${T_AVG}-${T_END}.npz" ARC22 \
    "$OUT/gri53_ext_mean_${T_AVG}-${T_END}.npz" GRI53 > "$REPO/results/sim1/ARC22/compare_of_gri_ext.md" 2>&1
say "done"

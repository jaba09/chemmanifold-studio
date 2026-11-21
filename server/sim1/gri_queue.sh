#!/bin/bash
# Queue on the 8-rank budget: ARC flame leg (sim1-arc, running) -> GRI-Mech 3.0 flame leg -> ARC ignition leg.
# Run as a systemd user unit (survives without tmux):
#   systemd-run --user --unit=sim1-gri -p WorkingDirectory=/opt/ofb/arc22-src env NP=8 GRI_END=0.15 bash server/sim1/gri_queue.sh
# 1. waits until arc_run.sh has finished the ARC flame leg (its snapshots are exported before "ignition leg" is
#    logged), then stops sim1-arc (the ignition leg it has just begun) and clears the partial ignition dir
# 2. GRI flame leg: standard OpenFOAM DI (seulex 1e-10/1e-5) from the A1r state at 0.1 s to GRI_END (0.15 or 0.2 s),
#    writes every 2.5 ms, through run_protocol_v2.sh (snapshots include the NOx species); early field file at 0.125 s
# 3. field files (results/sim1/ARC22/fields/gri53_*.npz, Fluent cell order)
# 4. restarts arc_run.sh as sim1-arc: its flame leg is complete (skipped), so it runs the ignition leg and the report
set -e
REPO=$(realpath "$(dirname "$(realpath "$0")")/../.."); NP=${NP:-8}; GRI_END=${GRI_END:-0.15}
W=${W:-/opt/ofb/runs/arc22}; G=$W/gri; PY=${PY:-/opt/ofb/ml/bin/python}; OUT=$REPO/results/sim1/ARC22/fields
. /opt/ofb/ofenv.sh
LOG=$W/gri_queue.log; say() { echo "$(date '+%F %T %Z') $*" | tee -a "$LOG"; }
say "queued (NP $NP, GRI to $GRI_END s)"
until grep -q "ignition leg" "$W/arc_run.log" 2>/dev/null; do
    systemctl --user is-active -q sim1-arc || { grep -q "ignition leg" "$W/arc_run.log" || { say "sim1-arc ended before its flame leg finished; not starting"; exit 1; }; }
    sleep 120
done
say "ARC flame leg done ($(cat $W/flame/protocol_status)); stopping sim1-arc before its ignition leg"
systemctl --user stop sim1-arc || true
sleep 5; rm -rf "$W/ign"
mkdir -p "$G/v2" "$OUT"
[ -d "$G/v2/base_flame" ] || bash "$REPO/server/sim1/gri_case.sh" /opt/ofb/protocol_v2/base_flame 0.1 "$G/v2/base_flame" >> "$LOG" 2>&1
# early field file: as soon as 0.125 s (25 ms of the leg) is written, from a scratch copy (niced, 1 core)
( until [ -f "$G/flame/processor0/0.125/T" ] && [ -n "$(ls $G/flame/processor0 2>/dev/null | awk '$1+0 > 0.12501')" ]; do
      [ -f "$G/flame/protocol_status" ] && grep -q "completed\|failed" "$G/flame/protocol_status" && exit 0; sleep 300; done
  nice -n 19 bash "$REPO/server/sim1/arc_early.sh" "$G/flame" gri53_flame "$G/snap_early" 0.1 0.125 >> "$LOG" 2>&1
  nice -n 19 $PY "$REPO/server/sim1/arc_fields.py" "$G/snap_early" gri53_flame 0.1 0.125 "$OUT/gri53_mean_0.1-0.125.npz" >> "$LOG" 2>&1
  nice -n 19 $PY "$REPO/server/sim1/arc_fields.py" "$G/snap_early" gri53_flame 0.125 0.125 "$OUT/gri53_t0.125.npz" >> "$LOG" 2>&1
  echo "$(date '+%F %T %Z') early GRI field files written" >> "$LOG" ) &
say "GRI flame leg"
LEGS="0.15:0.0025"; [ "$GRI_END" = 0.2 ] && LEGS="0.15:0.0025 0.2:0.0025"
V2=$G/v2 LABEL=gri53_flame LEGS_OVERRIDE="$LEGS" bash "$REPO/openfoam/protocol/run_protocol_v2.sh" flame "$G/flame" di "" "$NP" \
    >> "$LOG" 2>&1 || say "GRI flame leg returned $?"
say "GRI flame: $(cat $G/flame/protocol_status)"
T0F=0.1; [ "$GRI_END" = 0.2 ] && T0F=0.15
$PY "$REPO/server/sim1/arc_fields.py" "$G/flame/snap" gri53_flame $T0F "$GRI_END" "$OUT/gri53_mean_${T0F}-${GRI_END}.npz" >> "$LOG" 2>&1
$PY "$REPO/server/sim1/arc_fields.py" "$G/flame/snap" gri53_flame "$GRI_END" "$GRI_END" "$OUT/gri53_t${GRI_END}.npz" >> "$LOG" 2>&1
say "GRI field files written; restarting arc_run.sh (ARC ignition leg + report) as sim1-arc"
systemctl --user reset-failed sim1-arc 2>/dev/null || true
systemd-run --user --unit=sim1-arc -p WorkingDirectory="$REPO" env NP="$NP" bash server/sim1/arc_run.sh >> "$LOG" 2>&1
wait
say "queue done"

#!/bin/bash
# GRI-Mech 3.0 OpenFOAM ignition leg 0-5 ms (protocol v2 lean start, standard DI seulex 1e-10/1e-5), to compare the
# ARC22 ignition leg with GRI in the same code (A2r is GA18). Run as a systemd user unit:
#   systemd-run --user --unit=sim1-gri-ign -p WorkingDirectory=/opt/ofb/arc22-src env NP=8 bash server/sim1/gri_ign.sh
# Outputs: /opt/ofb/runs/arc22/gri/ign (snapshots every 0.5 ms), results/sim1/ARC22/ign_gri/: protocol v2 reports
# (GRI vs A2r, ARC vs GRI), ignition times, cell-by-cell ARC vs GRI at 1-5 ms (compare_of_fields.py).
set -e
REPO=$(realpath "$(dirname "$(realpath "$0")")/../.."); NP=${NP:-8}; END=${END:-0.005}
W=${W:-/opt/ofb/runs/arc22}; G=$W/gri; PY=${PY:-/opt/ofb/ml/bin/python}; P=$REPO/openfoam/protocol
OUT=$REPO/results/sim1/ARC22/ign_gri; mkdir -p "$OUT" "$G/v2"
. /opt/ofb/ofenv.sh
LOG=$W/gri_ign.log; say() { echo "$(date '+%F %T %Z') $*" | tee -a "$LOG"; }
say "start (NP $NP, to $END s)"
[ -d "$G/v2/base_ign" ] || bash "$REPO/server/sim1/gri_case.sh" /opt/ofb/protocol_v2/base_ign 0 "$G/v2/base_ign" >> "$LOG" 2>&1
V2=$G/v2 LABEL=gri53_ign LEGS_OVERRIDE="$END:0.0005" bash "$P/run_protocol_v2.sh" ign "$G/ign" di "" "$NP" >> "$LOG" 2>&1 \
    || say "GRI ignition leg returned $?"
say "GRI ignition: $(cat $G/ign/protocol_status)"
# ignition times (first domain Tmax > 1600 K in the minMaxT monitors, every 10 steps = 0.2 ms)
for c in "GRI53 $G/ign" "ARC22 $W/ign" "A2r_GA18 /opt/ofb/runs/A2r_ign"; do
    set -- $c
    t=$(cat "$2"/postProcessing/minMaxT/*/fieldMinMax.dat 2>/dev/null | awk -F'\t' '$2 ~ /^T/ && $6 > 1600 {print $1+0}' | sort -g | head -1)
    echo "$1 ignition (domain Tmax > 1600 K): ${t:-none} s"
done > "$OUT/ignition_times.txt"
cat "$OUT/ignition_times.txt" | tee -a "$LOG"
$PY $P/score_protocol.py --protocol $P/protocol_v2_ign.yaml --di /opt/ofb/runs/A2r_ign/snap --di-label A2r_ign \
    --run "$G/ign/snap" --label gri53_ign --run-dir "$G/ign" --di-dir /opt/ofb/runs/A2r_ign --out "$OUT/vsA2r" \
    > "$OUT/score_gri_vs_A2r.log" 2>&1 || say "score GRI vs A2r returned $?"
$PY $P/score_protocol.py --protocol $P/protocol_v2_ign.yaml --di "$G/ign/snap" --di-label gri53_ign \
    --run "$W/ign/snap" --label arc22_ign --run-dir "$W/ign" --di-dir "$G/ign" --out "$OUT/arc_vs_gri" \
    > "$OUT/score_arc_vs_gri.log" 2>&1 || say "score ARC vs GRI returned $?"
# cell by cell at 1-5 ms
S=$W/.ignfields; mkdir -p "$S"
{ for t in 0.001 0.002 0.003 0.004 0.005; do
    ms=$(awk -v t=$t 'BEGIN{printf "%g", t*1e3}')
    $PY "$REPO/server/sim1/arc_fields.py" "$W/ign/snap" arc22_ign $t $t "$S/arc_$ms.npz" > /dev/null &&
    $PY "$REPO/server/sim1/arc_fields.py" "$G/ign/snap" gri53_ign $t $t "$S/gri_$ms.npz" > /dev/null &&
    { echo "## t = $ms ms"; echo; $PY "$REPO/server/sim1/compare_of_fields.py" "$S/arc_$ms.npz" ARC22 "$S/gri_$ms.npz" GRI53; echo; }
  done; } > "$OUT/compare_arc_gri_ign.md" 2>&1
rm -rf "$S"
say "done"

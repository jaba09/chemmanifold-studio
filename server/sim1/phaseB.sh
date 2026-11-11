#!/bin/bash
# Phase B on sim1: protocol v2 (pure mode) for every candidate, 4 ranks each, 4 candidates at a time.
# Per candidate: ignition run (vs A2r) then flame run (vs A1r), both phase reports, score S (score_v2.py).
# Resumable: finished runs are skipped by run_protocol_v2.sh; scored candidates are skipped here.
#   phaseB.sh [candidates file]   (lines: label model_dir)
REPO=$(cd "$(dirname "$0")/../.." && pwd); P=$REPO/openfoam/protocol; PY=/opt/ofb/ml/bin/python
B=/opt/ofb/runs/B; OUT=$REPO/results/sim1/B; mkdir -p $B $OUT
LIST=${1:-$B/candidates.txt}
one() {
    lab=$1; m=$2; . /opt/ofb/ofenv.sh
    [ -f "$OUT/$lab/score_v2.json" ] && return 0
    echo "$(date '+%F %T %Z') $lab start" >> $B/phaseB.log
    for ph in ign flame; do
        LABEL=$lab $P/run_protocol_v2.sh $ph $B/$lab/$ph pure "$m" 4 > $B/$lab.$ph.out 2>&1
        grep -q completed $B/$lab/$ph/protocol_status || echo "$(date '+%F %T %Z') $lab $ph NOT completed: $(cat $B/$lab/$ph/protocol_status)" >> $B/phaseB.log
    done
    $PY $P/score_protocol.py --protocol $P/protocol_v2_ign.yaml --di /opt/ofb/runs/A2r_ign/snap --di-label A2r_ign \
        --run $B/$lab/ign/snap --label $lab --run-dir $B/$lab/ign --di-dir /opt/ofb/runs/A2r_ign --out $OUT/ign > $B/$lab.score_ign.log 2>&1
    $PY $P/score_protocol.py --protocol $P/protocol_v2_flame.yaml --di /opt/ofb/runs/A1r_R2rad/snap --di-label A1r \
        --run $B/$lab/flame/snap --label $lab --run-dir $B/$lab/flame --out $OUT/flame > $B/$lab.score_flame.log 2>&1
    $PY $P/score_v2.py --label $lab --ign $OUT/ign/$lab/protocol_report.json --flame $OUT/flame/$lab/protocol_report.json \
        --out $OUT/$lab > $B/$lab.score_v2.log 2>&1
    echo "$(date '+%F %T %Z') $lab done: $(tail -c 200 $B/$lab.score_v2.log | tr '\n' ' ')" >> $B/phaseB.log
}
export -f one; export REPO P PY B OUT
echo "$(date '+%F %T %Z') phase B start ($(wc -l < $LIST) candidates)" >> $B/phaseB.log
grep -v '^#' $LIST | xargs -P 4 -L 1 bash -c 'one "$0" "$1"'
$PY $P/score_v2.py --table $OUT/*/score_v2.json --out $OUT > /dev/null 2>&1
echo "$(date '+%F %T %Z') phase B finished" >> $B/phaseB.log; echo completed > $B/status

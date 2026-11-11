#!/bin/bash
# After A3r: A1r snapshot CSVs (DI reference of the flame phase), stage 19 of A1r at 0.1875 s (gate for A3r),
# then phase B lane b (3 candidates, 1 slot of 4 ranks).
REPO=$(cd "$(dirname "$0")/../.." && pwd); PY=/opt/ofb/ml/bin/python; R=/opt/ofb/runs
until grep -q "completed\|failed" $R/A3r_cheap/case/status 2>/dev/null; do sleep 60; done
. /opt/ofb/ofenv.sh
cd $R/A1r_R2rad && $PY $REPO/openfoam/tools/foam_snapshot.py . snap --label A1r --skip-existing > log.snapshots 2>&1
echo "$(date '+%F %T %Z') A1r snapshots: $(ls $R/A1r_R2rad/snap | wc -l)" >> $R/B/phaseB.log
cd $REPO && $PY scripts/19_flow_statistics.py case $R/A1r_R2rad --time 0.1875 --label R2rad_DI_0.1875 --out data/timescale \
    > $R/A1r_R2rad/log.stage19 2>&1
SLOTS=1 $REPO/server/sim1/phaseB.sh $R/B/lane_b.txt
# retries: candidates whose ignition or flame run failed (e.g. an FPE in the shadow DI check before the FPE retry
# existed): resume the failed run with the current runner and rescore
for lab in $(grep -o '^[^ ]*' $R/B/retry.txt 2>/dev/null); do
    rm -f $REPO/results/sim1/B/$lab/score_v2.json
    grep "^$lab " $R/B/all.txt > $R/B/retry_$lab.txt
    SLOTS=1 $REPO/server/sim1/phaseB.sh $R/B/retry_$lab.txt
done

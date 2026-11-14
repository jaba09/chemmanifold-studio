#!/bin/bash
# Resume one C1 lane: extra training seeds of one config, one after another (4 threads each).
#   c1_lane.sh <tix2|tix2h> <seed> [<seed> ...]
REPO=$(cd "$(dirname "$0")/../.." && pwd); PY=/opt/ofb/ml/bin/python; LOG=/opt/ofb/runs/C1
cd "$REPO"; n=$1; shift
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
for s in "$@"; do
    echo "$(date '+%F %T %Z') $n seed $s training start" >> $LOG/c1.log
    $PY -u scripts/train_seeds.py --config configs/burner_openfoam_$n.yaml --seeds $s --parallel 1 --threads 4 \
        >> $LOG/$n.s$s.log 2>&1 && echo "$(date '+%F %T %Z') $n seed $s done" >> $LOG/c1.log \
        || { echo "$(date '+%F %T %Z') $n seed $s FAILED" >> $LOG/c1.log; exit 1; }
done

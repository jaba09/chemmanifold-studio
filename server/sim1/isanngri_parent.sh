#!/bin/bash
# Physics-only ISANN parent for ARC_GRI30_NOx22 (configs/ch4_arc22.yaml = the ood7 parent's exploration on
# the 43-species skeletal GRI, network state = the ARC's 22 transported species + T). At most 8 cores.
# Resumable: each stage leaves a marker in the data dir and is skipped once done; training uses
# 07_train --resume (full state every epoch). Meant to run as the systemd user unit sim1-isanngri-parent
# (server/sim1/sim1-isanngri-parent.service: Nice 19, CPUSchedulingPolicy idle), so it only takes the
# cores the other runs leave free.
#   1. stages 0-4 (exploration, Cantera on gri30_skel43)
#   2. stages 5-6 (projection onto the 22 state species, scalers, manifold)
#   3. stage 7 resnet_film (8 threads), 8-12 (validation vs projected Cantera, OOD tables, export)
#   4. parent dir for ISANN: chemmanifold_model.txt + tests at the root of the data dir (isann_arc22.yaml)
REPO=$(cd "$(dirname "$0")/../.." && pwd); PY=${PY:-/opt/ofb/ml/bin/python}; LOG=${LOG:-/opt/ofb/runs/isanngri}
CFG=configs/ch4_arc22.yaml; D=/opt/ofb/isann/parent_arc22
mkdir -p "$LOG" "$D"; cd "$REPO"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
log() { echo "$(date '+%F %T %Z') $*" >> "$LOG/parent.log"; }
step() { [ -f "$D/.done_$1" ] && return 0; log "$1 start"; bash -c "$2" >> "$LOG/$1.log" 2>&1 \
    && { touch "$D/.done_$1"; log "$1 done"; } || { log "$1 FAILED (see $LOG/$1.log)"; echo failed > "$LOG/status"; exit 1; }; }
echo running > "$LOG/status"
log "start (repo $(git rev-parse --short HEAD))"
for s in 0 1 2 3 4 5 6; do step stage$s "$PY -u run_pipeline.py --config $CFG --from $s --to $s --arch resnet_film"; done
step train "OMP_NUM_THREADS=8 $PY -u scripts/07_train.py --config $CFG --arch resnet_film --resume"
step certify "OMP_NUM_THREADS=4 $PY -u run_pipeline.py --config $CFG --from 8 --to 12 --arch resnet_film"
M=$D/08_fluent/resnet_film
[ -f "$M/chemmanifold_model.txt" ] || { log "missing export $M"; echo failed > "$LOG/status"; exit 1; }
cp "$M/chemmanifold_model.txt" "$M/chemmanifold_tests.txt" "$D/"
echo "ARC_GRI30_NOx22 physics-only parent (configs/ch4_arc22.yaml, $(git rev-parse --short HEAD), $(date -I))" > "$D/README.txt"
log "done: ISANN parent in $D"; echo done > "$LOG/status"

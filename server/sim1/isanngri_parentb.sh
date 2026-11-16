#!/bin/bash
# ISANN parent for ARC_GRI30_NOx22 with ARC labels (configs/ch4_arc22b.yaml): the exploration of stages 0-4 of
# /opt/ofb/isann/parent_arc22 relabelled by the ARC kernel (scripts/25_arc_relabel.py, rollout segments of 24
# steps), then stages 5-12 (ARC as the reference of the tests). 8 cores, normal priority. Run as the systemd
# user unit sim1-isanngri-parentb, which waits until sim1-gri is inactive. Resumable: one marker per step,
# the relabel per file, training per epoch (07_train --resume).
REPO=$(cd "$(dirname "$0")/../.." && pwd); PY=${PY:-/opt/ofb/ml/bin/python}; LOG=${LOG:-/opt/ofb/runs/isanngri/parentb}
CFG=configs/ch4_arc22b.yaml; SRC=/opt/ofb/isann/parent_arc22; D=/opt/ofb/isann/parent_arc22b
mkdir -p "$LOG" "$D"; cd "$REPO"
# the ml env has chemmanifold installed from ~/chemmanifold-studio (editable): load this worktree's package first
export PYTHONPATH=$REPO${PYTHONPATH:+:$PYTHONPATH}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
log() { echo "$(date '+%F %T %Z') $*" >> "$LOG/parent.log"; }
step() { [ -f "$D/.done_$1" ] && return 0; log "$1 start"; bash -c "$2" >> "$LOG/$1.log" 2>&1 \
    && { touch "$D/.done_$1"; log "$1 done"; } || { log "$1 FAILED (see $LOG/$1.log)"; echo failed > "$LOG/status"; exit 1; }; }
echo running > "$LOG/status"
log "start (repo $(git rev-parse --short HEAD))"
[ -f "$SRC/.done_stage4" ] || { log "source exploration $SRC incomplete"; echo failed > "$LOG/status"; exit 1; }
step relabel "$PY -u scripts/25_arc_relabel.py --config $CFG --source $SRC --workers 8 --seg-steps 24"
for s in 5 6; do step stage$s "$PY -u run_pipeline.py --config $CFG --from $s --to $s --arch resnet_film"; done
step train "OMP_NUM_THREADS=8 $PY -u scripts/07_train.py --config $CFG --arch resnet_film --resume"
step certify "OMP_NUM_THREADS=8 $PY -u run_pipeline.py --config $CFG --from 8 --to 12 --arch resnet_film"
M=$D/08_fluent/resnet_film
[ -f "$M/chemmanifold_model.txt" ] || { log "missing export $M"; echo failed > "$LOG/status"; exit 1; }
cp "$M/chemmanifold_model.txt" "$M/chemmanifold_tests.txt" "$D/"
echo "ARC_GRI30_NOx22 physics-only parent, ARC labels (configs/ch4_arc22b.yaml, $(git rev-parse --short HEAD), $(date -I))" > "$D/README.txt"
log "done: ISANN parent in $D"; echo done > "$LOG/status"

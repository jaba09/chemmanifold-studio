#!/bin/bash
# C1 on sim1 (8 cores): tix2 and tix2h exploration (stages 0-6, side by side, single-threaded BLAS),
# then 3 training repeats of each (seeds 0-2, resnet_film, 2 trainings at a time x 4 torch threads),
# certification, export and registry (stages 7-10, 12, 15). Physics-only data; no CFD/DI state is used.
# Resumable: finished stages leave markers in <data_dir>/.c1_done_<stage>; exported seeds are skipped.
#   c1_run.sh            (log: /opt/ofb/runs/C1/c1.log)
REPO=$(cd "$(dirname "$0")/../.." && pwd); PY=/opt/ofb/ml/bin/python; LOG=/opt/ofb/runs/C1
mkdir -p $LOG; cd "$REPO"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
log() { echo "$(date '+%F %T %Z') $*" >> $LOG/c1.log; }
ddir() { echo "$REPO/configs/$($PY -c "import yaml,sys;print(yaml.safe_load(open(sys.argv[1]))['data_dir'])" "configs/burner_openfoam_$1.yaml")"; }
data() {  # data <name>: stages 0-6 with markers
    local n=$1 d; d=$(realpath -m "$(ddir $n)"); mkdir -p "$d"
    for s in 0 1 2 3 4 5 6; do
        [ -f "$d/.c1_done_$s" ] && continue
        log "$n stage $s start"
        $PY run_pipeline.py --config configs/burner_openfoam_$n.yaml --from $s --to $s --arch resnet_film \
            >> $LOG/$n.data.log 2>&1 || { log "$n stage $s FAILED"; return 1; }
        touch "$d/.c1_done_$s"; log "$n stage $s done"
    done
}
train0() {  # train0 <name>: seed 0 = the base run
    local n=$1 d; d=$(realpath -m "$(ddir $n)")
    [ -f "$d/08_fluent/resnet_film/chemmanifold_model.txt" ] && [ -f "$d/.c1_done_15" ] && return 0
    log "$n seed 0 training start"
    OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
    $PY run_pipeline.py --config configs/burner_openfoam_$n.yaml --from 7 --to 15 --arch resnet_film \
        >> $LOG/$n.s0.log 2>&1 || { log "$n seed 0 FAILED"; return 1; }
    touch "$d/.c1_done_15"; log "$n seed 0 done"
}
seeds() {  # seeds <name> <seed>: one extra repeat
    log "$1 seed $2 training start"
    OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
    $PY scripts/train_seeds.py --config configs/burner_openfoam_$1.yaml --seeds $2 --parallel 1 --threads 4 \
        >> $LOG/$1.s$2.log 2>&1 && log "$1 seed $2 done" || { log "$1 seed $2 FAILED"; return 1; }
}
log "C1 start"
data tix2 & P1=$!; data tix2h & P2=$!; wait $P1; r1=$?; wait $P2; r2=$?
[ $r1 = 0 ] && [ $r2 = 0 ] || { log "data failed ($r1 $r2)"; echo failed > $LOG/status; exit 1; }
# 6 trainings, 2 at a time (4 threads each)
( train0 tix2 && seeds tix2 1 && seeds tix2 2 ) & P1=$!
( train0 tix2h && seeds tix2h 1 && seeds tix2h 2 ) & P2=$!
wait $P1; r1=$?; wait $P2; r2=$?
[ $r1 = 0 ] && [ $r2 = 0 ] && { log "C1 completed"; echo completed > $LOG/status; } || { log "C1 training failed ($r1 $r2)"; echo failed > $LOG/status; exit 1; }

#!/bin/bash
# C2 on sim1 (G2: tix2h parent family, ignition first). At most 8 cores. Resumable (markers in the data dir).
#  1. tix2c exploration, stages 0-4 (configs/burner_openfoam_tix2c.yaml: tix2h + ignition-focused regime 17 and
#     vitiated ignition)
#  2. stage 23 committee round 1 from the tix2h s0-s2 members (regime 21, T > 800 K, 3 ms rollouts), physics only
#  3. stages 5-6; 3 training repeats in parallel (s0 3 threads + s1, s2 2 threads each), stages 8-10, 12, 15
#  4. P_tix2c = mean ensemble of the 3 repeats (make_ensemble.py selftest), protocol v2 pure on A1r/A2r (4 ranks)
REPO=$(cd "$(dirname "$0")/../.." && pwd); PY=/opt/ofb/ml/bin/python; LOG=/opt/ofb/runs/C2; mkdir -p $LOG; cd "$REPO"
CFG=configs/burner_openfoam_tix2c.yaml; D=$REPO/data/openfoam_tix2c; DH=$REPO/data/openfoam_tix2h; mkdir -p $D
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
log() { echo "$(date '+%F %T %Z') $*" >> $LOG/c2.log; }
step() { [ -f "$D/.c2_$1" ] && return 0; log "$1 start"; shift_cmd="$2"; bash -c "$shift_cmd" >> $LOG/$1.log 2>&1 \
    && { touch "$D/.c2_$1"; log "$1 done"; } || { log "$1 FAILED"; echo failed > $LOG/status; exit 1; }; }
echo running > $LOG/status
for s in 0 1 2 3 4; do step stage$s "$PY run_pipeline.py --config $CFG --from $s --to $s --arch resnet_film"; done
step committee "$PY scripts/23_committee_sampling.py --config $CFG --round 1 --T-min 800 --steps 150 --n-candidates 3000 --workers 8 \
    --models $DH/08_fluent/resnet_film/chemmanifold_model.txt ${DH}_seeds/s1/08_fluent/resnet_film/chemmanifold_model.txt \
             ${DH}_seeds/s2/08_fluent/resnet_film/chemmanifold_model.txt"
for s in 5 6; do step stage$s "$PY run_pipeline.py --config $CFG --from $s --to $s --arch resnet_film"; done
if [ ! -f "$D/.c2_train" ]; then
    # 07_train --resume saves the full training state every epoch (the tmux server crashed at 13:37 on 15 Nov and
    # took 5 h of training without it); stages 8-15 after. Seed configs written by scripts/train_seeds.py.
    log "training 3 repeats start (resumable)"
    CS1=${D}_seeds/burner_openfoam_tix2c_s1.yaml; CS2=${D}_seeds/burner_openfoam_tix2c_s2.yaml
    ( OMP_NUM_THREADS=3 $PY -u scripts/07_train.py --config $CFG --arch resnet_film --resume > $LOG/train_s0.log 2>&1; echo $? > $LOG/train_s0.rc ) &
    ( OMP_NUM_THREADS=2 $PY -u scripts/07_train.py --config $CS1 --arch resnet_film --resume > $LOG/train_s1.log 2>&1; echo $? > $LOG/train_s1.rc ) &
    ( OMP_NUM_THREADS=2 $PY -u scripts/07_train.py --config $CS2 --arch resnet_film --resume > $LOG/train_s2.log 2>&1; echo $? > $LOG/train_s2.rc ) &
    wait
    log "training rc s0=$(cat $LOG/train_s0.rc) s1=$(cat $LOG/train_s1.rc) s2=$(cat $LOG/train_s2.rc)"
    for c in $CFG $CS1 $CS2; do
        OMP_NUM_THREADS=4 $PY run_pipeline.py --config $c --from 8 --to 15 --arch resnet_film >> $LOG/certify.log 2>&1 || log "stages 8-15 FAILED for $c"
    done
    for m in $D/08_fluent/resnet_film ${D}_seeds/s1/08_fluent/resnet_film ${D}_seeds/s2/08_fluent/resnet_film; do
        [ -f $m/chemmanifold_model.txt ] || { log "missing export $m"; echo failed > $LOG/status; exit 1; }; done
    touch "$D/.c2_train"; log "training done"
fi
E=/opt/ofb/models/P_tix2c
if [ ! -f $E/chemmanifold_ensemble.txt ]; then
    mkdir -p $E
    { echo "blend: mean"; echo 'note: "P_tix2c = mean of tix2c s0-s2 (sim1 C2)"'; echo "members:"
      for m in $D/08_fluent/resnet_film ${D}_seeds/s1/08_fluent/resnet_film ${D}_seeds/s2/08_fluent/resnet_film; do
          echo "  - path: $m/chemmanifold_model.txt"; done; } > $E/spec.yaml
    $PY scripts/make_ensemble.py --config $CFG --spec $E/spec.yaml --out $E >> $LOG/ensemble.log 2>&1 || { log "ensemble FAILED"; exit 1; }
    sed -i "s|^member \.\./\.\./\.\./\.\./home/ubuntu/|member /home/ubuntu/|" $E/chemmanifold_ensemble.txt
    log "ensemble built: $(grep -o 'selftest [A-Z]*' $LOG/ensemble.log | tail -1)"
fi
echo "P_tix2c $E" > /opt/ofb/runs/B/c2.txt
SLOTS=1 server/sim1/phaseB.sh /opt/ofb/runs/B/c2.txt
log "C2 scored: $(cat $REPO/results/sim1/B/P_tix2c/score_v2.json 2>/dev/null | tr -d '\n ' | cut -c1-160)"
echo completed > $LOG/status

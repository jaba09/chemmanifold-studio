#!/bin/bash
# Phase D on sim1: ISANN on the radiation reference (docs/SIM1-ROADMAP.md section 7), 4 CFD ranks + 4 training threads.
# ISANN is the one method allowed to train on the run's own DI (GA18) pairs; everything here is labelled isann.
#   leg 1 (ign):   protocol v2 ignition base (lean start, LeFoam + constantLewis + fvDOM radiation), 0-25 ms, ISANN from
#                  the physics-only parent tix2c_s0 (member 0 of P_tix2c, the ITERML parent): DI phase first, then the
#                  daemon's networks (openfoam/isann/isann_D_tix2c.yaml).
#   leg 2 (flame): protocol v2 flame base (A1r state at 0.1 s), to 0.15 s, continuing leg 1's ISANN state (archive,
#                  rounds, last accepted network, named in the control file so every rank loads it at the first step).
#   then:          the final accepted network scored with protocol v2 pure (phaseB.sh, label isann_D), and both online
#                  legs scored against A2r / A1r (the ISANN runs themselves), ISANN reports, results/sim1/D, push.
# Resumable (systemd user unit sim1-d-isann): finished legs leave t_end, scoring steps leave markers.
set -u
REPO=$(cd "$(dirname "$0")/../.." && pwd); PY=/opt/ofb/ml/bin/python; P=$REPO/openfoam/protocol
CONF=$REPO/openfoam/isann/isann_D_tix2c.yaml; PARENT=$REPO/data/openfoam_tix2c/08_fluent/resnet_film
V2=/opt/ofb/protocol_v2; NP=4; L=/opt/ofb/runs/D; OUT=$REPO/results/sim1/D
R1=/opt/ofb/run/isann_D_ign; R2=/opt/ofb/run/isann_D_flame
mkdir -p $L $OUT; export PYTHONPATH=$REPO OMP_NUM_THREADS=1
say() { echo "$(TZ=Europe/Madrid date '+%F %T %Z') $*" | tee -a $L/d.log; }
set +u; . /opt/ofb/ofenv.sh > /dev/null 2>&1; set -u
cd "$REPO"

# an FPE (seen in phase B in the shadow DI check: GA18 on a network-advanced state) stops a leg: resume it once
# from the last write with FPE trapping off, and record it
fpe_retry() {   # <run dir> <run_isann args...>
    local R=$1; shift
    [ -f $R/t_end ] && return 0
    grep -aq "sigFpe" $R/log.run.* 2>/dev/null || return 1
    say "$(basename $R): FPE, resuming with FOAM_SIGFPE=false"; echo "$(date '+%F %T %Z') FPE retry" >> $R/protocol_notes
    rm -f $R/isann/STOP
    FOAM_SIGFPE=false "$@" >> $L/fpe_retry.out 2>&1
}

# --- leg 1: ignition, 0-25 ms, writes every 0.5 ms (A2r has 0.5 ms snapshots to 5 ms, then 2.5 ms) ----------------
if [ ! -f $R1/t_end ]; then
    say "leg 1 (ign) start"
    BASE=$V2/base_ign SOLVER=rhoReactingBuoyantLeFoam ENDTIME=0.025 WRITEINTERVAL=0.0005 \
        bash server/run_isann.sh isann_D_ign "$PARENT" $NP "$CONF" >> $L/leg1.out 2>&1
    SOLVER=rhoReactingBuoyantLeFoam fpe_retry $R1 bash server/run_isann.sh isann_D_ign "$PARENT" $NP "$CONF"
    [ -f $R1/t_end ] || { say "leg 1 did not finish (see $R1/log.run.*)"; exit 1; }
fi
# wait for the daemon (a round may still be training when the CFD ends; it publishes, then sees STOP)
while pgrep -f "[i]sann_daemon.py --run $R1 " > /dev/null; do sleep 30; done
say "leg 1 done: $($PY -c "import json;s=json.load(open('$R1/isann/state.json'));print('version',s['version'],'rounds',len(s['rounds']))")"

# --- leg 2: flame, 0.1-0.15 s, continuing leg 1's ISANN state ---------------------------------------------------
if [ ! -d $R2 ]; then
    say "leg 2 (flame) setup from leg 1's ISANN state"
    BASE=$V2/base_flame
    "$REPO/openfoam/isann/setup_isann.sh" $BASE $R2 "$PARENT" $NP > $L/leg2_setup.out 2>&1 || { say "leg 2 setup failed"; exit 1; }
    cp "$CONF" $R2/isann/isann.yaml
    foamDictionary -entry endTime -set 0.15 $R2/system/controlDict > /dev/null
    foamDictionary -entry writeInterval -set 0.0025 $R2/system/controlDict > /dev/null
    cp $R1/isann/archive.npz $R1/isann/state.json $R2/isann/
    cp $R1/isann/model_v*.txt $R2/isann/ 2>/dev/null
    [ -f $R1/isann/control ] && cp $R1/isann/control $R2/isann/control
    for d in $R1/isann/round*; do [ -d "$d" ] && ln -s "$d" $R2/isann/; done
    # time index of the flame base (0.1 s / 2e-5 s): the next retraining needs min_gap steps from there
    $PY - <<EOF
import json
p = "$R2/isann/state.json"; s = json.load(open(p))
s["leg1"] = dict(version=s["version"], rounds=len(s["rounds"]), published_step=s["published_step"])
s["published_step"] = 5000; s["retry_after"] = 0
s.pop("first_step", None)   # with no network from leg 1 (version 0), leg 2 has its own DI phase on the parent
json.dump(s, open(p, "w"), indent=1)
EOF
    # control file: version k, fromStep (leg 1's step) < 5000, so every rank loads model_vk at its first step
    [ -f $R2/isann/control ] && sed -i 's/^fromStep .*/fromStep 0/' $R2/isann/control
    echo "[$(TZ=Europe/Madrid date '+%F %H:%M %Z')] created from $V2/base_flame, ISANN state of $R1" >> $R2/server.log
fi
if [ ! -f $R2/t_end ]; then
    say "leg 2 (flame) start"
    SOLVER=rhoReactingBuoyantLeFoam bash server/run_isann.sh isann_D_flame "$PARENT" $NP "$CONF" >> $L/leg2.out 2>&1
    SOLVER=rhoReactingBuoyantLeFoam fpe_retry $R2 bash server/run_isann.sh isann_D_flame "$PARENT" $NP "$CONF"
    [ -f $R2/t_end ] || { say "leg 2 did not finish (see $R2/log.run.*)"; exit 1; }
fi
while pgrep -f "[i]sann_daemon.py --run $R2 " > /dev/null; do sleep 30; done
V=$($PY -c "import json;print(json.load(open('$R2/isann/state.json'))['version'])")
say "leg 2 done: final network version $V"
[ "$V" -gt 0 ] || { say "no accepted ISANN network: nothing to score in pure mode"; exit 1; }

# --- final model: protocol v2 pure (label isann_D) ----------------------------------------------------------------
M=/opt/ofb/models/isann_D; mkdir -p $M
[ -f $M/chemmanifold_model.txt ] || { cp $R2/isann/model_v$V.txt $M/chemmanifold_model.txt
    echo "isann_D: ISANN network v$V (CFD-adapted, label isann) of $R2, parent tix2c_s0; $(date -I)" > $M/README.txt; }
echo "isann_D $M" > $L/candidates.txt
if [ ! -f $OUT/isann_D/score_v2.json ]; then
    say "protocol v2 pure of isann_D (v$V)"
    PB_RUNS=$L/protocol PB_OUT=$OUT SLOTS=1 bash server/sim1/phaseB.sh $L/candidates.txt >> $L/protocol.out 2>&1
fi

# --- the online runs themselves, against the DI references -------------------------------------------------------
for leg in ign flame; do
    R=/opt/ofb/run/isann_D_$leg
    [ -f $L/.scored_$leg ] && continue
    cd $R; ls log.run.* > /dev/null 2>&1 && cat $(ls log.run.* | sort -t. -k3 -n) > log.run
    $PY $P/../tools/foam_snapshot.py . snap --label isann_D_online --skip-existing > log.snapshots 2>&1
    [ "$(ls snap 2>/dev/null | wc -l)" -gt 0 ] && find . -maxdepth 1 -type d -regex '\./[0-9.e+-]+' ! -name 0 ! -name 0.1 -exec rm -rf {} +
    cd "$REPO"
    if [ $leg = ign ]; then
        $PY $P/score_protocol.py --protocol $P/protocol_v2_ign.yaml --di /opt/ofb/runs/A2r_ign/snap --di-label A2r_ign \
            --run $R/snap --label isann_D_online --run-dir $R --di-dir /opt/ofb/runs/A2r_ign --out $OUT/online_ign >> $L/score_online.log 2>&1
    else
        $PY $P/score_protocol.py --protocol $P/protocol_v2_flame.yaml --di /opt/ofb/runs/A1r_R2rad/snap --di-label A1r \
            --run $R/snap --label isann_D_online --run-dir $R --out $OUT/online_flame >> $L/score_online.log 2>&1
    fi
    mkdir -p $OUT/isann_$leg
    $PY openfoam/isann/isann_report.py --run $R --label isann_D_$leg --out $OUT/isann_$leg >> $L/score_online.log 2>&1
    cp $R/isann/state.json $OUT/isann_$leg/state.json
    touch $L/.scored_$leg
done
$PY $P/score_v2.py --label isann_D_online --ign $OUT/online_ign/isann_D_online/protocol_report.json \
    --flame $OUT/online_flame/isann_D_online/protocol_report.json --out $OUT/isann_D_online >> $L/score_online.log 2>&1
say "scored: $(tail -c 300 $L/protocol.out | tr '\n' ' ')"
git add $OUT && git commit -q -m "sim1 phase D: ISANN (label isann) on the radiation reference, parent tix2c_s0: online legs and protocol v2 pure of the final network

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && say "committed $(git rev-parse --short HEAD)"
for i in 1 2 3 4; do git pull -q --rebase origin "$(git branch --show-current)" && git push -q origin "$(git branch --show-current)" && { say "pushed"; break; }; sleep $((2 ** i)); done
say "done"

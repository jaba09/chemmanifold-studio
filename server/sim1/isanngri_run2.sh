#!/bin/bash
# ISANN ARC22 run 2: the ARC-labelled parent /opt/ofb/isann/parent_arc22b (configs/ch4_arc22b.yaml) and NOx in the
# checks (openfoam/isann/isann_arc22b.yaml + shadow check on T, OH, NO, NO2, N2O, HCN), same protocol as run 1
# (flame base at 0.1 s, to 0.15 s, 8 ranks) into /opt/ofb/run/isann_arc22b; then scored against ARC22 DI with
# run 1 for comparison (results/sim1/ISANN_ARC22b, committed and pushed). Run as the user unit sim1-isanngri-run2,
# which waits for parent b. Resumable: the CFD and daemon resume (run_isann.sh); scoring runs once.
REPO=$(cd "$(dirname "$0")/../.." && pwd); PB=/opt/ofb/isann/parent_arc22b; R=/opt/ofb/run/isann_arc22b
[ "$(cat /opt/ofb/runs/isanngri/parentb/status 2>/dev/null)" = done ] && [ -f $PB/chemmanifold_model.txt ] \
    || { echo "parent b not done"; exit 1; }
export ISANN_ARC=1 BASE=/opt/ofb/runs/arc22/v2/base_flame SOLVER=rhoReactingBuoyantLeFoam ENDTIME=0.15 WRITEINTERVAL=0.0025 \
    DAEMON_NICE=5 TRUST_SPECIES="OH NO NO2 N2O HCN" TRUST_ABS="5e-5 3e-6 2e-7 5e-8 2e-6"
if [ ! -f $R/t_end ]; then
    bash "$REPO/server/run_isann.sh" isann_arc22b $PB 8 "$REPO/openfoam/isann/isann_arc22b.yaml" || exit 1
fi
[ -f $R/t_end ] || exit 1
if [ ! -f $R/.scored ]; then
    RUN=$R LABEL=isann_arc22b OUT="$REPO/results/sim1/ISANN_ARC22b" COMPARE="$REPO/results/sim1/ISANN_ARC22" \
        nice -n 10 bash "$REPO/server/sim1/isanngri_score.sh" && touch $R/.scored
fi

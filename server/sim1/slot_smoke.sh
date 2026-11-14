#!/bin/bash
# Phase-B de-risk: pure-mode surrogate (ood8_s0, userChemStep) on the radiation case from the A1r 0.1 s state,
# 500 steps on 4 ranks; starts when the last C1 training (tix2h seed 2) is done.
R=/opt/ofb/runs
until grep -q "tix2h seed 2 done\|tix2h seed 2 FAILED\|C1 completed\|C1 training failed" $R/C1/c1.log; do sleep 60; done
. /opt/ofb/ofenv.sh
cd $R/smoke_rad_ood8 && echo "$(date '+%F %T %Z') start" > status && \
mpirun -np 4 rhoReactingBuoyantLeFoam -parallel > log.run 2>&1; echo "$(date '+%F %T %Z') exit $?" >> status

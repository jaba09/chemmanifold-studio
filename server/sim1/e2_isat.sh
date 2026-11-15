#!/bin/bash
# Phase E2 (Javier, 15 Nov): longer ISAT vs network comparison. ISAT (TDAC, no reduction) through the full protocol v2
# (ignition 0-25 ms vs A2r, flame 50 ms from A1r 0.1 s vs A1r), same scoring as the surrogates (score_v2 S, flame
# abs dT, drift, s/step on 4 ranks). One tolerance after the other, 4 ranks.
#   e2_isat.sh [tol ...]     (default 1e-3 1e-4)
REPO=$(cd "$(dirname "$0")/../.." && pwd); P=$REPO/openfoam/protocol; PY=/opt/ofb/ml/bin/python
R=/opt/ofb/runs/E2; OUT=$REPO/results/sim1/E2; mkdir -p $R $OUT
. /opt/ofb/ofenv.sh
D() { foamDictionary -entry "$1" -set "$2" "$3" > /dev/null; }
for tol in ${@:-1e-3 1e-4}; do
    lab=isat$tol; V2=$R/bases_$lab
    [ -f $OUT/$lab/score_v2.json ] && continue
    if [ ! -d $V2 ]; then
        mkdir -p $V2; cp -r /opt/ofb/protocol_v2/base_ign /opt/ofb/protocol_v2/base_flame $V2/
        for b in $V2/base_ign $V2/base_flame; do
            CP=$b/constant/chemistryProperties
            D chemistryType/method TDAC $CP
            D reduction "{ active off; method none; }" $CP
            D tabulation "{ active on; log on; printProportion off; printNumRetrieve off; tolerance $tol; method ISAT; scaleFactor { otherSpecies 1; Temperature 1000; Pressure 1e15; deltaT 0.5; } maxNLeafs 5000; chPMaxLifeTime 100; maxGrowth 10; checkEntireTreeInterval 5; maxDepthFactor 2; minBalanceThreshold 30; MRURetrieve false; maxMRUSize 0; growPoints true; maxNumNewDim 10; variableTimeStep true; }" $CP
        done
    fi
    echo "$(date '+%F %T %Z') $lab start" >> $R/e2.log
    for ph in ign flame; do
        LABEL=$lab V2=$V2 $P/run_protocol_v2.sh $ph $R/$lab/$ph di "" 4 > $R/$lab.$ph.out 2>&1
    done
    $PY $P/score_protocol.py --protocol $P/protocol_v2_ign.yaml --di /opt/ofb/runs/A2r_ign/snap --di-label A2r_ign \
        --run $R/$lab/ign/snap --label $lab --run-dir $R/$lab/ign --di-dir /opt/ofb/runs/A2r_ign --out $OUT/ign > $R/$lab.si.log 2>&1
    $PY $P/score_protocol.py --protocol $P/protocol_v2_flame.yaml --di /opt/ofb/runs/A1r_R2rad/snap --di-label A1r \
        --run $R/$lab/flame/snap --label $lab --run-dir $R/$lab/flame --out $OUT/flame > $R/$lab.sf.log 2>&1
    $PY $P/score_v2.py --label $lab --ign $OUT/ign/$lab/protocol_report.json --flame $OUT/flame/$lab/protocol_report.json \
        --out $OUT/$lab > $R/$lab.sv.log 2>&1
    echo "$(date '+%F %T %Z') $lab done: $(tail -c 300 $R/$lab.sv.log | tr '\n' ' ')" >> $R/e2.log
done
echo completed > $R/status

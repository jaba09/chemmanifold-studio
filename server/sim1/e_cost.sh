#!/bin/bash
# Phase E (cost at matched accuracy) on sim1: 200 steps (2e-5 s) from the A1r (R2rad) state at t = 0.1 s, 4 ranks per
# case, in two lanes (8 cores). Cases: flow only (chemistry off), GA18 DI (seulex), DI with Treact 600 K, TDAC/ISAT
# (tolerance 1e-3, 1e-4, 1e-5; no reduction), tix2h_s0 pure, P_mix pure. Each writes its 0.104 s state as a snapshot
# CSV; e_cost_report.py makes the table (chemistry s/step = total - flow only; per cell; error vs DI).
#   e_cost.sh [case ...]       (default: all, two lanes)
REPO=$(cd "$(dirname "$0")/../.." && pwd); R=/opt/ofb/runs/E; BASE=/opt/ofb/protocol_v2/base_flame; NP=4
. /opt/ofb/ofenv.sh; mkdir -p $R
D() { foamDictionary -entry "$1" -set "$2" "$3" > /dev/null; }
mk() {  # mk <case>
    c=$1; d=$R/$c; [ -f $d/done ] && return 0
    rm -rf $d; mkdir -p $d; cp -r $BASE/constant $BASE/system $BASE/chemkin $BASE/0.1 $d/; cd $d
    D endTime 0.104 system/controlDict; D writeControl runTime system/controlDict; D writeInterval 0.004 system/controlDict
    D purgeWrite 0 system/controlDict; D numberOfSubdomains $NP system/decomposeParDict
    CP=constant/chemistryProperties
    case $c in
        flow) D chemistry off $CP ;;
        di) ;;
        treact600) D Treact 600 $CP ;;
        isat*) tol=${c#isat}; D chemistryType/method TDAC $CP
               D reduction "{ active off; method none; }" $CP
               D tabulation "{ active on; log off; printProportion off; printNumRetrieve off; tolerance $tol; method ISAT; scaleFactor { otherSpecies 1; Temperature 1000; Pressure 1e15; deltaT 0.5; } maxNLeafs 5000; chPMaxLifeTime 100; maxGrowth 10; checkEntireTreeInterval 5; maxDepthFactor 2; minBalanceThreshold 30; MRURetrieve false; maxMRUSize 0; growPoints true; maxNumNewDim 10; variableTimeStep true; }" $CP ;;
        tix2h_s0|P_mix)
            if [ $c = P_mix ]; then mf=/opt/ofb/models/P_mix/chemmanifold_ensemble.txt; t=""
            else M=$REPO/data/openfoam_tix2h/08_fluent/resnet_film; mf=$M/chemmanifold_model.txt; t="tests \"$M/chemmanifold_tests.txt\";"; fi
            sed -i 's/^application .*/&\n\nlibs                (userChemStep);/' system/controlDict
            D chemistryType/solver userChemStep $CP
            printf '\nuserChemStepCoeffs\n{\n    model "%s";\n    %s\n    T_freeze 600;\n    maxSubsteps 50;\n    oodAction 0;\n    checkOOD true;\n    oodFallback false;\n    reportCalls 15000;\n    shadowEvery 50;\n    shadowPerBin 2;\n}\n' "$mf" "$t" >> $CP ;;
    esac
    decomposePar -force -time 0.1 > log.decomposePar 2>&1
    echo "$(date '+%F %T %Z') start" > status
    mpirun -np $NP rhoReactingBuoyantLeFoam -parallel > log.run 2>&1; echo "$(date '+%F %T %Z') exit $?" >> status
    /opt/ofb/ml/bin/python $REPO/openfoam/tools/foam_snapshot.py . snap --label $c --skip-existing > log.snapshots 2>&1
    find . -maxdepth 1 -type d -regex '\./[0-9.e+-]+' ! -name 0.1 -exec rm -rf {} +       # keep CSVs + logs only
    for p in processor*; do find $p -maxdepth 1 -type d -regex '.*/[0-9.e+-]+' -exec rm -rf {} +; done
    touch done; cd - > /dev/null
}
if [ $# -gt 0 ]; then for c in "$@"; do mk $c; done; exit 0; fi
( for c in flow di isat1e-3 tix2h_s0; do mk $c; done ) &
( for c in treact600 isat1e-4 isat1e-5 P_mix; do mk $c; done ) &
wait
/opt/ofb/ml/bin/python $REPO/server/sim1/e_cost_report.py > $R/report.log 2>&1
echo completed > $R/status

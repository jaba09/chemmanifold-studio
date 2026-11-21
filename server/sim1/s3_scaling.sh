#!/bin/bash
# S3 smoke/scaling test: 50 GA18 DI steps at 8 and 16 ranks, 50 pure-surrogate steps (ood8_s0) at 4 ranks.
# (DI at 4 ranks is run the same way; see results/sim1/S3/scaling.md.)
set -e
. /opt/ofb/ofenv.sh
HERE=$(dirname "$(realpath "$0")"); S3=/opt/ofb/runs/s3; MODEL=${MODEL:-$HOME/inputs/sim1-extra/models/ood8_s0}
prof() { cat >> system/controlDict <<'P'

profiling { active true; cpuInfo false; memInfo false; sysInfo false; }
P
}
run50() {  # run50 <dir> <np>
    cd "$1"
    foamDictionary -entry endTime -set 0.001 system/controlDict > /dev/null
    foamDictionary -entry writeInterval -set 50 system/controlDict > /dev/null
    mpirun -np "$2" rhoReactingBuoyantLeFoam -parallel > log.run 2>&1
    cd - > /dev/null
}
for NP in 8 16; do
    D=$S3/di_np$NP
    [ -d $D ] || { "$HERE/make_transient.sh" $S3/base $D $NP; (cd $D && prof); }
    [ -d $D/processor0/0.001 ] || run50 $D $NP
done
D=$S3/ucs_np4
if [ ! -d $D ]; then
    "$HERE/make_transient.sh" $S3/base $D 4
    cd $D; prof
    cp "$MODEL/chemmanifold_model.txt" "$MODEL/chemmanifold_tests.txt" .
    sed -i 's/^application .*/&\n\nlibs                (userChemStep);/' system/controlDict
    foamDictionary -entry chemistryType/solver -set userChemStep constant/chemistryProperties > /dev/null
    cat >> constant/chemistryProperties <<'C'

userChemStepCoeffs
{
    model        "chemmanifold_model.txt";
    tests        "chemmanifold_tests.txt";
    T_freeze     600;
    maxSubsteps  50;
    oodAction    0;
    checkOOD     true;
    oodFallback  false;      // pure surrogate: OOD cells are only counted
    reportCalls  15000;
    shadowEvery  50;
    shadowPerBin 2;
}
C
    cd - > /dev/null
fi
[ -d $D/processor0/0.001 ] || run50 $D 4
echo done > $S3/s3_status

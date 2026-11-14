#!/bin/sh
# ITERML collection run [A] (docs/ITERML-ROADMAP.md) from a prepared base case (mesh, GA18, lit start):
# the model runs from step 1; OOD cells and cells of (T, Z) bins where the shadow DI check found it
# wrong go to GA18 (hybrid), and their states, the shadow-checked states and the sentinel induction
# cells are kept per rank in processor*/isannPairs.csv (the ISANN store, no daemon, no retraining).
# Those states are only SEEDS of the next physics exploration (scripts/19_iterml_seeds.py).
#   ./setup_collect.sh <base case> <new run dir> <model dir> <nProcs> <shadowEvery> <shadowPerBin> \
#       <capPerBox> "<T_lo T_hi Y_CH4 Y_O2>" <sentinelEvery> <sentinelPerStep>
set -e
BASE=${1:?base case}; RUN=${2:?run dir}; MODEL=${3:?model dir}; NP=${4:-4}
SE=${5:-25}; SPB=${6:-3}; CAP=${7:-2}; SEN=${8:-900 1700 1e-4 0.01}; SEVERY=${9:-100}; SPER=${10:-10}
HERE=$(dirname "$(realpath "$0")")
[ -e "$RUN" ] && { echo "$RUN exists"; exit 1; }
cp -r "$BASE" "$RUN"
rm -rf "$RUN"/processor*
cp "$MODEL/chemmanifold_model.txt" "$RUN/"
[ -f "$MODEL/chemmanifold_tests.txt" ] && cp "$MODEL/chemmanifold_tests.txt" "$RUN/"
cd "$RUN"
grep -q userChemStep system/controlDict || sed -i 's/^application .*/&\n\nlibs                (userChemStep);/' system/controlDict
[ -f system/tauCellHistogram ] || cp "$HERE/../quemadorUnico/system/tauCellHistogram" system/
grep -q '#include "tauCellHistogram"' system/controlDict || \
    sed -i '0,/^functions/{/^functions/{n;s/^{/{\n    #include "tauCellHistogram"/}}' system/controlDict
foamDictionary -entry chemistryType/solver -set userChemStep constant/chemistryProperties > /dev/null
TESTS=""
[ -f chemmanifold_tests.txt ] && TESTS='tests "chemmanifold_tests.txt";'
cat >> constant/chemistryProperties <<EOD

userChemStepCoeffs
{
    model        "chemmanifold_model.txt";
    $TESTS
    T_freeze     600;
    maxSubsteps  50;
    oodAction    0;
    checkOOD     true;
    oodFallback  false;      // the isann dictionary sends OOD / untrusted cells to GA18
    reportCalls  0;
    shadowEvery  $SE;        // stratified shadow DI checks -> shadowDI.csv (comparison only)
    shadowPerBin $SPB;
    isann
    {
        control      "iterml/none";   // never written: ITERML retrains between runs, not during
        startActive  true;
        writeEvery   25;
        capPerBox    $CAP;
        boxT 25; boxSqrtZ 0.02; boxLogY 0.25; boxLogDt 0.1; boxYFloor 1e-8;
        boxSpecies   (CO2 CO OH H CH4 O2 CH2O HO2);
        trustTAbs    1;
        trustRel     0.3;
        trustOHAbs   5e-5;
        trustMin     2;
        sentinel     ($SEN);
        sentinelEvery $SEVERY;
        sentinelPerStep $SPER;
    }
}
EOD
foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
decomposePar -force > log.decomposePar 2>&1
echo "ready: $RUN ($NP ranks)"

#!/bin/sh
# Make an ISANN run of the burner from a prepared base case (mesh, mechanism, lit start in 0/): it
# starts on GA18 for every cell, keeps the (state, dt, GA18 result) pairs, and switches to each
# network that isann_daemon.py trains and accepts during the run (openfoam/isann/README.md).
#   ./setup_isann.sh <base case> <new run dir> <parent model dir with chemmanifold_model.txt> [nProcs]
# then: cd <run dir> && mpirun -np <nProcs> rhoReactingBuoyantFoam -parallel > log.run 2>&1 &
#       python3 isann_daemon.py --run <run dir> --config isann.yaml > <run dir>/isann/daemon.out 2>&1 &
set -e
BASE=${1:?base case}; RUN=${2:?run dir}; MODEL=${3:?parent model dir}; NP=${4:-2}
[ -e "$RUN" ] && { echo "$RUN exists"; exit 1; }
cp -r "$BASE" "$RUN"
cp "$MODEL/chemmanifold_model.txt" "$RUN/"
[ -f "$MODEL/chemmanifold_tests.txt" ] && cp "$MODEL/chemmanifold_tests.txt" "$RUN/"
cd "$RUN"
mkdir -p isann
grep -q userChemStep system/controlDict || sed -i 's/^application .*/&\n\nlibs                (userChemStep);/' system/controlDict
foamDictionary -entry chemistryType/solver -set userChemStep constant/chemistryProperties > /dev/null
TESTS=""
[ -f chemmanifold_tests.txt ] && TESTS='tests "chemmanifold_tests.txt";'
cat >> constant/chemistryProperties <<EOD

userChemStepCoeffs
{
    model        "chemmanifold_model.txt";   // parent: Z and OOD tables until the first ISANN network
    $TESTS
    T_freeze     600;
    maxSubsteps  50;
    oodAction    0;
    checkOOD     true;
    oodFallback  false;
    reportCalls  0;
    shadowEvery  10;         // every 10 steps a few cells per (T, Z, inside/OOD) bin are also run on GA18:
    shadowPerBin 2;          //  shadowDI.csv, a training pair, and the trust of the network in that bin
    isann
    {
        control      "isann/control";
        writeEvery   25;
        capPerBox    1;
        boxT 25; boxSqrtZ 0.02; boxLogY 0.25; boxLogDt 0.1; boxYFloor 1e-8;
        boxSpecies   (CO2 CO OH H CH4 O2 CH2O HO2);
        trustTAbs    1;
        trustRel     0.3;
        trustOHAbs   5e-5;
        trustMin     2;
    }
}
EOD
foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
decomposePar -force > log.decomposePar 2>&1
echo "ready: $RUN ($NP ranks)"

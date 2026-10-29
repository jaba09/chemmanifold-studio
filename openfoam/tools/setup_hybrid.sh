#!/bin/sh
# Make a hybrid run of the burner from a prepared base case (mesh, mechanism, lit start in 0/):
# the ChemManifold surrogate advances the cells inside its training data and GA18 (the ODE solver of
# odeCoeffs) the cells it flags as outside (oodFallback). Same start, dt and writes as the DI run.
#   ./setup_hybrid.sh <base case> <new run dir> <model dir with chemmanifold_model.txt> [nProcs]
# then: cd <run dir> && mpirun -np <nProcs> rhoReactingBuoyantFoam -parallel > log.run 2>&1
set -e
BASE=${1:?base case}; RUN=${2:?run dir}; MODEL=${3:?model dir}; NP=${4:-4}
[ -e "$RUN" ] && { echo "$RUN exists"; exit 1; }
cp -r "$BASE" "$RUN"
cp "$MODEL/chemmanifold_model.txt" "$RUN/"
[ -f "$MODEL/chemmanifold_tests.txt" ] && cp "$MODEL/chemmanifold_tests.txt" "$RUN/"
cd "$RUN"
grep -q userChemStep system/controlDict || sed -i 's/^application .*/&\n\nlibs                (userChemStep);/' system/controlDict
foamDictionary -entry chemistryType/solver -set userChemStep constant/chemistryProperties > /dev/null
TESTS=""
[ -f chemmanifold_tests.txt ] && TESTS='tests "chemmanifold_tests.txt";'
cat >> constant/chemistryProperties <<EOF

userChemStepCoeffs
{
    model        "chemmanifold_model.txt";
    $TESTS
    T_freeze     600;
    maxSubsteps  50;
    oodAction    0;
    checkOOD     true;
    oodFallback  true;       // cells outside the training data -> GA18 (odeCoeffs)
    reportCalls  15000;      // about one counter line per rank and time step
    shadowEvery  50;         // every 50 steps (1 ms) a few cells per (T, Z, inside/OOD) bin are also
    shadowPerBin 2;          //  integrated with GA18 from the same state -> shadowDI.csv (comparison only)
}
EOF
foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
decomposePar -force > log.decomposePar 2>&1
echo "ready: $RUN ($NP ranks)"

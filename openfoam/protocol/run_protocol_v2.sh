#!/bin/bash
# One phase of a protocol v2 run (PROTOCOL.md, docs/SIM1-ROADMAP.md section 4), resumable.
#   run_protocol_v2.sh <ign|flame> <run dir> <di|hybrid|pure> [model dir] [nProcs]
# Cases (corrected outlets, rhoReactingBuoyantLeFoam + constantLewis, fvDOM wall radiation, GA18):
#   ign    lean start (phi 0.5 burnt gas 1480 K), 0-25 ms; writes every 0.5 ms to 5 ms, then every 2.5 ms.
#          Reference: A2r (DI with radiation).                   base: $V2/base_ign
#   flame  R2 state (A1r, DI with radiation) at t = 0.1 s, to 0.15 s; writes every 2.5 ms.
#          Reference: A1r snapshots 0.1-0.15 s.                  base: $V2/base_flame
# model dir: a stage-12 export (chemmanifold_model.txt [+ chemmanifold_tests.txt]) or an ensemble
# (chemmanifold_ensemble.txt, members with absolute paths). Snapshots: <run dir>/snap/<label>_t<ms>ms.csv,
# label = $LABEL or the run dir name. Status in <run dir>/protocol_status.
set -e
PH=${1:?ign or flame}; RUN=${2:?run dir}; MODE=${3:?di, hybrid or pure}; MODEL=${4:-}; NP=${5:-4}
HERE=$(dirname "$(realpath "$0")"); V2=${V2:-/opt/ofb/protocol_v2}; PY=${PY:-/opt/ofb/ml/bin/python}
case $PH in
    ign)   BASE=$V2/base_ign;   T0=0;   LEGS="0.005:0.0005 0.025:0.0025" ;;
    flame) BASE=$V2/base_flame; T0=0.1; LEGS="0.15:0.0025" ;;
    *) echo "phase must be ign or flame"; exit 1 ;;
esac
LEGS=${LEGS_OVERRIDE:-$LEGS}   # testing only
D() { foamDictionary -entry "$1" -set "$2" "$3" > /dev/null; }
if [ ! -d "$RUN/processor0" ]; then
    rm -rf "$RUN"; mkdir -p "$RUN"
    cp -r "$BASE/constant" "$BASE/system" "$BASE/chemkin" "$BASE/$T0" "$RUN/"
    cd "$RUN"
    if [ "$MODE" != di ]; then
        M=$(realpath "${MODEL:?model dir}")
        if [ -f "$M/chemmanifold_ensemble.txt" ]; then mf="$M/chemmanifold_ensemble.txt"; tests=""
        else mf="$M/chemmanifold_model.txt"; tests=""; [ -f "$M/chemmanifold_tests.txt" ] && tests="tests \"$M/chemmanifold_tests.txt\";"; fi
        sed -i 's/^application .*/&\n\nlibs                (userChemStep);/' system/controlDict
        D chemistryType/solver userChemStep constant/chemistryProperties
        fb=true; [ "$MODE" = pure ] && fb=false
        cat >> constant/chemistryProperties <<X

userChemStepCoeffs
{
    model        "$mf";
    $tests
    T_freeze     600;
    maxSubsteps  50;
    oodAction    0;
    checkOOD     true;
    oodFallback  $fb;        // protocol: pure = surrogate everywhere, OOD only counted (as in Fluent)
    reportCalls  15000;
    shadowEvery  50;         // shadow DI checks on (T, Z, inside/OOD) bins: comparison data, kept with the run
    shadowPerBin 2;
}
X
    fi
    D numberOfSubdomains "$NP" system/decomposeParDict
    decomposePar -force -time "$T0" > log.decomposePar 2>&1
    echo "$MODE ${MODEL:+$(realpath "$MODEL")} np=$NP phase=$PH v2" > protocol_run
    cd - > /dev/null
fi
cd "$RUN"
APP=$(foamDictionary -entry application -value system/controlDict)
latest() { ls processor0 | grep -E '^[0-9.e+-]+$' | sort -g | tail -1; }
lt() { awk "BEGIN{exit !($1 < $2 - 1e-9)}"; }
set +e
echo running > protocol_status
for L in $LEGS; do
    IFS=: read END WI <<< "$L"
    if lt "$(latest)" "$END"; then
        D endTime "$END" system/controlDict; D writeInterval "$WI" system/controlDict; D startFrom latestTime system/controlDict
        mpirun -np "$NP" "$APP" -parallel >> log.run 2>&1
        if lt "$(latest)" "$END" && grep -aq "sigFpe" log.run; then
            # an FPE (seen in the shadow DI check: GA18 on a surrogate-advanced state, comparison only):
            # retry once from the last write with FPE trapping off, and record it
            echo "$(date '+%F %T %Z') FPE retry from $(latest) with FOAM_SIGFPE=false" >> protocol_notes
            D startFrom latestTime system/controlDict
            FOAM_SIGFPE=false mpirun -np "$NP" -genv FOAM_SIGFPE false "$APP" -parallel >> log.run 2>&1
        fi
        lt "$(latest)" "$END" && { echo "failed $(latest)" > protocol_status; break; }
    fi
done
grep -q failed protocol_status || echo "completed $(latest)" > protocol_status
$PY "$HERE/../tools/foam_snapshot.py" . snap --label "${LABEL:-$(basename "$PWD")}" --skip-existing > log.snapshots 2>&1
cat protocol_status

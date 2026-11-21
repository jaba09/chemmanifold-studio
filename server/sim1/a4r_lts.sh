#!/bin/bash
# A4r: steady (LTS) GA18 burner with LeFoam + constantLewis AND Fluent's wall radiation, from the Fluent DI start.
# This is the PC run of 9-11 Nov (results in openfoam/quemadorUnico/results_realistic_diffusion: LTS, no radiation,
# settled at 3.3x Fluent's hot volume) plus the radiation that fixed A1r (results/sim1/A1r/G1.md).
# Decides: does a steady LTS run reproduce Fluent / the A1r mean once radiation is in? If yes, the cheap steady test
# (protocol test 6b) can be rebuilt on it and future reference checks cost hours instead of a day of DI.
#
#   a4r_lts.sh <prepared radiation case> <run dir> [NP, default 8]
# <prepared radiation case> = the case A1r was made from (mesh, GA18, LeFoam + constantLewis, Fluent DI field in an
# ASCII 0/, enable_radiation.sh applied). Only its constant/, chemkin/ and 0/ are used; system/ comes from the repo's
# LTS case. Resumable: rerun the same command. Status in <run dir>/status, log in <run dir>/supervisor.log.
# Settled = at least 3000 iterations, domain Tmax range < 10 K over the last 1000, and V(T>1500 K) change < 3 % over
# the last 1000 (checked every 1000 on the reconstructed field). Hard stop 12000.
set -u
SRC=$(realpath "${1:?prepared radiation case}"); RUN=${2:?run dir}; NP=${3:-8}
HERE=$(dirname "$(realpath "$0")"); REPO=$(realpath "$HERE/../.."); PY=/opt/ofb/ml/bin/python
FLUENT_DAT=${FLUENT_DAT:-$HOME/inputs/sim1-extra/quemadorUnicoTesis_60KCells-GA18--ID.dat.h5}
OUT=$REPO/results/sim1/A4r
set +u; . /opt/ofb/ofenv.sh; set -u        # etc/bashrc reads unset variables
D() { foamDictionary -entry "$1" -set "$2" "$3" > /dev/null; }
log() { echo "$(date '+%F %T %Z') $*" >> "$RUN/supervisor.log"; }

# --- build once -------------------------------------------------------------------------------------------------
if [ ! -d "$RUN/processor0" ]; then
    mkdir -p "$RUN" && cd "$RUN"
    cp -r "$SRC/constant" "$SRC/chemkin" "$SRC/0" .
    cp -r "$REPO/openfoam/quemadorUnico/system" .           # LTS: localEuler, maxCo 0.5, alphaTemp 0.05, maxDeltaT 0.01
    grep -q rhoReactingBuoyantLeFoam system/controlDict || D application rhoReactingBuoyantLeFoam system/controlDict
    [ -f constant/speciesDiffusion ] || cp "$REPO/openfoam/quemadorUnico/constant/speciesDiffusion" constant/
    grep -q 'model *constantLewis' constant/speciesDiffusion || { echo "speciesDiffusion is not constantLewis" >&2; exit 1; }
    [ -f constant/radiationProperties ] || { echo "no radiation in $SRC (run enable_radiation.sh first)" >&2; exit 1; }
    # radiation entries that enable_radiation.sh puts in system/ (lost by copying the repo's system/)
    D "divSchemes/div(Ji,Ii_h)" "bounded Gauss linearUpwind grad(Ii_h)" system/fvSchemes
    D "solvers/Ii" "{ solver GAMG; tolerance 1e-6; relTol 0.01; smoother symGaussSeidel; maxIter 5; nPostSweeps 1; }" system/fvSolution
    rm -f 0/C 0/Cx 0/Cy 0/Cz 0/rDeltaT
    D startFrom latestTime system/controlDict
    D startTime 0 system/controlDict
    D writeInterval 500 system/controlDict
    D purgeWrite 4 system/controlDict
    D writeFormat binary system/controlDict
    D numberOfSubdomains "$NP" system/decomposeParDict
    grep -q weightField system/decomposeParDict || sed -i 's/^method .*/&\nweightField         cellWeight;/' system/decomposeParDict
    python3 "$HERE/write_cell_weight.py" 0 "${TCUT:-500}" "${WEIGHT:-5}"
    decomposePar -force -time 0 > log.decomposePar 2>&1 || { echo "decomposePar failed" >&2; exit 1; }
    log "built from $SRC on $NP ranks"
fi
cd "$RUN"
latest() { ls processor0 | grep -E '^[0-9]+$' | sort -n | tail -1; }

# --- metrics of a saved iteration (ASCII copy in cmp/), against Fluent ---------------------------------------------
metrics() {   # metrics <iteration> -> writes cmp_<it>.txt, prints "V Tmax"
    local t=$1
    reconstructPar -time "$t" > log.reconstruct 2>&1
    rm -rf cmp && mkdir cmp && cp -r constant system "$t" cmp/
    ( cd cmp && D writeFormat ascii system/controlDict && foamFormatConvert -time "$t" > /dev/null 2>&1 \
      && postProcess -func writeCellCentres -time "$t" > /dev/null 2>&1 \
      && postProcess -func writeCellVolumes -time "$t" > /dev/null 2>&1 )
    $PY "$REPO/openfoam/tools/compare_fluent.py" cmp "$t" "$FLUENT_DAT" "cmp_$t.png" --label "A4r LTS + rad" > "cmp_$t.txt" 2>&1
    rm -rf "$t"
    awk '/^hot volume/ {v = $(NF)} /^Tmax \[K\]/ {m = $(NF)} END {print v, m}' "cmp_$t.txt"
}

# --- run in legs of 1000 iterations until settled ------------------------------------------------------------------
echo running > status
prevV=""
while true; do
    L=$(latest); L=${L:-0}
    if [ "$L" -gt 0 ] && [ $((L % 1000)) = 0 ] && [ ! -f "cmp_$L.txt" ]; then
        read V TM <<< "$(metrics "$L")"; log "it $L: V(T>1500) $V cm3, Tmax $TM K"
        echo "$L,$V,$TM" >> progress.csv
    fi
    [ "$L" -ge 12000 ] && { log "hard stop at $L"; break; }
    if [ "$L" -ge 3000 ] && [ "$(wc -l < progress.csv 2>/dev/null || echo 0)" -ge 2 ]; then
        ok=$(tail -2 progress.csv | awk -F, 'NR==1{v=$2; t=$3} NR==2{dv = ($2-v)/v; if (dv<0) dv=-dv; dt = $3-t; if (dt<0) dt=-dt;
            print (dv < 0.03 && dt < 10) ? 1 : 0}')
        [ "$ok" = 1 ] && { log "settled at $L"; break; }
    fi
    END=$((L - L % 1000 + 1000))
    D endTime $END system/controlDict
    log "leg to $END from $L"
    mpirun -np "$NP" rhoReactingBuoyantLeFoam -parallel >> log.run 2>&1 || {
        log "solver failed at $(latest)"; tail -30 log.run > "crash_$(latest).txt"
        [ "$(latest)" = "$L" ] && { echo "failed $L" > status; exit 1; }; }
done

# --- report ---------------------------------------------------------------------------------------------------------
T=$(latest); [ -f "cmp_$T.txt" ] || metrics "$T" > /dev/null
mkdir -p "$OUT"
cp progress.csv "cmp_$T.txt" "cmp_$T.png" "$OUT/"
{
    echo "# A4r: steady LTS GA18 + LeFoam/constantLewis + wall radiation vs Fluent"
    echo
    echo "$(date '+%F %H:%M %Z'), sim1, $NP ranks. Stopped at iteration $T ($(tail -1 supervisor.log | cut -c1-80))."
    echo
    echo "Progress (iteration, V(T>1500 K) cm3, Tmax K): \`progress.csv\`. PC run without radiation, for reference:"
    echo "settled at V 60.1 cm3, Tmax 2126 K. A1r (DI + radiation) mean 0.1-0.1875 s: V 19.95 cm3, Tmax 2121 K, base 1.39 mm."
    echo
    echo '```'; cat "cmp_$T.txt"; echo '```'
    echo
    echo "![A4r vs Fluent](cmp_$T.png)"
} > "$OUT/summary.md"
echo "completed $T" > status
log "completed $T; report in $OUT"

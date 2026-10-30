#!/bin/bash
# One run of the fixed CFD evaluation protocol (PROTOCOL.md) on the burner, resumable.
#   run_protocol.sh <base case> <run dir> <di|hybrid|pure> [model dir] [nProcs] [start time dir]
# base case: mesh, GA18, lit start in 0/ (lean phi 0.5 burnt gas at 1480 K), transient dt 2e-5 s.
#   di      GA18 everywhere (the reference)
#   hybrid  surrogate, GA18 in the cells it flags as outside its training data (oodFallback)
#   pure    surrogate everywhere, OOD cells only counted (as in Fluent, which has no hybrid mode)
# Snapshots go to <run dir>/snap/<label>_t<ms>ms.csv (label: \$LABEL or the run dir name).
# Writes every 0.5 ms up to 5 ms (start-up phase), then every 2.5 ms up to 100 ms. Both run the
# shadow DI checks (comparison only). Rerun the same command to resume after a restart.
# start time dir (optional): continue from that state instead of 0/ (to extend a reference run).
# Needs the OpenFOAM environment and, for hybrid/pure, libuserChemStep in FOAM_USER_LIBBIN.
set -e
BASE=$(realpath "${1:?base case}"); RUN=${2:?run dir}; MODE=${3:?di, hybrid or pure}
MODEL=${4:-}; NP=${5:-2}; FROM=${6:-}
HERE=$(dirname "$(realpath "$0")")
T_START=0.005; T_END=${T_END:-0.1}   # T_END=0.005: start-up phase only

if [ ! -d "$RUN" ]; then
    case $MODE in
        di) cp -r "$BASE" "$RUN"; rm -rf "$RUN"/processor* ;;
        hybrid|pure) "$HERE/../tools/setup_hybrid.sh" "$BASE" "$RUN" "${MODEL:?model dir}" "$NP" > /dev/null ;;
        *) echo "mode must be di, hybrid or pure"; exit 1 ;;
    esac
    cd "$RUN"
    [ "$MODE" = pure ] && sed -i 's/oodFallback  true;.*/oodFallback  false;      \/\/ pure surrogate: OOD cells are only counted/' \
        constant/chemistryProperties
    foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict > /dev/null
    if [ -n "$FROM" ]; then
        T0=$(basename "$FROM")
        rm -rf processor* "$T0"; cp -r "$FROM" "$T0"; rm -rf "$T0/uniform/functionObjects"
        # chemistry-weighted decomposition, as for 0/ of the base case
        # (setExprFields of v2412 aborts on this case, so the weights are written from an ASCII copy)
        foamDictionary -entry writeFormat -set ascii system/controlDict > /dev/null
        foamFormatConvert -time "$T0" > log.foamFormatConvert 2>&1
        foamDictionary -entry writeFormat -set binary system/controlDict > /dev/null
        python3 - "$T0" <<'PY'
import re, sys
t = sys.argv[1]
src = open(f"{t}/T").read()
n, body = re.search(r"internalField\s+nonuniform\s+List<scalar>\s*(\d+)\s*\((.*?)\)\s*;", src, re.S).groups()
w = ["25" if float(v) > 800 else "1" for v in body.split()]
hdr = src.split("internalField")[0].replace("T;", "cellWeight;").replace("[0 0 0 1 0 0 0]", "[0 0 0 0 0 0 0]")
open(f"{t}/cellWeight", "w").write(hdr + "internalField nonuniform List<scalar>\n%s\n(\n%s\n)\n;\n"
    "boundaryField\n{\n    \".*\" { type calculated; value uniform 1; }\n    \"(front|back)\" { type wedge; }\n}\n"
    % (n, "\n".join(w)))
PY
        foamDictionary -entry startTime -set "$T0" system/controlDict > /dev/null
        decomposePar -force -time "$T0" > log.decomposePar 2>&1
    elif [ ! -d processor0 ]; then
        decomposePar -force > log.decomposePar 2>&1
    fi
    echo "$MODE ${MODEL:+$(realpath "$MODEL")} np=$NP from=${FROM:-0}" > protocol_run
    cd - > /dev/null
fi

cd "$RUN"
latest() { ls processor0 | grep -E '^[0-9.e-]+$' | sort -g | tail -1; }
leg() {  # leg <endTime> <writeInterval>
    foamDictionary -entry endTime -set "$1" system/controlDict > /dev/null
    foamDictionary -entry writeInterval -set "$2" system/controlDict > /dev/null
    foamDictionary -entry startFrom -set latestTime system/controlDict > /dev/null
    mpirun -np "$NP" rhoReactingBuoyantFoam -parallel >> log.run 2>&1
}
snap() {  # Fluent-style CSV of every written time, for score_protocol.py (diagnostic only)
    python3 "$HERE/../tools/foam_snapshot.py" . snap --label "${LABEL:-$(basename "$PWD")}" --skip-existing \
        > log.snapshots 2>&1
}
set +e
if awk "BEGIN{exit !($(latest) < $T_START - 1e-9)}"; then
    leg $T_START 0.0005 || { echo "failed $(latest)" > protocol_status; snap; exit 1; }
fi
if awk "BEGIN{exit !($(latest) < $T_END - 1e-9)}"; then
    leg $T_END 0.0025 || { echo "failed $(latest)" > protocol_status; snap; exit 1; }
fi
echo "completed $(latest)" > protocol_status
snap

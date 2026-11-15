#!/bin/bash
# ARC_GRI30_NOx22 DI burner run on sim1, protocol v2 legs, resumable (thread "Run OpenFOAM DI flame with
# 22-species mechanism"). Run it as a systemd user unit:
#   systemd-run --user --unit=sim1-arc -p WorkingDirectory=$PWD bash server/sim1/arc_run.sh
# Steps (each skipped when done):
#   1. build libarcChemStep
#   2. ARC bases from the protocol v2 GA18 bases: $W/v2/base_flame (A1r state at 0.1 s), $W/v2/base_ign (lean start)
#   3. flame leg: DI ARC from A1r 0.1 s to 0.2 s, writes every 2.5 ms (protocol v2 flame = 0.1-0.15 s,
#      extended to 0.2 s for a settled window 0.15-0.2 s), NP ranks
#   4. ignition leg: DI ARC 0-25 ms from the lean start (protocol v2 ignition phase)
#   5. protocol v2 scores of both legs against the GA18 DI references (A1r, A2r)
set -e
REPO=$(realpath "$(dirname "$(realpath "$0")")/../.."); NP=${NP:-8}
W=${W:-/opt/ofb/runs/arc22}; V2SRC=${V2SRC:-/opt/ofb/protocol_v2}; PY=${PY:-/opt/ofb/ml/bin/python}
. /opt/ofb/ofenv.sh
mkdir -p "$W"; LOG=$W/arc_run.log
say() { echo "$(date '+%F %T %Z') $*" | tee -a "$LOG"; }
say "start (NP $NP)"
[ -f "$FOAM_USER_LIBBIN/libarcChemStep.so" ] && [ "$W/.built" -nt "$REPO/mechanisms/arc_gri30_nox22/arc_gri30_nox22.c" ] || {
    (cd "$REPO/openfoam/arcChemStep" && ./Allwmake > "$W/log.wmake" 2>&1) || { say "build failed, see $W/log.wmake"; exit 1; }
    touch "$W/.built"; say "built libarcChemStep"; }
mkdir -p "$W/v2"
[ -d "$W/v2/base_flame" ] || bash "$REPO/server/sim1/arc_case.sh" "$V2SRC/base_flame" 0.1 "$W/v2/base_flame" >> "$LOG"
[ -d "$W/v2/base_ign" ]   || bash "$REPO/server/sim1/arc_case.sh" "$V2SRC/base_ign" 0 "$W/v2/base_ign" >> "$LOG"
P=$REPO/openfoam/protocol
export V2=$W/v2 PY
say "flame leg"
LABEL=arc22_flame LEGS_OVERRIDE="0.15:0.0025 0.2:0.0025" bash "$P/run_protocol_v2.sh" flame "$W/flame" di "" "$NP" >> "$LOG" 2>&1 \
    || say "flame leg returned $?"
say "flame: $(cat $W/flame/protocol_status)"
say "ignition leg"
LABEL=arc22_ign bash "$P/run_protocol_v2.sh" ign "$W/ign" di "" "$NP" >> "$LOG" 2>&1 || say "ignition leg returned $?"
say "ignition: $(cat $W/ign/protocol_status)"
say "done; score with server/sim1/arc_report.sh"

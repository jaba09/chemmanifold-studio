#!/bin/bash
# Score the ISANN ARC22 run (sim1-isanngri-run) once it has finished: snapshots of its writes, protocol v2 flame
# reports against the ARC22 DI flame (same base, 0.1-0.15 s) and against GA18 DI (A1r), the ISANN report (DI share
# per window, rounds, s/step), NOx against ARC22 DI, and results/sim1/ISANN_ARC22/summary.md, committed and pushed
# to the worktree's branch. Run as the user unit sim1-isanngri-score (nice 10), which waits for sim1-isanngri-run.
set -u
REPO=$(cd "$(dirname "$0")/../.." && pwd); PY=${PY:-/opt/ofb/ml/bin/python}; P=$REPO/openfoam/protocol
RUN=${RUN:-/opt/ofb/run/isann_arc22}; DI=${DI:-/opt/ofb/runs/arc22/flame}; OUT=$REPO/results/sim1/ISANN_ARC22
export PYTHONPATH=$REPO OMP_NUM_THREADS=1
mkdir -p "$OUT"; LOG=$OUT/score.log; : > "$LOG"
say() { echo "$(date '+%F %T %Z') $*" | tee -a "$LOG"; }
. /opt/ofb/ofenv.sh > /dev/null 2>&1
[ -f "$RUN/t_end" ] || say "WARNING: $RUN has no t_end (run not finished); scoring what is there"
cd "$RUN" || exit 1
# score_protocol.py reads the solver log as log.run; run_isann.sh writes one log.run.<leg> per (re)start
ls log.run.* > /dev/null 2>&1 && cat $(ls log.run.* | sort -t. -k3 -n) > log.run
say "snapshots"
$PY "$P/../tools/foam_snapshot.py" . snap --label isann_arc22 --skip-existing > log.snapshots 2>&1 || say "foam_snapshot returned $?"
# disk: the ASCII reconstructions foam_snapshot leaves in the case root (~50 MB each); the start time stays
[ "$(ls snap 2>/dev/null | wc -l)" -gt 0 ] && find . -maxdepth 1 -type d -regex '\./[0-9.e+-]+' ! -name 0.1 -exec rm -rf {} +
cd "$REPO"
say "protocol v2 flame vs ARC22 DI"
$PY $P/score_protocol.py --protocol $P/protocol_v2_flame.yaml --di "$DI/snap" --di-label arc22_DI \
    --run "$RUN/snap" --label isann_arc22 --run-dir "$RUN" --out "$OUT/vs_arc22_di" >> "$LOG" 2>&1 || say "score vs ARC22 returned $?"
say "protocol v2 flame vs GA18 DI (A1r)"
$PY $P/score_protocol.py --protocol $P/protocol_v2_flame.yaml --di /opt/ofb/runs/A1r_R2rad/snap --di-label A1r \
    --run "$RUN/snap" --label isann_arc22 --run-dir "$RUN" --out "$OUT/vs_ga18_di" >> "$LOG" 2>&1 || say "score vs A1r returned $?"
say "isann report"
mkdir -p "$OUT/isann"
$PY openfoam/isann/isann_report.py --run "$RUN" --label isann_arc22 --out "$OUT/isann" >> "$LOG" 2>&1 || say "isann_report returned $?"
cp "$RUN/isann/state.json" "$OUT/isann/state.json" 2>/dev/null
say "summary"
$PY server/sim1/isanngri_summary.py --run "$RUN" --di-arc "$DI" --out "$OUT" >> "$LOG" 2>&1 || say "summary returned $?"
git add "$OUT" && git -c user.name="Javier" -c user.email="jaba09@gmail.com" commit -q -m "results/sim1/ISANN_ARC22: protocol v2 flame scores of the ISANN ARC22 run vs ARC22 DI and GA18 DI, NOx, rounds

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && say "committed $(git rev-parse --short HEAD)"
for i in 1 2 3 4; do git push origin "$(git branch --show-current)" >> "$LOG" 2>&1 && { say "pushed"; break; }; sleep $((2 ** i)); done
say "done"

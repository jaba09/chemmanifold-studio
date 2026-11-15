#!/bin/bash
# Scores of the ARC_GRI30_NOx22 DI legs (arc_run.sh) as in phaseB.sh, plus the G1-style mean-field metrics and NOx.
#   arc_report.sh [flame|ign|all]      -> results/sim1/ARC22/{flame,ign}/arc22_*/protocol_report.*, meanfield.{json,txt},
#                                         outlet_nox.txt
# flame: protocol v2 flame report vs A1r (0.1-0.15 s); mean field of 0.15-0.2 s vs A1r mean 0.1-0.1875 s and Fluent.
# ign:   protocol v2 ignition report vs A2r (0-25 ms).
WHAT=${1:-all}
REPO=$(realpath "$(dirname "$(realpath "$0")")/../.."); P=$REPO/openfoam/protocol; PY=${PY:-/opt/ofb/ml/bin/python}
W=${W:-/opt/ofb/runs/arc22}; OUT=${OUT:-$REPO/results/sim1/ARC22}; mkdir -p "$OUT"
DAT=${DAT:-$HOME/inputs/sim1-extra/fluent-corrected/quemadorUnicoTesis_60KCells-GA18--ID.dat.h5}
. /opt/ofb/ofenv.sh
if [ "$WHAT" != ign ] && [ -d "$W/flame/snap" ]; then
    $PY $P/score_protocol.py --protocol $P/protocol_v2_flame.yaml --di /opt/ofb/runs/A1r_R2rad/snap --di-label A1r \
        --run "$W/flame/snap" --label arc22_flame --run-dir "$W/flame" --out "$OUT/flame" > "$OUT/score_flame.log" 2>&1
    $PY "$REPO/server/sim1/arc_meanfield.py" \
        --set ARC22_0.15-0.2 "$W/flame/snap" arc22_flame 0.15 0.2 \
        --set ARC22_0.1-0.1875 "$W/flame/snap" arc22_flame 0.1 0.1875 \
        --set A1r_0.1-0.1875 /opt/ofb/runs/A1r_R2rad/snap A1r 0.1 0.1875 \
        --fluent "$DAT" --out "$OUT/meanfield.json" > "$OUT/meanfield.txt" 2>&1
    # outlet NOx (phi-weighted, every 10 steps): mean over 0.15-0.2 s and the last value
    for f in "$W"/flame/postProcessing/outletNOx_*/*/surfaceFieldValue.dat; do
        [ -f "$f" ] || continue
        echo "== $(basename "$(dirname "$(dirname "$f")")")"
        awk '/^# Time/{sub(/^# /,""); print; next} /^#/{next} {print}' "$f" | $PY -c '
import sys, pandas as pd
d = pd.read_csv(sys.stdin, sep=r"\s+")
d.columns = [c.replace("weightedAverage(", "").rstrip(")") for c in d.columns]
w = d[(d.Time >= 0.15) & (d.Time <= 0.2 + 1e-9)]
print("mean 0.15-0.2 s (%d samples):" % len(w)); print(w.drop(columns="Time").mean().to_string(float_format="%.4g"))
print("last (t = %.5f s):" % d.Time.iloc[-1]); print(d.iloc[-1].drop("Time").to_string(float_format="%.4g"))'
    done > "$OUT/outlet_nox.txt" 2>&1
    echo "flame: $(tail -1 "$OUT/score_flame.log")"
fi
if [ "$WHAT" != flame ] && [ -d "$W/ign/snap" ]; then
    $PY $P/score_protocol.py --protocol $P/protocol_v2_ign.yaml --di /opt/ofb/runs/A2r_ign/snap --di-label A2r_ign \
        --run "$W/ign/snap" --label arc22_ign --run-dir "$W/ign" --di-dir /opt/ofb/runs/A2r_ign --out "$OUT/ign" \
        > "$OUT/score_ign.log" 2>&1
    echo "ign: $(tail -1 "$OUT/score_ign.log")"
fi

#!/bin/bash
# After A2r (ignition DI with radiation) completes: its snapshot CSVs, then A3r (2-step LeFoam flame with
# radiation, LTS until settled, stage 19 as A3r_wd2_lefoam_rad) on the same 4 cores.
HERE=$(dirname "$(realpath "$0")"); REPO=$(realpath "$HERE/../.."); R=/opt/ofb/runs
until grep -q "completed\|failed" $R/A2r_ign/status 2>/dev/null; do sleep 60; done
. /opt/ofb/ofenv.sh
if grep -q completed $R/A2r_ign/status; then
    cd $R/A2r_ign && /opt/ofb/ml/bin/python "$REPO/openfoam/tools/foam_snapshot.py" . snap --label A2r_ign --skip-existing \
        > log.snapshots 2>&1
fi
LABEL=A3r_wd2_lefoam_rad "$HERE/a3_run.sh" $R/A3r_cheap/case 4

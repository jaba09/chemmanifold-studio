#!/bin/bash
# Start or resume an ISANN run of the burner (openfoam/isann/README.md): CFD on 2 MPI ranks plus the
# trainer daemon on 2 threads. Run it inside tmux. If the server restarts or you stop it, run the
# same command again: the CFD continues from its latest write and the daemon from its state.
#
#   bash server/run_isann.sh <run name> [parent model dir] [nProcs] [config yaml]
#   bash server/run_isann.sh isann1                       # parent /opt/ofb/isann/parent_ood7, 2 ranks
#   Optional env: BASE (base case, default /opt/ofb/base/base), SOLVER (default rhoReactingBuoyantFoam),
#   ENDTIME, WRITEINTERVAL (set at creation), DAEMON_NICE (nice of the trainer daemon)
#
# The run lives in /opt/ofb/run/<run name>. Stop it cleanly with Ctrl+C (CFD) or
#   touch /opt/ofb/run/<run name>/isann/STOP      (daemon)
set -e
REPO=$(cd "$(dirname "$0")/.." && pwd)
NAME=${1:?run name}; PARENT=${2:-/opt/ofb/isann/parent_ood7}; NP=${3:-2}
CONF=${4:-$REPO/openfoam/isann/isann.yaml}
R=/opt/ofb/run/$NAME
BASE=${BASE:-/opt/ofb/base/base}; SOLVER=${SOLVER:-rhoReactingBuoyantFoam}
# the ml env has chemmanifold installed from ~/chemmanifold-studio (editable): load this repo's package first
export PYTHONPATH=$REPO${PYTHONPATH:+:$PYTHONPATH}
. /opt/ofb/ofenv.sh
spain() { TZ=Europe/Madrid date '+%Y-%m-%d %H:%M %Z'; }

if [ ! -d "$R" ]; then
    mkdir -p /opt/ofb/run
    "$REPO/openfoam/isann/setup_isann.sh" "$BASE" "$R" "$PARENT" "$NP"
    cp "$CONF" "$R/isann/isann.yaml"
    [ -n "${ENDTIME:-}" ] && foamDictionary -entry endTime -set "$ENDTIME" "$R/system/controlDict" > /dev/null
    [ -n "${WRITEINTERVAL:-}" ] && foamDictionary -entry writeInterval -set "$WRITEINTERVAL" "$R/system/controlDict" > /dev/null
    echo "[$(spain)] created $R (parent $PARENT, $NP ranks)" >> "$R/server.log"
fi
cd "$REPO"
pgrep -f "[i]sann_daemon.py --run $R " > /dev/null || {
    nohup nice -n ${DAEMON_NICE:-0} /opt/ofb/ml/bin/python openfoam/isann/isann_daemon.py --run "$R" --config "$R/isann/isann.yaml" --poll 30 \
        >> "$R/isann/daemon.out" 2>&1 &
    echo "[$(spain)] daemon started" >> "$R/server.log"
}
cd "$R"
if [ -f t_end ]; then echo "this run has already finished ($(cat t_end))"; exit 0; fi
n=$(ls log.run* 2>/dev/null | wc -l)
echo "[$(spain)] CFD leg $n started; progress: tail -f $R/log.run.$n" | tee -a server.log
set +e
mpirun -np "$NP" "$SOLVER" -parallel > log.run.$n 2>&1
if grep -q "^End" log.run.$n; then
    spain > t_end; touch isann/STOP
    echo "[$(spain)] finished" | tee -a server.log
else
    echo "[$(spain)] CFD stopped before the end (see log.run.$n); run this command again to resume" | tee -a server.log
    exit 1
fi

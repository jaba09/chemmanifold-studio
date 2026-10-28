#!/bin/bash
# One-command setup and run of the burner case on a Linux x86_64 computer (or Windows WSL Ubuntu).
# Installs OpenFOAM v2412 from conda-forge into ~/openfoam-burner the first time (no sudo,
# about 1.5 GB), then builds and runs the case.
#
#   ./run_on_my_computer.sh                     start: uses the .cas.h5 in this folder
#   ./run_on_my_computer.sh path/to/case.cas.h5 start with that file
#   ./run_on_my_computer.sh --resume            continue a run that was stopped
#   ./run_on_my_computer.sh --results           prepare the latest saved step for ParaView
#
# CORES=2 ./run_on_my_computer.sh ...   overrides the number of processor cores used.
set -e
cd "${0%/*}" || exit 1

INSTALL_DIR=${OPENFOAM_BURNER_HOME:-$HOME/openfoam-burner}
ENV_DIR=$INSTALL_DIR/env
MAMBA_VERSION=2.6.2-1
CHANNEL=https://conda.anaconda.org/conda-forge

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
die() { printf '\n\033[31mProblem: %s\033[0m\n' "$*" >&2; exit 1; }

# --- what this computer is ------------------------------------------------------------------
[ "$(uname -s)" = Linux ] || die "this script runs on Linux or Windows WSL only. On a Mac, see the guide (Docker route)."
[ "$(uname -m)" = x86_64 ] || die "OpenFOAM's conda package exists only for x86_64 (Intel/AMD) Linux; this is $(uname -m)."
for tool in curl tar bzip2; do
    command -v $tool > /dev/null || die "'$tool' is missing. Install it with:  sudo apt install $tool"
done
if [ -z "$CORES" ]; then
    CORES=$(nproc)
    [ "$CORES" -gt 8 ] && CORES=8
fi

# --- install OpenFOAM once ------------------------------------------------------------------
if [ ! -x "$ENV_DIR/bin/rhoReactingBuoyantFoam" ]; then
    say "Installing OpenFOAM v2412 into $INSTALL_DIR (one time, 5-15 minutes)..."
    rm -rf "$ENV_DIR" "$INSTALL_DIR/mamba" && mkdir -p "$INSTALL_DIR/mamba"
    curl -fsSL "$CHANNEL/linux-64/micromamba-$MAMBA_VERSION.tar.bz2" \
        | tar -xj -C "$INSTALL_DIR/mamba" bin/micromamba \
        || die "could not download micromamba. Check the internet connection and try again."
    "$INSTALL_DIR/mamba/bin/micromamba" create -y -q -r "$INSTALL_DIR/mamba" -p "$ENV_DIR" \
        -c conda-forge --override-channels openfoam=2412 python numpy h5py \
        || die "the OpenFOAM download failed. Run the script again; it starts over cleanly."
    "$INSTALL_DIR/mamba/bin/micromamba" clean -y -q -a -r "$INSTALL_DIR/mamba" > /dev/null 2>&1 || true
fi
# OpenFOAM looks for its MPI library under lib/sys-mpich; conda ships it as lib/mpich-3.3
[ -e "$ENV_DIR/lib/sys-mpich" ] || ln -s mpich-3.3 "$ENV_DIR/lib/sys-mpich"

export PATH=$ENV_DIR/bin:$PATH
export LD_LIBRARY_PATH=$ENV_DIR/lib/sys-mpich:$ENV_DIR/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export WM_PROJECT_DIR=$ENV_DIR FOAM_ETC=$ENV_DIR/etc FI_PROVIDER=tcp
command -v rhoReactingBuoyantFoam > /dev/null || die "OpenFOAM did not install correctly. Delete $INSTALL_DIR and run again."

latest() { # newest saved iteration in processor0 (or 0 if none)
    ls -d processor0/[0-9]* 2>/dev/null | sed 's|.*/||' | sort -n | tail -1
}
results() {
    say "Collecting the latest saved step for ParaView..."
    if [ -d processor0 ]; then
        reconstructPar -latestTime > log.reconstructPar 2>&1 || die "reconstructPar failed, see log.reconstructPar"
    fi
    touch burner.foam
    say "Done. In ParaView open:  $(pwd)/burner.foam"
}

case "$1" in
--results)
    results
    exit 0
    ;;
--resume)
    [ -d processor0 ] || die "there is no stopped run here to resume. Start one without --resume."
    np=$(ls -d processor[0-9]* | wc -l)
    say "Resuming from iteration $(latest) on $np cores. Stop at any time with Ctrl+C."
    say "Progress:  tail -f $(pwd)/log.rhoReactingBuoyantFoam   (in a second terminal)"
    trap : INT  # Ctrl+C stops the solver but not this script, so the results still get collected
    mpirun -np "$np" rhoReactingBuoyantFoam -parallel >> log.rhoReactingBuoyantFoam 2>&1 || true
    results
    exit 0
    ;;
esac

# --- fresh start ----------------------------------------------------------------------------
CAS=$1
if [ -z "$CAS" ]; then
    set -- *.cas.h5
    [ -e "$1" ] || die "no .cas.h5 file in $(pwd). Copy quemadorUnicoTesis_60KCells-GA18--ID-UDF.cas.h5 here, or give its path."
    CAS=$1
fi
[ -f "$CAS" ] || die "file not found: $CAS"
CAS=$(cd "$(dirname "$CAS")" && pwd)/$(basename "$CAS")

if [ -d processor0 ]; then
    say "There is already a run in this folder (saved up to iteration $(latest))."
    read -r -p "Delete it and start over? Type yes, or anything else to keep it: " answer
    [ "$answer" = yes ] || die "kept the previous run. Continue it with:  ./run_on_my_computer.sh --resume"
fi
./Allclean
say "Building the case and starting the simulation on $CORES cores."
say "This runs for hours. Stop at any time with Ctrl+C and continue later with --resume."
say "Progress:  tail -f $(pwd)/log.rhoReactingBuoyantFoam   (in a second terminal)"
trap : INT
./Allrun "$CAS" "$CORES" || true
results

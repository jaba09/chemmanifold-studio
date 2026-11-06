#!/bin/bash
# One-time setup of a rented Ubuntu server (22.04 or 24.04, x86_64) for this project's runs.
# Installs, without touching the system Python:
#   /opt/ofb/env       OpenFOAM v2412 (openfoam.com) from conda-forge, with its own python + numpy + h5py
#   /opt/ofb/ml        Python 3.12 with Cantera, PyTorch (CPU), numpy, scipy, pandas, scikit-learn, ...
#                      and this repository installed in it (pip install -e)
#   /opt/ofb/ofenv.sh  the file to "source" before any OpenFOAM command
# and builds the userChemStep chemistry library (surrogate / hybrid / ISANN) and the
# tauCellHistogram function object.
#
#   bash server/setup_server.sh          (from the repository folder; asks for the sudo password once)
#
# The same /opt/ofb layout as the cloud containers where the runs were developed, so the commands in
# openfoam/*/README.md and configs/iterml/*.yaml work unchanged. Takes 10-20 minutes. Safe to run
# again: finished parts are skipped.
set -e
REPO=$(cd "$(dirname "$0")/.." && pwd)
OFB=/opt/ofb
MAMBA_VERSION=2.6.2-1
CHANNEL=https://conda.anaconda.org/conda-forge

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
die() { printf '\n\033[31mProblem: %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] || die "needs an x86_64 (Intel/AMD) Linux server; OpenFOAM's conda package has no ARM build."

# --- 1. system tools ------------------------------------------------------------------------
if command -v apt-get > /dev/null; then
    say "1/5 Installing system tools (compiler, tmux, git)..."
    sudo apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq build-essential tmux git curl bzip2 htop rsync zip unzip > /dev/null
else
    say "1/5 Not an apt system: make sure gcc, g++, make, tmux, git, curl, bzip2 and rsync are installed."
fi
sudo mkdir -p $OFB && sudo chown "$(id -u):$(id -g)" $OFB

# --- 2. micromamba (the package installer) ----------------------------------------------------
MM=$OFB/mamba/bin/micromamba
if [ ! -x $MM ]; then
    say "2/5 Downloading micromamba..."
    mkdir -p $OFB/mamba
    curl -fsSL "$CHANNEL/linux-64/micromamba-$MAMBA_VERSION.tar.bz2" | tar -xj -C $OFB/mamba bin/micromamba \
        || die "could not download micromamba; check the internet connection and run again."
fi

# --- 3. OpenFOAM v2412 ----------------------------------------------------------------------------
if [ ! -x $OFB/env/bin/rhoReactingBuoyantFoam ]; then
    say "3/5 Installing OpenFOAM v2412 into $OFB/env (about 1.5 GB)..."
    rm -rf $OFB/env
    $MM create -y -q -r $OFB/mamba -p $OFB/env -c conda-forge --override-channels \
        openfoam=2412 python numpy h5py || die "OpenFOAM download failed; run the script again."
fi
# OpenFOAM looks for its MPI under lib/sys-mpich; conda ships lib/mpich-3.3. wmake wants src/.
[ -e $OFB/env/lib/sys-mpich ] || ln -s mpich-3.3 $OFB/env/lib/sys-mpich
[ -e $OFB/env/src ] || ln -s include/OpenFOAM-2412/src $OFB/env/src

cat > $OFB/ofenv.sh <<'EOF'
# source this before any OpenFOAM command:   . /opt/ofb/ofenv.sh
E=/opt/ofb/env
export PATH=$E/bin:$PATH
export LD_LIBRARY_PATH=$E/lib/sys-mpich:$E/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export WM_PROJECT_DIR=$E FOAM_ETC=$E/etc FI_PROVIDER=tcp
. $E/etc/bashrc > /dev/null 2>&1 || true
export GXX=g++ GCC=gcc
export LD_LIBRARY_PATH=$FOAM_USER_LIBBIN:$LD_LIBRARY_PATH
EOF

# --- 4. Python for the ML pipeline (Cantera + PyTorch CPU) -----------------------------------------
if [ ! -x $OFB/ml/bin/python ] || ! $OFB/ml/bin/python -c "import torch, cantera" 2> /dev/null; then
    say "4/5 Installing Python 3.12 + Cantera + PyTorch (CPU) into $OFB/ml (about 1 GB)..."
    rm -rf $OFB/ml
    $MM create -y -q -r $OFB/mamba -p $OFB/ml -c conda-forge --override-channels \
        python=3.12 "pytorch=*=cpu*" cantera numpy scipy pandas scikit-learn matplotlib pyyaml h5py \
        || die "Python package download failed; run the script again."
fi
$OFB/ml/bin/pip install -q -e "$REPO" --no-deps
$MM clean -y -q -a -r $OFB/mamba > /dev/null 2>&1 || true

# --- 5. build the chemistry library and the tau_cell histogram -------------------------------------
say "5/5 Building userChemStep and tauCellHistogram..."
(
    set +e
    . $OFB/ofenv.sh
    cd "$REPO/openfoam/userChemStep" && ./Allwmake > log.Allwmake 2>&1
    cd "$REPO/openfoam/tauCellHistogram" && ./Allwmake > log.Allwmake 2>&1
    true
)
. $OFB/ofenv.sh
[ -f "$FOAM_USER_LIBBIN/libuserChemStep.so" ] || die "userChemStep did not build; see openfoam/userChemStep/log.Allwmake"

# --- check ---------------------------------------------------------------------------------------
say "Checking..."
command -v rhoReactingBuoyantFoam > /dev/null && echo "  OpenFOAM:        OK ($(command -v rhoReactingBuoyantFoam))"
echo "  userChemStep:    OK ($FOAM_USER_LIBBIN/libuserChemStep.so)"
[ -f "$FOAM_USER_LIBBIN/libtauCellHistogram.so" ] && echo "  tauCellHistogram: OK" || echo "  tauCellHistogram: not built (only needed for the tau_cell histogram)"
$OFB/ml/bin/python -c "import cantera, torch, chemmanifold; print('  Python ML:       OK (Cantera', cantera.__version__, '/ torch', torch.__version__, ')')"
echo "  cores: $(nproc)   memory: $(free -g | awk '/Mem/{print $2}') GB   free disk: $(df -h /opt | awk 'NR==2{print $4}')"
say "Setup finished. Next: bash server/unpack_inputs.sh <folder with the downloaded .tgz files>"

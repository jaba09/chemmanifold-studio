#!/bin/bash
# Unpack the project files a run needs (downloaded from the project's Library) into the layout the
# scripts and configs expect.
#
#   bash server/unpack_inputs.sh ~/uploads
#
# The folder must hold server-inputs.tgz, and optionally server-di-reference.tgz (the GA18 DI
# reference snapshots, needed only to SCORE protocol, ITERML and ensemble CFD runs).
#
# Result:
#   /opt/ofb/files/chemmanifold/...   the project files (same tree as the project's Library), also
#                                     reachable as /mnt/project-files/chemmanifold/... (a link), so the
#                                     paths written in configs/iterml/*.yaml work unchanged
#   /opt/ofb/base/base                the burner base case: mesh, GA18, lit start, dt 2e-5 s, 50 ms
#   /opt/ofb/isann/parent_ood7        ISANN parent (data of ood7 + its model file), as isann.yaml expects
#   /opt/ofb/iterml/data/iter0        ITERML parent data (ood8), as configs/iterml/*.yaml expect
#   /opt/ofb/iterml/base/base         the base case again, where the ITERML configs look for it
set -e
SRC=$(cd "${1:?give the folder that holds server-inputs.tgz}" && pwd)
OFB=/opt/ofb
F=$OFB/files
say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
die() { printf '\n\033[31mProblem: %s\033[0m\n' "$*" >&2; exit 1; }

[ -f "$SRC/server-inputs.tgz" ] || die "server-inputs.tgz is not in $SRC"
[ -d $OFB ] || die "run server/setup_server.sh first"
mkdir -p $F

say "Unpacking server-inputs.tgz..."
tar xzf "$SRC/server-inputs.tgz" -C $F
if [ -f "$SRC/server-di-reference.tgz" ]; then
    say "Unpacking server-di-reference.tgz (DI reference snapshots)..."
    tar xzf "$SRC/server-di-reference.tgz" -C $F
fi

# the configs name /mnt/project-files/chemmanifold/...; point that path at the unpacked copy
if [ ! -e /mnt/project-files ]; then
    sudo mkdir -p /mnt && sudo ln -s $F /mnt/project-files
fi

C=$F/chemmanifold
say "Base case -> $OFB/base/base"
mkdir -p $OFB/base $OFB/iterml/base
[ -d $OFB/base/base ] || tar xzf $C/protocolo-cfd/de-bucle-ood/caso_base.tgz -C $OFB/base
[ -d $OFB/iterml/base/base ] || cp -r $OFB/base/base $OFB/iterml/base/

say "ISANN parent (ood7) -> $OFB/isann/parent_ood7"
mkdir -p $OFB/isann/parent_ood7
rsync -a --ignore-existing $C/handoff-ood7/ $OFB/isann/parent_ood7/
rsync -a --ignore-existing $C/benchmark/modelos/ood7/chemmanifold_model.txt $C/benchmark/modelos/ood7/chemmanifold_tests.txt \
    $OFB/isann/parent_ood7/

say "ITERML parent data (ood8) -> $OFB/iterml/data/iter0"
mkdir -p $OFB/iterml/data/iter0
rsync -a --ignore-existing $C/handoff-ood8/ $OFB/iterml/data/iter0/

say "Done. Models are in $C/benchmark/modelos/<name>/ (chemmanifold_model.txt for each)."
du -sh $F $OFB/base $OFB/isann $OFB/iterml 2>/dev/null

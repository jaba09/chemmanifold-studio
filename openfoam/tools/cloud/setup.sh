#!/bin/bash
# setup.sh <name> <di|noadiabatico|recirculacion>: transient case from the LTS state 4227
set -e
. /opt/ofb/env.sh
SRC=/opt/ofb/run/quemadorUnico; T0=4227
D=/opt/ofb/tr/$1; rm -rf $D; mkdir -p $D; cd $D
cp -r $SRC/constant $SRC/system $SRC/chemkin .
cp -r $SRC/$T0 .; rm -f $T0/rDeltaT
cp /opt/ofb/run/sur/system/fvSchemes system/
cp /opt/ofb/run/sur/system/fvSolution system/
cp /opt/ofb/run/sur/system/controlDict system/
sed -i "s/^startTime .*/startTime       $T0;/; s/^endTime .*/endTime         $T0.05;/; s/^deltaT .*/deltaT          2e-05;/; s/^writeInterval .*/writeInterval   500;/; s/^purgeWrite .*/purgeWrite      0;/" system/controlDict
if [ "$2" = di ]; then
    cp /opt/ofb/run/sur/constant/chemistryProperties.di constant/chemistryProperties
else
    mkdir -p models; cp -r /opt/ofb/run/sur/models/$2 models/
    sed "s|models/noadiabatico|models/$2|g; s/reportCalls     0;/reportCalls     1000000;/" /opt/ofb/run/sur/constant/chemistryProperties.sur > constant/chemistryProperties
fi
# chemistry-weighted decomposition
/usr/bin/python3 - <<PY
import sys; sys.path.insert(0,'/opt/ofb/tools'); from foamread import read_field; import numpy as np
T=read_field('$T0/T'); w=np.where(T>800,25.0,1.0)
hdr=open('$T0/T').read().split('internalField')[0].replace('object      T;','object      cellWeight;').replace('[0 0 0 1 0 0 0]','[0 0 0 0 0 0 0]')
open('$T0/cellWeight','w').write(hdr+"internalField   nonuniform List<scalar> \n%d\n(\n%s\n)\n;\nboundaryField\n{\n    \".*\" { type calculated; value uniform 1; }\n    \"(front|back)\" { type wedge; }\n}\n"%(len(w),"\n".join("%g"%x for x in w)))
PY
decomposePar -time $T0 > log.decomposePar 2>&1

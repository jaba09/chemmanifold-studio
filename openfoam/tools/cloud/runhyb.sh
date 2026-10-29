#!/bin/bash
. /opt/ofb/env.sh
for v in noadiabatico:hyb_noad recirculacion:hyb_recirc; do
    m=${v%%:*}; n=${v##*:}
    grep -q "^$n done" /opt/ofb/tr/status && continue
    [ -d /opt/ofb/tr/$n/processor3 ] || /opt/ofb/tr/setup.sh $n $m > /opt/ofb/tr/setup_$n.log 2>&1
    cd /opt/ofb/tr/$n && mpirun -np 4 rhoReactingBuoyantFoam -parallel >> log.run 2>&1
    echo "$n done $(date)" >> /opt/ofb/tr/status
done

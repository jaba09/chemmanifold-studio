#!/bin/bash
# the three transient runs, one after the other on 4 cores; resumes after a restart
. /opt/ofb/env.sh
for v in noadiabatico:sur_noad recirculacion:sur_recirc di:di; do
    m=${v%%:*}; n=${v##*:}
    grep -q "^$n done" /opt/ofb/tr/status 2>/dev/null && continue
    if [ ! -d /opt/ofb/tr/$n/processor3 ]; then
        /opt/ofb/tr/setup.sh $n $m > /opt/ofb/tr/setup_$n.log 2>&1 || { echo "setup $n failed"; continue; }
    fi
    cd /opt/ofb/tr/$n && mpirun -np 4 rhoReactingBuoyantFoam -parallel >> log.run 2>&1
    echo "$n done $(date)" >> /opt/ofb/tr/status
done

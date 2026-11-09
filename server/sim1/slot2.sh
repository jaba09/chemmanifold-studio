#!/bin/bash
# sim1 slot 2 (4 cores): A2 ignition DI reference, then A3 cheap flame + stage 19.
HERE=$(dirname "$(realpath "$0")")
"$HERE/supervise.sh" /opt/ofb/runs/A2_ign 4 0.005:25:0 0.025:125:0
"$HERE/a3_run.sh" /opt/ofb/runs/A3_cheap/case 4

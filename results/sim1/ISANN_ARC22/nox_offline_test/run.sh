#!/bin/bash
cd /opt/ofb/isann-gri-src; export PYTHONPATH=$PWD OMP_NUM_THREADS=3
D=$1
for st in 05_preprocess.py 07_train.py 12_export_fluent.py; do
  nice -n 10 /opt/ofb/ml/bin/python -u scripts/$st --config $D/config.yaml $( [ $st != 05_preprocess.py ] && echo --arch resnet_film ) >> $D/log.txt 2>&1 || { echo "FAILED $st" >> $D/log.txt; exit 1; }
done
echo DONE >> $D/log.txt

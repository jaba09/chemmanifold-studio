#!/bin/bash
# Nightly: summarise yesterday, prune raw data older than 60 days, publish to git.
cd $HOME/sim1-usage
D=$(date -d yesterday +%F)
nice -n 19 bin/summarize.py "$D" > /dev/null
find data -name '*-20??-??-??.csv' -mtime +60 -delete
bin/publish.sh "$D"

# sim1 usage statistics

Lightweight monitoring of the sim1 server (16 cores, 62 GB, Europe/Madrid time).

* `bin/sample.py` runs from cron every 5 minutes (`nice 19`, `ionice idle`, about 0.1 s of CPU). It only reads `/proc`
  and writes one system row plus one row per run (grouped by the run's working directory) to `~/sim1-usage/data/`.
  CPU numbers are exact averages over each 5-minute interval, from kernel jiffy counters.
* `bin/daily.sh` runs at 00:15 and writes `reports/YYYY-MM-DD.md` (summary), `reports/YYYY-MM-DD-runs.csv`
  (core-hours per run) and appends `reports/daily.csv` (one row per day), then commits them here.
* Days before 2026-11-14 are back-filled from sysstat (10-minute system CPU only, no per-run split). sysstat stopped
  recording while the disk was full on Nov 12–14, so those days are only partly covered.

Columns in `daily.csv`: mean utilisation of all 16 cores, peak/min busy cores, busy and idle core-hours,
hours in which at least one core was idle on average, minimum and end-of-day free disk, peak memory used.

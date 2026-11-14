#!/usr/bin/env python3
"""Daily summary of sim1 usage. Usage: summarize.py [YYYY-MM-DD]  (default: yesterday, local time Europe/Madrid).
Uses data/system-*.csv + data/procs-*.csv from sample.py; falls back to sysstat (sar) for system CPU if absent."""
import os, sys, csv, datetime, subprocess, collections
BASE = os.path.expanduser('~/sim1-usage')
D, R = os.path.join(BASE, 'data'), os.path.join(BASE, 'reports')
os.makedirs(R, exist_ok=True)
day = sys.argv[1] if len(sys.argv) > 1 else (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
NCPU = os.cpu_count()

def read(p):
    return list(csv.DictReader(open(p))) if os.path.exists(p) else []

sysrows = read(os.path.join(D, f'system-{day}.csv'))
prows = read(os.path.join(D, f'procs-{day}.csv'))
source = 'sampler (5 min)'
samples = []  # (time, interval_s, busy_cores)
if sysrows:
    samples = [(r['time'][11:16], float(r['interval_s']), float(r['busy_cores'])) for r in sysrows]
else:
    sa = f"/var/log/sysstat/sa{day[8:10]}"
    if os.path.exists(sa):
        out = subprocess.run(['sar', '-u', '-f', sa], capture_output=True, text=True,
                             env={**os.environ, 'LC_ALL': 'C'}).stdout.splitlines()
        for l in out:
            f = l.split()
            if len(f) >= 8 and f[1] == 'all' and f[0][:2].isdigit():
                samples.append((f[0][:5], 600.0, (100 - float(f[-1])) * NCPU / 100))
        source = 'sysstat history (10 min, no per-run data)'
if not samples:
    print(f'no data for {day}'); sys.exit(0)

cov_h = sum(s[1] for s in samples) / 3600
busy_ch = sum(s[1] * s[2] for s in samples) / 3600
mean_util = 100 * busy_ch / (cov_h * NCPU)
peak = max(samples, key=lambda s: s[2])
low = min(samples, key=lambda s: s[2])
idle_ch = cov_h * NCPU - busy_ch
# hours with spare capacity (>=1 idle core on average)
spare_h = sum(s[1] for s in samples if NCPU - s[2] >= 1) / 3600

loads = [float(r['load1']) for r in sysrows]
disk = [float(r['disk_free_gb']) for r in sysrows]
memu = [float(r['mem_used_gb']) for r in sysrows]

runs = collections.OrderedDict()
for r in prows:
    k = (r['kind'], r['run_dir'] or '(system / other)')
    g = runs.setdefault(k, {'ch': 0.0, 'peak': 0.0, 'first': r['time'][11:16], 'last': r['time'][11:16], 'cmd': set()})
    c, dt = float(r['cores']), float(r['interval_s'])
    g['ch'] += c * dt / 3600; g['peak'] = max(g['peak'], c); g['last'] = r['time'][11:16]
    g['cmd'].update(r['commands'].split('|'))
order = sorted(runs.items(), key=lambda kv: -kv[1]['ch'])

with open(os.path.join(R, f'{day}-runs.csv'), 'w') as f:
    w = csv.writer(f); w.writerow(['date', 'kind', 'run_dir', 'core_hours', 'mean_cores_while_active', 'peak_cores', 'first_seen', 'last_seen'])
    for (kind, rd), g in order:
        span = sum(float(r['interval_s']) for r in prows if (r['kind'], r['run_dir'] or '(system / other)') == (kind, rd)) / 3600
        w.writerow([day, kind, rd, f"{g['ch']:.2f}", f"{g['ch']/span:.2f}" if span else '', f"{g['peak']:.2f}", g['first'], g['last']])

hdr = ['date', 'source', 'hours_covered', 'mean_util_pct', 'peak_busy_cores', 'peak_time', 'min_busy_cores', 'min_time',
       'busy_core_hours', 'idle_core_hours', 'hours_with_idle_core', 'disk_free_gb_min', 'disk_free_gb_end', 'mem_used_gb_peak']
row = [day, source.split(' ')[0], f'{cov_h:.1f}', f'{mean_util:.1f}', f'{peak[2]:.1f}', peak[0], f'{low[2]:.1f}', low[0],
       f'{busy_ch:.1f}', f'{idle_ch:.1f}', f'{spare_h:.1f}',
       f'{min(disk):.1f}' if disk else '', f'{disk[-1]:.1f}' if disk else '', f'{max(memu):.1f}' if memu else '']
dp = os.path.join(R, 'daily.csv')
old = [r for r in read(dp) if r['date'] != day]
with open(dp, 'w') as f:
    w = csv.writer(f); w.writerow(hdr)
    for r in sorted(old + [dict(zip(hdr, row))], key=lambda r: r['date']):
        w.writerow([r[h] for h in hdr])

L = [f'# sim1 usage, {day} (Europe/Madrid)', '',
     f'Source: {source}; {cov_h:.1f} h covered; {NCPU} cores.', '',
     '| metric | value |', '|---|---|',
     f'| mean CPU utilisation | {mean_util:.1f} % ({mean_util*NCPU/100:.1f} of {NCPU} cores) |',
     f'| peak | {peak[2]:.1f} cores at {peak[0]} |',
     f'| lowest | {low[2]:.1f} cores at {low[0]} |',
     f'| busy core-hours | {busy_ch:.1f} |',
     f'| idle core-hours | {idle_ch:.1f} |',
     f'| hours with at least one idle core | {spare_h:.1f} |']
if loads: L.append(f'| load average (1 min) mean / max | {sum(loads)/len(loads):.1f} / {max(loads):.1f} |')
if memu: L.append(f'| memory used, peak | {max(memu):.1f} GB of 62 |')
if disk: L.append(f'| disk free, min / end of day | {min(disk):.1f} / {disk[-1]:.1f} GB |')
if order:
    L += ['', '## Core-hours by run', '', '| run | kind | core-hours | peak cores | active |', '|---|---|---|---|---|']
    for (kind, rd), g in order:
        if g['ch'] < 0.05: continue
        L.append(f"| `{rd}` | {kind} | {g['ch']:.1f} | {g['peak']:.1f} | {g['first']}–{g['last']} |")
open(os.path.join(R, f'{day}.md'), 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))

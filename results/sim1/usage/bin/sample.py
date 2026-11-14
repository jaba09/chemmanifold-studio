#!/usr/bin/env python3
"""Cheap sim1 usage sampler (read-only /proc reads). Run from cron every 5 min.
Writes one row to data/system-YYYY-MM-DD.csv and per-group rows to data/procs-YYYY-MM-DD.csv.
CPU figures are exact averages over the interval since the previous sample (jiffy deltas)."""
import os, json, time, shutil, datetime
BASE = os.path.expanduser('~/sim1-usage')
STATE = os.path.join(BASE, 'data', 'state.json')
HZ = os.sysconf('SC_CLK_TCK')
now = time.time()
day = datetime.datetime.fromtimestamp(now).strftime('%Y-%m-%d')
ts = datetime.datetime.fromtimestamp(now).strftime('%Y-%m-%dT%H:%M:%S')

def cpu_total():
    f = open('/proc/stat').readline().split()[1:]
    v = list(map(int, f[:8]))
    idle = v[3] + v[4]
    return sum(v), idle

def group_of(comm, cwd):
    c = comm.lower()
    if 'foam' in c or c in ('decomposepar', 'reconstructpar', 'blockmesh', 'snappyhexmesh'):
        kind = 'openfoam'
    elif c in ('mpirun', 'mpiexec', 'hydra_pmi_proxy'):
        return 'other', ''
    elif c.startswith('python') or c in ('mpirun', 'mpiexec', 'hydra_pmi_proxy'):
        kind = 'python'
    else:
        return 'other', ''
    return kind, cwd

procs = {}
for pid in os.listdir('/proc'):
    if not pid.isdigit():
        continue
    try:
        s = open(f'/proc/{pid}/stat').read()
        comm = s[s.index('(') + 1:s.rindex(')')]
        rest = s[s.rindex(')') + 2:].split()
        ticks = int(rest[11]) + int(rest[12])
        start = rest[19]
        try:
            cwd = os.readlink(f'/proc/{pid}/cwd')
        except OSError:
            cwd = ''
        try:
            a0 = open(f'/proc/{pid}/cmdline', 'rb').read().split(b'\0')[0].decode(errors='replace')
            if a0:
                comm = os.path.basename(a0)[:40]
        except OSError:
            pass
        procs[pid] = (comm, cwd, ticks, start)
    except (OSError, ValueError, IndexError):
        continue

tot, idle = cpu_total()
try:
    st = json.load(open(STATE))
except Exception:
    st = None

la = open('/proc/loadavg').read().split()[:3]
mem = {}
for line in open('/proc/meminfo'):
    k, v = line.split(':'); mem[k] = int(v.split()[0])
du = shutil.disk_usage('/')
ncpu = os.cpu_count()

if st and now - st['t'] < 3600:
    dt = now - st['t']
    dtot = tot - st['tot']; didle = idle - st['idle']
    util = 100.0 * (dtot - didle) / dtot if dtot > 0 else 0.0
    groups = {}
    for pid, (comm, cwd, ticks, start) in procs.items():
        prev = st['p'].get(pid)
        d = ticks - prev[0] if prev and prev[1] == start else 0
        if d <= 0:
            continue
        key = group_of(comm, cwd)
        g = groups.setdefault(key, [0, 0, set()])
        g[0] += d; g[2].add(comm)
        if d / HZ / dt > 0.5:
            g[1] += 1
    sysf = os.path.join(BASE, 'data', f'system-{day}.csv')
    new = not os.path.exists(sysf)
    with open(sysf, 'a') as f:
        if new:
            f.write('time,interval_s,ncpu,cpu_util_pct,busy_cores,load1,load5,load15,mem_used_gb,mem_avail_gb,disk_free_gb\n')
        f.write(f"{ts},{dt:.0f},{ncpu},{util:.1f},{util*ncpu/100:.2f},{la[0]},{la[1]},{la[2]},"
                f"{(mem['MemTotal']-mem['MemAvailable'])/1048576:.1f},{mem['MemAvailable']/1048576:.1f},{du.free/1e9:.1f}\n")
    pf = os.path.join(BASE, 'data', f'procs-{day}.csv')
    new = not os.path.exists(pf)
    with open(pf, 'a') as f:
        if new:
            f.write('time,interval_s,kind,run_dir,cores,busy_procs,commands\n')
        for (kind, cwd), (d, nbusy, comms) in sorted(groups.items()):
            cores = d / HZ / dt
            if kind == 'other' and cores < 0.05:
                continue
            f.write(f"{ts},{dt:.0f},{kind},{cwd},{cores:.2f},{nbusy},{'|'.join(sorted(comms))[:80]}\n")

tmp = STATE + '.tmp'
json.dump({'t': now, 'tot': tot, 'idle': idle,
           'p': {pid: [v[2], v[3]] for pid, v in procs.items()}}, open(tmp, 'w'))
os.replace(tmp, STATE)

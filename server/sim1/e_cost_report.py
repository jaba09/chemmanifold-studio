#!/usr/bin/env python3
"""Phase E table from /opt/ofb/runs/E/<case>: s/step (median of steps 11-200, from ExecutionTime), chemistry s/step
(= total - flow-only), cells that get chemistry per step, chemistry cost per cell (CPU-us per cell-step = chem s/step x
ranks / cells), speed-up of chemistry vs DI, and error of the 0.104 s state vs the DI case (hot cells T > 600 K in DI:
mean abs dT, volume-weighted L1 of OH and CO, V(T>1500) ratio).  -> results/sim1/E/cost.md, cost.json"""
import json, re, glob, os
import numpy as np, pandas as pd
R, NP, NCELL = "/opt/ofb/runs/E", 4, 63087
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "results", "sim1", "E")
CNT = re.compile(r"^\[(\d+)\] userChemStep: (\d+) calls, (\d+) advanced, (\d+) frozen, OOD (\d+) \(([0-9.e+-]+) % of advanced\)")
order = ["flow", "di", "treact600", "isat1e-3", "isat1e-4", "isat1e-5", "tix2h_s0", "P_mix"]
label = {"flow": "flow only (chemistry off)", "di": "GA18 DI (seulex 1e-5/1e-10)", "treact600": "DI, Treact 600 K",
         "isat1e-3": "TDAC/ISAT tol 1e-3", "isat1e-4": "TDAC/ISAT tol 1e-4", "isat1e-5": "TDAC/ISAT tol 1e-5",
         "tix2h_s0": "surrogate tix2h_s0 (pure)", "P_mix": "surrogate P_mix, 6 members (pure)"}
def sstep(c):
    e = [float(l.split()[2]) for l in open(f"{R}/{c}/log.run", errors="replace") if l.startswith("ExecutionTime")]
    d = np.diff(e); return float(np.median(d[10:])) if len(d) > 20 else float("nan"), len(e)
def snap(c):
    f = glob.glob(f"{R}/{c}/snap/{c}_t0104.00ms.csv"); return pd.read_csv(f[0]) if f else None
def advanced(c):
    calls = adv = 0
    for l in open(f"{R}/{c}/log.run", errors="replace"):
        m = CNT.search(l)
        if m and int(m.group(5)) <= int(m.group(3)) and int(m.group(3)) + int(m.group(4)) == int(m.group(2)):
            calls += int(m.group(2)); adv += int(m.group(3))
    return NCELL * adv / calls if calls else float("nan")
rows, ref = {}, snap("di")
init = pd.read_csv(f"/opt/ofb/runs/A1r_R2rad/snap/A1r_t0100.00ms.csv")
for c in order:
    if not os.path.exists(f"{R}/{c}/done"): continue
    s, n = sstep(c); rows[c] = dict(case=c, label=label[c], s_step=s, steps=n)
flow = rows.get("flow", {}).get("s_step", float("nan")); di_chem = rows.get("di", {}).get("s_step", np.nan) - flow
for c, r in rows.items():
    if c == "flow": continue
    chem = r["s_step"] - flow
    cells = {"di": NCELL, "treact600": int((init.temperature > 600).sum())}.get(c, advanced(c) if c in ("tix2h_s0", "P_mix") else NCELL)
    r.update(chem_s_step=chem, cells=cells, us_per_cell=chem * NP / cells * 1e6, chem_speedup=di_chem / chem if chem > 0 else float("nan"))
    S = snap(c)
    if S is not None and ref is not None:
        hot = ref.temperature > 600; V = ref["cell-volume"]
        r["absdT_hot_K"] = float(np.average(np.abs(S.temperature - ref.temperature)[hot], weights=V[hot])) if c != "di" else 0.0
        for k in ("oh", "co"):
            r[f"L1_{k}"] = float((V[hot] * np.abs(S[k] - ref[k])[hot]).sum() / (V[hot] * ref[k][hot]).sum()) if c != "di" else 0.0
        r["V1500_ratio"] = float(V[S.temperature > 1500].sum() / V[ref.temperature > 1500].sum())
os.makedirs(OUT, exist_ok=True); json.dump(rows, open(f"{OUT}/cost.json", "w"), indent=1, default=float)
f = lambda v, s="{:.2f}": "-" if v is None or (isinstance(v, float) and not np.isfinite(v)) else s.format(v)
L = ["# Phase E: chemistry cost at matched accuracy (sim1, 4 ranks per case)\n",
     "200 steps of 2e-5 s from the A1r (R2rad) state at t = 0.1 s, same case and radiation as protocol v2. Two cases ran at a time "
     "(8 cores) next to C2's 8, so absolute times include the machine's load; ratios are the point. Chemistry s/step = total - "
     "flow only. Per cell = CPU-us per chemistry cell per step. Error = the 0.104 s state against the DI case (hot cells T > 600 K "
     "in DI, volume-weighted).\n",
     "| Case | s/step | chemistry s/step | cells with chemistry | CPU-us / cell-step | chemistry speed-up vs DI | abs dT hot [K] | L1 OH | L1 CO | V(T>1500) xDI |",
     "|---|---|---|---|---|---|---|---|---|---|"]
for c in order:
    if c not in rows: continue
    r = rows[c]
    L.append(f"| {r['label']} | {f(r['s_step'])} | {f(r.get('chem_s_step'))} | {r.get('cells', '-') if c != 'flow' else '-'} | "
             f"{f(r.get('us_per_cell'), '{:.0f}')} | {f(r.get('chem_speedup'), '{:.1f}x')} | {f(r.get('absdT_hot_K'), '{:.2f}')} | "
             f"{f(100 * r['L1_oh'] if 'L1_oh' in r else None, '{:.1f} %')} | {f(100 * r['L1_co'] if 'L1_co' in r else None, '{:.1f} %')} | {f(r.get('V1500_ratio'), '{:.3f}')} |")
open(f"{OUT}/cost.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))

"""Data tables of the Y(t+dt) vs dY paper, from the two ISANN runs, the DI run and the pair archive.

  python analyse.py <out data dir>
Writes bands.csv (error by temperature band at every snapshot), scales.csv (size of the per-step
increments relative to the loss scales of each output) and copies nothing else: the figures read the
metrics/report JSON files of the runs and the stage-18 benchmark directly.
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

P = Path("/mnt/project-files/chemmanifold")
DI = P / "protocolo-cfd/de-bucle-ood/snap_di"
SNAP = {"Y": Path("/opt/ofb/snap/isann_y"), "dY": Path("/opt/ofb/snap/isann_dy")}
LABEL = {"Y": "isanny", "dY": "isanndy"}
BANDS = [(600, 1000), (1000, 1300), (1300, 1600), (1600, 2300)]
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

rows = []
for f in sorted(DI.glob("di_t*.csv")):
    t = f.stem.split("_t")[1].replace("ms", "")
    di = pd.read_csv(f)
    for run, d in SNAP.items():
        g = d / f"{LABEL[run]}_t{t}ms.csv"
        if not g.exists():
            continue
        r = pd.read_csv(g)
        T = np.maximum(di.temperature, r.temperature)
        V = di["cell-volume"]
        for lo, hi in BANDS:
            m = (T >= lo) & (T < hi)
            dT = (r.temperature - di.temperature)[m]
            row = dict(run=run, t_ms=float(t), T_lo=lo, T_hi=hi, cells=int(m.sum()),
                       mean_abs_dT=float(dT.abs().mean()), mean_dT=float(dT.mean()))
            for s in ("co", "oh", "h", "ch2o"):
                row[f"{s}_ratio"] = float((r[s] * V)[m].sum() / (di[s] * V)[m].sum())
            rows.append(row)
pd.DataFrame(rows).to_csv(OUT / "bands.csv", index=False)

# increment sizes: GA18 pairs of the dY run (CFD states), in the units each loss uses
a = np.load("/opt/ofb/run/isann_dy/isann/archive.npz")
s = json.load(open("/opt/ofb/isann/parent_ood7dy/04_prep/scalers.json"))
sp, lam = s["species"], s["boxcox_lambda"]
bc = lambda y: (np.maximum(y, 0) ** lam - 1) / lam
dY = a["Y_out"] - a["Y_in"]
dyt = bc(a["Y_out"]) - bc(a["Y_in"])
rows = []
for lo, hi in [(600, 1300), (1300, 1600), (1600, 2300)]:
    m = (a["T_in"] >= lo) & (a["T_in"] < hi)
    for k in ("CO", "OH", "H", "CO2", "H2O", "O2"):
        i = sp.index(k)
        rows.append(dict(T_lo=lo, T_hi=hi, species=k, pairs=int(m.sum()), Y_median=float(np.median(a["Y_in"][m, i])),
                         dY_over_sigma_dYp=float(np.median(np.abs(dY[m, i])) / s["sigma_dYp"][i]),
                         dyBC_over_sigma_dy=float(np.median(np.abs(dyt[m, i])) / s["sigma_dy"][i])))
pd.DataFrame(rows).to_csv(OUT / "scales.csv", index=False)
print("ok", OUT)

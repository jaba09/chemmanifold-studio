#!/usr/bin/env python3
"""Compare a steady (LTS) surrogate solution of the burner with a reference (timescale roadmap, test 6b).

Inputs are cell tables: foam_snapshot.py CSVs (OpenFOAM) or a Fluent ASCII export. Cells are matched by
position (nearest cell centre in (x, r)), so an OpenFOAM run can be compared with the Fluent DI solution
on the same mesh (converted) as well as with an OpenFOAM reference.

Reported over the cells where either solution is above --T-hot (600 K):
  flame |dT| (either > 1600 K), hot |dT| mean / p95, T_max of both and the position of T_max,
  volume above 1500 K, and for CO and OH: total amount ratio (mass-weighted) and mean relative error,
  in the flame and separately in lean burnt gas (Z < 0.03, 600-1600 K).
Comparison only; nothing here is training data.

  python3 compare_steady.py --ref di_tau.csv --ref-label "DI tau_cell" --run tix.csv --label tix1 --out report.json
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

W = {"C": 12.011, "H": 1.008, "O": 15.999}
SP = {"ch4": (1, 4, 0), "co": (1, 0, 1), "co2": (1, 0, 2), "o2": (0, 0, 2), "h2o": (0, 2, 1), "h2": (0, 2, 0),
      "oh": (0, 1, 1), "h": (0, 1, 0), "o": (0, 0, 1), "ho2": (0, 1, 2), "h2o2": (0, 2, 2), "ch2": (1, 2, 0),
      "ch2<s>": (1, 2, 0), "ch3": (1, 3, 0), "hco": (1, 1, 1), "ch2o": (1, 2, 1), "ch3o": (1, 3, 1)}


def load(path):
    d = pd.read_csv(path, skipinitialspace=True)
    d.columns = [c.strip() for c in d.columns]
    x = d["axial-coordinate"] if "axial-coordinate" in d else d["x-coordinate"]
    r = d["radial-coordinate"] if "radial-coordinate" in d else d["y-coordinate"]
    out = pd.DataFrame(dict(x=x.values, r=r.values, V=d["cell-volume"].values, T=d["temperature"].values))
    for s in SP:
        out[s] = d[s].values if s in d else 0.0
    # Bilger Z with the case's streams (CH4; air Y_O2 0.233)
    def beta(Y):
        b = 0.0
        for s, (c, h, o) in SP.items():
            w = c * W["C"] + h * W["H"] + o * W["O"]
            b = b + Y[s] * (2 * c + 0.5 * h - o) / w
        return b
    bf = 2 / 16.043 * 1 + 0.5 * 4 / 16.043
    bo = -0.233 * 2 / 31.998
    out["Z"] = (beta(out) - bo) / (bf - bo)
    return out


def metrics(ref, run, T_hot=600, T_flame=1600):
    tree = cKDTree(np.c_[run.x, run.r])
    dist, idx = tree.query(np.c_[ref.x, ref.r])
    b = run.iloc[idx].reset_index(drop=True)
    a = ref
    hot = (a["T"] > T_hot) | (b["T"] > T_hot)
    flame = (a["T"] > T_flame) | (b["T"] > T_flame)
    lean = hot & ~flame & (a["Z"] < 0.03)
    dT = (b["T"] - a["T"]).abs()
    m = dict(match_dist_max_m=float(dist.max()), n_hot=int(hot.sum()), n_flame=int(flame.sum()),
             flame_absdT=float(dT[flame].mean()), flame_bias=float((b["T"] - a["T"])[flame].mean()),
             hot_absdT=float(dT[hot].mean()), hot_p95dT=float(np.percentile(dT[hot], 95)),
             lean_absdT=float(dT[lean].mean()) if lean.any() else None,
             Tmax_ref=float(a["T"].max()), Tmax_run=float(b["T"].max()),
             Tmax_pos_ref=[float(a.x[a["T"].idxmax()]), float(a.r[a["T"].idxmax()])],
             Tmax_pos_run=[float(b.x[b["T"].idxmax()]), float(b.r[b["T"].idxmax()])],
             V1500_ratio=float(a.V[b["T"] > 1500].sum() / max(a.V[a["T"] > 1500].sum(), 1e-30)))
    for s in ("co", "oh"):
        for name, msk in (("flame", flame), ("lean", lean), ("hot", hot)):
            if not msk.any():
                continue
            ya, yb = a[s][msk].values, b[s][msk].values
            v = a.V[msk].values
            m[f"{s}_{name}_ratio"] = float((yb * v).sum() / max((ya * v).sum(), 1e-30))
            fl = max(1e-3 * ya.max(), 1e-12)
            m[f"{s}_{name}_relerr"] = float(np.mean(np.abs(yb - ya) / np.maximum(ya, fl)))
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--ref-label", default="ref")
    ap.add_argument("--run", required=True, nargs="+")
    ap.add_argument("--label", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ref = load(a.ref)
    res = {}
    for i, p in enumerate(a.run):
        lab = a.label[i] if a.label else Path(p).stem
        res[lab] = metrics(ref, load(p))
    Path(a.out).write_text(json.dumps(dict(reference=a.ref_label, ref_file=a.ref, runs=res), indent=1))
    keys = ["flame_absdT", "flame_bias", "hot_absdT", "lean_absdT", "Tmax_ref", "Tmax_run", "V1500_ratio",
            "co_flame_ratio", "co_lean_ratio", "oh_flame_ratio", "oh_lean_ratio"]
    print(f"vs {a.ref_label}")
    for lab, m in res.items():
        print(lab, " ".join(f"{k}={m[k]:.3g}" for k in keys if m.get(k) is not None))


if __name__ == "__main__":
    main()

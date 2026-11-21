#!/usr/bin/env python3
"""Per-regime coverage of the A1r DI hot cells by the tix2c training data (paper 1; stage 16 style).

For every hot cell (T >= 600 K) of the A1r DI snapshots (GA18 with wall radiation), in the model's own OOD
coordinates (Box-Cox z-scored species + z-scored T, isann_lib.features, at the flow dt 2e-5 s): the nearest
training pair, its regime label, and the distance in units of the model's landmark threshold (the UDF calls a
cell far from the data above 1). The DI states are only measured here, never trained on.

    regime_coverage.py --data data/openfoam_tix2c --model .../chemmanifold_model.txt --snap A1r_t*.csv --out DIR
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "openfoam" / "isann"))
sys.path.insert(0, str(REPO))
from isann_lib import features, landmark_threshold  # noqa: E402

NAMES = {0: "reactor_0D", 1: "PaSR", 2: "flamelet_states", 3: "wall_cooled_0D", 4: "recirculation",
         5: "unsteady_flamelets", 6: "equilibrium_tail_0D", 7: "vitiated_ignition", 8: "burnt_relaxation",
         9: "equilibrium_fixed_point", 10: "seeded_PaSR", 11: "seeded_relaxation", 12: "seeded_ignition",
         13: "seeded_cooling", 15: "dilution_cooling", 16: "dynamic_PaSR", 17: "induction_layer", 18: "hot_wall",
         19: "relaxation_flame_dt", 20: "isann_online", 21: "committee"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--snap", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dt", type=float, default=2e-5)
    ap.add_argument("--T-min", type=float, default=600.0)
    a = ap.parse_args()
    sc = json.load(open(Path(a.data) / "04_prep" / "scalers.json"))
    sp = list(sc["species"])
    d = np.load(Path(a.data) / "04_prep" / "dataset.npz")
    tr = ~d["is_val"].astype(bool)
    Xd = features(d["Y_in"][tr], d["T_in"][tr], d["dt"][tr], sc)
    reg = d["regime"][tr]
    thr = landmark_threshold(a.model)
    tree = BallTree(Xd)
    col = {s: s.lower().replace("(s)", "<s>") for s in sp}
    rows = []
    for f in a.snap:
        df = pd.read_csv(f)
        df = df[df["temperature"] >= a.T_min]
        Y = df[[col[s] for s in sp]].to_numpy()
        Y = Y / Y.sum(1, keepdims=True)
        X = features(Y, df["temperature"].to_numpy(), a.dt, sc)
        dist, idx = tree.query(X, k=1)
        rows.append(pd.DataFrame(dict(snap=Path(f).stem, T=df["temperature"].to_numpy(), Z=df["mixture-fraction"].to_numpy(),
                                      vol=df["cell-volume"].to_numpy(), regime=reg[idx[:, 0]], d=dist[:, 0] / thr)))
    c = pd.concat(rows, ignore_index=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    c.to_csv(out / "a1r_cells_nearest_regime.csv.gz", index=False)
    n, nvol = len(c), c["vol"].sum()
    L = ["# Per-regime coverage of the A1r DI hot cells by the tix2c training data\n",
         f"{n:,} hot cells (T >= {a.T_min:.0f} K) of {len(a.snap)} A1r snapshots ({', '.join(Path(f).stem for f in a.snap)}); "
         f"nearest of {tr.sum():,} training pairs in the model's OOD coordinates (isann_lib.features at dt {a.dt:g} s); "
         f"distance in landmark thresholds ({thr:.4g}; > 1 = far from the data in the UDF). DI states are only measured.\n",
         "| regime | label | nearest for cells | (volume-weighted) | median distance | p95 distance | cells > 1 | training share |",
         "|---|---|---|---|---|---|---|---|"]
    out_rows = []
    for g, s in c.groupby("regime"):
        tshare = float((reg == g).mean())
        r = dict(regime=int(g), label=NAMES.get(int(g), str(g)), cells=len(s), share=len(s) / n, vol_share=s["vol"].sum() / nvol,
                 d_median=float(s["d"].median()), d_p95=float(s["d"].quantile(0.95)), far=int((s["d"] > 1).sum()), train_share=tshare)
        out_rows.append(r)
    out_rows.sort(key=lambda r: -r["share"])
    for r in out_rows:
        L.append(f"| {r['regime']} | {r['label']} | {100 * r['share']:.1f} % | {100 * r['vol_share']:.1f} % | {r['d_median']:.3f} | "
                 f"{r['d_p95']:.3f} | {r['far']} | {100 * r['train_share']:.1f} % |")
    L += ["", f"All hot cells: median distance {c['d'].median():.3f}, p95 {c['d'].quantile(0.95):.3f}, "
          f"{(c['d'] > 1).sum()} cells ({100 * (c['d'] > 1).mean():.2f} %) beyond one landmark threshold.", "",
          "## By temperature band (share of the band's cells whose nearest pair is in each of the top regimes)\n"]
    top = [r["regime"] for r in out_rows[:6]]
    c["Tband"] = pd.cut(c["T"], [600, 1000, 1400, 1800, 2400], right=False)
    L.append("| T band [K] | cells | median d | " + " | ".join(NAMES.get(g, str(g)) for g in top) + " |")
    L.append("|---|---|---|" + "---|" * len(top))
    for b, s in c.groupby("Tband", observed=True):
        L.append(f"| {b.left:.0f}-{b.right:.0f} | {len(s):,} | {s['d'].median():.3f} | "
                 + " | ".join(f"{100 * (s['regime'] == g).mean():.1f} %" for g in top) + " |")
    (out / "a1r_regime_coverage.md").write_text("\n".join(L) + "\n")
    pd.DataFrame(out_rows).to_csv(out / "a1r_regime_coverage.csv", index=False)
    print("\n".join(L))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Accuracy and GA18 share of a hybrid surrogate run against the direct-integration (DI) run.

Both runs start from the same state, so at each common snapshot time the two fields differ only
by the chemistry. For each time it reports, over the cells where either run is above --T-hot:

  mean and 95th-percentile |dT|, max |dT|, Tmax of both runs, mean relative error of OH and CO;

and, from the hybrid run's log (userChemStep counters, reportCalls), the share of advanced cells
that were integrated with GA18 (the ODE fallback) in each window between snapshots.

  python3 hybrid_metrics.py --di <DI csv dir> --di-label di --run <hyb csv dir> --label hyb1 \
      --log <hyb run>/log.run --out <dir>

The snapshot CSVs are those of foam_snapshot.py.
"""

import argparse
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load(path):
    with open(path) as f:
        names = f.readline().strip().split(",")
    d = np.loadtxt(path, delimiter=",", skiprows=1)
    return {n: d[:, j] for j, n in enumerate(names)}


def snapshots(d, label):
    out = {}
    for p in Path(d).glob(f"{label}_t*ms.csv"):
        out[round(float(p.stem.split("_t")[-1][:-2]), 2)] = p
    return out


def ga18_share(log):
    """[(time, advanced, fallback)] summed over ranks for each solver time step with a report."""
    rows, t = {}, 0.0
    pat = re.compile(r"userChemStep: (\d+) calls, (\d+) advanced, (\d+) frozen, OOD (\d+).*?ODE fallback (\d+)")
    for line in open(log, errors="replace"):
        if line.startswith("Time = "):
            t = float(line.split()[2])
            continue
        m = pat.search(line)
        if m:
            a = rows.setdefault(t, [0, 0])
            a[0] += int(m.group(2))
            a[1] += int(m.group(5))
    return sorted((k, v[0], v[1]) for k, v in rows.items())


def window_share(rows, t0, t1):
    a = sum(r[1] for r in rows if t0 < r[0] <= t1)
    f = sum(r[2] for r in rows if t0 < r[0] <= t1)
    return f / a if a else float("nan")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--di", required=True)
    ap.add_argument("--di-label", default="di")
    ap.add_argument("--run", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--log", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--T-hot", type=float, default=600.0)
    ap.add_argument("--T-flame", type=float, default=1600.0, help="K; the flame zone of the second |dT| column")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    di, hy = snapshots(a.di, a.di_label), snapshots(a.run, a.label)
    rows = ga18_share(a.log) if a.log else []
    res, prev = [], 0.0
    common = sorted(set(di) & set(hy))
    for t in common:
        A, B = load(di[t]), load(hy[t])
        hot = (A["temperature"] > a.T_hot) | (B["temperature"] > a.T_hot)
        dT = np.abs(A["temperature"] - B["temperature"])[hot]
        r = dict(t_ms=t, hot_cells=int(hot.sum()), mean_abs_dT=float(dT.mean()),
                 p95_abs_dT=float(np.quantile(dT, 0.95)), max_abs_dT=float(dT.max()),
                 Tmax_DI=float(A["temperature"].max()), Tmax_run=float(B["temperature"].max()))
        flame = (A["temperature"] > a.T_flame) | (B["temperature"] > a.T_flame)
        dTf = (B["temperature"] - A["temperature"])[flame]
        r.update(flame_cells=int(flame.sum()), flame_mean_abs_dT=float(np.abs(dTf).mean()),
                 flame_mean_dT=float(dTf.mean()))
        for s in ("oh", "co"):
            ref = A[s][hot]
            m = ref > 1e-3 * ref.max()
            r[f"rel_err_{s}"] = float(np.mean(np.abs(B[s][hot][m] - ref[m]) / ref[m]))
        if rows:
            r["ga18_share"] = window_share(rows, prev * 1e-3, t * 1e-3)
        prev = t
        res.append(r)
    if rows:
        tot_a = sum(x[1] for x in rows)
        tot_f = sum(x[2] for x in rows)
        overall = tot_f / tot_a if tot_a else float("nan")
    else:
        overall = None
    rep = dict(label=a.label, T_hot=a.T_hot, ga18_share_overall=overall, snapshots=res)
    json.dump(rep, open(out / f"metrics_{a.label}.json", "w"), indent=2)
    with open(out / f"metrics_{a.label}.md", "w") as f:
        f.write(f"# {a.label} vs DI (celdas con T > {a.T_hot:.0f} K en alguna de las dos)\n\n")
        if overall is not None:
            f.write(f"Fracción de celdas avanzadas integradas con GA18 (global): {overall:.1%}\n\n")
        f.write(f"Zona de llama: celdas con T > {a.T_flame:.0f} K en alguna de las dos.\n\n")
        f.write("| t [ms] | celdas | media abs dT [K] | p95 [K] | máx [K] | celdas llama | media abs dT llama [K] | "
                "media dT llama [K] | Tmax DI | Tmax run | err OH | err CO | GA18 |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in res:
            f.write(f"| {r['t_ms']:.1f} | {r['hot_cells']} | {r['mean_abs_dT']:.1f} | {r['p95_abs_dT']:.0f} | "
                    f"{r['max_abs_dT']:.0f} | {r['flame_cells']} | {r['flame_mean_abs_dT']:.1f} | {r['flame_mean_dT']:+.1f} | "
                    f"{r['Tmax_DI']:.0f} | {r['Tmax_run']:.0f} | {r['rel_err_oh']:.0%} | "
                    f"{r['rel_err_co']:.0%} | {r.get('ga18_share', float('nan')):.1%} |\n")
    if common:
        t = common[-1]
        A, B = load(di[t]), load(hy[t])
        x, y = A["x-coordinate"], A["y-coordinate"]
        sel = (x > x.min()) & (y < 0.06)
        fig, ax = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
        kw = dict(s=1.5, rasterized=True)
        for k, (v, ttl, cm, lim) in enumerate([(A["temperature"], f"T DI, {t:.1f} ms", "inferno", (300, 2200)),
                                               (B["temperature"], f"T {a.label}", "inferno", (300, 2200)),
                                               (B["temperature"] - A["temperature"], "T run - T DI [K]", "RdBu_r",
                                                (-300, 300))]):
            sc = ax[k].scatter(x[sel], y[sel], c=v[sel], cmap=cm, vmin=lim[0], vmax=lim[1], **kw)
            fig.colorbar(sc, ax=ax[k])
            ax[k].set(title=ttl, ylabel="r [m]")
            ax[k].set_aspect("equal")
        ax[-1].set_xlabel("x [m]")
        fig.tight_layout()
        fig.savefig(out / f"T_DI_vs_{a.label}.png", dpi=130)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()

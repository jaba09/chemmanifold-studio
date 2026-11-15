#!/usr/bin/env python3
"""Mean-field metrics of protocol snapshots (foam_snapshot.py CSVs) against Fluent, as in G1 (results/sim1/A1r/G1.md).

The per-cell average of the snapshots in [t0, t1] stands in for the fieldAverage mean. Metrics as compare_fluent.py:
V(T>1500) (full revolution), Tmax, flame base, x(OH max), OH/CO max, axis Tmax, mean hot |dT| vs Fluent (cells hot in
either, volume-weighted), plus the per-snapshot range of V(T>1500) and Tmax (drift), and the maximum of the NOx
species (NO, NO2, N2O, HCN, ...) when the snapshots have them.

  arc_meanfield.py --set ARC22 <snap dir> <label> 0.15 0.2 --set A1r <snap dir> A1r 0.1 0.1875 \
      --fluent <dat.h5> --out <json>
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

FLUENT_SP = "h2 h o o2 oh h2o ho2 h2o2 ch2 ch2<s> ch3 ch4 co co2 hco ch2o ch3o n2".split()
NOX = ["no", "no2", "n2o", "hcn", "c2h2", "ch3oh", "c2h4", "c2h6"]


def snaps(d, label, t0, t1):
    out = []
    for p in sorted(Path(d).glob(f"{label}_t*ms.csv")):
        m = re.search(r"_t([0-9.]+)ms\.csv$", p.name)
        t = float(m.group(1)) * 1e-3
        if t0 - 1e-9 <= t <= t1 + 1e-9:
            out.append((t, p))
    return out


def metrics(F, x, r, w):
    T = F["temperature"]
    hot = T > 1500
    ax = r < 1.5e-3
    m = {
        "V(T>1500) [cm3]": 1e6 * w[hot].sum(),
        "Tmax [K]": T.max(),
        "flame base x(T>1500) [mm]": 1e3 * x[hot].min() if hot.any() else np.nan,
        "x(OH max) [mm]": 1e3 * x[np.argmax(F["oh"])],
        "OH max": F["oh"].max(),
        "CO max": F["co"].max(),
        "axis Tmax [K]": T[ax].max(),
    }
    return m


def fluent(dat):
    import h5py
    with h5py.File(dat, "r") as f:
        c = f["results/1/phase-1/cells"]
        Y = c["SV_Y"]["1"][()]
        out = {"temperature": c["SV_T"]["1"][()]}
    for i, s in enumerate(FLUENT_SP):
        out[s] = Y[:, i]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", nargs=5, action="append", metavar=("NAME", "DIR", "LABEL", "T0", "T1"), required=True)
    ap.add_argument("--fluent")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res, geo, Fl = {}, None, None
    for name, d, label, t0, t1 in a.set:
        S = snaps(d, label, float(t0), float(t1))
        if not S:
            res[name] = {"error": f"no snapshots of {label} in {d} for {t0}-{t1} s"}
            continue
        acc, series = None, []
        for t, p in S:
            df = pd.read_csv(p)
            if geo is None:
                geo = (df["x-coordinate"].to_numpy(), df["y-coordinate"].to_numpy(), df["cell-volume"].to_numpy() * 72.0)
            x, r, w = geo
            cols = ["temperature", "oh", "co"] + [s for s in NOX if s in df]
            hot = df["temperature"].to_numpy() > 1500
            series.append({"t": t, "V1500": 1e6 * w[hot].sum(), "Tmax": float(df["temperature"].max()),
                           **{f"{s} max": float(df[s].max()) for s in NOX if s in df}})
            v = df[cols]
            acc = v.copy() if acc is None else acc + v
        M = {k: (acc[k] / len(S)).to_numpy() for k in acc}
        x, r, w = geo
        m = metrics(M, x, r, w)
        for s in NOX:
            if s in M:
                m[f"{s.upper()} max (mean field)"] = float(M[s].max())
                m[f"{s.upper()} max (instantaneous, over window)"] = max(q[f"{s} max"] for q in series)
        if a.fluent:
            if Fl is None:
                Fl = fluent(a.fluent)
            dT = M["temperature"] - Fl["temperature"]
            h = (Fl["temperature"] > 1000) | (M["temperature"] > 1000)
            m["mean hot |dT| vs Fluent [K]"] = float(np.abs(dT[h]).mean())
            m["mean hot |dT| vs Fluent, volume-weighted [K]"] = float(np.average(np.abs(dT[h]), weights=w[h]))
        Vs = [q["V1500"] for q in series]; Ts = [q["Tmax"] for q in series]
        m["window"] = f"{S[0][0]:.4f}-{S[-1][0]:.4f} s, {len(S)} snapshots"
        m["V(T>1500) range over snapshots [cm3]"] = [float(min(Vs)), float(max(Vs))]
        m["Tmax range over snapshots [K]"] = [float(min(Ts)), float(max(Ts))]
        res[name] = {k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in m.items()}
        res[name]["series"] = series
    if a.fluent:
        x, r, w = geo
        res["Fluent"] = {k: float(v) for k, v in metrics(Fl, x, r, w).items()}
    Path(a.out).write_text(json.dumps(res, indent=1))
    keys = [k for k in res[a.set[0][0]] if k != "series"]
    names = list(res)
    print(f"{'metric':48s}" + "".join(f"{n:>22s}" for n in names))
    for k in keys:
        row = f"{k:48s}"
        for n in names:
            v = res[n].get(k, "")
            row += f"{v:>22.5g}" if isinstance(v, float) else f"{str(v):>22s}"
        print(row)


if __name__ == "__main__":
    main()

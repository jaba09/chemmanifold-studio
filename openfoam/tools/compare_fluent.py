#!/usr/bin/env python3
"""Compare an OpenFOAM burner time directory with a Fluent .dat.h5 solution of the same mesh.

The mesh converter (fluent_h5_to_foam.py) keeps the Fluent cell order, so cell i matches cell i
directly. The OpenFOAM fields must be ASCII (run foamFormatConvert -time <t> first) and the case
needs <time>/C (postProcess -func writeCellCentres -time <t>).

Usage:
    python compare_fluent.py <case> <time> <solution.dat.h5> <out.png> [--label OpenFOAM]

Prints a table of flame metrics for both solutions and their cell-by-cell differences, and saves
T, OH and CO maps (Fluent on top, OpenFOAM below; x up the axis drawn left to right).
"""
import argparse
import os
import re
import sys

import h5py
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloud"))
from foamread import read_field  # noqa: E402

SPECIES = "h2 h o o2 oh h2o ho2 h2o2 ch2 ch2<s> ch3 ch4 co co2 hco ch2o ch3o n2".split()


def fluent(dat):
    with h5py.File(dat, "r") as f:
        c = f["results/1/phase-1/cells"]
        g = lambda k: c[k]["1"][()]
        Y = g("SV_Y")
        out = {"T": g("SV_T"), "Ux": g("SV_U"), "Ur": g("SV_V")}
    for i, s in enumerate(SPECIES):
        out[s.upper().replace("<S>", "(S)")] = Y[:, i]
    return out


def foam(case, t):
    d = os.path.join(case, t)
    out = {k: read_field(os.path.join(d, k)) for k in ("T", "OH", "CO", "CH4", "O2", "CO2", "H2")}
    U = read_field(os.path.join(d, "U"))
    C = read_field(os.path.join(d, "C"))
    r = np.hypot(C[:, 1], C[:, 2])
    out["Ux"] = U[:, 0]
    out["Ur"] = (U[:, 1] * C[:, 1] + U[:, 2] * C[:, 2]) / np.maximum(r, 1e-30)
    return out, C[:, 0], r


def metrics(F, x, r, w):
    T = F["T"]
    hot = T > 1500
    ax = r < 1.5e-3                                   # cells on the axis
    xa = x[ax]; Ta = T[ax]
    o = np.argsort(xa); xa, Ta = xa[o], Ta[o]
    # flame length: last axial position with T above 1500 K; lift-off: lowest x of any cell above 1500 K
    m = {
        "Tmax [K]": T.max(),
        "x(Tmax) [mm]": 1e3 * x[np.argmax(T)],
        "r(Tmax) [mm]": 1e3 * r[np.argmax(T)],
        "axis Tmax [K]": Ta.max(),
        "x(axis Tmax) [mm]": 1e3 * xa[np.argmax(Ta)],
        "flame length T>1500 on axis [mm]": 1e3 * xa[Ta > 1500].max() if (Ta > 1500).any() else np.nan,
        "flame base x T>1500 [mm]": 1e3 * x[hot].min() if hot.any() else np.nan,
        "hot volume T>1500 [cm3]": 1e6 * w[hot].sum(),
        "OH max": F["OH"].max(),
        "CO max": F["CO"].max(),
        "x(OH max) [mm]": 1e3 * x[np.argmax(F["OH"])],
        "Ux max [m/s]": F["Ux"].max(),
    }
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case"); ap.add_argument("time"); ap.add_argument("dat"); ap.add_argument("png")
    ap.add_argument("--label", default="OpenFOAM")
    a = ap.parse_args()

    O, x, r = foam(a.case, a.time)
    Fl = fluent(a.dat)
    if len(Fl["T"]) != len(x):
        raise SystemExit(f"cell count differs: OpenFOAM {len(x)}, Fluent {len(Fl['T'])}")
    V = read_field(os.path.join(a.case, a.time, "V")) if os.path.exists(os.path.join(a.case, a.time, "V")) else None
    w = V * 360.0 / 5.0 if V is not None else np.ones_like(x)   # full-revolution volume of the 5 deg wedge

    mf, mo = metrics(Fl, x, r, w), metrics(O, x, r, w)
    print(f"{'metric':36s} {'Fluent':>12s} {a.label:>12s}")
    for k in mf:
        print(f"{k:36s} {mf[k]:12.5g} {mo[k]:12.5g}")
    dT = O["T"] - Fl["T"]
    hot = (Fl["T"] > 1000) | (O["T"] > 1000)
    print(f"\ncell-by-cell T difference ({a.label} - Fluent): mean |dT| in hot cells {np.abs(dT[hot]).mean():.1f} K, "
          f"volume-weighted {np.average(np.abs(dT[hot]), weights=w[hot]):.1f} K, max |dT| {np.abs(dT).max():.0f} K")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.tri as mtri
    tri = mtri.Triangulation(x, r)
    p = np.stack([x[tri.triangles], r[tri.triangles]], -1)
    e = np.max([np.hypot(*(p[:, i] - p[:, (i + 1) % 3]).T) for i in range(3)], 0)
    tri.set_mask(e > 0.006)
    fields = [("T", "T [K]", np.linspace(300, 2100, 19), "inferno"),
              ("OH", "Y_OH", np.linspace(0, max(Fl["OH"].max(), O["OH"].max()), 15), "viridis"),
              ("CO", "Y_CO", np.linspace(0, max(Fl["CO"].max(), O["CO"].max()), 15), "viridis")]
    fig, axs = plt.subplots(len(fields), 2, figsize=(13, 2.6 * len(fields)), sharex=True, sharey=True)
    for row, (k, lab, lev, cm) in zip(axs, fields):
        for a_, (name, F) in zip(row, (("Fluent", Fl), (a.label, O))):
            cs = a_.tricontourf(tri, F[k], levels=lev, cmap=cm, extend="both")
            a_.set_aspect("equal"); a_.set_xlim(0, 0.30); a_.set_ylim(0, 0.06)
            a_.set_title(f"{name}: {lab}, max {F[k].max():.4g}", fontsize=9)
        fig.colorbar(cs, ax=row, fraction=0.02)
    for a_ in axs[-1]:
        a_.set_xlabel("x [m] (up the axis)")
    for a_ in axs[:, 0]:
        a_.set_ylabel("r [m]")
    fig.savefig(a.png, dpi=130, bbox_inches="tight")
    print("saved", a.png)


if __name__ == "__main__":
    main()

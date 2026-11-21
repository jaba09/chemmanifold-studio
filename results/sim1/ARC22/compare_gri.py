#!/usr/bin/env python3
"""Cell-by-cell comparison of OpenFOAM mean fields (results/sim1/ARC22/fields/*.npz, row i = Fluent cell i+1)
with the Fluent DI solutions of the same mesh: GRI-Mech 3.0 (benchmark) and GA18.
    compare_gri.py <fluent_GRI.dat.h5> <fluent_GA18.dat.h5> <fields dir> [out dir]
Writes compare_gri.md (metric table + pairwise differences) and compare_gri_*.png into out dir."""
import os, sys
import numpy as np, h5py
GA = "h2 h o o2 oh h2o ho2 h2o2 ch2 ch2<s> ch3 ch4 co co2 hco ch2o ch3o n2".split()
GRI = ("h2 h o o2 oh h2o ho2 h2o2 c ch ch2 ch2<s> ch3 ch4 co co2 hco ch2o ch2oh ch3o ch3oh c2h c2h2 c2h3 c2h4 "
       "c2h5 c2h6 hcco ch2co hccoh n nh nh2 nh3 nnh no no2 n2o hno cn hcn h2cn hcnn hcno hocn hnco nco ar c3h7 "
       "c3h8 ch2cho ch3cho n2").split()
SP = ["OH", "CO", "CO2", "H2", "CH4", "NO", "NO2", "N2O", "HCN", "C2H2", "CH3OH"]


def fluent(fn, names):
    with h5py.File(fn) as f:
        c = f["results/1/phase-1/cells"]; Y = c["SV_Y"]["1"][()]
        d = {"T": c["SV_T"]["1"][()]}
    for i, s in enumerate(names):
        d[s.upper().replace("<S>", "(S)")] = Y[:, i]
    return d


def foam(fn):
    z = np.load(fn); d = {"T": z["T"].astype(float)}
    for k in z.files:
        if k.startswith("Y_"): d[k[2:]] = z[k].astype(float)
    return d, z["x"].astype(float), z["r"].astype(float), z["V"].astype(float) * 72.0  # 5 deg wedge -> 360


def metrics(d, x, r, V):
    T = d["T"]; hot = T > 1500; ax = r < 1.5e-3
    m = {"Tmax [K]": T.max(), "x(Tmax) [mm]": 1e3 * x[T.argmax()], "r(Tmax) [mm]": 1e3 * r[T.argmax()],
         "V(T>1500) [cm3]": 1e6 * V[hot].sum(), "V(T>1800) [cm3]": 1e6 * V[T > 1800].sum(),
         "V(T>2000) [cm3]": 1e6 * V[T > 2000].sum(), "flame base x(T>1500) [mm]": 1e3 * x[hot].min(),
         "axis Tmax [K]": T[ax].max(), "x(OH max) [mm]": 1e3 * x[d["OH"].argmax()]}
    for s in SP:
        m["%s max" % s] = d[s].max() if s in d else np.nan
    return m


def diff(a, b, V):
    hot = (a["T"] > 1500) | (b["T"] > 1500); warm = (a["T"] > 600) | (b["T"] > 600)
    dT = np.abs(a["T"] - b["T"])
    out = {"mean hot |dT| [K] (vol-w)": np.average(dT[hot], weights=V[hot]),
           "mean |dT| T>600 [K] (vol-w)": np.average(dT[warm], weights=V[warm]), "max |dT| [K]": dT.max()}
    for s in SP:
        if s in a and s in b:
            sc = max(a[s][warm].max(), b[s][warm].max())
            out["%s rel L1 (T>600)" % s] = np.average(np.abs(a[s] - b[s])[warm], weights=V[warm]) / \
                np.average(np.maximum(a[s], b[s])[warm], weights=V[warm])
    return out


def main():
    gri_fn, ga_fn, fdir = sys.argv[1:4]; out = sys.argv[4] if len(sys.argv) > 4 else os.path.dirname(os.path.abspath(__file__))
    F = {"Fluent GRI": fluent(gri_fn, GRI), "Fluent GA18": fluent(ga_fn, GA)}
    x = r = V = None
    for lab, fn in [("OF GA18 A1r mean", "a1r_mean_0.1-0.1875.npz"), ("OF ARC22 mean", "arc22_mean_0.15-0.185.npz"),
                    ("OF ARC22 early mean", "arc22_mean_0.125-0.15.npz")]:
        p = os.path.join(fdir, fn)
        if os.path.exists(p):
            F[lab], x, r, V = foam(p)
    if "OF ARC22 mean" in F: F.pop("OF ARC22 early mean", None)
    labs = list(F)
    M = {l: metrics(F[l], x, r, V) for l in labs}
    L = ["# ARC_GRI30_NOx22 OpenFOAM DI vs Fluent DI (GRI-Mech 3.0 benchmark) and GA18", "",
         "| metric | " + " | ".join(labs) + " |", "|---|" + "---|" * len(labs)]
    for k in M[labs[0]]:
        L.append("| %s | " % k + " | ".join("%.4g" % M[l][k] for l in labs) + " |")
    pairs = [(a, b) for a, b in [("OF ARC22 mean", "Fluent GRI"), ("OF ARC22 early mean", "Fluent GRI"),
             ("OF GA18 A1r mean", "Fluent GA18"), ("Fluent GRI", "Fluent GA18"), ("OF ARC22 mean", "OF GA18 A1r mean"),
             ("OF ARC22 early mean", "OF GA18 A1r mean"), ("OF GA18 A1r mean", "Fluent GRI")] if a in F and b in F]
    D = {p: diff(F[p[0]], F[p[1]], V) for p in pairs}
    L += ["", "Cell-by-cell differences (volume-weighted; rel L1 = mean |a-b| / mean max(a,b) over cells above 600 K):", "",
          "| | " + " | ".join("%s vs %s" % p for p in pairs) + " |", "|---|" + "---|" * len(pairs)]
    for k in D[pairs[0]]:
        L.append("| %s | " % k + " | ".join("%.3g" % D[p].get(k, np.nan) for p in pairs) + " |")
    open(os.path.join(out, "compare_gri.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, matplotlib.patches
        from matplotlib.tri import Triangulation
        X, R = 1e3 * x, 1e3 * r
        tri = Triangulation(X, R)
        t = tri.triangles
        edge = np.max([np.hypot(X[t[:, i]] - X[t[:, (i + 1) % 3]], R[t[:, i]] - R[t[:, (i + 1) % 3]]) for i in range(3)], axis=0)
        inside = ((X[t] < 125) & (R[t] < 85)).all(1)
        tri.set_mask(~inside | (edge > 3.0))   # no triangles across the pot / outside the zoom
        for fld, lim in [("T", (300, 2150)), ("NO", None), ("OH", None), ("CO", None)]:
            show = [l for l in labs if fld in F[l]]
            fig, axs = plt.subplots(len(show), 1, figsize=(7, 2.3 * len(show)), sharex=True, constrained_layout=True)
            axs = np.atleast_1d(axs)
            zoom = (X < 125) & (R < 85)
            vmax = lim[1] if lim else max(F[l][fld][zoom].max() for l in show)
            for a, l in zip(axs, show):
                c = a.tricontourf(tri, np.clip(F[l][fld], lim[0] if lim else 0, vmax),
                                  levels=np.linspace(lim[0] if lim else 0, vmax, 41), cmap="inferno")
                a.add_patch(matplotlib.patches.Rectangle((50, 0), 75, 50, color="0.75"))   # pot
                a.set_xlim(0, 120); a.set_ylim(0, 80); a.set_aspect("equal")
                a.set_title(l, fontsize=9); a.set_ylabel("r [mm]")
            axs[-1].set_xlabel("x [mm] (axis, up)")
            fig.colorbar(c, ax=axs, shrink=0.8, label=fld + (" [K]" if fld == "T" else " mass fraction"))
            fig.savefig(os.path.join(out, "compare_gri_%s.png" % fld), dpi=130); plt.close(fig)
    except Exception as e:
        print("plots skipped:", e)


if __name__ == "__main__":
    main()

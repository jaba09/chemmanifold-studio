#!/usr/bin/env python3
"""Figures of the ARC_GRI30_NOx22 Combustion and Flame preprint (papers/arc22-cnf/figs).

  fig_1d_errors.pdf   S_L and post-flame NO error vs phi, 1 and 5 atm (original reduction, VALIDATION_REPORT.md)
  fig_burner_maps.pdf T and NO, OpenFOAM GRI-Mech 3.0 vs ARC22 (mean 0.125-0.15 s) and their T difference
  fig_ignition.pdf    domain Tmax vs time, ignition leg 0-5 ms: GRI-Mech 3.0, ARC22, GA18 (A2r)

  make_figs.py [--fields results/sim1/ARC22/fields] [--runs /opt/ofb/runs]
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "figs"
REPO = HERE.parents[2]
plt.rcParams.update({"font.size": 9, "font.family": "serif", "axes.linewidth": 0.6, "savefig.bbox": "tight"})

# VALIDATION_REPORT.md (original reduction): p, phi, S_L GRI, S_L ARC [cm/s], post-flame NO GRI, ARC [ppm]
FLAMES = [(1, 0.6, 11.54, 11.39, 2.00, 2.00), (1, 0.7, 19.53, 19.40, 6.55, 6.59), (1, 0.8, 27.43, 27.29, 20.13, 20.29),
          (1, 0.9, 34.04, 33.85, 51.47, 51.92), (1, 1.0, 38.09, 37.85, 80.78, 81.37), (1, 1.1, 38.45, 38.15, 71.88, 72.67),
          (1, 1.2, 33.67, 33.28, 68.94, 70.49), (1, 1.3, 23.73, 23.49, 85.48, 88.11), (5, 0.7, 8.36, 8.23, 5.01, 5.06),
          (5, 0.8, 12.89, 12.78, 17.16, 17.37), (5, 0.9, 16.74, 16.64, 51.83, 52.58), (5, 1.0, 19.13, 18.99, 95.03, 96.08),
          (5, 1.1, 18.88, 18.68, 83.09, 84.85), (5, 1.2, 14.36, 14.07, 90.74, 94.13), (5, 1.3, 9.42, 8.98, 38.37, 43.52)]


def fig_1d():
    d = np.array(FLAMES)
    fig, ax = plt.subplots(1, 2, figsize=(6.6, 2.5))
    for p, c, m in ((1, "0.55", "o"), (5, "C0", "s")):
        s = d[d[:, 0] == p]
        ax[0].plot(s[:, 1], 100 * (s[:, 3] - s[:, 2]) / s[:, 2], "-", color=c, marker=m, ms=3.5, lw=1.2, label=f"{p} atm")
        ax[1].plot(s[:, 1], 100 * (s[:, 5] - s[:, 4]) / s[:, 4], "-", color=c, marker=m, ms=3.5, lw=1.2, label=f"{p} atm")
    ax[0].axhline(-5, ls="--", lw=0.7, color="0.4"); ax[0].text(0.61, -4.8, "target $-5$ %", fontsize=7, color="0.3")
    ax[1].axhline(4, ls="--", lw=0.7, color="0.4"); ax[1].text(0.61, 4.4, "target +4 % (1 atm)", fontsize=7, color="0.3")
    for a, t in zip(ax, ("(a) laminar flame speed", "(b) post-flame NO")):
        a.axhline(0, lw=0.5, color="k"); a.set_xlabel(r"equivalence ratio $\phi$"); a.set_title(t, fontsize=9)
    ax[0].set_ylabel("ARC error vs GRI-Mech 3.0 [%]"); ax[0].legend(frameon=False, fontsize=8)
    fig.savefig(OUT / "fig_1d_errors.pdf")


def fig_maps(F):
    a = np.load(F / "arc22_ext_mean_0.2-0.3.npz"); g = np.load(F / "gri53_ext_mean_0.2-0.3.npz")
    x, r = 1e3 * a["x"].astype(float), 1e3 * a["r"].astype(float)
    tri = mtri.Triangulation(x, r)
    p = np.stack([x[tri.triangles], r[tri.triangles]], -1)
    e = np.max([np.hypot(*(p[:, i] - p[:, (i + 1) % 3]).T) for i in range(3)], 0)
    pot = (x[tri.triangles].mean(1) > 50) & (x[tri.triangles].mean(1) < 200) & (r[tri.triangles].mean(1) < 50)
    tri.set_mask((e > 6) | pot)
    fig, axs = plt.subplots(3, 2, figsize=(6.8, 5.4))
    lev_T = np.linspace(300, 2150, 38); nmax = 1e6 * max(a["Y_NO"].max(), g["Y_NO"].max()); lev_N = np.linspace(0, nmax, 30)
    panels = [(g["T"], lev_T, "inferno", "(a) T [K], OpenFOAM GRI-Mech 3.0", [300, 1000, 1500, 2000]),
              (a["T"], lev_T, "inferno", "(b) T [K], OpenFOAM ARC22", [300, 1000, 1500, 2000]),
              (1e6 * g["Y_NO"], lev_N, "viridis", r"(c) $10^6\,Y_{\rm NO}$, GRI-Mech 3.0", [0, 100, 200]),
              (1e6 * a["Y_NO"], lev_N, "viridis", r"(d) $10^6\,Y_{\rm NO}$, ARC22", [0, 100, 200]),
              (a["T"].astype(float) - g["T"], np.linspace(-20, 20, 21), "RdBu_r", "(e) T, ARC22 $-$ GRI-Mech 3.0 [K]", [-20, -10, 0, 10, 20])]
    for k, (fv, lev, cm, t, tk) in enumerate(panels):
        ax = axs.flat[k]
        cs = ax.tricontourf(tri, fv, levels=lev, cmap=cm, extend="both")
        ax.add_patch(plt.Rectangle((50, 0), 150, 50, fc="0.85", ec="k", lw=0.5))
        ax.set_xlim(0, 56); ax.set_ylim(0, 22); ax.set_aspect("equal")
        ax.set_title(t, fontsize=8, loc="left"); ax.set_ylabel("r [mm]", fontsize=8); ax.set_xlabel("x [mm]", fontsize=8)
        cb = fig.colorbar(cs, ax=ax, fraction=0.03, pad=0.02, ticks=tk); cb.ax.tick_params(labelsize=7)
    h = (a["T"] > 1500) | (g["T"] > 1500); V = a["V"].astype(float)
    dT = np.average(np.abs(a["T"].astype(float) - g["T"])[h], weights=V[h])
    axs.flat[5].axis("off")
    axs.flat[5].text(0.02, 0.5, "Mean of the snapshots 0.2-0.3 s\n(41 each), same mesh, same start,\nsame radiation and pot walls.\n"
                     f"Hot-cell mean |dT| = {dT:.1f} K\nThe pot bottom (grey) is at x = 50 mm.", fontsize=8, va="center")
    fig.subplots_adjust(wspace=0.45, hspace=0.35)
    fig.savefig(OUT / "fig_burner_maps.pdf")


def tmax(case):
    rows = []
    for f in sorted(Path(case, "postProcessing", "minMaxT").glob("*/fieldMinMax.dat")):
        for l in open(f):
            s = l.split("\t")
            if len(s) > 5 and s[1].strip() == "T":
                rows.append((float(s[0]), float(s[5])))
    rows = sorted(set(rows))
    return np.array(rows)


def fig_ign(R):
    fig, ax = plt.subplots(figsize=(3.3, 2.5))
    for lab, case, st in (("GRI-Mech 3.0", R / "arc22/gri/ign", dict(color="k", lw=1.6)),
                          ("ARC22", R / "arc22/ign", dict(color="C0", lw=1.0, ls="--")),
                          ("GA18 (A2r)", R / "A2r_ign", dict(color="0.55", lw=1.0))):
        d = tmax(case); d = d[d[:, 0] <= 0.0051]
        ax.plot(1e3 * d[:, 0], d[:, 1], label=lab, **st)
    ax.axhline(1600, ls=":", lw=0.7, color="0.4")
    ax.set_xlabel("t [ms]"); ax.set_ylabel(r"domain $T_{\max}$ [K]"); ax.legend(frameon=False, fontsize=8)
    fig.savefig(OUT / "fig_ignition.pdf")


def fig_domain(F):
    """Sketch of the burner domain: every cell centre (grey), the flame (mean T of OF GRI-Mech 3.0), labels."""
    g = np.load(F / "gri53_ext_mean_0.2-0.3.npz")
    x, r, T = 1e3 * g["x"].astype(float), 1e3 * g["r"].astype(float), g["T"].astype(float)
    fig, ax = plt.subplots(figsize=(6.8, 2.4))
    ax.scatter(x, r, s=0.15, c="0.75", lw=0, rasterized=True)
    hot = T > 600
    sc = ax.scatter(x[hot], r[hot], s=0.4, c=T[hot], cmap="inferno", vmin=600, vmax=2100, lw=0, rasterized=True)
    ax.add_patch(plt.Rectangle((50, 0), 150, 50, fc="0.55", ec="k", lw=0.6))
    ax.plot([85, 220, 370, 519], [75, 75, 20, 20], "k-", lw=1.4)
    kw = dict(fontsize=7, arrowprops=dict(arrowstyle="->", lw=0.6))
    ax.text(125, 22, "pot", fontsize=8, color="w", ha="center")
    ax.annotate("CH$_4$ jet, $r<2.5$ mm", xy=(1, 1.5), xytext=(8, -26), **kw)
    ax.annotate("air coflow, $50<r<75$ mm", xy=(1, 62), xytext=(8, 128), **kw)
    ax.annotate("flame", xy=(38, 22), xytext=(100, 108), color="C3", **kw)
    ax.annotate("hood (baffle) and chimney", xy=(300, 46), xytext=(260, 108), **kw)
    ax.annotate("outlets", xy=(519, 80), xytext=(440, 128), **kw)
    ax.text(300, -26, "axis of symmetry, r = 0", fontsize=7, ha="center")
    ax.set_xlim(-5, 525); ax.set_ylim(-34, 142); ax.set_aspect("equal")
    ax.set_xlabel("x [mm] (axis, up)"); ax.set_ylabel("r [mm]")
    cb = fig.colorbar(sc, ax=ax, fraction=0.015, pad=0.01); cb.set_label("T [K]", fontsize=7); cb.ax.tick_params(labelsize=6)
    fig.savefig(OUT / "fig_domain.pdf", dpi=300)


def fig_qss(edges_json):
    """QSS coupling graph: 21 radicals in three chemical sub-blocks, 90 linear couplings (from arc_gri30_nox22_data.h)."""
    import json
    d = json.load(open(edges_json)); names = d["names"]; E = [tuple(e) for e in d["edges"]]
    blocks = [("C1/C2 hydrocarbon and oxy radicals", ["C", "CH", "CH2", "CH2(S)", "HCO", "CH2OH", "CH3O", "C2H3", "C2H5", "HCCO"]),
              ("amine, diazenyl, nitroso", ["N", "NH", "NH2", "NNH", "HNO"]),
              ("cyano, isocyanate", ["CN", "H2CN", "HCNO", "HOCN", "HNCO", "NCO"])]
    pos, blk = {}, {}
    centres = [(-1.7, 0.0), (1.7, 1.1), (1.7, -1.1)]
    radii = [0.95, 0.55, 0.6]
    for b, ((lab, sp), c, rad) in enumerate(zip(blocks, centres, radii)):
        for i, n in enumerate(sp):
            a = np.pi / 2 - 2 * np.pi * i / len(sp)
            pos[names.index(n)] = (c[0] + rad * np.cos(a), c[1] + rad * np.sin(a)); blk[names.index(n)] = b
    fig, ax = plt.subplots(figsize=(6.6, 3.9))
    nin = sum(blk[i] == blk[j] for i, j in E)
    for i, j in E:
        (x0, y0), (x1, y1) = pos[i], pos[j]
        same = blk[i] == blk[j]
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", lw=0.5 if same else 0.7, color="0.6" if same else "C0",
                                    shrinkA=9, shrinkB=9, mutation_scale=6))
    for k, (x0, y0) in pos.items():
        lab = names[k].replace("2", "$_2$").replace("3", "$_3$").replace("5", "$_5$")
        ax.text(x0, y0, lab, ha="center", va="center", fontsize=7,
                bbox=dict(boxstyle="round,pad=0.25", fc="w", ec=["C3", "C2", "C1"][blk[k]], lw=0.8))
    for b, ((lab, sp), c, rad) in enumerate(zip(blocks, centres, radii)):
        yl = c[1] - rad - 0.38 if b == 2 else c[1] + rad + 0.28
        ax.text(c[0] + (0.55 if b == 2 else 0), yl, lab, ha="center", fontsize=7.5, style="italic")
    ax.text(-0.1, -1.95, f"{len(E)} linear couplings $k\\to i$ ({nin} within a sub-block, grey; {len(E) - nin} between sub-blocks, blue)",
            ha="center", fontsize=7)
    ax.set_xlim(-2.9, 2.6); ax.set_ylim(-2.0, 2.2); ax.set_aspect("equal"); ax.axis("off")
    fig.savefig(OUT / "fig_qss_graph.pdf")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fields", default=str(REPO / "results/sim1/ARC22/fields"))
    ap.add_argument("--runs", default="/opt/ofb/runs")
    ap.add_argument("--qss", default=str(HERE / "qss_edges.json"), help="from scripts/qss_graph.py")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    fig_1d(); fig_ign(Path(a.runs)); fig_maps(Path(a.fields)); fig_domain(Path(a.fields)); fig_qss(a.qss)
    print("figures in", OUT)

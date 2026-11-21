#!/usr/bin/env python3
"""G1 figures from g1_report.sh output: drift series (Tmax, V(T>1500), flame base, hot |dT| vs t, with Fluent)
and the T RMS map from TPrime2Mean.   g1_figures.py <run>/g1 <out dir>"""
import glob, os, re, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "openfoam", "tools", "cloud"))
from foamread import read_field  # noqa: E402

G, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
KEYS = {"Tmax [K]": "Tmax", "hot volume T>1500 [cm3]": "V", "flame base x T>1500 [mm]": "base", "CO max": "COmax", "OH max": "OHmax"}
def parse(p):
    d, f = {}, {}
    for line in open(p):
        for k, s in KEYS.items():
            if line.startswith(k):
                a = line[len(k):].split(); f[s], d[s] = float(a[0]), float(a[1])
        m = re.search(r"mean \|dT\| in hot cells ([\d.]+) K, volume-weighted ([\d.]+) K", line)
        if m: d["dT"], d["dTv"] = float(m.group(1)), float(m.group(2))
    return d, f
rows = []
for p in glob.glob(f"{G}/compare_0*.txt"):
    t = float(re.search(r"compare_([\d.e-]+)\.txt", p).group(1)); d, fl = parse(p); rows.append((t, d))
rows.sort(); t = np.array([r[0] for r in rows]) * 1e3
mean, fl = parse(f"{G}/compare_mean.txt")
with open(f"{OUT}/drift.csv", "w") as o:
    o.write("t_ms,Tmax_K,V1500_cm3,base_mm,COmax,OHmax,hot_absdT_K,hot_absdT_volw_K\n")
    for tt, (_, d) in zip(t, rows):
        o.write(f"{tt:.2f},{d['Tmax']:.1f},{d['V']:.2f},{d['base']:.2f},{d['COmax']:.5f},{d['OHmax']:.6f},{d['dT']:.1f},{d['dTv']:.1f}\n")
fig, ax = plt.subplots(2, 2, figsize=(10, 6.5), sharex=True)
for a, k, lab in zip(ax.flat, ["Tmax", "V", "base", "dT"], ["domain Tmax [K]", "V(T>1500 K) [cm3]", "flame base x [mm]", "mean hot-cell |dT| vs Fluent [K]"]):
    a.plot(t, [r[1][k] for r in rows], "o-", ms=3, color="#c0392b", label="R2 snapshots")
    a.axhline(mean[k], color="#c0392b", ls="--", lw=1, label="R2 mean field")
    if k in fl: a.axhline(fl[k], color="k", lw=1.2, label="Fluent DI")
    a.set_ylabel(lab); a.grid(alpha=.3)
ax[0, 0].legend(fontsize=8); [a.set_xlabel("t [ms]") for a in ax[1]]
fig.suptitle("A1 (R2) statistics window vs Fluent DI"); fig.tight_layout(); fig.savefig(f"{OUT}/drift.png", dpi=130)
# T RMS map
tp = glob.glob(f"{G}/TPrime2Mean_*")[0]
C = read_field(f"{G}/C"); x, r = C[:, 0], C[:, 1]
rms = np.sqrt(np.maximum(read_field(tp), 0))
tri = mtri.Triangulation(x, r); p = np.stack([x[tri.triangles], r[tri.triangles]], -1)
e = np.max([np.hypot(*(p[:, i] - p[:, (i + 1) % 3]).T) for i in range(3)], 0); tri.set_mask(e > 0.006)
fig, a = plt.subplots(figsize=(10, 2.8))
cs = a.tricontourf(tri, rms, levels=np.linspace(0, max(rms.max(), 1), 16), cmap="magma")
a.set_aspect("equal"); a.set_xlim(0, 0.30); a.set_ylim(0, 0.06); a.set_xlabel("x [m]"); a.set_ylabel("r [m]")
a.set_title(f"R2 T RMS over the statistics window, max {rms.max():.0f} K"); fig.colorbar(cs, ax=a, fraction=0.02)
fig.savefig(f"{OUT}/T_rms.png", dpi=130, bbox_inches="tight")
print("mean:", mean, "\nfluent:", fl, "\nrms max", rms.max())

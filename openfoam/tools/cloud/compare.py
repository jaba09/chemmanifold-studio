# compare.py <time> <out.png> run1 run2 ...: T contours side by side + metrics vs the first run
import sys, os, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.tri as mtri
sys.path.insert(0, "/opt/ofb/tools"); from foamread import read_field
t, out, runs = sys.argv[1], sys.argv[2], sys.argv[3:]
C = read_field("/opt/ofb/run/quemadorUnico/0/C"); x = C[:,0]; r = np.hypot(C[:,1], C[:,2])
V = r  # axisymmetric volume weight ~ r * cell area; cells similar size near flame is not true, use r only for weighting
tri = mtri.Triangulation(x, r)
p = np.stack([x[tri.triangles], r[tri.triangles]], -1)
e = np.max([np.hypot(*(p[:,i]-p[:,(i+1)%3]).T) for i in range(3)], 0)
xc, rc = p[:,:,0].mean(1), p[:,:,1].mean(1)
tri.set_mask((e > 0.006) | ((xc > 0.05) & (xc < 0.20) & (rc < 0.05)))
F = {}
for run in runs:
    d = f"/opt/ofb/tr/{run}/{t}"
    F[run] = {k: read_field(f"{d}/{k}") for k in ("T", "CO", "OH", "CH4")}
ref = F[runs[0]]
fig, ax = plt.subplots(len(runs), 1, figsize=(10, 2.9*len(runs)))
for a, run in zip(np.atleast_1d(ax), runs):
    cs = a.tricontourf(tri, F[run]["T"], levels=np.linspace(300, 2100, 19), cmap="jet", extend="both")
    a.add_patch(plt.Rectangle((0.05, 0), 0.15, 0.05, color="0.85"))
    a.set_aspect("equal"); a.set_xlim(0, 0.30); a.set_ylim(0, 0.14)
    a.set_title(f"{run}: Tmax {F[run]['T'].max():.0f} K")
fig.colorbar(cs, ax=ax, label="T [K]", fraction=0.02)
fig.savefig(out, dpi=100, bbox_inches="tight")
hot = (ref["T"] > 1000)
for run in runs:
    f = F[run]; dT = f["T"] - ref["T"]
    print(f"{run:12s} Tmax {f['T'].max():7.1f}  mean|dT| hot {np.abs(dT[hot]).mean():6.1f}  max|dT| {np.abs(dT).max():6.1f}  "
          f"cells>1500 {int((f['T']>1500).sum()):5d}  COmax {f['CO'].max():.4f}  OHmax {f['OH'].max():.5f}")

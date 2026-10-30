import sys, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.tri as mtri
sys.path.insert(0, "/opt/ofb/tools"); from foamread import read_field
case, t, out = sys.argv[1], sys.argv[2], sys.argv[3]
field = sys.argv[4] if len(sys.argv) > 4 else "T"
C = read_field(f"{case}/0/C"); x = C[:,0]; r = np.hypot(C[:,1], C[:,2])
f = read_field(f"{case}/{t}/{field}")
if np.isscalar(f): f = np.full(len(x), f)
tri = mtri.Triangulation(x, r)
p = np.stack([x[tri.triangles], r[tri.triangles]], -1)
e = np.max([np.hypot(*(p[:,i]-p[:,(i+1)%3]).T) for i in range(3)], 0)
# drop triangles that bridge the unmeshed pot (x 0.05-0.20, r < 0.05) or are long
xc, rc = p[:,:,0].mean(1), p[:,:,1].mean(1)
tri.set_mask((e > 0.006) | ((xc > 0.05) & (xc < 0.20) & (rc < 0.05)))
fig, ax = plt.subplots(figsize=(11, 3.4))
lo, hi = (300, float(sys.argv[5])) if field == "T" and len(sys.argv) > 5 else (f.min(), f.max())
cs = ax.tricontourf(tri, f, levels=np.linspace(lo, hi, 21), cmap="jet", extend="both")
ax.add_patch(plt.Rectangle((0.05, 0), 0.15, 0.05, color="0.85"))
ax.set_aspect("equal"); ax.set_xlim(0, 0.52); ax.set_ylim(0, 0.14)
ax.set_xlabel("x (m, eje)"); ax.set_ylabel("r (m)")
fig.colorbar(cs, ax=ax, label=f"{field}", fraction=0.025)
ax.set_title(f"OpenFOAM DI GA18, {field}, iteracion {t}: max {f.max():.0f}")
fig.tight_layout(); fig.savefig(out, dpi=110)

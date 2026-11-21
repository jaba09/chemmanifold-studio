#!/usr/bin/env python3
"""Impose Fluent's wall-face temperatures (from a .dat.h5) as fixedValue T on OpenFOAM wall patches.

For the G1 wall-temperature check (results/sim1/A1/G1.md): the Fluent case radiates heat away from its
walls (DO radiation), so its wall temperatures differ from an adiabatic or convective wall. Faces are
matched by face-centre position (x, r): Fluent face centre = mid-point of its two nodes; OpenFOAM face
centre = boundary value of <time>/C (postProcess -func writeCellCentres). <time>/T must be ASCII.

    fluent_wall_T_to_foam.py case.cas.h5 sol.dat.h5 <case> <time> wall-pot-fff-fluid-fuel [more patches]
"""
import os, re, sys
import h5py
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fluent_h5_to_foam import read_mesh  # noqa: E402

cas, dat, case, t, *patches = sys.argv[1:]
coords, fnodes, c0, c1, fzones, czones, ncell = read_mesh(cas)
D = h5py.File(dat, "r")["results/1/phase-1/faces/SV_T"]
secs = [(int(D[k].attrs["minId"][0]) - 1, D[k][()]) for k in D]

def fluent_wall(name):
    z = next(z for z in fzones if z["name"].replace(":", "-") == name)
    for lo, a in secs:
        if lo <= z["lo"] and z["hi"] <= lo + len(a):
            T = a[z["lo"] - lo:z["hi"] - lo]
            xy = coords[fnodes[z["lo"]:z["hi"]]].mean(axis=1)
            return xy, T
    raise SystemExit(f"no face data for {name}")

def foam_centres(name):
    s = open(os.path.join(case, t, "C")).read()
    m = re.search(r"\n\s*" + re.escape(name) + r"\s*\{[^}]*?value\s+nonuniform\s+List<vector>\s*(\d+)\s*\((.*?)\)\s*;", s, re.S)
    n, body = int(m.group(1)), m.group(2)
    v = np.array(body.replace("(", " ").replace(")", " ").split(), float).reshape(n, 3)
    # wedge faces: the centre of the +/- half-angle quad lies at r cos(half-angle); undo that
    half = np.radians(float(os.environ.get("WEDGE_DEG", "5")) / 2)
    return np.column_stack([v[:, 0], np.hypot(v[:, 1], v[:, 2]) / np.cos(half)])

Tpath = os.path.join(case, t, "T"); s = open(Tpath).read()
for p in patches:
    xy, Tf = fluent_wall(p); fc = foam_centres(p)
    d = np.hypot(fc[:, None, 0] - xy[None, :, 0], fc[:, None, 1] - xy[None, :, 1])
    j = d.argmin(axis=1); err = d.min(axis=1).max()
    Tp = Tf[j]
    print(f"{p}: {len(fc)} faces, max match distance {err*1e3:.3f} mm, T {Tp.min():.0f}-{Tp.max():.0f} K (mean {Tp.mean():.0f})")
    if err > 5e-4 or len(set(j)) != len(fc):   # wedge face centroids near the axis sit up to ~0.3 mm off the 2D mid-point
        raise SystemExit("face matching failed")
    entry = ("    %s\n    {\n        type            fixedValue;   // Fluent wall T (radiating wall), G1 check\n"
             "        value           nonuniform List<scalar> %d\n(\n%s\n)\n;\n    }\n"
             % (p, len(Tp), "\n".join("%.3f" % v for v in Tp)))
    # replace an explicit entry for p, else insert before the first patch entry
    m = re.search(r"\n    " + re.escape(p) + r"\s*\n\s*\{.*?\n    \}\n", s, re.S)
    if m:
        s = s[:m.start()] + "\n" + entry + s[m.end():]
    else:
        i = s.index("{", s.index("boundaryField")) + 1
        s = s[:i] + "\n" + entry + s[i:]
open(Tpath, "w").write(s)

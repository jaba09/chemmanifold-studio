#!/usr/bin/env python3
"""Impose the frozen pot-wall temperatures of one decomposed OpenFOAM case on another (same mesh, any decomposition):
for the patches wall-pot-fff-fluid-fuel (pot bottom) and wall-pot-fff-fluid-exhaust (pot upper side + top), every face
of the target gets the value of the source face at the same centre (within 1e-6 m). Both cases must first be copied to
scratch dirs with ASCII T and C (postProcess -func writeCellCentres; foamFormatConvert), as done on 22 Nov 2026 to give
the GRI-Mech 3.0 leg exactly the ARC leg's 0.205 / 0.22 s pot profile (results/sim1/ARC22, L306 remedy ii-d).
  map_pot_T.py <scratch root with arc/, gri/ and a 'times' file: "arc <t>" / "gri <t>">
The edited ASCII T files are written in place in <root>/gri/processor*/<t>/T; copy them into the real case."""
import glob, re, sys
import numpy as np
S = sys.argv[1]
times = dict(l.split() for l in open(S + "/times"))
PATCHES = ["wall-pot-fff-fluid-fuel", "wall-pot-fff-fluid-exhaust"]
def block(txt, patch):
    b = txt.index("boundaryField")
    m = re.search(r"\n\s*" + re.escape(patch) + r"\s*\n\s*\{", txt[b:])
    if not m:
        return None
    s = b + m.end(); depth = 1; i = s
    while depth:
        depth += (txt[i] == "{") - (txt[i] == "}"); i += 1
    return s, i - 1
def values(seg, kind):
    return re.search(r"value\s+(uniform\s+[^;]+|nonuniform\s+List<" + kind + r">\s*(\d+)\s*\((.*?)\)\s*);", seg, re.S)
def read_patch(proc, t, patch):
    T = open(f"{proc}/{t}/T").read(); C = open(f"{proc}/{t}/C").read()
    bt, bc = block(T, patch), block(C, patch)
    if bt is None:
        return None
    mc, mt = values(C[bc[0]:bc[1]], "vector"), values(T[bt[0]:bt[1]], "scalar")
    if not mc or not mc.group(3):
        return np.zeros((0, 2)), np.zeros(0)
    xyz = np.array([list(map(float, s.split())) for s in re.findall(r"\(([^()]*)\)", mc.group(3))])
    tv = np.array(mt.group(3).split(), float)
    return np.c_[xyz[:, 0], np.hypot(xyz[:, 1], xyz[:, 2])], tv
ref = {}
for patch in PATCHES:
    parts = [read_patch(p, times["arc"], patch) for p in sorted(glob.glob(S + "/arc/processor*"))]
    parts = [q for q in parts if q is not None]
    ref[patch] = (np.vstack([q[0] for q in parts]), np.concatenate([q[1] for q in parts]))
tg = times["gri"]
for proc in sorted(glob.glob(S + "/gri/processor*")):
    path = f"{proc}/{tg}/T"; T = open(path).read(); changed = False
    for patch in PATCHES:
        r = read_patch(proc, tg, patch)
        if r is None or len(r[1]) == 0:
            continue
        Xa, Va = ref[patch]; new = []
        for x in r[0]:
            d = np.hypot(Xa[:, 0] - x[0], Xa[:, 1] - x[1]); j = d.argmin()
            assert d[j] < 1e-6, (patch, x, d[j])
            new.append(Va[j])
        bt = block(T, patch); seg = T[bt[0]:bt[1]]; m = values(seg, "scalar")
        rep = "value           nonuniform List<scalar> %d\n(\n%s\n);" % (len(new), "\n".join("%.8g" % v for v in new))
        T = T[:bt[0]] + seg[:m.start()] + rep + seg[m.end():] + T[bt[1]:]; changed = True
    if changed:
        open(path, "w").write(T)
print("done")

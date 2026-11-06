#!/usr/bin/env python3
"""Mesh of the simple laminar CH4/air coflow flame, written for BOTH solvers from one node list.

2D axisymmetric (x = axis, y = r), structured quads:
    fuel jet   r 0 - 2.5 mm   (same nozzle radius and CH4 mass flow as the burner)
    air coflow r 2.5 - 30 mm
    height     x 0 - 120 mm

Outputs
    coflow.msh                   ASCII Fluent mesh (File > Read > Mesh)
    <case>/constant/polyMesh     OpenFOAM 5 deg wedge with the same cells (same order)

Usage:  python make_mesh.py <OpenFOAM case dir> [--out coflow.msh]
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from fluent_h5_to_foam import write_wedge  # noqa: E402

R_FUEL, R_OUT, H = 2.5e-3, 30e-3, 120e-3


def graded(x0, x1, d0, d1):
    """Nodes from x0 to x1, cell size growing geometrically from about d0 to about d1."""
    L = x1 - x0
    if abs(d1 - d0) < 1e-15:
        n = max(1, round(L / d0))
        return np.linspace(x0, x1, n + 1)
    r_guess = (L - d0) / (L - d1)          # sum of geometric series: d0 (r^n - 1)/(r - 1) = L
    n = max(1, round(np.log(d1 / d0) / np.log(r_guess)) + 1)
    r = (d1 / d0) ** (1.0 / max(n - 1, 1))
    s = np.cumsum(np.r_[0.0, r ** np.arange(n)])
    return x0 + L * s / s[-1]


def nodes_1d():
    r = np.unique(np.r_[np.linspace(0, R_FUEL, 21),               # 0.125 mm in the jet
                        graded(R_FUEL, 10e-3, 0.125e-3, 0.4e-3),  # flame zone
                        graded(10e-3, R_OUT, 0.4e-3, 1.5e-3)])
    x = np.unique(np.r_[graded(0.0, 20e-3, 0.1e-3, 0.4e-3),
                        graded(20e-3, H, 0.4e-3, 1.5e-3)])
    return x, r


def build():
    x, r = nodes_1d()
    nx, nr = len(x) - 1, len(r) - 1
    X, Rr = np.meshgrid(x, r, indexing="ij")
    xy = np.column_stack([X.ravel(), Rr.ravel()])           # node (i, j) -> i*(nr+1)+j
    nid = lambda i, j: i * (nr + 1) + j                     # noqa: E731
    cid = lambda i, j: i * nr + j                           # noqa: E731
    ncell = nx * nr

    # faces, grouped by zone; c0 is the cell on the LEFT of n1 -> n2 (Fluent convention, checked
    # on the burner .cas.h5)
    groups = {k: [] for k in ("interior", "axis", "inlet-fuel", "inlet-air", "outlet", "side")}
    for i in range(nx + 1):          # faces normal to x (constant x), from node j to j+1
        for j in range(nr):
            a, b = nid(i, j), nid(i, j + 1)          # direction +r; left side is -x
            if i == 0:
                groups["inlet-fuel" if r[j + 1] <= R_FUEL + 1e-12 else "inlet-air"].append(
                    (b, a, cid(0, j), -1))           # reversed so the cell (at +x) is on the left
            elif i == nx:
                groups["outlet"].append((a, b, cid(nx - 1, j), -1))
            else:
                groups["interior"].append((a, b, cid(i - 1, j), cid(i, j)))
    for j in range(nr + 1):          # faces normal to r (constant r), from node i to i+1
        for i in range(nx):
            a, b = nid(i, j), nid(i + 1, j)          # direction +x; left side is +r
            if j == 0:
                groups["axis"].append((a, b, cid(i, 0), -1))
            elif j == nr:
                groups["side"].append((b, a, cid(i, nr - 1), -1))
            else:
                groups["interior"].append((a, b, cid(i, j), cid(i, j - 1)))
    return xy, groups, ncell, (nx, nr)


# Fluent zone ids and type codes: 2 interior, 3 wall, 5 pressure-outlet, 7 symmetry,
# 10 velocity-inlet, 37 axis
ZONES = [("interior", 3, 2), ("axis", 4, 37), ("inlet-fuel", 5, 10), ("inlet-air", 6, 10),
         ("outlet", 7, 5), ("side", 8, 7)]
FLUENT_TYPE_NAME = {2: "interior", 3: "wall", 5: "pressure-outlet", 7: "symmetry",
                    10: "velocity-inlet", 37: "axis"}


def write_msh(path, xy, groups, ncell):
    h = lambda v: format(v, "x")                            # noqa: E731
    nn = len(xy)
    nf = sum(len(v) for v in groups.values())
    with open(path, "w") as f:
        f.write('(0 "simple CH4/air laminar coflow flame, 2D axisymmetric, x = axis, metres")\n')
        f.write("(2 2)\n")
        f.write(f"(10 (0 1 {h(nn)} 0 2))\n")
        f.write(f"(10 (1 1 {h(nn)} 1 2)(\n")
        for px, py in xy:
            f.write(f"{px:.12e} {py:.12e}\n")
        f.write("))\n")
        f.write(f"(12 (0 1 {h(ncell)} 0))\n")
        f.write(f"(12 (2 1 {h(ncell)} 1 3))\n")          # zone 2, active, quads
        f.write(f"(13 (0 1 {h(nf)} 0))\n")
        first = 1
        for name, zid, ztype in ZONES:
            faces = groups[name]
            last = first + len(faces) - 1
            f.write(f"(13 ({h(zid)} {h(first)} {h(last)} {h(ztype)} 2)(\n")
            for a, b, c0, c1 in faces:
                f.write(f"{h(a + 1)} {h(b + 1)} {h(c0 + 1)} {h(c1 + 1 if c1 >= 0 else 0)}\n")
            f.write("))\n")
            first = last + 1
        f.write("(45 (2 fluid fluid)())\n")
        for name, zid, ztype in ZONES:
            f.write(f"(45 ({zid} {FLUENT_TYPE_NAME[ztype]} {name})())\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case")
    ap.add_argument("--out", default="coflow.msh")
    args = ap.parse_args()
    xy, groups, ncell, (nx, nr) = build()
    write_msh(args.out, xy, groups, ncell)

    fnodes, c0, c1, fzones, lo = [], [], [], [], 0
    for name, zid, ztype in ZONES:
        for a, b, p, q in groups[name]:
            fnodes.append((a, b)); c0.append(p); c1.append(q)
        fzones.append(dict(id=zid, name=name, type=ztype, lo=lo, hi=lo + len(groups[name])))
        lo += len(groups[name])
    write_wedge(xy, np.array(fnodes), np.array(c0), np.array(c1), fzones,
                [dict(id=2, name="fluid", lo=0, hi=ncell)], ncell, args.case, source=args.out)
    print(f"{nx} x {nr} = {ncell} cells; wrote {args.out}")


if __name__ == "__main__":
    main()

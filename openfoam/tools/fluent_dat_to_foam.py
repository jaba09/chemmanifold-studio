#!/usr/bin/env python3
"""Copy a Fluent .dat.h5 solution (2D axisymmetric) into the internal fields of an OpenFOAM time directory.

Works on a case whose mesh was built by fluent_h5_to_foam.py from the matching .cas.h5: that converter keeps
the Fluent cell order, so OpenFOAM cell i is Fluent cell i + 1 and no interpolation is needed.

Writes T, U, k, omega and one file per species (Y, mass fractions) into <case>/<time>, taking the boundary
conditions from the existing files in <time> (species not yet there get the boundaryField of Ydefault).
The pressure is not copied (it settles within a few iterations), and nut/alphat are recomputed by the solver.
The OpenFOAM time directory must be in ASCII format and needs 0/C (postProcess -func writeCellCentres).

Usage:
    python fluent_dat_to_foam.py solution.dat.h5 <case> [--time 0]
"""
import argparse
import os
import re

import h5py
import numpy as np

# Fluent species order of the GA18 case -> OpenFOAM (chemkinToFoam) names
FLUENT_SPECIES = "h2 h o o2 oh h2o ho2 h2o2 ch2 ch2<s> ch3 ch4 co co2 hco ch2o ch3o n2".split()
FOAM_NAME = {s: s.upper().replace("<S>", "(S)") for s in FLUENT_SPECIES}


def read_internal_vector(path):
    s = open(path).read()
    m = re.search(r"internalField\s+nonuniform\s+List<vector>\s*(\d+)\s*\(", s)
    n = int(m.group(1))
    body = s[m.end():s.index("\n)", m.end())]
    return np.array(body.replace("(", " ").replace(")", " ").split(), float).reshape(n, 3)


def replace_internal(path, out, values, obj=None):
    """Write <out> as <path> with its internalField replaced by <values> (scalar n or vector n x 3)."""
    s = open(path).read()
    i = s.index("internalField")
    j = s.index("boundaryField")
    if values.ndim == 1:
        body = "nonuniform List<scalar>\n%d\n(\n%s\n)\n;\n\n" % (len(values), "\n".join("%.10g" % v for v in values))
    else:
        body = "nonuniform List<vector>\n%d\n(\n%s\n)\n;\n\n" % (
            len(values), "\n".join("(%.10g %.10g %.10g)" % tuple(v) for v in values))
    old = s[i + len("internalField"):s.index(";", i)].strip()
    bf = s[j:]
    if old.startswith("uniform"):
        # boundary entries such as "value $internalField;" keep the old uniform value
        bf = bf.replace("$internalField", old)
    s = s[:i] + "internalField   " + body + bf
    if obj:
        s = re.sub(r"object\s+\S+;", f"object      {obj};", s, count=1)
    open(out, "w").write(s)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dat")
    ap.add_argument("case")
    ap.add_argument("--time", default="0")
    a = ap.parse_args()
    td = os.path.join(a.case, a.time)

    with h5py.File(a.dat, "r") as f:
        c = f["results/1/phase-1/cells"]
        get = lambda k: c[k]["1"][()]
        T, ux, ur, k, om, Y = get("SV_T"), get("SV_U"), get("SV_V"), get("SV_K"), get("SV_O"), get("SV_Y")

    C = read_internal_vector(os.path.join(a.case, "0", "C"))
    if len(C) != len(T):
        raise SystemExit(f"cell count differs: OpenFOAM {len(C)}, Fluent {len(T)}")
    r = np.hypot(C[:, 1], C[:, 2])
    cy, cz = np.where(r > 0, C[:, 1] / np.maximum(r, 1e-30), 1.0), np.where(r > 0, C[:, 2] / np.maximum(r, 1e-30), 0.0)
    U = np.c_[ux, ur * cy, ur * cz]

    for name, v in (("T", T), ("U", U), ("k", np.maximum(k, 1e-12)), ("omega", np.maximum(om, 1e-6))):
        p = os.path.join(td, name)
        replace_internal(p, p, v)
    Y = np.clip(Y, 0, 1)
    Y /= Y.sum(1, keepdims=True)
    for i, s in enumerate(FLUENT_SPECIES):
        n = FOAM_NAME[s]
        p = os.path.join(td, n)
        src = p if os.path.exists(p) else os.path.join(td, "Ydefault")
        replace_internal(src, p, Y[:, i], obj=n)
    print(f"wrote T U k omega + {len(FLUENT_SPECIES)} species into {td}; Tmax {T.max():.1f} K")


if __name__ == "__main__":
    main()

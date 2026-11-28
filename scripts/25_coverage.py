#!/usr/bin/env python3
"""COVLOOP step 3: coverage, holes and hole states of one run leg (docs/COVERAGE-LOOP-ROADMAP.md, s. 5).

Inputs (npz, written by the OpenFOAM plug-in post-processing or by foam_snapshot.py):
  --cells     T (N,), Y (N,S), species (S,), mass (N,), ood (N, bool)  [several snapshots may be concatenated]
  --shadow    T, Y, species, pass (one-step ARC22 DI checks)            [comparison data, never training]
  --sentinel  T, Y, species, pass (25/200-step checks)
Outputs in --out: coverage.json (C, C_data, ...), bins.csv (per-bin table, sorted by mass),
hole_states.npz (cell states in hole bins: STARTING STATES for step 4, flagged excluded from training).

Example:
  python scripts/25_coverage.py --mech mechanisms/arc_gri30_nox22/gri30_skel43.yaml \
      --cells run/cells.npz --shadow run/shadow.npz --sentinel run/sentinel.npz --out results/covloop/iter0/A_flame
"""
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from chemmanifold.coverage import CoverageGrid, coverage, reacting_mask, save_table, save_summary


def place(grid, d):
    Z, T, c, dh = grid.coordinates(d["T"], d["Y"], species=[str(s) for s in d["species"]])
    b, dims = grid.bin_index(Z, T, c, dh)
    return b, dims, T, c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mech", required=True)
    ap.add_argument("--cells", required=True)
    ap.add_argument("--shadow")
    ap.add_argument("--sentinel")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-hole-states", type=int, default=15000)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    grid = CoverageGrid(a.mech)
    cells = dict(np.load(a.cells, allow_pickle=True))
    b, dims, T, c = place(grid, cells)
    cd = {"bin": b, "mass": cells["mass"], "ood": cells["ood"].astype(bool), "reacting": reacting_mask(T, c)}
    checks = {}
    for key, path in (("shadow", a.shadow), ("sentinel", a.sentinel)):
        if path:
            d = dict(np.load(path, allow_pickle=True))
            checks[key] = {"bin": place(grid, d)[0], "pass": d["pass"].astype(bool)}
    summary, table = coverage(cd, checks.get("shadow"), checks.get("sentinel"))
    save_summary(os.path.join(a.out, "coverage.json"), summary)
    save_table(os.path.join(a.out, "bins.csv"), table, dims)
    holes = table["bin"][~table["trusted"]]
    sel = np.where(np.isin(b, holes) & cd["reacting"])[0]
    if len(sel) > a.max_hole_states:
        sel = np.random.default_rng(0).choice(sel, a.max_hole_states, replace=False)
    np.savez(os.path.join(a.out, "hole_states.npz"), T=cells["T"][sel], Y=cells["Y"][sel],
             species=cells["species"], bin=b[sel], excluded=np.ones(len(sel), bool),
             note="CFD states: starting points for physics sampling only, never training pairs")
    print("C %.4f  C_data %.4f  holes %d / %d bins, %d hole states" % (
        summary["C"], summary["C_data"], summary["n_holes"], summary["n_bins_visited"], len(sel)))


if __name__ == "__main__":
    main()

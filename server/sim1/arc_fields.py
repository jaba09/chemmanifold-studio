#!/usr/bin/env python3
"""Compact per-cell fields of protocol snapshots (foam_snapshot.py CSVs) for cell-by-cell comparisons elsewhere
(e.g. with the Fluent GRI-Mech 3.0 DI solution). Row i = OpenFOAM cell i = Fluent cell i+1 (fluent_dat_to_foam.py keeps
the Fluent cell order); rows are sorted by the CSV cellnumber.

  arc_fields.py <snap dir> <label> <t0> <t1> <out.npz>     time mean of the snapshots in [t0, t1] s (t0 = t1: one time)

npz (float32, savez_compressed): T, Ux, Ur, Y_<species> for every species column of the CSVs (GA18 names in
OpenFOAM spelling: CH2(S); ARC: also CH3OH C2H2 C2H4 C2H6 NO NO2 N2O HCN), x, r, V (cell volume of the 5 deg wedge,
m3), times (the snapshot times used), and the metadata strings label / window / cell_order.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

GA18 = "h2 h o o2 oh h2o ho2 h2o2 ch2 ch2<s> ch3 ch4 co co2 hco ch2o ch3o n2".split()
EXTRA = "ch3oh c2h2 c2h4 c2h6 no no2 n2o hcn".split()
NON_SPECIES = {"cellnumber", "x-coordinate", "y-coordinate", "cell-volume", "temperature", "absolute-pressure",
               "x-velocity", "radial-velocity", "velocity-magnitude", "strain-rate-mag", "mixture-fraction",
               "scalar-dissipation"}
ARC = "h2 h o o2 oh h2o ho2 h2o2 ch4 ch3 co co2 ch2o ch3oh c2h2 c2h4 c2h6 n2 no no2 n2o hcn".split()


def main():
    d, label, t0, t1, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
    S = []
    for p in sorted(Path(d).glob(f"{label}_t*ms.csv")):
        t = float(re.search(r"_t([0-9.]+)ms\.csv$", p.name).group(1)) * 1e-3
        if t0 - 1e-9 <= t <= t1 + 1e-9:
            S.append((t, p))
    if not S:
        raise SystemExit(f"no snapshots of {label} in {d} for {t0}-{t1} s")
    def species_of(df):
        known = set(GA18) | set(EXTRA)
        others = [c for c in df.columns if c not in NON_SPECIES and c not in known]
        if others:                                   # e.g. GRI-Mech 3.0: every species column of the table
            return [c for c in df.columns if c not in NON_SPECIES]
        if all(c in df for c in EXTRA):
            return ARC                               # ARC run: its 22 species
        return GA18                                  # GA18 run: the 18

    # the species set is the newest snapshot's; a snapshot without some of them (the GA18 start state at 0.1 s of a
    # leg run with another mechanism) is left out of the mean, and the window string says which times were used
    sp = species_of(pd.read_csv(S[-1][1], nrows=1))
    cols = ["temperature", "x-velocity", "radial-velocity"] + sp
    acc, used = None, []
    for t, p in S:
        df = pd.read_csv(p).sort_values("cellnumber")
        if any(c not in df for c in sp):
            print(f"skipped {p.name}: lacks species of the newest snapshot")
            continue
        v = df[cols].to_numpy(np.float64)
        if acc is None:
            acc, geo = v.copy(), df[["x-coordinate", "y-coordinate", "cell-volume"]].to_numpy(np.float64)
            assert np.array_equal(df["cellnumber"].to_numpy(), np.arange(len(df))), "cell numbers not 0..n-1"
        else:
            acc += v
        used.append((t, p))
    S = used
    M = acc / len(S)
    f32 = lambda a: a.astype(np.float32)
    data = {"T": f32(M[:, 0]), "Ux": f32(M[:, 1]), "Ur": f32(M[:, 2]),
            "x": f32(geo[:, 0]), "r": f32(geo[:, 1]), "V": f32(geo[:, 2]),
            "times": np.array([t for t, _ in S], np.float32),
            "label": np.array(label), "window": np.array(f"{S[0][0]:.4f}-{S[-1][0]:.4f} s, {len(S)} snapshots"),
            "cell_order": np.array("row i = OpenFOAM cell i = Fluent cell i+1")}
    for j, s in enumerate(sp):
        data["Y_" + s.upper().replace("<S>", "(S)")] = f32(M[:, 3 + j])
    np.savez_compressed(out, **data)
    print(f"{out}: {len(M)} cells, {len(S)} snapshots ({data['window']}), {len(sp)} species, "
          f"{Path(out).stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

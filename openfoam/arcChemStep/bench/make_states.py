#!/usr/bin/env python3
"""States for arcBench from a foam_snapshot CSV: make_states.py <csv> <out.txt> [n 1000] [Tmin 0] (GA18 species
mapped onto the 22 ARC species, the new ones 0, renormalized)."""
import sys
import numpy as np
import pandas as pd
df = pd.read_csv(sys.argv[1]); n = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
Tmin = float(sys.argv[4]) if len(sys.argv) > 4 else 0
arc = "H2 H O O2 OH H2O HO2 H2O2 CH4 CH3 CO CO2 CH2O CH3OH C2H2 C2H4 C2H6 N2 NO NO2 N2O HCN".split()
idx = np.where(df.temperature > Tmin)[0]
d = df.iloc[np.random.default_rng(0).choice(idx, min(n, len(idx)), replace=False)]
Y = np.maximum(np.array([d[s.lower()].values if s.lower() in d else np.zeros(len(d)) for s in arc]).T, 0)
Y /= Y.sum(1, keepdims=True)
with open(sys.argv[2], "w") as f:
    f.write(f"{len(d)}\n")
    for T, p, y in zip(d.temperature, d["absolute-pressure"], Y):
        f.write(f"{T} {p} " + " ".join(f"{v:.10g}" for v in y) + "\n")

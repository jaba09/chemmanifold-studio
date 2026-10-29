#!/usr/bin/env python3
"""Summary of the shadow DI checks of a run (userChemStep shadowEvery/shadowPerBin).

At every shadowEvery-th time step, userChemStep takes a few cells per (T band, Z band, inside/OOD)
bin, advances each with the surrogate AND with GA18 from the same state over the same dt, and writes
both to shadowDI.csv (one file per processor). The cell itself keeps its normal update: this is a
comparison only, never training data.

For every bin and overall this reports the number of checks, the mean |T_surrogate - T_DI| of one
step, and the relative error of the one-step chemical increment of T, OH and CO
(|d_surrogate - d_DI| / max(|d_DI|, floor)), plus the same per output time window.

  python3 shadow_report.py <run dir> <out dir> --label hyb2
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

Z_EDGES = [0, 0.01, 0.02, 0.03, 0.045, 0.055, 0.07, 0.1, 0.15, 0.22, 0.4, 1.01]


def load(run):
    files = sorted(Path(run).glob("processor*/shadowDI.csv")) + sorted(Path(run).glob("shadowDI.csv"))
    if not files:
        raise SystemExit(f"no shadowDI.csv under {run}")
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def increment_errors(d):
    out = pd.DataFrame(index=d.index)
    out["abs_dT"] = (d.T_surrogate - d.T_DI).abs()
    dT_d = d.T_DI - d["T"]
    out["rel_inc_T"] = (d.T_surrogate - d.T_DI).abs() / np.maximum(dT_d.abs(), 0.5)
    for s in ("OH", "CO"):
        inc_d = d[f"Yd_{s}"] - d[f"Y0_{s}"]
        floor = 1e-3 * max(d[f"Y0_{s}"].max(), 1e-12)
        out[f"rel_inc_{s}"] = (d[f"Ys_{s}"] - d[f"Yd_{s}"]).abs() / np.maximum(inc_d.abs(), floor)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("out")
    ap.add_argument("--label", default="run")
    a = ap.parse_args()
    d = load(a.run)
    e = increment_errors(d)
    d = pd.concat([d, e], axis=1)
    d["ood"] = (d.ood_flags.astype(int) & 63) > 0
    d["T_band"] = (np.clip((d["T"] - 600) // 100, 0, 17) * 100 + 600).astype(int)
    d["Z_band"] = pd.cut(d.Z, Z_EDGES, right=False).astype(str)
    cols = ["abs_dT", "rel_inc_T", "rel_inc_OH", "rel_inc_CO"]
    agg = {c: "median" for c in cols} | {"time": "size"}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    d.to_csv(out / f"shadow_{a.label}.csv", index=False)
    by_bin = d.groupby(["ood", "Z_band", "T_band"]).agg(agg).rename(columns={"time": "checks"})
    by_bin.round(4).to_csv(out / f"shadow_{a.label}_bins.csv")
    by_z = d.groupby(["ood", "Z_band"]).agg(agg).rename(columns={"time": "checks"})
    by_t = d.groupby((d.time * 1e3 // 2.5 * 2.5).rename("t_ms")).agg(agg).rename(columns={"time": "checks"})
    with open(out / f"shadow_{a.label}.md", "w") as f:
        f.write(f"# Comprobaciones DI en sombra: {a.label}\n\n"
                "Cada fila: mediana sobre las celdas comprobadas (un paso del surrogado frente a un paso de GA18 "
                "desde el mismo estado). Solo comparación; nada de esto entra en el entrenamiento.\n\n")
        f.write(f"Total: {len(d)} comprobaciones, {d.ood.sum()} en celdas OOD. Mediana |dT| de un paso "
                f"{d.abs_dT.median():.3g} K; error relativo del incremento T {d.rel_inc_T.median():.0%}, "
                f"OH {d.rel_inc_OH.median():.0%}, CO {d.rel_inc_CO.median():.0%}.\n\n")
        f.write("## Por banda de Z (dentro / OOD)\n\n" + by_z.round(3).to_markdown() + "\n\n")
        f.write("## Por tiempo\n\n" + by_t.round(3).to_markdown() + "\n")
    print(open(out / f"shadow_{a.label}.md").read())


if __name__ == "__main__":
    main()

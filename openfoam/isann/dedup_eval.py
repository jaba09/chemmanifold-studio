#!/usr/bin/env python3
"""How much the two deduplication levels of ISANN shrink the stored pairs, and what coverage is lost.

The candidates are the hot cells (T > --T-hot) of the DI snapshots of the burner (every 2.5 ms,
the states a DI phase would offer at those steps, dt = 2e-5 s). They are offered in time order to

  level 1: the grid with a cap per box and reservoir replacement (isannStore.H, mirrored here);
  level 2: the radius of novelty r in the model's OOD coordinates (isann_lib.radius_dedup);

and, as the baseline, to a random subset of the same size as level 1 + 2. Coverage is the distance
from every candidate to its nearest stored pair, in units of the model's landmark threshold (the
'data' OOD check flags a state when its distance to the nearest landmark is above 1).

  python3 dedup_eval.py --snapshots <dir of di_t*.csv> --model <chemmanifold_model.txt> --out <dir>
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from chemmanifold.fluent import fluent_species_name, model_file_scalers, read_model_arrays  # noqa: E402
from isann_lib import coverage, features, grid_keys, grid_reservoir, landmark_threshold, radius_dedup, save_json  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshots", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--T-hot", type=float, default=600.0)
    ap.add_argument("--dt", type=float, default=2e-5)
    ap.add_argument("--caps", default="1,2,4")
    ap.add_argument("--radii", default="0.05,0.1,0.2", help="in units of the landmark threshold")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    arr = read_model_arrays(a.model)
    species = [s for s in arr.get("species_names", [])] if "species_names" in arr else None
    scalers, _ = model_file_scalers(a.model)
    species = species or ['H2', 'H', 'O', 'O2', 'OH', 'H2O', 'HO2', 'H2O2', 'CH2', 'CH2(S)', 'CH3', 'CH4',
                          'CO', 'CO2', 'HCO', 'CH2O', 'CH3O', 'N2']
    thr = landmark_threshold(a.model)

    Ys, Ts, Zs, ts = [], [], [], []
    for p in sorted(Path(a.snapshots).glob("di_t*ms.csv")):
        df = pd.read_csv(p)
        df = df[df["temperature"] > a.T_hot]
        Y = df[[fluent_species_name(s) for s in species]].to_numpy()
        Ys.append(Y / Y.sum(1, keepdims=True))
        Ts.append(df["temperature"].to_numpy())
        Zs.append(df["mixture-fraction"].to_numpy())
        ts.append(np.full(len(df), float(p.stem.split("_t")[-1][:-2])))
    Y, T, Z, t = np.vstack(Ys), np.concatenate(Ts), np.concatenate(Zs), np.concatenate(ts)
    n = len(T)
    print(f"{n} candidates (hot cells of {len(Ys)} snapshots)")
    X = features(Y, T, a.dt, scalers)
    rng = np.random.default_rng(0)

    rows = []
    keys = grid_keys(T, Z, Y, a.dt, species)
    for cap in map(int, a.caps.split(",")):
        k1, nbox = grid_reservoir(keys, cap=cap)
        d1 = coverage(X, X[k1]) / thr
        rows.append(dict(method=f"rejilla cap {cap}", stored=len(k1), boxes=nbox, reduction=n / len(k1),
                         cov_p50=np.median(d1), cov_p99=np.quantile(d1, 0.99), cov_max=d1.max(),
                         frac_within_0p1=np.mean(d1 < 0.1)))
        for rr in map(float, a.radii.split(",")):
            k2 = k1[radius_dedup(X[k1], rr * thr)]
            d2 = coverage(X, X[k2]) / thr
            rnd = rng.choice(n, size=len(k2), replace=False)
            d3 = coverage(X, X[rnd]) / thr
            rows.append(dict(method=f"rejilla cap {cap} + radio {rr}", stored=len(k2), boxes=nbox,
                             reduction=n / len(k2), cov_p50=np.median(d2), cov_p99=np.quantile(d2, 0.99),
                             cov_max=d2.max(), frac_within_0p1=np.mean(d2 < 0.1)))
            rows.append(dict(method=f"  azar, mismo tamaño ({len(k2)})", stored=len(k2), boxes=0,
                             reduction=n / len(k2), cov_p50=np.median(d3), cov_p99=np.quantile(d3, 0.99),
                             cov_max=d3.max(), frac_within_0p1=np.mean(d3 < 0.1)))
            print(rows[-2], rows[-1], flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(out / "dedup_eval.csv", index=False)
    with open(out / "dedup_eval.md", "w") as f:
        f.write(f"# Deduplicación ISANN sobre {n} candidatos (celdas T > {a.T_hot:.0f} K de {len(Ys)} "
                f"instantáneas DI, dt {a.dt:g} s)\n\n")
        f.write("Cobertura = distancia de cada candidato al par guardado más cercano, en unidades del umbral "
                f"de landmarks del modelo ({thr:.3f}); 1 = lo que el detector OOD 'data' ya considera lejos.\n\n")
        f.write("| método | guardados | reducción | cobertura p50 | p99 | máx | % a < 0,1 |\n|---|---|---|---|---|---|---|\n")
        for r in rows:
            f.write(f"| {r['method']} | {r['stored']} | {r['reduction']:.0f}x | {r['cov_p50']:.3f} | "
                    f"{r['cov_p99']:.3f} | {r['cov_max']:.2f} | {100 * r['frac_within_0p1']:.1f} |\n")
    save_json(out / "dedup_eval.json", dict(n_candidates=n, landmark_threshold=thr, rows=rows))


if __name__ == "__main__":
    main()

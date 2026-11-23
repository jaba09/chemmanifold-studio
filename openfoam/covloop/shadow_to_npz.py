#!/usr/bin/env python3
"""Convert userChemStep shadowDI.csv files (all processors of a leg) into the shadow.npz of scripts/25_coverage.py,
applying the COVLOOP trust criteria (docs/COVERAGE-LOOP-ROADMAP.md 5.2) to each one-step check:
  fail if |T_s - T_DI| > max(1 K, 0.3 |T_DI - T0|)
       or for OH, CO, H, O:      |Ys - Yd| > max(5e-5, 0.3 |Yd - Y0|)
       or for NO, NO2, N2O, HCN: |Ys - Yd| > max(floor, 0.3 |Yd - Y0|), floors 3e-6, 2e-7, 5e-8, 2e-6
Comparison data only: the DI results in these files are never training pairs.
  python3 shadow_to_npz.py OUT.npz processor*/shadowDI.csv [--tmin 0]
"""
import argparse
import numpy as np

FLOORS = {"OH": 5e-5, "CO": 5e-5, "H": 5e-5, "O": 5e-5, "NO": 3e-6, "NO2": 2e-7, "N2O": 5e-8, "HCN": 2e-6}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--tmin", type=float, default=0.0)
    a = ap.parse_args()
    T, Y, P, species = [], [], [], None
    for path in a.csv:
        with open(path) as f:
            head = f.readline().strip().split(",")
        d = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
        if not len(d):
            continue
        col = {n: i for i, n in enumerate(head)}
        sp = [n[3:] for n in head if n.startswith("Y0_")]
        species = species or sp
        d = d[d[:, col["time"]] >= a.tmin]
        Y0 = d[:, [col["Y0_" + s] for s in sp]]
        Ys = d[:, [col["Ys_" + s] for s in sp]]
        Yd = d[:, [col["Yd_" + s] for s in sp]]
        T0, Ts, Td = d[:, col["T"]], d[:, col["T_surrogate"]], d[:, col["T_DI"]]
        bad = np.abs(Ts - Td) > np.maximum(1.0, 0.3 * np.abs(Td - T0))
        for s, fl in FLOORS.items():
            if s in sp:
                k = sp.index(s)
                bad |= np.abs(Ys[:, k] - Yd[:, k]) > np.maximum(fl, 0.3 * np.abs(Yd[:, k] - Y0[:, k]))
        T.append(T0); Y.append(Y0); P.append(~bad)
    T, Y, P = np.concatenate(T), np.concatenate(Y), np.concatenate(P)
    np.savez(a.out, T=T, Y=Y, species=np.array(species), **{"pass": P})
    print(f"{len(T)} shadow checks, {100 * (1 - P.mean()):.1f} % fail -> {a.out}")


if __name__ == "__main__":
    main()

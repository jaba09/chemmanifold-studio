#!/usr/bin/env python3
"""Cell-by-cell comparison of two field files of arc_fields.py (same mesh, same window): flame metrics of each and
their hot-cell differences (hot = T > 1000 K in either; volume-weighted over the full revolution).

  compare_of_fields.py <a.npz> <name a> <b.npz> <name b>      (b = the reference)
"""
import sys

import numpy as np


def main():
    fa, na, fb, nb = sys.argv[1:5]
    a, b = np.load(fa), np.load(fb)
    w = a["V"].astype(float) * 72.0
    x = a["x"].astype(float)
    print(f"{na}: {a['window']}   {nb}: {b['window']}")
    print(f"| Metric | {na} | {nb} |\n|---|---|---|")

    def row(name, fa_, fb_):
        print(f"| {name} | {fa_} | {fb_} |")

    for name, f in [("V(T > 1500 K) [cm3]", lambda d: f"{1e6 * w[d['T'] > 1500].sum():.2f}"),
                    ("Tmax [K]", lambda d: f"{float(d['T'].max()):.1f}"),
                    ("x(OH max) [mm]", lambda d: f"{1e3 * x[np.argmax(d['Y_OH'])]:.1f}")]:
        row(name, f(a), f(b))
    for s in ["OH", "CO", "H", "NO", "NO2", "N2O", "HCN", "C2H2", "CH3OH"]:
        k = "Y_" + s
        if k in a.files and k in b.files:
            row(f"{s} max", f"{float(a[k].max()):.3g}", f"{float(b[k].max()):.3g}")
    h = (a["T"] > 1000) | (b["T"] > 1000)
    dT = a["T"].astype(float) - b["T"].astype(float)
    print(f"\nhot cells ({h.sum()}): mean abs(dT) {np.abs(dT[h]).mean():.1f} K, volume-weighted "
          f"{np.average(np.abs(dT[h]), weights=w[h]):.1f} K, bias {np.average(dT[h], weights=w[h]):+.1f} K, "
          f"max abs(dT) {np.abs(dT).max():.0f} K")
    print(f"\n| Species | L1 rel, hot cells | total {na}/{nb} |\n|---|---|---|")
    for s in ["OH", "CO", "CO2", "H", "H2", "CH4", "NO", "NO2", "N2O", "HCN", "C2H2", "CH3OH"]:
        k = "Y_" + s
        if k in a.files and k in b.files:
            A, B = a[k].astype(float), b[k].astype(float)
            l1 = np.sum(w[h] * np.abs(A[h] - B[h])) / np.sum(w[h] * np.abs(B[h]))
            print(f"| {s} | {100 * l1:.1f} % | {np.sum(w * A) / np.sum(w * B):.3f} |")


if __name__ == "__main__":
    main()

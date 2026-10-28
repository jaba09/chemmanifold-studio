#!/usr/bin/env python3
"""Fit Sutherland coefficients to Chemkin (Lennard-Jones) transport data for chemkinToFoam.

chemkinToFoam does not read a Chemkin tran.dat; it wants an OpenFOAM dictionary with the
Sutherland coefficients As, Ts of every species. This evaluates each pure-species viscosity from
kinetic theory with Cantera (what Fluent's kinetic-theory option uses) and fits
    mu(T) = As sqrt(T) / (1 + Ts/T)
by linear least squares on sqrt(T)/mu = 1/As + (Ts/As)/T.

Usage:
    python chemkin_transport_to_foam.py chem.inp therm.dat tran.dat transportProperties [--tmin 300 --tmax 2500]
"""
import argparse
import os
import tempfile

import cantera as ct
import numpy as np
from cantera import ck2yaml


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chem")
    ap.add_argument("therm")
    ap.add_argument("tran")
    ap.add_argument("out")
    ap.add_argument("--tmin", type=float, default=300.0)
    ap.add_argument("--tmax", type=float, default=2500.0)
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        yml = os.path.join(tmp, "mech.yaml")
        ck2yaml.main(["--input", args.chem, "--thermo", args.therm, "--transport", args.tran,
                      "--output", yml, "--quiet", "--permissive"])
        gas = ct.Solution(yml)

    T = np.linspace(args.tmin, args.tmax, 60)
    lines, worst = [], 0.0
    for sp in gas.species_names:
        mu = np.empty_like(T)
        for i, t in enumerate(T):
            gas.TPX = t, ct.one_atm, {sp: 1.0}
            mu[i] = gas.viscosity
        a, b = np.polyfit(1.0 / T, np.sqrt(T) / mu, 1)  # slope = Ts/As, intercept = 1/As
        As, Ts = 1.0 / b, a / b
        fit = As * np.sqrt(T) / (1 + Ts / T)
        err = np.max(np.abs(fit / mu - 1))
        worst = max(worst, err)
        lines.append(f'"{sp}"\n{{\n    transport\n    {{\n        As  {As:.6e};\n        Ts  {Ts:.4f};\n    }}\n}}\n'
                     f"// max fit error {100 * err:.2f}% over {args.tmin:g}-{args.tmax:g} K\n")

    with open(args.out, "w") as f:
        f.write("FoamFile\n{\n    version     2.0;\n    format      ascii;\n    class       dictionary;\n"
                "    object      transportProperties;\n}\n"
                f"// Sutherland fits to kinetic-theory viscosity from {os.path.basename(args.tran)}\n\n")
        f.write("\n".join(lines))
    print(f"wrote {args.out}: {len(lines)} species, worst fit error {100 * worst:.2f}%")


if __name__ == "__main__":
    main()

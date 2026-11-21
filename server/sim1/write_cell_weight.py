#!/usr/bin/env python3
"""Write <case>/<time>/cellWeight (25 where T > 800 K, 1 elsewhere) from an ASCII T, for a
chemistry-balanced scotch decomposition (decomposeParDict: weightField cellWeight;).
    write_cell_weight.py <case>/<time> [Tcut 800] [weight 25]"""
import re, sys
t = sys.argv[1]; Tcut = float(sys.argv[2]) if len(sys.argv) > 2 else 800.0
W = sys.argv[3] if len(sys.argv) > 3 else "25"
src = open(f"{t}/T", errors="strict").read()
n, body = re.search(r"internalField\s+nonuniform\s+List<scalar>\s*(\d+)\s*\((.*?)\)\s*;", src, re.S).groups()
w = [W if float(v) > Tcut else "1" for v in body.split()]
hdr = src.split("internalField")[0].replace("object      T;", "object      cellWeight;").replace(
    "[0 0 0 1 0 0 0]", "[0 0 0 0 0 0 0]")
open(f"{t}/cellWeight", "w").write(
    hdr + "internalField nonuniform List<scalar>\n%s\n(\n%s\n)\n;\n"
    "boundaryField\n{\n    \".*\" { type calculated; value uniform 1; }\n    \"(front|back)\" { type wedge; }\n}\n"
    % (n, "\n".join(w)))
print(f"cellWeight: {w.count(W)} of {n} cells weighted {W} (T > {Tcut:g} K)")

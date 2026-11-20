#!/usr/bin/env python3
"""Linear QSS couplings of ARC_GRI30_NOx22 from the generated tables (mechanisms/arc_gri30_nox22/arc_gri30_nox22_data.h):
an edge j -> i for every reaction direction with exactly one QSS reactant j that produces QSS species i (i != j);
directions with two QSS reactants are the truncated ones. Writes qss_edges.json next to this script.
Expected: 90 couplings, 11 truncated directions (as in the reduction report)."""
import json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
s = (HERE.parents[2] / "mechanisms/arc_gri30_nox22/arc_gri30_nox22_data.h").read_text()
def arr(n): return re.search(r"arc_" + n + r"\[[^\]]*\](?:\[[^\]]*\])?\s*=\s*\{(.*?)\};", s, re.S).group(1)
def flat(n, t=int): return [t(x) for x in arr(n).replace("\n", "").split(",") if x.strip()]
def rows(n, t): return [[t(x) for x in r.split(",") if x.strip()] for r in re.findall(r"\{([^{}]*)\}", arr(n))]
names = re.findall(r'"([^"]+)"', arr("names")); NODE = 22
nr, np_, rev = flat("nr"), flat("np"), flat("rev")
ri, rn, pi, pn = rows("ri", int), rows("rn", float), rows("pi", int), rows("pn", float)
edges, dropped = set(), 0
for r in range(len(nr)):
    dirs = [(ri[r][:nr[r]], rn[r][:nr[r]], pi[r][:np_[r]])]
    if rev[r]:
        dirs.append((pi[r][:np_[r]], pn[r][:np_[r]], ri[r][:nr[r]]))
    for R, Rn, P in dirs:
        q = [(k, n) for k, n in zip(R, Rn) if k >= NODE]
        if sum(n for _, n in q) >= 2:
            dropped += 1; continue
        if q:
            j = q[0][0]
            edges |= {(j, k) for k in P if k >= NODE and k != j}
json.dump({"names": names, "edges": sorted(edges), "truncated_directions": dropped}, open(HERE / "qss_edges.json", "w"))
print(f"{len(edges)} couplings, {dropped} truncated directions")

"""Smoke test of the COVLOOP leg export (openfoam/covloop/cells_to_npz.py, sentinel_from_cells.py) on a FAKE
OpenFOAM run built from physics states (no OpenFOAM needed), then scripts/25_coverage.py on the result.
Run: python -I tests/smoke_cell_export.py PAIRS.npz MODEL.npz WORKDIR   (~1 min)."""
import os, subprocess, sys
import numpy as np

pairs, model, work = sys.argv[1:4]
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
py = sys.executable
d = np.load(pairs, allow_pickle=True)
sp = [str(s) for s in d["species"]]
_, first = np.unique(d["T"], return_index=True)
rng = np.random.default_rng(0)
run = os.path.join(work, "fake_run")
for t, sel in (("0.001", first[::2]), ("0.002", first[1::2])):
    td = os.path.join(run, t)
    os.makedirs(os.path.join(td, "uniform"), exist_ok=True)

    def w(name, v):
        with open(os.path.join(td, name), "w") as f:
            f.write("FoamFile { version 2.0; format ascii; class volScalarField; object %s; }\n" % name)
            f.write("dimensions [0 0 0 0 0 0 0];\ninternalField nonuniform List<scalar>\n%d\n(\n" % len(v))
            f.write("\n".join(f"{x:.12g}" for x in v) + "\n);\nboundaryField {}\n")
    w("T", d["T"][sel])
    w("p", np.full(len(sel), 101325.0))
    w("V", rng.uniform(1e-12, 2e-12, len(sel)))
    for k, s in enumerate(sp):
        if s != "N2":                                    # N2 left out: written implicitly by OpenFOAM
            w(s, d["Y"][sel, k])
    open(os.path.join(td, "uniform", "time"), "w").write("value %s;\ndeltaT 2e-05;\n" % t)
cells, sent = os.path.join(work, "cells.npz"), os.path.join(work, "sentinel.npz")
subprocess.run([py, "-I", os.path.join(root, "openfoam/covloop/cells_to_npz.py"), run, cells, "--model", model],
               check=True)
c = np.load(cells, allow_pickle=True)
N = len(first)
assert len(c["T"]) == N and c["excluded"].all() and np.allclose(c["Y"].sum(1), 1.0, atol=1e-6)
assert np.allclose(c["dt"], 2e-5) and (c["mass"] > 0).all()
subprocess.run([py, "-I", os.path.join(root, "openfoam/covloop/sentinel_from_cells.py"), cells, sent,
                "--model", model, "--per-bin", "1", "--max-starts", "40", "--steps", "5", "25", "--np", "4"],
               check=True)
s = np.load(sent, allow_pickle=True)
assert len(s["T"]) > 10 and s["pass"].dtype == bool and s["excluded"].all()
out = os.path.join(work, "cov")
subprocess.run([py, "-I", os.path.join(root, "scripts/25_coverage.py"), "--mech",
                os.path.join(root, "mechanisms/arc_gri30_nox22/gri30_skel43.yaml"), "--cells", cells,
                "--sentinel", sent, "--out", out], check=True)
assert os.path.exists(os.path.join(out, "coverage.json"))
print("SMOKE OK")

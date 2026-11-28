#!/usr/bin/env python3
"""COVLOOP: write chemmanifold_tests.txt for an exported moe_top2 model, so the OpenFOAM plug-in (userChemStep,
`tests` entry) and the Fluent UDF can run their on-load selftest.

  python scripts/29_export_moe_tests.py MODEL_DIR pairs.npz [--n 300] [--seed 0]
MODEL_DIR holds moe.npz/.json and chemmanifold_model.txt (scripts/27). Cases: n states drawn across T and dt
from the pairs file (physics data), plus a few off-manifold and out-of-range cases so the flags are exercised.
Expected values come from a standalone gcc build of fluent/udf/chemmanifold_core.c (cm_make_tests.c); before
the file is written they are checked against the numpy model (CPUFastMoE) on every single-step case:
|dY| < 1e-10, |dT| < 0.5 K (Newton tolerance), same trust decision.
"""
import argparse, os, subprocess, sys, tempfile
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import numpy as np
from chemmanifold.moe import CPUFastMoE, project_elements


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model_dir")
    ap.add_argument("pairs")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    d = np.load(a.pairs, allow_pickle=True)
    fast = CPUFastMoE.load(os.path.join(a.model_dir, "moe.npz"))
    model_txt = os.path.join(a.model_dir, "chemmanifold_model.txt")
    # stratified draw over T (8 bins) so cold, igniting and burnt states are all present
    T, Y, dt = d["T"], d["Y"], d["dt"]
    edges = np.quantile(T, np.linspace(0, 1, 9))
    pick = np.concatenate([rng.choice(np.where((T >= lo) & (T <= hi))[0], a.n // 8, replace=True)
                           for lo, hi in zip(edges[:-1], edges[1:])])
    Tc, Yc, dtc = T[pick].copy(), Y[pick].copy(), dt[pick].copy()
    # flag exercisers: OH +5 % (off-manifold), dt above the model range (sub-stepping)
    k_oh = [str(s) for s in d["species"]].index("OH")
    Yo = Yc[:5].copy(); Yo[:, k_oh] += 0.05; Yo /= Yo.sum(1, keepdims=True)
    Tc = np.concatenate([Tc, Tc[:5], Tc[5:10]])
    Yc = np.concatenate([Yc, Yo, Yc[5:10]])
    dtc = np.concatenate([dtc, dtc[:5], np.full(5, 3.0 * fast.dt_max)])
    N, S = Yc.shape
    with tempfile.TemporaryDirectory() as tmp:
        exe = os.path.join(tmp, "cm_make_tests")
        subprocess.check_call(["gcc", "-O2", "-I", f"{ROOT}/fluent/udf", "-o", exe,
                               f"{ROOT}/fluent/udf/cm_make_tests.c", f"{ROOT}/fluent/udf/chemmanifold_core.c", "-lm"])
        st = os.path.join(tmp, "states.txt")
        with open(st, "w") as f:
            f.write(f"{N} {S}\n")
            for i in range(N):
                f.write(" ".join("%.17g" % v for v in (dtc[i], 101325.0, Tc[i], *Yc[i])) + "\n")
        tests = os.path.join(a.model_dir, "chemmanifold_tests.txt")
        subprocess.check_call([exe, model_txt, st, tests + ".tmp"])
    o = np.loadtxt(tests + ".tmp", skiprows=1)
    T_out, Y_out = o[:, 3 + S], o[:, 4 + S:4 + 2 * S]
    flags, n_sub = o[:, 4 + 2 * S].astype(int), o[:, -2].astype(int)
    # numpy cross-check on single-step, advanced cases
    one = (n_sub == 1) & (Tc >= fast.T_frozen)
    import cantera as ct
    sp = [str(s) for s in d["species"]]
    gri = ct.Solution("gri30.yaml")
    g = ct.Solution(thermo="ideal-gas", species=[gri.species(s) for s in sp])
    A = np.array([[g.n_atoms(k, e) * g.atomic_weights[e] / g.molecular_weights[k] for k in range(S)]
                  for e in range(g.n_elements)])
    R, info = fast.rate(Tc[one], Yc[one], dtc[one])
    Yn = project_elements(Yc[one], Yc[one] + dtc[one, None] * R, A)
    Tn = []
    for i, j in enumerate(np.where(one)[0]):
        g.TPY = Tc[j], 101325.0, Yc[j]; h = g.enthalpy_mass
        g.HPY = h, 101325.0, Yn[i]; Tn.append(g.T)
    dY = np.abs(Y_out[one] - Yn).max() if one.any() else 0.0
    dT = np.abs(T_out[one] - np.array(Tn)).max() if one.any() else 0.0
    print(f"{N} cases ({one.sum()} single-step checked vs numpy: max |dY| {dY:.2e}, max |dT| {dT:.2e} K); "
          f"flagged {np.mean(flags != 0):.1%}, sub-stepped {np.mean(n_sub > 1):.1%}")
    if dY > 1e-10 or dT > 0.5:
        os.remove(tests + ".tmp")
        sys.exit("C core and numpy disagree: test file NOT written")
    os.replace(tests + ".tmp", tests)
    print(f"wrote {tests}")


if __name__ == "__main__":
    main()

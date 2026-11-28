#!/usr/bin/env python3
"""COVLOOP step 1 driver: run every general sampling family, project to ARC22, balance on the coverage grid,
label with the ARC22 kernel at several dt, save pairs (docs/COVERAGE-LOOP-ROADMAP.md s. 4).

  python scripts/26_general_sampling.py configs/covloop_general.yaml OUT_DIR [--families R1,F1,...] [--np 8]
Output: OUT_DIR/states_<FAM>.npz (raw states, 43 sp) and OUT_DIR/pairs.npz with
  T, Y (N,22), dt, dY (N,22), family (N,), species (22,)   -- physics data, may be used for training;
  OUT_DIR/segments.npz (config `rollout:`): T0, Y0, dt, Tref (M,n), Yref (M,n,22) for the MoE rollout loss.
"""
import argparse, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from multiprocessing import Pool
import numpy as np
import yaml
import cantera as ct
from chemmanifold import general_sampling as gs
from chemmanifold.coverage import CoverageGrid

_ARC = None


def _label(args):
    global _ARC
    if _ARC is None:
        _ARC = gs.ARC()
    T, Y, dts = args
    try:
        r = gs.label_arc(_ARC, T, Y, dts)
    except Exception:
        return None
    return None if r[0] is None else r


_GAS = None


def _segment(args):
    global _ARC, _GAS
    if _ARC is None:
        _ARC, _GAS = gs.ARC(), ct.Solution(gs.SKEL)
    T, Y, dt, n = args
    try:
        Ts, Ys = gs.label_segment(_ARC, T, Y, dt, n, _GAS)
    except Exception:
        return None
    return None if Ts is None or not np.all(np.isfinite(Ts)) else (Ts, Ys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("out")
    ap.add_argument("--families")
    ap.add_argument("--np", type=int, default=4)
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(cfg.get("seed", 0))
    gas = ct.Solution(gs.SKEL)
    st = gs.Streams(gas)
    fams = a.families.split(",") if a.families else [f for f in gs.FAMILIES if f in cfg["families"]]
    raw = {}
    for f in fams:
        p = cfg["families"][f] or {}
        t0 = time.time()
        if f in ("P1", "P2", "P3"):
            base = gs.collect([s for k, v in raw.items() if k[0] in "RF" for s in v])
            sets = getattr(gs, "fam_" + f)(gas, base, rng, **p)
        elif f == "F5":
            sets = gs.fam_F5(gas, st, rng, raw.get("F2", []), **p)
        else:
            sets = getattr(gs, "fam_" + f)(gas, st, rng, **p)
        raw[f] = [(s[0], s[1]) for s in sets]
        T, Y = gs.collect(raw[f])
        np.savez(os.path.join(a.out, f"states_{f}.npz"), T=T, Y=Y)
        print(f"[{f}] {len(T)} states in {time.time() - t0:.0f} s", flush=True)

    arc = gs.ARC()
    proj = gs.Projector(gas, arc)
    T = np.concatenate([gs.collect(raw[f])[0] for f in fams])
    Y43 = np.concatenate([gs.collect(raw[f])[1] for f in fams])
    fam = np.concatenate([[f] * len(gs.collect(raw[f])[0]) for f in fams])
    ok = np.isfinite(T) & (T > 250) & (T < 3500)
    T, Y43, fam = T[ok], Y43[ok], fam[ok]
    Y22 = proj(Y43)

    # balance on the coverage grid: cap per bin
    grid = CoverageGrid(gs.SKEL)
    Zc, Tc, cc, dhc = grid.coordinates(T, Y43)
    b, _ = grid.bin_index(Zc, Tc, cc, dhc)
    cap = cfg.get("balance", {}).get("cap_per_bin", 2000)
    keep = []
    for bb in np.unique(b):
        i = np.where(b == bb)[0]
        keep.append(i if len(i) <= cap else rng.choice(i, cap, replace=False))
    keep = np.sort(np.concatenate(keep))
    T, Y22, fam = T[keep], Y22[keep], fam[keep]
    print(f"[balance] {len(keep)} states after cap {cap}/bin ({len(np.unique(b))} bins)", flush=True)

    dtc = cfg["dt"]
    lo, hi, n_dt = np.log10(dtc["min"]), np.log10(dtc["max"]), dtc.get("per_state", 2)
    jobs = [(T[i], Y22[i], 10 ** rng.uniform(lo, hi, n_dt)) for i in range(len(T))]
    t0 = time.time()
    with Pool(a.np) as pool:
        res = pool.map(_label, jobs, chunksize=16)
    P = {"T": [], "Y": [], "dt": [], "dY": [], "family": []}
    for i, r in enumerate(res):
        if r is None:
            continue
        dts, Yn, _ = r
        for d, yn in zip(dts, Yn):
            P["T"].append(T[i]); P["Y"].append(Y22[i]); P["dt"].append(d); P["dY"].append(yn - Y22[i])
            P["family"].append(fam[i])
    P = {k: np.array(v) for k, v in P.items()}
    np.savez(os.path.join(a.out, "pairs.npz"), species=np.array(arc.ode), **P)
    print(f"[label] {len(P['T'])} pairs in {time.time() - t0:.0f} s; failed states {sum(r is None for r in res)}")
    for f in fams:
        print(f"   {f}: {int((P['family'] == f).sum())} pairs")

    # reference segments for the rollout loss (states drawn across families, one dt each)
    rc = cfg.get("rollout", {})
    M, n = int(rc.get("n_segments", 0)), int(rc.get("steps", 24))
    if M > 0:
        hot = np.where(T > rc.get("T_min", 450.0))[0]
        pick = rng.choice(hot, min(M, len(hot)), replace=False)
        sdt = 10 ** rng.uniform(lo, np.log10(dtc["max"]), len(pick))
        t0 = time.time()
        with Pool(a.np) as pool:
            res = pool.map(_segment, [(T[i], Y22[i], d, n) for i, d in zip(pick, sdt)], chunksize=4)
        ok = [j for j, r in enumerate(res) if r is not None]
        np.savez(os.path.join(a.out, "segments.npz"), species=np.array(arc.ode),
                 T0=T[pick[ok]], Y0=Y22[pick[ok]], dt=sdt[ok], family=fam[pick[ok]],
                 Tref=np.array([res[j][0] for j in ok]), Yref=np.array([res[j][1] for j in ok]))
        print(f"[segments] {len(ok)}/{len(pick)} segments x {n} steps in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()

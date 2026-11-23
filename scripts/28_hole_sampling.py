#!/usr/bin/env python3
"""COVLOOP step 4: new physics sampling started from hole states (docs/COVERAGE-LOOP-ROADMAP.md s. 6).

  python scripts/28_hole_sampling.py OUT_DIR hole_states.npz [more ...] --general pairs_general.npz
      [--previous earlier_starts.npz ...] [--max-starts 15000] [--dt-min 1e-6 --dt-max 1e-3] [--np 8]
The hole states (CFD/DI states) are STARTING POINTS only: each is flagged `excluded` and never becomes a training
pair. Generic operators (no heat-loss model, no flow-derived mixing):
  S1 reactor from the jittered state (majors +/-3 %, radicals +/-0.25 decade, h +/-20 kJ/kg), 1-30 ms, arc length
  S2 relaxation from the state with radicals scaled 0.1-10x
  S3 random-pair mixing: start x start, and start x general-set state, then reaction
  S4 perturbation cloud inside the hole bin (box over the bin's species ranges), short integration
Labels with the ARC22 kernel at several dt. Output OUT_DIR/pairs_seeded.npz (+ starts_used.npz for deduplication).
"""
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from multiprocessing import Pool
import numpy as np
import cantera as ct
from chemmanifold import general_sampling as gs

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


def to43(gas, arc, Y22):
    """22 ARC species -> Cantera skel43 vector (QSS species 0)."""
    Y = np.zeros(gas.n_species)
    for k, s in enumerate(arc.ode):
        Y[gas.species_index(s)] = Y22[k]
    return Y / Y.sum()


def dedup(T, Y, prev, rtol=0.02):
    """Drop starts within a small normalised distance of earlier ones (this and previous iterations)."""
    f = np.column_stack([T / 2000.0, np.log10(np.maximum(Y, 1e-10)) / 10.0])
    keep, ref = [], [np.column_stack([p["T"] / 2000.0, np.log10(np.maximum(p["Y"], 1e-10)) / 10.0]) for p in prev]
    ref = np.concatenate(ref) if ref else np.zeros((0, f.shape[1]))
    kept = []
    for i in range(len(f)):
        if len(ref) and np.min(np.linalg.norm(ref - f[i], axis=1)) < rtol:
            continue
        if kept and np.min(np.linalg.norm(np.array(kept) - f[i], axis=1)) < rtol:
            continue
        kept.append(f[i]); keep.append(i)
    return np.array(keep, int)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("holes", nargs="+")
    ap.add_argument("--general", required=True)
    ap.add_argument("--previous", nargs="*", default=[])
    ap.add_argument("--max-starts", type=int, default=15000)
    ap.add_argument("--dt-min", type=float, default=1e-6)
    ap.add_argument("--dt-max", type=float, default=1e-3)
    ap.add_argument("--per-start", type=int, default=12, help="states generated per start (all operators)")
    ap.add_argument("--np", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    H = [dict(np.load(p, allow_pickle=True)) for p in a.holes]
    T0 = np.concatenate([h["T"] for h in H]); Y0 = np.concatenate([h["Y"] for h in H])
    B0 = np.concatenate([h["bin"] for h in H])
    prev = [dict(np.load(p)) for p in a.previous]
    k = dedup(T0, Y0, prev)
    if len(k) > a.max_starts:
        k = rng.choice(k, a.max_starts, replace=False)
    T0, Y0, B0 = T0[k], Y0[k], B0[k]
    np.savez(os.path.join(a.out, "starts_used.npz"), T=T0, Y=Y0, bin=B0, excluded=np.ones(len(T0), bool))
    print(f"[starts] {len(T0)} after deduplication")

    gas = ct.Solution(gs.SKEL); arc = gs.ARC(); proj = gs.Projector(gas, arc)
    G = np.load(a.general, allow_pickle=True)
    out_T, out_Y, op = [], [], []
    rs = gs.RADICALS
    for i in range(len(T0)):
        Y43 = to43(gas, arc, Y0[i])
        gas.TPY = T0[i], gs.P0, Y43; h0 = gas.enthalpy_mass
        n1 = max(1, a.per_start // 3)
        # S1 jittered reactor
        Tj, Yj = gs.perturb(gas, T0[i], Y43, rng, dh=0.0)
        gas.TPY = Tj, gs.P0, Yj
        gas.HPY = gas.enthalpy_mass + rng.uniform(-20e3, 20e3), gs.P0, gas.Y
        Ts, Ys = gs.reactor_traj(gas, gas.T, gas.Y, 10 ** rng.uniform(-3, np.log10(0.03)), n1)
        out_T += list(Ts); out_Y += list(Ys); op += ["S1"] * len(Ts)
        # S2 relaxation with scaled radicals
        Yr = Y43.copy()
        for s in rs:
            Yr[gas.species_index(s)] *= 10 ** rng.uniform(-1, 1)
        gas.HPY = h0, gs.P0, Yr / Yr.sum()
        Ts, Ys = gs.reactor_traj(gas, gas.T, gas.Y, 0.01, n1)
        out_T += list(Ts); out_Y += list(Ys); op += ["S2"] * len(Ts)
        # S3 mixing with another start or a general-set state
        if rng.uniform() < 0.5 and len(T0) > 1:
            j = rng.integers(len(T0)); Tb, Yb = T0[j], to43(gas, arc, Y0[j])
        else:
            j = rng.integers(len(G["T"])); Tb, Yb = G["T"][j], to43(gas, arc, G["Y"][j])
        gas.TPY = Tb, gs.P0, Yb; hb = gas.enthalpy_mass
        f = rng.uniform()
        gas.HPY = f * h0 + (1 - f) * hb, gs.P0, f * Y43 + (1 - f) * Yb
        Ts, Ys = gs.reactor_traj(gas, gas.T, gas.Y, 10 ** rng.uniform(-5, -2), max(2, n1 // 2))
        out_T += list(Ts); out_Y += list(Ys); op += ["S3"] * len(Ts)
        # S4 cloud inside the bin: other starts of the same bin give the box
        same = np.where(B0 == B0[i])[0]
        lo, hi = Y0[same].min(0), Y0[same].max(0)
        for _ in range(max(1, n1 // 2)):
            Yc = lo + rng.uniform(size=lo.size) * (hi - lo)
            Tc = rng.uniform(T0[same].min(), T0[same].max() + 1e-9)
            Ts, Ys = gs.reactor_traj(gas, Tc, to43(gas, arc, Yc), 1e-4, 3)
            out_T += list(Ts); out_Y += list(Ys); op += ["S4"] * len(Ts)
    out_T, out_Y = np.array(out_T), np.array(out_Y)
    Y22 = proj(out_Y)
    lo, hi = np.log10(a.dt_min), np.log10(a.dt_max)
    jobs = [(out_T[i], Y22[i], 10 ** rng.uniform(lo, hi, 2)) for i in range(len(out_T))]
    with Pool(a.np) as pool:
        res = pool.map(_label, jobs, chunksize=16)
    P = {"T": [], "Y": [], "dt": [], "dY": [], "family": []}
    for i, r in enumerate(res):
        if r is None:
            continue
        for d, yn in zip(r[0], r[1]):
            P["T"].append(out_T[i]); P["Y"].append(Y22[i]); P["dt"].append(d); P["dY"].append(yn - Y22[i])
            P["family"].append(op[i])
    P = {k: np.array(v) for k, v in P.items()}
    np.savez(os.path.join(a.out, "pairs_seeded.npz"), species=np.array(arc.ode), origin="physics-seeded", **P)
    print(f"[seeded] {len(P['T'])} pairs from {len(T0)} starts: " +
          ", ".join(f"{o} {int((P['family'] == o).sum())}" for o in ("S1", "S2", "S3", "S4")))


if __name__ == "__main__":
    main()

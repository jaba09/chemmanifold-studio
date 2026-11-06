"""Stage 22: training pairs for a FIXED-time-step surrogate, from an existing exploration.

Javier's "ladder" idea (2026-11-06): instead of one network that takes dt as an input, train one
network per time step (1e-6, 1e-5, 1e-4, 1e-3, 1e-2 s) and, in the CFD, split each cell's chemistry
step tau_cell into calls of these networks, largest first (1.36e-3 s = 1 x 1e-3 + 3 x 1e-4 + 6 x 1e-5).

This stage takes the input states of every pair of a finished exploration (the base data_dir, e.g.
the tix1 flow-informed exploration, stages 0-4), removes repeated input states (the base pairs each
state with up to dt_range.per_state different steps), and advances every state adiabatically at
constant pressure and enthalpy over the fixed dt with Cantera (GA18). The rollout-loss segments are
rebuilt the same way: K steps of the fixed dt from each segment's first state. So all five
fixed-dt models see exactly the same starting states; only the step differs.
Physics-only: nothing here comes from a CFD solution.

    python scripts/22_fixed_dt_pairs.py --config configs/burner_openfoam_tix1_dt1e-4.yaml

The config is the base config plus
    fixed_dt: {dt: 1.0e-4, base_data_dir: ../data/openfoam_tix1, workers: 4}
and its own data_dir. Stages 0-2 outputs of the base are linked, not copied.

Writes 03_samples/pairs_*.npz (same names and arrays as the base, dt = fixed dt everywhere)
       03_samples/segments.npz, 03_samples/fixed_dt_report.json
"""

import hashlib
import os
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from chemmanifold.io import STAGE_DIRS, base_parser, load_config, load_npz, save_json, save_npz, stage_dir

_GAS = None


def _init(mech):
    global _GAS
    import cantera as ct
    _GAS = ct.Solution(mech)


def _advance(args):
    """Advance each state (Y, h, P) by n_steps x dt; returns Y [N, n+1, Ns], T [N, n+1]."""
    import cantera as ct
    Y, h, P, dt, n_steps = args
    g = _GAS
    Ys = np.empty((len(Y), n_steps + 1, g.n_species))
    Ts = np.empty((len(Y), n_steps + 1))
    ok = np.ones(len(Y), bool)
    for i in range(len(Y)):
        try:
            g.HPY = h[i], P[i], Y[i]
            r = ct.IdealGasConstPressureReactor(g, clone=False)
            net = ct.ReactorNet([r])
            Ys[i, 0], Ts[i, 0] = g.Y, g.T
            for k in range(n_steps):
                net.advance((k + 1) * dt)
                Ys[i, k + 1], Ts[i, k + 1] = g.Y, g.T
        except Exception:      # a state Cantera cannot integrate is dropped, and counted
            ok[i] = False
    return Ys, Ts, ok


def advance_all(mech, Y, h, P, dt, n_steps, workers, chunk=500):
    jobs = [(Y[a:a + chunk], h[a:a + chunk], P[a:a + chunk], dt, n_steps) for a in range(0, len(Y), chunk)]
    with Pool(workers, initializer=_init, initargs=(mech,)) as pool:
        res = pool.map(_advance, jobs)
    return (np.concatenate([r[0] for r in res]), np.concatenate([r[1] for r in res]),
            np.concatenate([r[2] for r in res]))


def unique_inputs(d):
    """Indices of the first pair of every distinct input state (Y_in, T_in, P_in, h_in)."""
    seen, keep = set(), []
    for i in range(len(d["T_in"])):
        key = hashlib.blake2b(np.ascontiguousarray(
            np.r_[d["Y_in"][i], d["T_in"][i], d["P_in"][i], d["h_in"][i]]).tobytes(), digest_size=16).digest()
        if key not in seen:
            seen.add(key)
            keep.append(i)
    return np.asarray(keep, int)


def main(cfg):
    from chemmanifold.chemistry import mechanism_path
    fx = cfg["fixed_dt"]
    dt = float(fx["dt"])
    workers = int(fx.get("workers", os.cpu_count() or 1))
    base = (Path(cfg["_config_path"]).parent / fx["base_data_dir"]).resolve()
    root = Path(cfg["_config_path"]).parent / cfg["data_dir"]
    root.mkdir(parents=True, exist_ok=True)
    for st in ("flame", "envelope", "autoignition"):          # dt-independent upstream stages
        link = root / STAGE_DIRS[st]
        if not link.exists() and (base / STAGE_DIRS[st]).exists():
            link.symlink_to(base / STAGE_DIRS[st])
    src, out = base / STAGE_DIRS["samples"], stage_dir(cfg, "samples")
    mech = mechanism_path(cfg)
    rep = dict(dt=dt, base=str(base), files={})
    t0 = time.time()
    for f in sorted(src.glob("pairs_*.npz")):
        d = load_npz(f)
        keep = unique_inputs(d)
        Ys, Ts, ok = advance_all(mech, d["Y_in"][keep], d["h_in"][keep], d["P_in"][keep], dt, 1, workers)
        sel = keep[ok]
        arrays = {k: v[sel] for k, v in d.items() if len(v) == len(d["T_in"])}
        arrays["Y_out"], arrays["T_out"] = Ys[ok, 1], Ts[ok, 1]
        arrays["dt"] = np.full(len(sel), dt)
        save_npz(out / f.name, **arrays)
        rep["files"][f.name] = dict(base_pairs=len(d["T_in"]), unique_states=len(keep), dropped=int((~ok).sum()))
        print(f"  {f.name}: {len(d['T_in'])} base pairs -> {len(keep)} distinct states -> {len(sel)} pairs "
              f"at dt {dt:g} s ({time.time() - t0:.0f} s)", flush=True)
    seg_file = src / "segments.npz"
    if seg_file.exists():
        s = load_npz(seg_file)
        K = s["Y"].shape[1] - 1
        Ys, Ts, ok = advance_all(mech, s["Y"][:, 0], s["h"], s["P"], dt, K, workers, chunk=100)
        save_npz(out / "segments.npz", Y=Ys[ok], T=Ts[ok], P=s["P"][ok], h=s["h"][ok], dt=np.full(ok.sum(), dt))
        rep["segments"] = dict(n=int(ok.sum()), steps=K, dropped=int((~ok).sum()))
        print(f"  segments: {ok.sum()} x {K} steps of {dt:g} s", flush=True)
    rep["n_pairs"] = sum(v["unique_states"] - v["dropped"] for v in rep["files"].values())
    rep["wall_time_s"] = time.time() - t0
    save_json(out / "fixed_dt_report.json", rep)


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))

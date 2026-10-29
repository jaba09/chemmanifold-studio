"""Stage 3 (Section 2.4): phase-space arc-length importance sampling, induction seeding and
multi-stride pairing of the 0D trajectories.

Trajectories with wall heat loss (tau_q > 0, stage 2 regime 3) are not paired with their own later
points, whose enthalpy has changed: each selected state is advanced adiabatically at constant
pressure over stride * dt_base with Cantera instead, since the surrogate is a constant-(p, h)
chemistry step. These pairs get regime 3.

With `rollout_loss` in the config it also writes multi-step segments for stage 7's rollout loss:
`segments_per_traj` random starts per trajectory, each followed for `steps` adiabatic steps of
stride x dt_base (slices of the trajectory, or Cantera re-integration for wall-cooled ones).

With a top-level dt_range the strides span it log-uniformly (chemmanifold.io.dt_strides); those above
arclength.max_slice_stride, or below dt_base, are re-integrated with Cantera from the selected states
(dt_range.per_state of them per state, at random).

Equilibrium tails of stage 2 (tail_* arrays, optional) are paired the same way as wall-cooled
states, each advanced adiabatically over every stride with Cantera; these pairs get regime 6.

Reads  02_autoignition/traj_*.npz.
Writes 03_samples/pairs_0d.npz with arrays Y_in, T_in, P_in, h_in, dt, Y_out, T_out, regime, traj_id,
       03_samples/segments.npz with arrays Y [N, K+1, Ns], T [N, K+1], P, h, dt (rollout loss only).
"""

import numpy as np

from chemmanifold.boxcox import boxcox
from chemmanifold.chemistry import advance_const_p, make_gas
from chemmanifold.io import base_parser, dt_strides, load_config, load_npz, save_npz, stage_dir


def slice_strides(cfg):
    """(strides paired by slicing the trajectory, strides re-integrated with Cantera). With a wide
    dt_range, steps above arclength.max_slice_stride are advanced from the selected states instead,
    so short trajectories still give pairs at every dt."""
    st = dt_strides(cfg, "arclength")
    cap = cfg["arclength"].get("max_slice_stride", max(st))
    sliced = [s for s in st if isinstance(s, int) and s <= cap]
    return sliced or [1], [s for s in st if s not in sliced]


def select_indices(Y, T, cfg, rng):
    a = cfg["arclength"]
    s_max = max(slice_strides(cfg)[0])
    L = len(T)
    n_avail = L - s_max                        # admissible n in {0, ..., L - s_max - 1}
    T_lo, T_hi = T.min(), T.max()
    phi_star = np.hstack([boxcox(Y, a["boxcox_lambda"]),                  # Eq. 12
                          10.0 * ((T - T_lo) / max(T_hi - T_lo, 1e-12))[:, None]])
    ds = np.linalg.norm(np.diff(phi_star, axis=0), axis=1)[:n_avail]      # Eq. 13
    w = ds + a["floor_frac"] * ds.mean()                                   # Eq. 14
    n_seed = min(a["n_seed"], n_avail)
    seeds = np.arange(n_seed)                                              # chain-initiation seeding
    pool = np.arange(n_seed, n_avail)
    n_draw = min(max(a["n_pick"] - n_seed, 0), len(pool))
    if n_draw > 0:
        p = w[pool] / w[pool].sum()
        drawn = rng.choice(pool, size=n_draw, replace=False, p=p)
        return np.sort(np.concatenate([seeds, drawn]))
    return seeds


def main(cfg):
    rng = np.random.default_rng(cfg["seed"])
    files = sorted(stage_dir(cfg, "autoignition").glob("traj_*.npz"))
    if not files:
        raise FileNotFoundError("no trajectories found - run 02_autoignition_0d.py first")
    dt_base = cfg["autoignition"]["dt_base"]
    gas = make_gas(cfg)
    out = {k: [] for k in ("Y_in", "T_in", "P_in", "h_in", "dt", "Y_out", "T_out", "regime", "traj_id")}
    for f in files:
        tr = load_npz(f)
        tid = int(f.stem.split("_")[1])
        idx = select_indices(tr["Y"], tr["T"], cfg, rng)
        if "tail_T" in tr:
            tail = {k: tr[f"tail_{k}"] for k in ("Y", "T", "P", "h")}
            cooling_pairs(gas, tail, np.arange(len(tail["T"])), tid, cfg, out, regime=6)
        if float(tr.get("tau_q", 0.0)) > 0:
            cooling_pairs(gas, tr, idx, tid, cfg, out)
            continue
        sliced, readvanced = slice_strides(cfg)
        if readvanced:
            readvance_pairs(gas, tr, idx, tid, cfg, out, readvanced, rng)
        for s in sliced:                                                   # Eq. 15
            out["Y_in"].append(tr["Y"][idx])
            out["T_in"].append(tr["T"][idx])
            out["P_in"].append(tr["P"][idx])
            out["h_in"].append(tr["h"][idx])
            out["dt"].append(np.full(len(idx), s * dt_base))
            out["Y_out"].append(tr["Y"][idx + s])
            out["T_out"].append(tr["T"][idx + s])
            out["regime"].append(np.zeros(len(idx), dtype=np.int64))
            out["traj_id"].append(np.full(len(idx), tid))
    if cfg.get("rollout_loss"):
        rollout_segments(gas, files, cfg, rng)
    arrays = {k: np.concatenate(v) for k, v in out.items()}
    n_cool = int((arrays["regime"] == 3).sum())
    n_tail = int((arrays["regime"] == 6).sum())
    print(f"  {len(arrays['dt'])} 0D transition pairs from {len(files)} trajectories "
          f"({n_cool} of them adiabatic steps from wall-cooled states, {n_tail} from equilibrium tails)")
    save_npz(stage_dir(cfg, "samples") / "pairs_0d.npz", **arrays)


def rollout_segments(gas, files, cfg, rng):
    rl, dt_base = cfg["rollout_loss"], cfg["autoignition"]["dt_base"]
    K, s = rl["steps"], rl["stride"]
    seg = {k: [] for k in ("Y", "T", "P", "h", "dt")}
    for f in files:
        tr = load_npz(f)
        cooled = float(tr.get("tau_q", 0.0)) > 0
        L = len(tr["T"])
        n_start = L if cooled else L - K * s
        if n_start <= 0:
            continue
        for i in rng.choice(n_start, size=min(rl["segments_per_traj"], n_start), replace=False):
            if cooled:   # adiabatic continuation of a wall-cooled state
                gas.HPY = tr["h"][i], tr["P"][i], tr["Y"][i]
                Ys, Ts = [gas.Y.copy()], [gas.T]
                for _ in range(K):
                    advance_const_p(gas, s * dt_base)
                    Ys.append(gas.Y.copy())
                    Ts.append(gas.T)
                Ys, Ts = np.array(Ys), np.array(Ts)
            else:
                Ys, Ts = tr["Y"][i:i + K * s + 1:s], tr["T"][i:i + K * s + 1:s]
            for k, v in (("Y", Ys), ("T", Ts), ("P", tr["P"][i]), ("h", tr["h"][i]), ("dt", s * dt_base)):
                seg[k].append(v)
    arrays = {k: np.asarray(v) for k, v in seg.items()}
    print(f"  {len(arrays['dt'])} rollout segments of {K} x {s * dt_base * 1e6:.0f} us")
    save_npz(stage_dir(cfg, "samples") / "segments.npz", **arrays)


def readvance_pairs(gas, tr, idx, tid, cfg, out, strides, rng, regime=0):
    """Pairs at the time steps that slicing cannot give (fractions of dt_base, or longer than
    max_slice_stride): each selected state is advanced with Cantera over dt_range.per_state of them,
    drawn at random, so the data covers the dt range without multiplying its size."""
    dt_base = cfg["autoignition"]["dt_base"]
    k = min(int(cfg.get("dt_range", {}).get("per_state", len(strides))), len(strides))
    rows = {key: [] for key in out}
    for i in idx:
        for s in rng.choice(strides, size=k, replace=False):
            gas.HPY = tr["h"][i], tr["P"][i], tr["Y"][i]
            advance_const_p(gas, float(s) * dt_base)
            for key, v in (("Y_in", tr["Y"][i]), ("T_in", tr["T"][i]), ("P_in", tr["P"][i]), ("h_in", tr["h"][i]),
                           ("dt", float(s) * dt_base), ("Y_out", gas.Y.copy()), ("T_out", gas.T), ("regime", regime),
                           ("traj_id", tid)):
                rows[key].append(v)
    for key, v in rows.items():
        if v:
            out[key].append(np.asarray(v, dtype=np.int64 if key in ("regime", "traj_id") else float))


def cooling_pairs(gas, tr, idx, tid, cfg, out, regime=3, strides=None):
    if cfg.get("dt_range"):     # a few random time steps per state over the whole dt range
        readvance_pairs(gas, tr, idx, tid, cfg, out, strides or dt_strides(cfg, "arclength"),
                        np.random.default_rng(cfg["seed"] + tid + 1000 * regime), regime)
        return
    dt_base = cfg["autoignition"]["dt_base"]
    for s in strides or dt_strides(cfg, "arclength"):
        Y_out, T_out = [], []
        for i in idx:
            gas.HPY = tr["h"][i], tr["P"][i], tr["Y"][i]
            advance_const_p(gas, s * dt_base)
            Y_out.append(gas.Y.copy())
            T_out.append(gas.T)
        out["Y_in"].append(tr["Y"][idx])
        out["T_in"].append(tr["T"][idx])
        out["P_in"].append(tr["P"][idx])
        out["h_in"].append(tr["h"][idx])
        out["dt"].append(np.full(len(idx), s * dt_base))
        out["Y_out"].append(np.array(Y_out))
        out["T_out"].append(np.array(T_out))
        out["regime"].append(np.full(len(idx), regime, dtype=np.int64))
        out["traj_id"].append(np.full(len(idx), tid))


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))

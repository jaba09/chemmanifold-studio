"""Stage 3 (Section 2.4): phase-space arc-length importance sampling, induction seeding and
multi-stride pairing of the 0D trajectories.

Reads  02_autoignition/traj_*.npz.
Writes 03_samples/pairs_0d.npz with arrays Y_in, T_in, P_in, h_in, dt, Y_out, T_out, regime, traj_id.
"""

import numpy as np

from chemmanifold.boxcox import boxcox
from chemmanifold.io import base_parser, load_config, load_npz, save_npz, stage_dir


def select_indices(Y, T, cfg, rng):
    a = cfg["arclength"]
    s_max = max(a["strides"])
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
    out = {k: [] for k in ("Y_in", "T_in", "P_in", "h_in", "dt", "Y_out", "T_out", "regime", "traj_id")}
    for f in files:
        tr = load_npz(f)
        tid = int(f.stem.split("_")[1])
        idx = select_indices(tr["Y"], tr["T"], cfg, rng)
        for s in cfg["arclength"]["strides"]:                              # Eq. 15
            out["Y_in"].append(tr["Y"][idx])
            out["T_in"].append(tr["T"][idx])
            out["P_in"].append(tr["P"][idx])
            out["h_in"].append(tr["h"][idx])
            out["dt"].append(np.full(len(idx), s * dt_base))
            out["Y_out"].append(tr["Y"][idx + s])
            out["T_out"].append(tr["T"][idx + s])
            out["regime"].append(np.zeros(len(idx), dtype=np.int64))
            out["traj_id"].append(np.full(len(idx), tid))
    arrays = {k: np.concatenate(v) for k, v in out.items()}
    print(f"  {len(arrays['dt'])} autoignition transition pairs from {len(files)} trajectories")
    save_npz(stage_dir(cfg, "samples") / "pairs_0d.npz", **arrays)


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))

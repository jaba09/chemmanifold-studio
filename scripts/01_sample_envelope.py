"""Stage 1 (Section 2.2): scrambled Sobol sampling of the operating envelope.

premixed mode: (phi, T0, P0) -> columns id, phi, T0, P0, regime
flame mode:    (Z, alpha, heat loss, flamelet) of the burner flame at its fixed pressure
               -> columns id, Z, alpha, dh, flamelet, P0, regime
               Z is the Bilger mixture fraction (mapped through `z_knots`/`u_knots` so that seeds
               concentrate around Z_st), alpha the burnt fraction of the seed state and dh <= 0 the
               enthalpy loss, and `flamelet` the training flamelet (strain rate) whose state at Z
               is the burnt end. Seeds and PaSR streams are built by chemmanifold.flame.FlameSeeds.

Output: 01_envelope/initial_conditions.csv (regime 0 = 0D trajectory, 1 = PaSR micromixing).
"""

import numpy as np
import pandas as pd
from scipy.stats import qmc

from chemmanifold.flame import flame_pressure, flamelet_split, is_flame, z_from_unit
from chemmanifold.io import base_parser, load_config, load_npz, stage_dir


def main(cfg):
    env = cfg["envelope"]
    n = env["n_traj"]
    sobol = qmc.Sobol(d=4 if is_flame(cfg) else 3, scramble=True, seed=cfg["seed"])
    u = sobol.random(n)
    n0d = int(round(n * (1.0 - env["f_pasr"])))                               # Eq. 10
    regime = np.where(np.arange(n) < n0d, 0, 1)
    if is_flame(cfg):
        Z = z_from_unit(u[:, 0], env["z_knots"], env["u_knots"])
        alpha = env["alpha"][0] + u[:, 1] * (env["alpha"][1] - env["alpha"][0])
        dh = -u[:, 2] * env["heat_loss_max"] * alpha
        n_fl = int(load_npz(stage_dir(cfg, "flame") / "flamelets.npz")["strain_id"].max()) + 1
        train_ids, _ = flamelet_split(cfg, n_fl)
        flamelet = train_ids[np.minimum((u[:, 3] * len(train_ids)).astype(int), len(train_ids) - 1)]
        df = pd.DataFrame({"id": np.arange(n), "Z": Z, "alpha": alpha, "dh": dh, "flamelet": flamelet,
                           "P0": flame_pressure(cfg), "regime": regime})
    else:
        df = premixed_envelope(env, u, regime)
    out = stage_dir(cfg, "envelope") / "initial_conditions.csv"
    df.to_csv(out, index=False)
    print(f"  {n0d} 0D trajectories + {n - n0d} PaSR ensembles -> {out}")


def premixed_envelope(env, u, regime):
    phi = env["phi"][0] + u[:, 0] * (env["phi"][1] - env["phi"][0])          # Eq. 7
    T0 = env["T0"][0] + u[:, 1] * (env["T0"][1] - env["T0"][0])               # Eq. 8
    P0 = (env["P0_atm"][0] + u[:, 2] * (env["P0_atm"][1] - env["P0_atm"][0])) * 101325.0  # Eq. 9
    return pd.DataFrame({"id": np.arange(len(u)), "phi": phi, "T0": T0, "P0": P0, "regime": regime})


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))

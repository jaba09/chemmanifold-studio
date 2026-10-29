"""Stage 1 (Section 2.2): scrambled Sobol sampling of the operating envelope.

premixed mode: (phi, T0, P0) -> columns id, phi, T0, P0, regime
flame mode:    (Z, alpha, heat loss, flamelet[, cooling time]) of the burner flame at its fixed
               pressure -> columns id, Z, alpha, dh, psi, flamelet, tau_q, P0, regime
               Z is the Bilger mixture fraction (mapped through `z_knots`/`u_knots` so that seeds
               concentrate around Z_st), alpha the burnt fraction of the seed state and dh <= 0 the
               enthalpy loss, and `flamelet` the training flamelet (strain rate) whose state at Z
               is the burnt end. Seeds and PaSR streams are built by chemmanifold.flame.FlameSeeds.
               With `heat_loss: fraction` the loss is psi in [0, psi_max] times the largest physical
               loss of the seed (cooling it to `T_wall`), instead of a fixed dh up to heat_loss_max.
               A share `f_cool` of the 0D seeds become cooling reactors (regime 3): they lose heat
               towards T_wall with a time constant tau_q, log-uniform in `tau_q_range`, while reacting.
               `burnt_seeds` (optional) adds n regime-0 seeds that start nearly burnt (alpha in its
               range, small psi, Z log-uniform in Z_range): hot products that stage 2 follows towards
               equilibrium (with autoignition.equilibrium_tail), the state of the gas leaving the flame.

Output: 01_envelope/initial_conditions.csv (regime 0 = 0D trajectory, 1 = PaSR micromixing,
        3 = 0D trajectory with heat loss to the walls).
"""

import numpy as np
import pandas as pd
from scipy.stats import qmc

from chemmanifold.chemistry import make_gas
from chemmanifold.flame import FlameSeeds, flame_pressure, flamelet_split, is_flame, z_from_unit
from chemmanifold.io import base_parser, load_config, load_npz, stage_dir


def main(cfg):
    env = cfg["envelope"]
    n = env["n_traj"]
    cooling = is_flame(cfg) and env.get("f_cool", 0.0) > 0
    sobol = qmc.Sobol(d=(5 if cooling else 4) if is_flame(cfg) else 3, scramble=True, seed=cfg["seed"])
    u = sobol.random(n)
    n0d = int(round(n * (1.0 - env["f_pasr"])))                               # Eq. 10
    regime = np.where(np.arange(n) < n0d, 0, 1)
    n_cool = int(round(n0d * env.get("f_cool", 0.0)))
    regime[n0d - n_cool:n0d] = 3
    if is_flame(cfg):
        Z = z_from_unit(u[:, 0], env["z_knots"], env["u_knots"])
        alpha = env["alpha"][0] + u[:, 1] * (env["alpha"][1] - env["alpha"][0])
        n_fl = int(load_npz(stage_dir(cfg, "flame") / "flamelets.npz")["strain_id"].max()) + 1
        train_ids, _ = flamelet_split(cfg, n_fl)
        flamelet = train_ids[np.minimum((u[:, 3] * len(train_ids)).astype(int), len(train_ids) - 1)]
        if env.get("heat_loss", "absolute") == "fraction":
            psi = u[:, 2] * env.get("psi_max", 1.0)
            seeds = FlameSeeds(make_gas(cfg), cfg)
            dh = np.array([seeds.set_state(z, a, flamelet=j, psi=s)[1] - seeds.set_state(z, a, flamelet=j)[1]
                           for z, a, j, s in zip(Z, alpha, flamelet, psi)])
        else:
            psi = np.full(n, np.nan)
            dh = -u[:, 2] * env["heat_loss_max"] * alpha
        lo, hi = np.log10(env.get("tau_q_range", [1e-3, 1.0]))
        tau_q = np.where(regime == 3, 10.0 ** (lo + u[:, -1] * (hi - lo)), 0.0)
        df = pd.DataFrame({"id": np.arange(n), "Z": Z, "alpha": alpha, "dh": dh, "psi": psi,
                           "flamelet": flamelet, "tau_q": tau_q, "P0": flame_pressure(cfg), "regime": regime})
        if env.get("burnt_seeds") and env.get("heat_loss", "absolute") == "fraction":
            df = pd.concat([df, burnt_seeds(cfg, env["burnt_seeds"], train_ids, n)], ignore_index=True)
    else:
        df = premixed_envelope(env, u, regime)
    out = stage_dir(cfg, "envelope") / "initial_conditions.csv"
    df.to_csv(out, index=False)
    print(f"  {n0d} 0D trajectories ({int((regime == 3).sum())} with wall heat loss) + {n - n0d} PaSR "
          f"ensembles -> {out}")


def burnt_seeds(cfg, b, train_ids, id0):
    u = qmc.Sobol(d=4, scramble=True, seed=cfg["seed"] + 1).random(int(b["n"]))
    lz = np.log10(b["Z_range"])
    Z = 10.0 ** (lz[0] + u[:, 0] * (lz[1] - lz[0]))
    alpha = b["alpha"][0] + u[:, 1] * (b["alpha"][1] - b["alpha"][0])
    psi = u[:, 2] * b["psi_max"]
    flamelet = train_ids[np.minimum((u[:, 3] * len(train_ids)).astype(int), len(train_ids) - 1)]
    seeds = FlameSeeds(make_gas(cfg), cfg)
    dh = np.array([seeds.set_state(z, a, flamelet=j, psi=s)[1] - seeds.set_state(z, a, flamelet=j)[1]
                   for z, a, j, s in zip(Z, alpha, flamelet, psi)])
    print(f"  + {len(Z)} burnt seeds (Z {b['Z_range']}, alpha {b['alpha']}, psi <= {b['psi_max']})")
    return pd.DataFrame({"id": id0 + np.arange(len(Z)), "Z": Z, "alpha": alpha, "dh": dh, "psi": psi,
                         "flamelet": flamelet, "tau_q": 0.0, "P0": flame_pressure(cfg), "regime": 0})


def premixed_envelope(env, u, regime):
    phi = env["phi"][0] + u[:, 0] * (env["phi"][1] - env["phi"][0])          # Eq. 7
    T0 = env["T0"][0] + u[:, 1] * (env["T0"][1] - env["T0"][0])               # Eq. 8
    P0 = (env["P0_atm"][0] + u[:, 2] * (env["P0_atm"][1] - env["P0_atm"][0])) * 101325.0  # Eq. 9
    return pd.DataFrame({"id": np.arange(len(u)), "phi": phi, "T0": T0, "P0": P0, "regime": regime})


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))

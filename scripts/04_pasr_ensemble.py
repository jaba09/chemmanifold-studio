"""Stage 4 (Section 2.5): Partially Stirred Reactor stochastic micromixing ensemble.

premixed mode: fresh = unburnt (phi, T0, P0) mixture, burnt = its HP equilibrium.
flame mode:    fresh = stream mixture at Z (cold mixing line), burnt = the state of the row's training
               flamelet at the same Z; with `dh_scale_by_alpha` the heat loss dh is multiplied by
               alpha so that the cold mixing line keeps its 300 K inlet enthalpy.
               With `loss_fraction_range: [a, b]` the loss is instead psi ~ U(a, b) times the largest
               physical loss of each particle (cooling it to envelope.T_wall), so the ensemble spans
               adiabatic to wall-cooled mixtures.
               Also writes 03_samples/pairs_flamelet.npz (regime 2): the training flamelets' own
               states advanced by a random stride, so the radical pools that only diffusion
               creates in a flame are in the data, not just what 0D chemistry reaches.

Reads  01_envelope/initial_conditions.csv (regime 1 rows).
Writes 03_samples/pairs_pasr.npz with the same layout as pairs_0d.npz (regime = 1).
"""

import numpy as np
import pandas as pd

from chemmanifold.chemistry import advance_const_p, make_gas, set_unburnt
from chemmanifold.flame import FlameSeeds, case_label, heat_loss, is_flame, wall_temperature
from chemmanifold.io import base_parser, load_config, require, save_npz, stage_dir


def main(cfg):
    p = cfg["pasr"]
    rng = np.random.default_rng(cfg["seed"] + 1)
    dt_base = cfg["autoignition"]["dt_base"]
    ics = pd.read_csv(require(stage_dir(cfg, "envelope") / "initial_conditions.csv"))
    ics = ics[ics.regime == 1]
    gas = make_gas(cfg)
    seeds = FlameSeeds(gas, cfg) if is_flame(cfg) else None
    out = {k: [] for k in ("Y_in", "T_in", "P_in", "h_in", "dt", "Y_out", "T_out", "regime", "traj_id")}
    n_fail = 0
    for _, row in ics.iterrows():
        if seeds is not None:
            (Y_fresh, h_fresh), (Y_burnt, h_burnt) = seeds.fresh(row.Z), seeds.burnt(row.Z, row.flamelet)
        else:
            set_unburnt(gas, cfg, row.phi, row.T0, row.P0)
            Y_fresh, h_fresh = gas.Y.copy(), gas.enthalpy_mass
            gas.equilibrate("HP")                  # burnt state with identical elemental ratios
            Y_burnt, h_burnt = gas.Y.copy(), gas.enthalpy_mass

        alpha = rng.beta(p["beta_a"], p["beta_b"], size=p["n_particles"])
        fraction = seeds is not None and "loss_fraction_range" in p
        if fraction:
            psi = rng.uniform(*p["loss_fraction_range"], size=p["n_particles"])
            dh = np.zeros(p["n_particles"])
        else:
            dh = rng.uniform(*p["dh_range"], size=p["n_particles"])
            if p.get("dh_scale_by_alpha", False):
                dh = dh * alpha
        strides = rng.choice(p["strides"], size=p["n_particles"])
        for i, (a, d, s) in enumerate(zip(alpha, dh, strides)):
            Y_mix = (1 - a) * Y_fresh + a * Y_burnt                        # Eq. 16
            h_mix = (1 - a) * h_fresh + a * h_burnt
            try:
                if fraction:
                    d = heat_loss(gas, Y_mix, h_mix, psi[i], row.P0, wall_temperature(cfg))
                h_mix = h_mix + d
                gas.HPY = h_mix, row.P0, Y_mix
                if not 280.0 < gas.T < 3800.0:
                    raise ValueError("temperature out of range")
                Y_in, T_in = gas.Y.copy(), gas.T
                advance_const_p(gas, s * dt_base)
            except Exception:
                n_fail += 1
                continue
            out["Y_in"].append(Y_in)
            out["T_in"].append(T_in)
            out["P_in"].append(row.P0)
            out["h_in"].append(h_mix)
            out["dt"].append(s * dt_base)
            out["Y_out"].append(gas.Y.copy())
            out["T_out"].append(gas.T)
            out["regime"].append(1)
            out["traj_id"].append(int(row.id))
        print(f"  PaSR {int(row.id):04d}: {case_label(row.to_dict())}")
    arrays = {k: np.asarray(v) for k, v in out.items()}
    print(f"  {len(arrays['dt'])} PaSR transition pairs ({n_fail} rejected states)")
    save_npz(stage_dir(cfg, "samples") / "pairs_pasr.npz", **arrays)
    if seeds is not None:
        flamelet_pairs(gas, cfg, seeds, rng)


def flamelet_pairs(gas, cfg, seeds, rng):
    p, dt_base = cfg["pasr"], cfg["autoignition"]["dt_base"]
    out = {k: [] for k in ("Y_in", "T_in", "P_in", "h_in", "dt", "Y_out", "T_out", "regime", "traj_id")}
    for j in seeds.train_ids:
        for Y, h in zip(*seeds.raw[j]):
            s = rng.choice(p["strides"])
            gas.HPY = h, seeds.P, Y
            Y_in, T_in = gas.Y.copy(), gas.T
            advance_const_p(gas, s * dt_base)
            for k, v in (("Y_in", Y_in), ("T_in", T_in), ("P_in", seeds.P), ("h_in", h), ("dt", s * dt_base),
                         ("Y_out", gas.Y.copy()), ("T_out", gas.T), ("regime", 2), ("traj_id", int(j))):
                out[k].append(v)
    arrays = {k: np.asarray(v) for k, v in out.items()}
    print(f"  {len(arrays['dt'])} flamelet-state transition pairs from flamelets {list(seeds.train_ids)} "
          f"(held out for the coverage check: {list(seeds.heldout_ids)})")
    save_npz(stage_dir(cfg, "samples") / "pairs_flamelet.npz", **arrays)


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))

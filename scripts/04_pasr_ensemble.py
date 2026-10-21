"""Stage 4 (Section 2.5): Partially Stirred Reactor stochastic micromixing ensemble.

Reads  01_envelope/initial_conditions.csv (regime 1 rows).
Writes 03_samples/pairs_pasr.npz with the same layout as pairs_0d.npz (regime = 1).
"""

import numpy as np
import pandas as pd

from chemmanifold.chemistry import advance_const_p, make_gas, set_unburnt
from chemmanifold.io import base_parser, load_config, require, save_npz, stage_dir


def main(cfg):
    p = cfg["pasr"]
    rng = np.random.default_rng(cfg["seed"] + 1)
    dt_base = cfg["autoignition"]["dt_base"]
    ics = pd.read_csv(require(stage_dir(cfg, "envelope") / "initial_conditions.csv"))
    ics = ics[ics.regime == 1]
    gas = make_gas(cfg)
    out = {k: [] for k in ("Y_in", "T_in", "P_in", "h_in", "dt", "Y_out", "T_out", "regime", "traj_id")}
    n_fail = 0
    for _, row in ics.iterrows():
        set_unburnt(gas, cfg, row.phi, row.T0, row.P0)
        Y_fresh, h_fresh = gas.Y.copy(), gas.enthalpy_mass
        gas.equilibrate("HP")                      # burnt state with identical elemental ratios
        Y_burnt, h_burnt = gas.Y.copy(), gas.enthalpy_mass

        alpha = rng.beta(p["beta_a"], p["beta_b"], size=p["n_particles"])
        dh = rng.uniform(*p["dh_range"], size=p["n_particles"])
        strides = rng.choice(p["strides"], size=p["n_particles"])
        for a, d, s in zip(alpha, dh, strides):
            Y_mix = (1 - a) * Y_fresh + a * Y_burnt                        # Eq. 16
            h_mix = (1 - a) * h_fresh + a * h_burnt + d
            try:
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
        print(f"  PaSR {int(row.id):04d}: phi={row.phi:.2f} T0={row.T0:.0f}K P0={row.P0/101325:.2f}atm")
    arrays = {k: np.asarray(v) for k, v in out.items()}
    print(f"  {len(arrays['dt'])} PaSR transition pairs ({n_fail} rejected states)")
    save_npz(stage_dir(cfg, "samples") / "pairs_pasr.npz", **arrays)


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))

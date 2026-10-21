"""Stage 2 (Section 2.3): 0D adiabatic constant-pressure autoignition trajectories.

Reads  01_envelope/initial_conditions.csv (regime 0 rows).
Writes 02_autoignition/traj_XXXX.npz with arrays t, Y, T, P, h, qdot (+ phi, T0, P0).
"""

import numpy as np
import pandas as pd

from chemmanifold.chemistry import const_p_reactor, make_gas, set_unburnt
from chemmanifold.io import base_parser, load_config, require, save_npz, stage_dir


def integrate(gas, cfg, phi, T0, P0):
    a = cfg["autoignition"]
    set_unburnt(gas, cfg, phi, T0, P0)
    _, net = const_p_reactor(gas)
    n_max = int(round(a["t_max"] / a["dt_base"]))
    rec = {k: [] for k in ("t", "Y", "T", "P", "h", "qdot")}

    def record(t):
        rec["t"].append(t)
        rec["Y"].append(gas.Y.copy())
        rec["T"].append(gas.T)
        rec["P"].append(gas.P)
        rec["h"].append(gas.enthalpy_mass)
        rec["qdot"].append(gas.heat_release_rate)  # -sum(w_k * hbar_k), W/m^3

    record(0.0)
    streak = 0
    for n in range(1, n_max + 1):
        t = n * a["dt_base"]
        net.advance(t)
        record(t)
        if n > a["min_steps"]:                                     # Eq. 11
            burnt = rec["T"][-1] - T0 > a["dT_rise"]
            flat = abs(rec["T"][-1] - rec["T"][-2]) < a["dT_flat"]
            streak = streak + 1 if (burnt and flat) else 0
            if streak >= a["n_consecutive"]:
                break
    return {k: np.asarray(v) for k, v in rec.items()}


def main(cfg):
    ics = pd.read_csv(require(stage_dir(cfg, "envelope") / "initial_conditions.csv"))
    ics = ics[ics.regime == 0]
    out = stage_dir(cfg, "autoignition")
    gas = make_gas(cfg)
    for _, row in ics.iterrows():
        traj = integrate(gas, cfg, row.phi, row.T0, row.P0)
        i_ign = int(np.argmax(np.gradient(traj["T"], traj["t"])))
        print(f"  traj {int(row.id):04d}: phi={row.phi:.2f} T0={row.T0:.0f}K P0={row.P0/101325:.2f}atm "
              f"steps={len(traj['t'])} tau_ign={traj['t'][i_ign]*1e6:.0f}us")
        save_npz(out / f"traj_{int(row.id):04d}.npz", phi=row.phi, T0=row.T0, P0=row.P0, **traj)


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))

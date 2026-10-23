"""Stage 2 (Section 2.3): 0D adiabatic constant-pressure reactor trajectories.

premixed mode: autoignition of the fresh mixture at (phi, T0, P0); early termination per Eq. 11.
flame mode:    reaction of the seed state (Z, alpha, dh) toward equilibrium. Eq. 11's fixed 400 K
               rise is replaced by "at least `rise_frac` of this seed's own equilibrium rise", since
               seeds start anywhere between the cold mixing line and the burnt state; seeds that do
               not ignite within t_max are kept whole (slow low-temperature chemistry).

Reads  01_envelope/initial_conditions.csv (regime 0 rows).
Writes 02_autoignition/traj_XXXX.npz with arrays t, Y, T, P, h, qdot and the case parameters.
"""

import numpy as np
import pandas as pd

from chemmanifold.chemistry import const_p_reactor, make_gas
from chemmanifold.flame import case_label, is_flame, make_initializer
from chemmanifold.io import base_parser, load_config, require, save_npz, stage_dir


def required_rise(gas, cfg):
    """Temperature rise after which a flat trajectory counts as burnt (Eq. 11 in premixed mode)."""
    a = cfg["autoignition"]
    if not is_flame(cfg):
        return a["dT_rise"]
    state = gas.state
    T0 = gas.T
    gas.equilibrate("HP")
    rise = gas.T - T0
    gas.state = state
    return a["rise_frac"] * max(rise, 0.0)


def integrate(gas, cfg, init, case):
    a = cfg["autoignition"]
    init(case)
    T0 = gas.T
    dT_req = required_rise(gas, cfg)
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
            burnt = rec["T"][-1] - T0 >= dT_req
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
    init = make_initializer(gas, cfg)
    params = [c for c in ics.columns if c not in ("id", "regime")]
    for _, row in ics.iterrows():
        case = row.to_dict()
        traj = integrate(gas, cfg, init, case)
        i_ign = int(np.argmax(np.gradient(traj["T"], traj["t"])))
        print(f"  traj {int(row.id):04d}: {case_label(case)} T={traj['T'][0]:.0f}->{traj['T'][-1]:.0f}K "
              f"steps={len(traj['t'])} t_maxdT={traj['t'][i_ign]*1e6:.0f}us")
        save_npz(out / f"traj_{int(row.id):04d}.npz", **{k: case[k] for k in params}, **traj)


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))

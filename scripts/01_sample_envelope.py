"""Stage 1 (Section 2.2): scrambled Sobol sampling of the (phi, T0, P0) operating envelope.

Output: 01_envelope/initial_conditions.csv with columns id, phi, T0, P0, regime
(regime 0 = 0D autoignition, 1 = PaSR micromixing).
"""

import numpy as np
import pandas as pd
from scipy.stats import qmc

from chemmanifold.io import base_parser, load_config, stage_dir


def main(cfg):
    env = cfg["envelope"]
    n = env["n_traj"]
    sobol = qmc.Sobol(d=3, scramble=True, seed=cfg["seed"])
    u = sobol.random(n)

    phi = env["phi"][0] + u[:, 0] * (env["phi"][1] - env["phi"][0])          # Eq. 7
    T0 = env["T0"][0] + u[:, 1] * (env["T0"][1] - env["T0"][0])               # Eq. 8
    P0 = (env["P0_atm"][0] + u[:, 2] * (env["P0_atm"][1] - env["P0_atm"][0])) * 101325.0  # Eq. 9

    n0d = int(round(n * (1.0 - env["f_pasr"])))                               # Eq. 10
    regime = np.where(np.arange(n) < n0d, 0, 1)

    df = pd.DataFrame({"id": np.arange(n), "phi": phi, "T0": T0, "P0": P0, "regime": regime})
    out = stage_dir(cfg, "envelope") / "initial_conditions.csv"
    df.to_csv(out, index=False)
    print(f"  {n0d} autoignition + {n - n0d} PaSR initial conditions -> {out}")


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))

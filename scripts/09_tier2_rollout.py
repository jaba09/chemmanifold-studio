"""Stage 9 (Section 6.2): Tier 2 a-posteriori closed-loop autoregressive rollout vs Cantera.

Reads  04_prep/*, 06_models/<arch>/model.pt.
Writes 07_eval/<arch>/tier2_rollout.npz, 07_eval/<arch>/tier2.json, 07_eval/<arch>/tier2_rollout.png
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from chemmanifold.chemistry import make_gas
from chemmanifold.io import base_parser, load_config, save_json, save_npz, stage_dir
from chemmanifold.loading import load_surrogate
from chemmanifold.rollout import (cantera_trajectory, ignition_index, manifold_T_mae, phase_aligned_nrmse,
                                  surrogate_rollout)


def main(cfg, arch):
    r = cfg["evaluation"]["rollout"]
    model, scalers, _ = load_surrogate(cfg, arch)
    gas = make_gas(cfg)
    dt = r["stride"] * cfg["autoignition"]["dt_base"]
    P0 = r["P0_atm"] * 101325.0
    Y_ct, T_ct, h0 = cantera_trajectory(gas, cfg, r["phi"], r["T0"], P0, dt, r["n_steps"])
    Y_ml, T_ml = surrogate_rollout(model, Y_ct[0], T_ct[0], P0, h0, dt, r["n_steps"])
    Y_ml, T_ml = Y_ml[0], T_ml[0]
    t = np.arange(r["n_steps"] + 1) * dt

    i_ct, i_ml = ignition_index(T_ct, t), ignition_index(T_ml, t)
    tau_ct, tau_ml = t[i_ct], t[i_ml]
    report = dict(
        arch=arch, phi=r["phi"], T0=r["T0"], P0_atm=r["P0_atm"], dt=dt, n_steps=r["n_steps"],
        tau_ign_cantera_us=tau_ct * 1e6, tau_ign_ml_us=tau_ml * 1e6,
        tau_ign_rel_err_pct=float((tau_ml - tau_ct) / tau_ct * 100.0),          # Eq. 47
        T_final_cantera=float(T_ct[-1]), T_final_ml=float(T_ml[-1]),
        T_mae_manifold_K=manifold_T_mae(T_ml, T_ct),
        nrmse_Y_pct=phase_aligned_nrmse(Y_ml, Y_ct, i_ml, i_ct),
    )
    out_dir = stage_dir(cfg, "eval", arch)
    save_npz(out_dir / "tier2_rollout.npz", t=t, Y_ml=Y_ml, T_ml=T_ml, Y_ct=Y_ct, T_ct=T_ct)
    save_json(out_dir / "tier2.json", report)

    species = scalers["species"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(t * 1e6, T_ct, "k-", label="Cantera")
    axes[0].plot(t * 1e6, T_ml, "r--", label=arch)
    axes[0].set(xlabel="t [us]", ylabel="T [K]", title=f"tau error {report['tau_ign_rel_err_pct']:+.1f}%")
    axes[0].legend()
    for name in ("H2", "O2", "H2O", "OH", "H", "HO2"):
        k = species.index(name)
        line, = axes[1].semilogy(t * 1e6, np.maximum(Y_ct[:, k], 1e-12), "-", label=name)
        axes[1].semilogy(t * 1e6, np.maximum(Y_ml[:, k], 1e-12), "--", color=line.get_color())
    axes[1].set(xlabel="t [us]", ylabel="Y", ylim=(1e-10, 1), title="solid: Cantera, dashed: surrogate")
    axes[1].legend(ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "tier2_rollout.png", dpi=150)
    print(f"  tau_ign Cantera={tau_ct*1e6:.1f}us ML={tau_ml*1e6:.1f}us "
          f"({report['tau_ign_rel_err_pct']:+.1f}%), T_final {T_ct[-1]:.0f}/{T_ml[-1]:.0f} K")


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--arch", choices=["resnet_film", "chemnode"], default="resnet_film")
    a = p.parse_args()
    main(load_config(a.config), a.arch)

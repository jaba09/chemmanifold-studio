"""Stage 10 (Section 6.3): Tier 3 global (phi, T0, P0) operating-envelope certification.

Reads  04_prep/*, 06_models/<arch>/model.pt.
Writes 07_eval/<arch>/tier3.csv, 07_eval/<arch>/tier3_summary.json, 07_eval/<arch>/tier3_tau_error.png
"""

import itertools

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from chemmanifold.chemistry import make_gas
from chemmanifold.io import base_parser, load_config, save_json, stage_dir
from chemmanifold.loading import load_surrogate
from chemmanifold.rollout import (cantera_trajectory, ignition_index, manifold_T_mae, phase_aligned_nrmse,
                                  surrogate_rollout)


def main(cfg, arch):
    g = cfg["evaluation"]["envelope_grid"]
    r = cfg["evaluation"]["rollout"]
    model, _, _ = load_surrogate(cfg, arch)
    gas = make_gas(cfg)
    dt = r["stride"] * cfg["autoignition"]["dt_base"]
    n = r["n_steps"]
    t = np.arange(n + 1) * dt

    cases = list(itertools.product(g["phi"], g["T0"], g["P0_atm"]))
    refs = [cantera_trajectory(gas, cfg, phi, T0, P * 101325.0, dt, n) for phi, T0, P in cases]
    Y0 = np.array([ref[0][0] for ref in refs])
    T0s = np.array([ref[1][0] for ref in refs])
    h0 = np.array([ref[2] for ref in refs])
    P0 = np.array([c[2] * 101325.0 for c in cases])
    Y_ml, T_ml = surrogate_rollout(model, Y0, T0s, P0, h0, dt, n)  # whole grid as one batch

    rows = []
    for c, (Y_ct, T_ct, _), Ym, Tm in zip(cases, refs, Y_ml, T_ml):
        i_ct, i_ml = ignition_index(T_ct, t), ignition_index(Tm, t)
        ignited = T_ct[-1] - T_ct[0] > 400.0
        rows.append(dict(
            phi=c[0], T0=c[1], P0_atm=c[2], ignited_cantera=bool(ignited),
            tau_cantera_us=t[i_ct] * 1e6, tau_ml_us=t[i_ml] * 1e6,
            tau_err_pct=(t[i_ml] - t[i_ct]) / t[i_ct] * 100.0 if ignited and i_ct > 0 else np.nan,
            T_mae_manifold_K=manifold_T_mae(Tm, T_ct),
            nrmse_Y_pct=phase_aligned_nrmse(Ym, Y_ct, i_ml, i_ct),
            T_final_cantera=T_ct[-1], T_final_ml=Tm[-1],
        ))
    df = pd.DataFrame(rows)
    out_dir = stage_dir(cfg, "eval", arch)
    df.to_csv(out_dir / "tier3.csv", index=False)
    print(f"  wrote {out_dir / 'tier3.csv'}")
    summary = dict(
        arch=arch, n_cases=len(df),
        mean_abs_tau_err_pct=float(df.tau_err_pct.abs().mean()),
        max_abs_tau_err_pct=float(df.tau_err_pct.abs().max()),
        mean_T_mae_manifold_K=float(df.T_mae_manifold_K.mean()),
        max_T_mae_manifold_K=float(df.T_mae_manifold_K.max()),
        mean_nrmse_Y_pct=float(df.nrmse_Y_pct.mean()),
        max_nrmse_Y_pct=float(df.nrmse_Y_pct.max()),
    )
    save_json(out_dir / "tier3_summary.json", summary)

    Ps = sorted(set(g["P0_atm"]))
    fig, axes = plt.subplots(1, len(Ps), figsize=(4.2 * len(Ps), 3.6), squeeze=False)
    vmax = max(np.nanmax(df.tau_err_pct.abs()), 1.0)
    for ax, P in zip(axes[0], Ps):
        sub = df[df.P0_atm == P].pivot(index="phi", columns="T0", values="tau_err_pct")
        im = ax.imshow(sub.values, cmap="RdBu_r", vmin=-vmax, vmax=vmax, origin="lower", aspect="auto")
        ax.set_xticks(range(len(sub.columns)), [f"{v:.0f}" for v in sub.columns])
        ax.set_yticks(range(len(sub.index)), [f"{v:.2f}" for v in sub.index])
        for (i, j), v in np.ndenumerate(sub.values):
            ax.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=8)
        ax.set(xlabel="T0 [K]", ylabel="phi", title=f"tau_ign error [%], P0={P:g} atm")
    fig.colorbar(im, ax=axes[0].tolist(), shrink=0.8)
    fig.savefig(out_dir / "tier3_tau_error.png", dpi=150, bbox_inches="tight")
    print(f"  mean |tau err|={summary['mean_abs_tau_err_pct']:.1f}%  mean T MAE={summary['mean_T_mae_manifold_K']:.1f}K  "
          f"mean NRMSE_Y={summary['mean_nrmse_Y_pct']:.1f}%")


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--arch", choices=["resnet_film", "chemnode"], default="resnet_film")
    a = p.parse_args()
    main(load_config(a.config), a.arch)

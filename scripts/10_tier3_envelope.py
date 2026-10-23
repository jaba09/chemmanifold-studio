"""Stage 10 (Section 6.3): Tier 3 operating-envelope certification on the factorial grid
`evaluation.envelope_grid`: (phi, T0, P0_atm) in premixed mode, (Z, alpha) seeds in flame mode.

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
from chemmanifold.flame import make_initializer
from chemmanifold.io import base_parser, load_config, save_json, stage_dir
from chemmanifold.loading import load_surrogate
from chemmanifold.rollout import (cantera_trajectory, grid_cases, ignition_index, manifold_T_mae,
                                  phase_aligned_nrmse, surrogate_rollout)


def main(cfg, arch):
    g = cfg["evaluation"]["envelope_grid"]
    r = cfg["evaluation"]["rollout"]
    model, _, _ = load_surrogate(cfg, arch)
    gas = make_gas(cfg)
    dt = r["stride"] * cfg["autoignition"]["dt_base"]
    n = r["n_steps"]
    t = np.arange(n + 1) * dt

    keys, cases = grid_cases(cfg)
    values = list(itertools.product(*g.values()))
    init = make_initializer(gas, cfg)
    refs = [cantera_trajectory(gas, init, c, dt, n) for c in cases]
    Y0 = np.array([ref[0][0] for ref in refs])
    T0s = np.array([ref[1][0] for ref in refs])
    h0 = np.array([ref[2] for ref in refs])
    P0 = np.array([c["P0"] for c in cases])
    Y_ml, T_ml = surrogate_rollout(model, Y0, T0s, P0, h0, dt, n)  # whole grid as one batch

    rows = []
    for v, (Y_ct, T_ct, _), Ym, Tm in zip(values, refs, Y_ml, T_ml):
        i_ct, i_ml = ignition_index(T_ct, t), ignition_index(Tm, t)
        ignited = T_ct[-1] - T_ct[0] > 400.0
        rows.append(dict(
            **dict(zip(keys, v)), T_start=T_ct[0], ignited_cantera=bool(ignited),
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

    # heatmap of tau error over the first two grid axes, one panel per value of a third axis
    panel_key = keys[2] if len(keys) > 2 else None
    panels = sorted(set(df[panel_key])) if panel_key else [None]
    fig, axes = plt.subplots(1, len(panels), figsize=(4.2 * len(panels), 3.6), squeeze=False)
    vmax = max(np.nanmax(df.tau_err_pct.abs()) if df.tau_err_pct.notna().any() else 1.0, 1.0)
    for ax, pv in zip(axes[0], panels):
        sub = df if pv is None else df[df[panel_key] == pv]
        sub = sub.pivot(index=keys[0], columns=keys[1], values="tau_err_pct")
        im = ax.imshow(sub.values, cmap="RdBu_r", vmin=-vmax, vmax=vmax, origin="lower", aspect="auto")
        ax.set_xticks(range(len(sub.columns)), [f"{v:g}" for v in sub.columns])
        ax.set_yticks(range(len(sub.index)), [f"{v:g}" for v in sub.index])
        for (i, j), v in np.ndenumerate(sub.values):
            ax.text(j, i, "n/a" if np.isnan(v) else f"{v:+.1f}", ha="center", va="center", fontsize=8)
        title = "tau_ign error [%]" + ("" if pv is None else f", {panel_key}={pv:g}")
        ax.set(xlabel=keys[1], ylabel=keys[0], title=title)
    fig.colorbar(im, ax=axes[0].tolist(), shrink=0.8)
    fig.savefig(out_dir / "tier3_tau_error.png", dpi=150, bbox_inches="tight")
    print(f"  mean |tau err|={summary['mean_abs_tau_err_pct']:.1f}%  mean T MAE={summary['mean_T_mae_manifold_K']:.1f}K  "
          f"mean NRMSE_Y={summary['mean_nrmse_Y_pct']:.1f}%")


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--arch", choices=["resnet_film", "chemnode"], default="resnet_film")
    a = p.parse_args()
    main(load_config(a.config), a.arch)

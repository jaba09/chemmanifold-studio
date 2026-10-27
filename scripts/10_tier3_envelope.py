"""Stage 10 (Section 6.3): Tier 3 operating-envelope certification on the factorial grid
`evaluation.envelope_grid`: (phi, T0, P0_atm) in premixed mode, (Z, alpha) seeds in flame mode.

Flame mode with `evaluation.cooled_grid` (Z x psi): also rolls out burnt gas (alpha = 1) that has
lost a fraction psi of its heat to the walls, at the Fluent time step `cooled_rollout.stride` x
dt_base, and compares T and species with Cantera point by point in time (no ignition to align).
Writes 07_eval/<arch>/tier3_cooled.csv and adds its means to tier3_summary.json.

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
from chemmanifold.flame import flame_pressure, make_initializer
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
    if cfg["evaluation"].get("cooled_grid"):
        summary.update(cooled_cases(cfg, model, gas, init, out_dir))
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


def cooled_cases(cfg, model, gas, init, out_dir):
    g, r = cfg["evaluation"]["cooled_grid"], cfg["evaluation"].get("cooled_rollout", {})
    dt = r.get("stride", 4) * cfg["autoignition"]["dt_base"]
    n = r.get("n_steps", 250)
    P = flame_pressure(cfg)
    cases = [{"Z": float(z), "alpha": 1.0, "psi": float(s), "P0": P} for z, s in itertools.product(g["Z"], g["psi"])]
    refs = [cantera_trajectory(gas, init, c, dt, n) for c in cases]
    Y_ml, T_ml = surrogate_rollout(model, np.array([x[0][0] for x in refs]), np.array([x[1][0] for x in refs]),
                                   np.full(len(cases), P), np.array([x[2] for x in refs]), dt, n)
    rows = []
    for c, (Y_ct, T_ct, _), Ym, Tm in zip(cases, refs, Y_ml, T_ml):
        rows.append(dict(Z=c["Z"], psi=c["psi"], T_start=T_ct[0], T_final_cantera=T_ct[-1], T_final_ml=Tm[-1],
                         T_mae_K=float(np.abs(Tm - T_ct).mean()),
                         nrmse_Y_pct=float(np.linalg.norm(Ym - Y_ct) / np.linalg.norm(Y_ct) * 100.0)))
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "tier3_cooled.csv", index=False)
    print(f"  cooled burnt gas ({len(df)} cases, {n} x {dt * 1e6:.0f} us): mean T MAE {df.T_mae_K.mean():.1f} K "
          f"(max {df.T_mae_K.max():.1f} K), mean NRMSE_Y {df.nrmse_Y_pct.mean():.1f}%")
    return dict(cooled_mean_T_mae_K=float(df.T_mae_K.mean()), cooled_max_T_mae_K=float(df.T_mae_K.max()),
                cooled_mean_nrmse_Y_pct=float(df.nrmse_Y_pct.mean()))


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--arch", choices=["resnet_film", "chemnode"], default="resnet_film")
    a = p.parse_args()
    main(load_config(a.config), a.arch)

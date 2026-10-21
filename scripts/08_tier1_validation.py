"""Stage 8 (Section 6.1): Tier 1 a-priori single-step validation and conservation audit.

Reads  04_prep/*, 06_models/<arch>/model.pt.
Writes 07_eval/<arch>/tier1.json, 07_eval/<arch>/tier1_parity.png
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

from chemmanifold.io import base_parser, load_config, load_npz, save_json, stage_dir
from chemmanifold.loading import load_surrogate


def r2(pred, true):
    ss_tot = np.sum((true - true.mean(0)) ** 2)
    return float(1.0 - np.sum((pred - true) ** 2) / ss_tot) if ss_tot > 0 else float("nan")


def main(cfg, arch):
    model, scalers, thermo = load_surrogate(cfg, arch)
    ds = load_npz(stage_dir(cfg, "prep") / "dataset.npz")
    m = ds["is_val"]
    t = {k: torch.as_tensor(ds[k][m], dtype=torch.float64) for k in ("Y_in", "T_in", "P_in", "h_in", "dt")}
    with torch.no_grad():
        out = model(t["Y_in"], t["T_in"], t["P_in"], t["h_in"], t["dt"])
        yt_phys = model.encode_Y(out["Y"]).numpy()
    sdy = np.asarray(scalers["sigma_dy"])
    v_true = (ds["yt_out"][m] - ds["yt_in"][m]) / sdy
    v_pred = (yt_phys - ds["yt_in"][m]) / sdy                         # projected prediction
    v_cand = (out["yt_cand"].numpy() - ds["yt_in"][m]) / sdy         # raw network candidate
    A = thermo["A"]
    Y_hat = out["Y"].numpy()
    e_elem = float(np.max(np.abs(Y_hat @ A.T - ds["Y_in"][m] @ A.T)))  # Eq. 45
    e_sum = float(np.max(np.abs(Y_hat.sum(1) - ds["Y_in"][m].sum(1))))
    T_err = out["T"].numpy() - ds["T_out"][m]
    species = scalers["species"]
    report = dict(
        arch=arch, n_val=int(m.sum()),
        r2_dy_projected=r2(v_pred, v_true), r2_dy_candidate=r2(v_cand, v_true),
        r2_dy_per_species={s: r2(v_pred[:, k], v_true[:, k]) for k, s in enumerate(species)},
        elemental_residual_max=e_elem, mass_sum_residual_max=e_sum,
        min_mass_fraction=float(Y_hat.min()),
        T_mae_K=float(np.mean(np.abs(T_err))), T_max_err_K=float(np.max(np.abs(T_err))),
        by_regime={name: dict(r2_dy=r2(v_pred[ds["regime"][m] == g], v_true[ds["regime"][m] == g]),
                              T_mae_K=float(np.mean(np.abs(T_err[ds["regime"][m] == g]))))
                   for g, name in ((0, "autoignition_0D"), (1, "PaSR_micromixing"))},
    )
    out_dir = stage_dir(cfg, "eval", arch)
    save_json(out_dir / "tier1.json", report)

    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    axes[0].scatter(v_true.ravel(), v_pred.ravel(), s=1, alpha=0.3)
    lim = [v_true.min(), v_true.max()]
    axes[0].plot(lim, lim, "k--", lw=0.8)
    axes[0].set(xlabel="v_true", ylabel="v_pred", title=f"Box-Cox increments, R2={report['r2_dy_projected']:.4f}")
    axes[1].scatter(ds["T_out"][m], out["T"].numpy(), s=2, alpha=0.4)
    lim = [ds["T_out"][m].min(), ds["T_out"][m].max()]
    axes[1].plot(lim, lim, "k--", lw=0.8)
    axes[1].set(xlabel="T Cantera [K]", ylabel="T surrogate [K]", title=f"MAE={report['T_mae_K']:.2f} K")
    fig.tight_layout()
    fig.savefig(out_dir / "tier1_parity.png", dpi=150)
    print(f"  R2_dy*={report['r2_dy_projected']:.4f}  E_elem={e_elem:.2e}  T_MAE={report['T_mae_K']:.2f} K")


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--arch", choices=["resnet_film", "chemnode"], default="resnet_film")
    a = p.parse_args()
    main(load_config(a.config), a.arch)

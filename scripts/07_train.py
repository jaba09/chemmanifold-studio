"""Stage 7 (Section 5): train a hard-constrained surrogate with pushforward manifold perturbation.

Reads  04_prep/dataset.npz, 04_prep/scalers.json, 04_prep/thermo.npz, 05_manifold/manifold_report.json.
Writes 06_models/<arch>/model.pt, 06_models/<arch>/history.csv, 06_models/<arch>/loss.png

Composite loss (Eq. 44), all terms computed per batch:
  L_inc   MSE between normalized step velocities v_pred and v_true (Eq. 43), with v_pred taken
          from the raw network candidate relative to the clean input state.
  L_mass  mean squared elemental residual A(Y_cand - Y_t) of the *unprojected* candidate (in units
          of 1e-2), so the network itself learns to be near-conservative and the projection stays small.
  L_T     MSE of the Newton-recovered temperature, normalized by the std of the training dT.
  L_equil MSE of v_pred on near-equilibrium pairs (|v_true|_inf < threshold): no spurious drift.
  L_AE    autoencoder reconstruction |D(E(y~_t)) - y~_t|^2 (Phy-ChemNODE only).
"""

import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from chemmanifold.io import base_parser, load_config, load_npz, stage_dir
from chemmanifold.loading import latent_dim, load_prep
from chemmanifold.models import build_surrogate, resolve_device

MASS_SCALE = 1e-2


def to_tensors(ds, mask):
    keys = ("Y_in", "T_in", "P_in", "h_in", "dt", "Y_out", "T_out", "yt_in", "yt_out")
    return {k: torch.as_tensor(ds[k][mask], dtype=torch.float64) for k in keys}


def batch_losses(model, b, A, sigma_dT, weights, eq_thr, alpha):
    sdy = model.sigma_dy
    Y_in, T_in = b["Y_in"], b["T_in"]
    if alpha > 0:  # pushforward perturbation, projected back onto the polytope (Section 5.2)
        noisy = b["yt_in"] + alpha * sdy * torch.randn_like(b["yt_in"])
        Y_in, T_in = model.project_state(b["Y_in"], noisy, b["h_in"], b["T_in"])
    out = model(Y_in, T_in, b["P_in"], b["h_in"], b["dt"])
    v_true = (b["yt_out"] - b["yt_in"]) / sdy
    v_pred = (out["yt_cand"] - b["yt_in"]) / sdy
    L = {}
    L["inc"] = ((v_pred - v_true) ** 2).mean()
    L["mass"] = ((((out["Y_cand"] - b["Y_in"]) @ A.T) / MASS_SCALE) ** 2).mean()
    L["T"] = (((out["T"] - b["T_out"]) / sigma_dT) ** 2).mean()
    eq = v_true.abs().amax(-1) < eq_thr
    L["equil"] = (v_pred[eq] ** 2).mean() if eq.any() else v_pred.sum() * 0.0
    ae = out["extras"].get("ae_recon")
    L["ae"] = ((ae.to(torch.float64) - out["yt_in"]) ** 2).mean() if ae is not None else v_pred.sum() * 0.0
    total = sum(weights[k] * L[k] for k in L)
    return total, {k: float(v.detach()) for k, v in L.items()}, out


def main(cfg, arch):
    tc = cfg["training"]
    torch.manual_seed(cfg["seed"])
    if tc.get("threads", "auto") != "auto":
        torch.set_num_threads(int(tc["threads"]))
    ds = load_npz(stage_dir(cfg, "prep") / "dataset.npz")
    scalers, thermo = load_prep(cfg)
    d = latent_dim(cfg)
    model = build_surrogate(arch, cfg, scalers, thermo, latent_dim=d)
    device = resolve_device(tc.get("device", "auto"))
    model.net.to(device)
    A = model.project.A

    train, val = to_tensors(ds, ~ds["is_val"]), to_tensors(ds, ds["is_val"])
    sigma_dT = float(torch.clamp((train["T_out"] - train["T_in"]).std(), min=1.0))
    n_train = len(train["dt"])
    bs, E = tc["batch_size"], tc["epochs"]
    steps = (n_train + bs - 1) // bs
    opt = torch.optim.AdamW(model.net.parameters(), lr=tc["lr_max"], weight_decay=tc["weight_decay"])
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=tc["lr_max"], total_steps=E * steps)
    w = tc["loss_weights"]

    out_dir = stage_dir(cfg, "models", arch)
    hist, best = [], np.inf
    n_params = sum(p.numel() for p in model.net.parameters())
    print(f"  {arch}: {n_params} parameters, latent d={d}, {n_train} train pairs, {E} epochs, "
          f"network on {device}, {torch.get_num_threads()} CPU threads")
    for e in range(1, E + 1):
        t0 = time.time()
        alpha = tc["noise_amp"] * max(0.0, 1.0 - e / (tc["noise_end_frac"] * E))
        model.train()
        perm = torch.randperm(n_train)
        agg = {}
        for i in range(steps):
            idx = perm[i * bs:(i + 1) * bs]
            b = {k: v[idx] for k, v in train.items()}
            loss, parts, _ = batch_losses(model, b, A, sigma_dT, w, tc["equil_threshold"], alpha)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.net.parameters(), 1.0)
            opt.step()
            sched.step()
            for k, v in parts.items():
                agg[k] = agg.get(k, 0.0) + v / steps
        model.eval()
        with torch.no_grad():
            vloss, vparts, vout = batch_losses(model, val, A, sigma_dT, w, tc["equil_threshold"], 0.0)
            T_mae = float((vout["T"] - val["T_out"]).abs().mean())
        row = {"epoch": e, "alpha": alpha, **{f"train_{k}": v for k, v in agg.items()},
               **{f"val_{k}": v for k, v in vparts.items()}, "val_total": float(vloss), "val_T_mae": T_mae}
        hist.append(row)
        if float(vloss) < best:
            best = float(vloss)
            state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
            torch.save({"arch": arch, "latent_dim": d, "state_dict": state, "epoch": e},
                       out_dir / "model.pt")
        if e == 1 or e % 5 == 0 or e == E:
            print(f"  epoch {e:3d}  alpha={alpha:.4f}  train_inc={agg['inc']:.4f}  val_inc={vparts['inc']:.4f}  "
                  f"val_T_MAE={T_mae:.2f}K  ({time.time() - t0:.1f}s)")

    h = pd.DataFrame(hist)
    h.to_csv(out_dir / "history.csv", index=False)
    fig, ax = plt.subplots(figsize=(5, 3.5))
    for k in ("train_inc", "val_inc", "val_T", "val_mass"):
        ax.semilogy(h.epoch, h[k], label=k)
    ax.set(xlabel="epoch", ylabel="loss", title=arch)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "loss.png", dpi=150)
    print(f"  best val loss {best:.4f} -> {out_dir / 'model.pt'}")


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--arch", choices=["resnet_film", "chemnode"], default="resnet_film")
    a = p.parse_args()
    main(load_config(a.config), a.arch)

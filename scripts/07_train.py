"""Stage 7 (Section 5): train a hard-constrained surrogate with pushforward manifold perturbation.

Reads  04_prep/dataset.npz, 04_prep/scalers.json, 04_prep/thermo.npz, 05_manifold/manifold_report.json.
Writes 06_models/<arch>/model.pt, 06_models/<arch>/history.csv, 06_models/<arch>/loss.png,
       06_models/<arch>/train_info.json (when, how long, where, best epoch) and
       06_models/<arch>/config_used.yaml (the exact config, for the model registry, stage 15)

Composite loss (Eq. 44), all terms computed per batch:
  L_inc   MSE between normalized step velocities v_pred and v_true (Eq. 43), with v_pred taken
          from the raw network candidate relative to the clean input state. With
          training.dt_scaled_loss the increments (and dT in L_T) are normalized by their std at the
          pair's own time step, so every dt of a wide dt_range weighs the same.
  L_mass  mean squared elemental residual A(Y_cand - Y_t) of the *unprojected* candidate (in units
          of 1e-2), so the network itself learns to be near-conservative and the projection stays small.
  L_T     MSE of the Newton-recovered temperature, normalized by the std of the training dT.
  L_equil MSE of v_pred on near-equilibrium pairs (|v_true|_inf < threshold): no spurious drift.
  L_rad   (optional, `training.radical_loss`) relative error of the radicals' increments (OH, H, O,
          HO2 by default): |dY_pred - dY_true| over |dY_true| + rel_floor * Y + abs_floor, in mass
          fractions after the projection, through a pseudo-Huber penalty. The Box-Cox increments of
          L_inc are scaled by their std over the whole data set, set by the flame, so an increment
          of OH that is 10x the true one in burnt gas near equilibrium costs almost nothing there.
  L_fp    (optional, `training.fixed_point`) on the equilibrium pairs (regime 9, F(Y_eq, dt) = Y_eq):
          every species' change relative to rel_floor * Y_eq + abs_floor, and the temperature change
          in units of T_tol, also pseudo-Huber: equilibrium must be a fixed point of the step.
  L_AE    autoencoder reconstruction |D(E(y~_t)) - y~_t|^2 (Phy-ChemNODE only).
  L_roll  (optional, `rollout_loss`) multi-step loss: the surrogate is chained over K steps from the
          first state of a segment (03_samples/segments.npz) and every step's Box-Cox state (in units
          of sigma_dy) and temperature (in units of the training dT std) are compared with Cantera.
          It penalizes the error growth of closed-loop use, which single-step pairs do not see.
          Switched on after `start_frac` of the epochs, once the single-step map is reasonable.

Warm start: `training.init_from` (a parent model.pt, with preprocess.scalers_from set to the
parent's scalers.json so the units match) starts from the parent network instead of from the
identity map; use fewer epochs, a lower lr_max (and `pct_start`, the OneCycle warm-up share) and
a weaker pushforward noise. `training.patience` stops when the validation loss has not improved for
that many epochs after the noise is off; the parent is the epoch-0 checkpoint to beat. `--seed` sets the training seed (weights, batches,
noise; the data stay those of the config's seed) and `--tag` names the output 06_models/<arch>_<tag>,
so several seeds of one configuration live side by side.
"""

import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import yaml

from chemmanifold.io import base_parser, load_config, load_npz, save_json, stage_dir
from chemmanifold.loading import latent_dim, load_prep, model_dir_name
from chemmanifold.models import build_surrogate, resolve_device

MASS_SCALE = 1e-2


def to_tensors(ds, mask):
    keys = ("Y_in", "T_in", "P_in", "h_in", "dt", "Y_out", "T_out", "yt_in", "yt_out")
    d = {k: torch.as_tensor(ds[k][mask], dtype=torch.float64) for k in keys}
    d["regime"] = torch.as_tensor(ds["regime"][mask], dtype=torch.long)
    return d


def pseudo_huber(r):
    """~r^2/2 for small r, ~|r| for large: relative errors of 100x must not swamp the batch."""
    return torch.sqrt(1.0 + r ** 2) - 1.0


class RelativeTerms:
    """L_rad and L_fp (training.radical_loss, training.fixed_point); both read mass fractions."""

    def __init__(self, tc, species):
        rl, fp = tc.get("radical_loss") or {}, tc.get("fixed_point") or {}
        self.rad = [species.index(s) for s in rl.get("species", ["OH", "H", "O", "HO2"]) if s in species] if rl else []
        self.rad_rel, self.rad_abs = float(rl.get("rel_floor", 0.01)), float(rl.get("abs_floor", 1e-10))
        self.fp = bool(fp)
        self.fp_rel, self.fp_abs = float(fp.get("rel_floor", 0.01)), float(fp.get("abs_floor", 1e-9))
        self.fp_T, self.fp_regime = float(fp.get("T_tol", 1.0)), int(fp.get("regime", 9))

    def __call__(self, b, out, L):
        zero = out["Y"].sum() * 0.0
        if self.rad:
            Yi, Yo, Yp = b["Y_in"][:, self.rad], b["Y_out"][:, self.rad], out["Y"][:, self.rad]
            den = (Yo - Yi).abs() + self.rad_rel * torch.maximum(Yi, Yo) + self.rad_abs
            L["rad"] = pseudo_huber((Yp - Yo) / den).mean()
        else:
            L["rad"] = zero
        m = b["regime"] == self.fp_regime if self.fp else None
        if self.fp and m.any():
            Yi = b["Y_in"][m]
            r = (out["Y"][m] - Yi) / (self.fp_rel * Yi + self.fp_abs)
            L["fp"] = pseudo_huber(r).mean() + pseudo_huber((out["T"][m] - b["T_in"][m]) / self.fp_T).mean()
        else:
            L["fp"] = zero


def dt_scales(train, val, sigma_min):
    """training.dt_scaled_loss: increments and dT normalized by their std among the training pairs
    with the same time step (log10 dt to 0.1), not by one global std. With a wide dt_range the long
    steps have increments orders of magnitude larger, and a global scale makes the short steps (the
    ones the solver calls most in hot cells) nearly free in the loss."""
    key = lambda d: torch.round(torch.log10(d["dt"]) * 10).long()
    kt = key(train)
    dy = train["yt_out"] - train["yt_in"]
    dT = train["T_out"] - train["T_in"]
    bins = torch.unique(kt)
    sy = torch.stack([torch.clamp(dy[kt == k].std(0), min=sigma_min) for k in bins])
    sT = torch.stack([torch.clamp(dT[kt == k].std(), min=1.0) for k in bins])
    for d in (train, val):
        j = torch.argmin((key(d)[:, None] - bins[None, :]).abs(), dim=1)
        d["sdy"], d["sdT"] = sy[j], sT[j]
    return bins, sy, sT


def batch_losses(model, b, A, sigma_dT, weights, eq_thr, alpha, rel=None):
    sdy = model.sigma_dy
    sdy_loss = b.get("sdy", sdy)            # per-sample scales with training.dt_scaled_loss
    sigma_dT = b.get("sdT", sigma_dT)
    Y_in, T_in = b["Y_in"], b["T_in"]
    if alpha > 0:  # pushforward perturbation, projected back onto the polytope (Section 5.2)
        noisy = b["yt_in"] + alpha * sdy * torch.randn_like(b["yt_in"])
        Y_in, T_in = model.project_state(b["Y_in"], noisy, b["h_in"], b["T_in"])
    out = model(Y_in, T_in, b["P_in"], b["h_in"], b["dt"])
    v_true = (b["yt_out"] - b["yt_in"]) / sdy_loss
    v_pred = (out["yt_cand"] - b["yt_in"]) / sdy_loss
    L = {}
    L["inc"] = ((v_pred - v_true) ** 2).mean()
    L["mass"] = ((((out["Y_cand"] - b["Y_in"]) @ A.T) / MASS_SCALE) ** 2).mean()
    L["T"] = (((out["T"] - b["T_out"]) / sigma_dT) ** 2).mean()
    eq = v_true.abs().amax(-1) < eq_thr
    L["equil"] = (v_pred[eq] ** 2).mean() if eq.any() else v_pred.sum() * 0.0
    ae = out["extras"].get("ae_recon")
    L["ae"] = ((ae.to(torch.float64) - out["yt_in"]) ** 2).mean() if ae is not None else v_pred.sum() * 0.0
    if rel is not None:
        rel(b, out, L)
    total = sum(weights.get(k, 0.0) * L[k] for k in L)
    return total, {k: float(v.detach()) for k, v in L.items()}, out


def rollout_loss(model, seg, idx, sigma_dT, sigma_dy=None):
    Y, T = seg["Y"][idx, 0], seg["T"][idx, 0]
    P, h, dt = seg["P"][idx], seg["h"][idx], seg["dt"][idx]
    K = seg["Y"].shape[1] - 1
    loss = 0.0
    for k in range(1, K + 1):
        out = model(Y, T, P, h, dt)
        Y, T = out["Y"], out["T"]
        dy = (model.encode_Y(Y) - model.encode_Y(seg["Y"][idx, k])) / (model.sigma_dy if sigma_dy is None else sigma_dy)
        loss = loss + (dy ** 2).mean() + (((T - seg["T"][idx, k]) / sigma_dT) ** 2).mean()
    return loss / K


def main(cfg, arch, seed=None, tag=None):
    tc = cfg["training"]
    seed = int(cfg["seed"] if seed is None else seed)
    torch.manual_seed(seed)
    if tc.get("threads", "auto") != "auto":
        torch.set_num_threads(int(tc["threads"]))
    ds = load_npz(stage_dir(cfg, "prep") / "dataset.npz")
    scalers, thermo = load_prep(cfg)
    d = latent_dim(cfg)
    model = build_surrogate(arch, cfg, scalers, thermo, latent_dim=d)
    device = resolve_device(tc.get("device", "auto"))
    model.net.to(device)
    A = model.project.A
    if tc.get("init_from"):
        parent = Path(cfg["_config_path"]).parent / tc["init_from"]
        ck = torch.load(parent, map_location="cpu", weights_only=False)
        sd = ck["state_dict"]
        for k in ("mu_y", "sigma_y", "ctx_mu", "ctx_sigma", "sigma_dy"):
            if not torch.allclose(sd[k], getattr(model, k)):
                raise ValueError(f"warm start: scaler {k} of {parent} differs from 04_prep - set "
                                 "preprocess.scalers_from to the parent's scalers.json and re-run stage 5")
        model.load_state_dict(sd)
        model.net.to(device)
        print(f"  warm start from {parent} (epoch {ck.get('epoch')})")
    rel = RelativeTerms(tc, list(scalers["species"]))

    train, val = to_tensors(ds, ~ds["is_val"]), to_tensors(ds, ds["is_val"])
    sigma_dT = float(torch.clamp((train["T_out"] - train["T_in"]).std(), min=1.0))
    roll_sdy, roll_sdT = None, sigma_dT
    if tc.get("dt_scaled_loss"):
        bins, sy, sT = dt_scales(train, val, float(cfg["preprocess"]["sigma_dy_min"]))
        print("  dt-scaled loss, dT std per time step: " + ", ".join(
            f"{10 ** (k / 10):.2g}s {t:.3g}K" for k, t in zip(bins.tolist(), sT.tolist())))
    n_train = len(train["dt"])
    bs, E = tc["batch_size"], tc["epochs"]
    steps = (n_train + bs - 1) // bs
    opt = torch.optim.AdamW(model.net.parameters(), lr=tc["lr_max"], weight_decay=tc["weight_decay"])
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=tc["lr_max"], total_steps=E * steps,
                                                pct_start=float(tc.get("pct_start", 0.3)))
    w = tc["loss_weights"]
    rl = cfg.get("rollout_loss")
    seg = None
    if rl and rl.get("weight", 0) > 0:
        seg = {k: torch.as_tensor(v, dtype=torch.float64)
               for k, v in load_npz(stage_dir(cfg, "samples") / "segments.npz").items()}
        if tc.get("dt_scaled_loss"):    # the rollout steps are scaled like the pairs at their dt
            j = int(torch.argmin((bins - torch.round(torch.log10(seg["dt"][0]) * 10).long()).abs()))
            roll_sdy, roll_sdT = sy[j], float(sT[j])
        print(f"  rollout loss: {len(seg['dt'])} segments of {seg['Y'].shape[1] - 1} steps, weight {rl['weight']}, "
              f"from epoch {int(rl.get('start_frac', 0.0) * E) + 1}")

    out_dir = stage_dir(cfg, "models", model_dir_name(arch, tag))
    patience = int(tc.get("patience", 0))   # counted once the pushforward noise is off: while it is on,
    noise_off = int(np.ceil(tc["noise_end_frac"] * E))   # the clean validation loss is 2-3x higher
    t_start, started = time.time(), datetime.now(timezone.utc)
    hist, best, best_epoch = [], np.inf, 0
    if tc.get("init_from"):   # the parent is the checkpoint to beat: if nothing improves on it, keep it
        model.eval()
        with torch.no_grad():
            best = float(batch_losses(model, val, A, sigma_dT, w, tc["equil_threshold"], 0.0, rel)[0])
        state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
        torch.save({"arch": arch, "latent_dim": d, "state_dict": state, "epoch": 0}, out_dir / "model.pt")
        print(f"  parent validation loss {best:.5f} (epoch 0)")
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
            loss, parts, _ = batch_losses(model, b, A, sigma_dT, w, tc["equil_threshold"], alpha, rel)
            if seg is not None and e > rl.get("start_frac", 0.0) * E:
                ridx = torch.randint(len(seg["dt"]), (rl["batch_size"],))
                L_roll = rollout_loss(model, seg, ridx, roll_sdT, roll_sdy)
                loss = loss + rl["weight"] * L_roll
                parts["roll"] = float(L_roll.detach())
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.net.parameters(), 1.0)
            opt.step()
            sched.step()
            for k, v in parts.items():
                agg[k] = agg.get(k, 0.0) + v / steps
        model.eval()
        with torch.no_grad():
            vloss, vparts, vout = batch_losses(model, val, A, sigma_dT, w, tc["equil_threshold"], 0.0, rel)
            T_mae = float((vout["T"] - val["T_out"]).abs().mean())
        row = {"epoch": e, "alpha": alpha, **{f"train_{k}": v for k, v in agg.items()},
               **{f"val_{k}": v for k, v in vparts.items()}, "val_total": float(vloss), "val_T_mae": T_mae}
        hist.append(row)
        rolling = seg is None or e > rl.get("start_frac", 0.0) * E
        if rolling and float(vloss) < best:   # with the rollout loss, only checkpoints trained with it
            best, best_epoch = float(vloss), e
            state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
            torch.save({"arch": arch, "latent_dim": d, "state_dict": state, "epoch": e},
                       out_dir / "model.pt")
        elif rolling and patience and alpha == 0 and e - max(best_epoch, noise_off) >= patience:
            print(f"  early stop at epoch {e}: no validation improvement since epoch {best_epoch}")
            break
        if e == 1 or e % 5 == 0 or e == E:
            print(f"  epoch {e:3d}  alpha={alpha:.4f}  train_inc={agg['inc']:.4f}  val_inc={vparts['inc']:.4f}  "
                  + (f"train_roll={agg['roll']:.4f}  " if "roll" in agg else "")
                  + (f"val_rad={vparts['rad']:.4f}  " if rel.rad else "")
                  + (f"val_fp={vparts['fp']:.4f}  " if rel.fp else "") +
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
    with open(out_dir / "config_used.yaml", "w") as f:
        yaml.safe_dump({k: v for k, v in cfg.items() if not k.startswith("_")}, f, sort_keys=False)
    save_json(out_dir / "train_info.json", dict(
        started_utc=started.isoformat(timespec="seconds"), wall_time_s=round(time.time() - t_start, 1),
        config=str(Path(cfg["_config_path"]).name), git_commit=git_commit(), epochs=E, epochs_run=e,
        best_epoch=best_epoch, seed=seed, init_from=tc.get("init_from"),
        best_val_loss=best, n_parameters=n_params, n_train_pairs=n_train, latent_dim=d, device=str(device),
        threads=torch.get_num_threads(), torch=torch.__version__, python=platform.python_version(),
        machine=f"{platform.system()} {platform.machine()}"))


def git_commit():
    try:
        root = Path(__file__).resolve().parents[1]
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True,
                             check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root,
                               capture_output=True, text=True).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return None


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--arch", choices=["resnet_film", "chemnode"], default="resnet_film")
    p.add_argument("--seed", type=int, default=None, help="training seed (default: the config's seed)")
    p.add_argument("--tag", default=None, help="write to 06_models/<arch>_<tag> (e.g. s1 for seed 1)")
    a = p.parse_args()
    main(load_config(a.config), a.arch, a.seed, a.tag)

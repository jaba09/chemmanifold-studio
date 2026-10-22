"""Load upstream artifacts (scalers, thermo tables, trained surrogates) from disk."""

import torch

from .io import load_json, load_npz, require, stage_dir
from .models import build_surrogate


def load_prep(cfg):
    prep = stage_dir(cfg, "prep")
    return load_json(prep / "scalers.json"), load_npz(prep / "thermo.npz")


def latent_dim(cfg):
    d = cfg["model"]["latent_dim"]
    if d == "auto":
        return int(load_json(stage_dir(cfg, "manifold") / "manifold_report.json")["recommended_latent_dim"])
    return int(d)


def load_surrogate(cfg, arch):
    scalers, thermo = load_prep(cfg)
    ckpt = torch.load(require(stage_dir(cfg, "models", arch) / "model.pt"), map_location="cpu", weights_only=False)
    model = build_surrogate(arch, cfg, scalers, thermo, latent_dim=ckpt["latent_dim"])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model, scalers, thermo

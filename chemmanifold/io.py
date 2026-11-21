"""Configuration loading and on-disk handoff helpers shared by all pipeline stages."""

import argparse
import json
from pathlib import Path

import numpy as np
import yaml

# Stage output directories, relative to `data_dir`.
STAGE_DIRS = {
    "flame": "00_flame",
    "envelope": "01_envelope",
    "autoignition": "02_autoignition",
    "samples": "03_samples",
    "prep": "04_prep",
    "manifold": "05_manifold",
    "models": "06_models",
    "eval": "07_eval",
    "fluent": "08_fluent",
}


def dt_strides(cfg, section):
    """Chemistry time steps of the transition pairs, as integer multiples of autoignition.dt_base.

    With a top-level `dt_range: {min, max, n}` [s] the strides are n log-spaced steps over that range
    (the range of chemistry time steps the CFD solver will ask for, e.g. Fluent's tau_cell; given by the
    user at first), so the surrogate learns Y(t + dt) in a single jump for any dt in it. Strides below
    1 are fractions of dt_base. Without dt_range, `<section>.strides`."""
    r = cfg.get("dt_range")
    if not r:
        return list(cfg[section]["strides"])
    base = cfg["autoignition"]["dt_base"]
    s = np.geomspace(r["min"] / base, r["max"] / base, int(r.get("n", 8)))
    s = np.where(s >= 1, np.round(s), s)             # whole multiples of dt_base above it, fractions below
    return [int(v) if v >= 1 else float(f"{v:.3g}") for v in np.unique(s)]


def stride_probs(cfg, strides):
    """Probabilities for drawing each dt stride, or None (uniform).

    With `dt_range.histogram: {log10_dt: [...bin centres], mass: [...]}` (stage 20, from the tau_cell
    histogram of a cheap flow solution) each stride gets the histogram mass of its window in log dt
    (midway to its neighbours), mixed with a uniform share `dt_range.uniform_share` (default 0.3) so
    no stride of the range is starved."""
    h = (cfg.get("dt_range") or {}).get("histogram")
    if not h or len(strides) < 2:
        return None
    x = np.log10(np.asarray(strides, float) * cfg["autoignition"]["dt_base"])
    c, m = np.asarray(h["log10_dt"], float), np.asarray(h["mass"], float)
    mid = 0.5 * (x[1:] + x[:-1])
    lo, hi = np.r_[-np.inf, mid], np.r_[mid, np.inf]
    share = np.array([m[(c >= a) & (c < b)].sum() for a, b in zip(lo, hi)])
    share = share / share.sum() if share.sum() > 0 else np.full(len(x), 1.0 / len(x))
    f = float(cfg["dt_range"].get("uniform_share", 0.3))
    p = (1 - f) * share + f / len(x)
    return p / p.sum()


def choose_strides(cfg, rng, strides, size=None, replace=True):
    """rng.choice over the dt strides, weighted by stride_probs when the config gives a histogram."""
    p = stride_probs(cfg, strides)
    return rng.choice(strides, size=size, replace=replace, p=p)


def load_config(path):
    with open(path) as f:
        cfg = yaml.safe_load(f)
    cfg["_config_path"] = str(Path(path).resolve())
    return cfg


def stage_dir(cfg, stage, *sub, create=True):
    root = Path(cfg["_config_path"]).parent / cfg["data_dir"]
    d = root / STAGE_DIRS[stage]
    for s in sub:
        d = d / s
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def require(path):
    """Fail with a clear message when an upstream stage has not been run."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found - run the upstream pipeline stage first.")
    return path


def save_npz(path, **arrays):
    np.savez_compressed(path, **arrays)
    print(f"  wrote {path}")


def load_npz(path):
    with np.load(require(path), allow_pickle=False) as f:
        return {k: f[k] for k in f.files}


def save_json(path, obj):
    def default(o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.generic):
            return o.item()
        raise TypeError(type(o))

    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=default)
    print(f"  wrote {path}")


def load_json(path):
    with open(require(path)) as f:
        return json.load(f)


def base_parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--config", default="config.yaml", help="pipeline configuration file")
    return p

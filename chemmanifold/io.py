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
}


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

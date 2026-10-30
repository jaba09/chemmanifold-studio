"""ISANN (ISAT-like online ANN): the pieces shared by the trainer daemon and the tests.

The run (userChemStep with an `isann` dictionary) keeps (state, dt, GA18 result) pairs per rank in
processor*/isannPairs.csv, already thinned by a coarse grid with a cap per box (isannStore.H).
This module:

  - mirrors that grid (grid_keys, grid_reservoir) so its reduction can be measured offline;
  - merges the pairs of all ranks into one archive and removes near-duplicates by a radius of
    novelty in the OOD coordinates of the model (radius_dedup): a pair is kept only if no kept
    pair is closer than r, in [Box-Cox z-scored species, z-scored T, z-scored log10 dt];
  - builds the data directory of one training round (online pairs + a replay share of the a priori
    data of the parent), with the warm-start config;
  - scores a model on held-out online pairs (one-step errors through the same advance() as the
    C core) for the acceptance gate.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from chemmanifold.fluent import ood_features, read_ood_tables

REASONS = {0: "fase DI", 1: "OOD", 2: "casilla no fiable", 3: "sombra"}
KEY_SPECIES = ("CO2", "CO", "OH", "H", "CH4", "O2", "CH2O", "HO2")


# --- first level: the grid of isannStore.H --------------------------------------------------------

def grid_keys(T, Z, Y, dt, species, wT=25.0, wZ=0.02, wLogY=0.25, wLogDt=0.1, yFloor=1e-8,
              key_species=KEY_SPECIES):
    """Integer box indices of each state, as isannStore::key (before hashing)."""
    cols = [np.floor(np.asarray(T) / wT), np.floor(np.sqrt(np.maximum(Z, 0.0)) / wZ)]
    for s in key_species:
        cols.append(np.floor(np.log10(np.maximum(Y[:, species.index(s)], yFloor)) / wLogY))
    cols.append(np.floor(np.log10(np.maximum(np.broadcast_to(dt, len(T)), 1e-30)) / wLogDt))
    return np.column_stack(cols).astype(np.int64)


def grid_reservoir(keys, cap=2, seed=1):
    """Indices kept by a cap-per-box reservoir over the candidates in order (isannStore::offer)."""
    rng = np.random.default_rng(seed)
    boxes, kept = {}, []
    for i, k in enumerate(map(tuple, keys)):
        b = boxes.setdefault(k, [0, []])
        b[0] += 1
        if len(b[1]) < cap:
            b[1].append(len(kept))
            kept.append(i)
        else:
            j = rng.integers(b[0])
            if j < cap:
                kept[b[1][j]] = i
    return np.array(kept, dtype=np.int64), len(boxes)


# --- second level: radius of novelty ---------------------------------------------------------------

def features(Y, T, dt, scalers):
    """OOD coordinates of the model plus z-scored log10 dt."""
    X = ood_features(Y, T, scalers)
    ldt = (np.log10(np.broadcast_to(dt, len(T))) - scalers["ctx_mu"][3]) / scalers["ctx_sigma"][3]
    return np.column_stack([X, ldt])


def radius_dedup(X, r, X_old=None, chunk=4000):
    """Greedy: keep a point if no kept point (or point of X_old) lies within r. Returns the indices
    of X that were kept, in their original order."""
    kept = []
    ref = [X_old] if X_old is not None and len(X_old) else []
    tree = BallTree(np.vstack(ref)) if ref else None
    for s in range(0, len(X), chunk):
        C = X[s:s + chunk]
        ok = np.ones(len(C), bool)
        if tree is not None:
            ok = tree.query_radius(C, r, count_only=True) == 0
        cand = np.flatnonzero(ok)
        local = []
        if len(cand):
            sub = BallTree(C[cand])
            nb = sub.query_radius(C[cand], r)
            taken = np.zeros(len(cand), bool)
            blocked = np.zeros(len(cand), bool)
            for j in range(len(cand)):
                if blocked[j]:
                    continue
                taken[j] = True
                blocked[nb[j]] = True
            local = cand[taken]
        kept.extend((s + np.asarray(local, dtype=np.int64)).tolist())
        if len(local):
            ref.append(C[local])
            tree = BallTree(np.vstack(ref))
    return np.array(kept, dtype=np.int64)


def coverage(X_all, X_kept):
    """Distance from every candidate to its nearest kept pair."""
    d, _ = BallTree(X_kept).query(X_all, k=1)
    return d[:, 0]


def landmark_threshold(model_file):
    return float(read_ood_tables(model_file)["ood.landmark_threshold"])


# --- pairs written by the run --------------------------------------------------------------------

def read_run_pairs(run_dir, species):
    """All processor*/isannPairs.csv of a run as one DataFrame (empty if none yet)."""
    frames = []
    for p in sorted(Path(run_dir).glob("processor*/isannPairs.csv")):
        try:
            frames.append(pd.read_csv(p))
        except (pd.errors.EmptyDataError, pd.errors.ParserError):
            continue
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    return df


def read_status(run_dir):
    """Per-step totals over the ranks of processor*/isannStatus.csv (steps all ranks reached)."""
    frames = []
    for p in sorted(Path(run_dir).glob("processor*/isannStatus.csv")):
        try:
            frames.append(pd.read_csv(p))
        except (pd.errors.EmptyDataError, pd.errors.ParserError):
            continue
    if not frames:
        return pd.DataFrame()
    # after a restart a rank appends the steps it repeats (from the last write): keep the last copy
    frames = [f.drop_duplicates("step", keep="last") for f in frames]
    last = min(int(f["step"].max()) for f in frames)
    df = pd.concat([f[f["step"] <= last] for f in frames]).groupby("step").sum(numeric_only=True)
    df["version"] = pd.concat(frames).groupby("step")["version"].max()
    return df.reset_index()


def pairs_arrays(df, species):
    Y0 = df[[f"Y0_{s}" for s in species]].to_numpy()
    Y1 = df[[f"Y1_{s}" for s in species]].to_numpy()
    return dict(Y_in=Y0 / Y0.sum(1, keepdims=True), T_in=df["T0"].to_numpy(), P_in=df["p"].to_numpy(),
                dt=df["dt"].to_numpy(), Y_out=Y1 / Y1.sum(1, keepdims=True), T_out=df["T1"].to_numpy(),
                step=df["step"].to_numpy(), reason=df["reason"].to_numpy(), id=df["id"].to_numpy(),
                Z=df["Z"].to_numpy())


class Archive:
    """Every pair the run ever offered (by id), with a flag for the radius-deduplicated set."""

    def __init__(self, path):
        self.path = Path(path)
        self.d = dict(np.load(self.path)) if self.path.exists() else None

    def merge(self, new):
        if self.d is None:
            self.d = {k: v for k, v in new.items()}
            self.d["kept"] = np.zeros(len(new["id"]), bool)
            self.d["trained"] = np.zeros(len(new["id"]), bool)
            self.d["holdout"] = np.zeros(len(new["id"]), bool)
            return len(new["id"])
        m = ~np.isin(new["id"], self.d["id"])
        if not m.any():
            return 0
        for k in new:
            self.d[k] = np.concatenate([self.d[k], new[k][m]])
        for k in ("kept", "trained", "holdout"):
            self.d[k] = np.concatenate([self.d[k], np.zeros(m.sum(), bool)])
        return int(m.sum())

    def save(self):
        tmp = self.path.with_suffix(".tmp.npz")
        np.savez(tmp, **self.d)
        tmp.replace(self.path)

    def __len__(self):
        return 0 if self.d is None else len(self.d["id"])


def enthalpy(gas, Y, T, P):
    h = np.empty(len(T))
    for i in range(len(T)):
        gas.TPY = T[i], P[i], Y[i]
        h[i] = gas.enthalpy_mass
    return h


def one_step_errors(model, scalers, arrays, dt_range):
    """Errors of the model's step on GA18 pairs: |dT| [K], relative T increment, OH and CO errors."""
    from chemmanifold.fluent import advance
    sp = list(scalers["species"])
    Yn, Tn, flags, _, _ = advance(model, arrays["Y_in"], arrays["T_in"], arrays["P_in"], arrays["dt"], *dt_range)
    dT_true = arrays["T_out"] - arrays["T_in"]
    eT = np.abs(Tn - arrays["T_out"])
    out = dict(T_mae=float(eT.mean()), T_p95=float(np.quantile(eT, 0.95)),
               T_rel=float(np.median(eT / (np.abs(dT_true) + 1.0))))
    for s in ("OH", "CO", "H"):
        k = sp.index(s)
        dY = arrays["Y_out"][:, k] - arrays["Y_in"][:, k]
        e = np.abs(Yn[:, k] - arrays["Y_out"][:, k])
        out[f"{s}_rel"] = float(np.median(e / (np.abs(dY) + 1e-3 * np.abs(arrays["Y_out"][:, k]) + 1e-9)))
    return out


def save_json(path, d):
    Path(path).write_text(json.dumps(d, indent=1, default=float))

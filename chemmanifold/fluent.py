"""Ansys Fluent coupling: model-file export for the C UDF (fluent/udf), a Python twin of the UDF's
time stepping and out-of-distribution (OOD) checks, and a reader for Fluent ASCII solution exports.

The UDF and this module must agree to round-off; scripts/12_export_fluent.py writes test vectors
from `advance` / `ood` below that the compiled UDF checks against (fluent/tests, or the
`chemmanifold_selftest` on-demand function inside Fluent).
"""

import re
from pathlib import Path

import numpy as np
import torch
from sklearn.cluster import KMeans, MiniBatchKMeans

from .boxcox import boxcox
from .flame import BilgerZ, is_flame, stream_states

FORMAT_VERSION = 1

# cm_info.flags bits, as in fluent/udf/chemmanifold_core.h
OOD_T, OOD_TZ, OOD_P, OOD_SPECIES, OOD_MANIFOLD, OOD_DATA = 0x1, 0x2, 0x4, 0x8, 0x10, 0x20
OOD_ANY = 0x3F
DT_CAPPED, FROZEN, INVALID, DT_SCALED, OOD_SKIPPED = 0x40, 0x80, 0x100, 0x200, 0x400
FLAG_NAMES = {OOD_T: "T_range", OOD_TZ: "T_range_at_Z", OOD_P: "pressure", OOD_SPECIES: "species_range",
              OOD_MANIFOLD: "off_manifold", OOD_DATA: "far_from_data", DT_CAPPED: "dt_capped",
              FROZEN: "frozen", INVALID: "invalid", DT_SCALED: "dt_scaled", OOD_SKIPPED: "ood_skipped"}

# User-defined memory slots written by the UDF (fluent/udf/chemmanifold_udf.c)
UDM_NAMES = ["ood_any", "ood_flags", "manifold_ratio", "data_ratio", "mixture_fraction",
             "heat_release_rate", "n_substeps"]

DEFAULT_OPTIONS = dict(T_freeze=0.0, max_substeps=50, ood_action=0, T_margin=25.0, y_margin=0.25,
                       p_tol=0.05, check_ood=1)


def fluent_species_name(name):
    """Fluent's name for a Chemkin species: lower case, parentheses as angle brackets (CH2(S) -> ch2<s>)."""
    return name.lower().replace("(", "<").replace(")", ">")


# --------------------------------------------------------------------------------------------
# OOD tables

def ood_features(Y, T, scalers):
    """[Box-Cox z-scored species, z-scored T], the coordinates of stage 11 and of the UDF checks."""
    lam = scalers["boxcox_lambda"]
    y = (boxcox(Y, lam) - np.asarray(scalers["mu_y"])) / np.asarray(scalers["sigma_y"])
    t = (np.asarray(T) - scalers["ctx_mu"][0]) / scalers["ctx_sigma"][0]
    return np.column_stack([y, t])


def z_bin_edges(Z_st):
    """Mixture-fraction bands for the T(Z) bounds: fine around Z_st, coarse in the rich core."""
    fine = np.linspace(0.0, 6 * Z_st, 25)
    return np.unique(np.concatenate([fine, np.linspace(6 * Z_st, 1.0, 9)]))


def build_ood_tables(gas, cfg, scalers, ds, vq_K, vq_d, n_landmarks=1024, quantile=0.999, seed=0):
    """Ranges and manifold-distance tables of the training states (inputs and targets)."""
    tr = ~ds["is_val"]
    Y = np.vstack([ds["Y_in"][tr], ds["Y_out"][tr]])
    T = np.concatenate([ds["T_in"][tr], ds["T_out"][tr]])
    X = ood_features(Y, T, scalers)
    if is_flame(cfg):
        (Yf, _), (Yo, _) = stream_states(gas, cfg)
        bz = BilgerZ(gas, Yf, Yo)
        coef, b_f, b_o = bz.coef, float(bz.b_f[0]), float(bz.b_o[0])
        Z = bz(Y)
        Z_st = -b_o / (b_f - b_o)
        edges = z_bin_edges(Z_st)
    else:   # premixed: no mixture fraction, a single band (the T|Z check is the global T range)
        coef, b_f, b_o, Z_st = np.zeros(len(gas.element_names)), 1.0, 0.0, 0.0
        Z = np.zeros(len(T))
        edges = np.array([0.0, 1.0])
    nb = len(edges) - 1
    b = np.clip(np.searchsorted(edges, Z, side="right") - 1, 0, nb - 1)
    T_min_z, T_max_z = np.full(nb, np.nan), np.full(nb, np.nan)
    for i in range(nb):
        if np.any(b == i):
            T_min_z[i], T_max_z[i] = T[b == i].min(), T[b == i].max()
    for arr, fill in ((T_min_z, T.min()), (T_max_z, T.max())):  # empty bands: widest neighbour bound
        for i in np.flatnonzero(np.isnan(arr)):
            near = [arr[j] for j in (i - 1, i + 1) if 0 <= j < nb and not np.isnan(arr[j])]
            arr[i] = (min(near) if arr is T_min_z else max(near)) if near else fill

    rng = np.random.default_rng(seed)
    km = KMeans(n_clusters=vq_K, random_state=seed, n_init=5).fit(X)
    F = X.shape[1]
    means, bases, thr = np.zeros((vq_K, F)), np.zeros((vq_K, F, vq_d)), np.zeros(vq_K)
    for k in range(vq_K):
        Xk = X[km.labels_ == k]
        means[k] = Xk.mean(0)
        _, _, Vt = np.linalg.svd(Xk - means[k], full_matrices=False)
        U = Vt[:vq_d].T
        if U.shape[1] < vq_d:
            U = np.pad(U, ((0, 0), (0, vq_d - U.shape[1])))
        bases[k] = U
        res = np.linalg.norm((Xk - means[k]) - (Xk - means[k]) @ U @ U.T, axis=1)
        thr[k] = max(np.quantile(res, quantile), 1e-6)

    n_land = min(n_landmarks, len(X))
    sub = X[rng.choice(len(X), size=min(len(X), 50 * n_land), replace=False)]
    land = MiniBatchKMeans(n_clusters=n_land, random_state=seed, n_init=3, batch_size=4096).fit(sub).cluster_centers_
    d = nearest_distance(X, land)
    return {
        "ood.T_range": [T.min(), T.max()],
        "ood.beta_coef": coef, "ood.beta_fuel": b_f, "ood.beta_ox": b_o,
        "ood.yt_min": X[:, :-1].min(0), "ood.yt_max": X[:, :-1].max(0),
        "ood.n_zbins": nb, "ood.z_edges": edges, "ood.T_min_z": T_min_z, "ood.T_max_z": T_max_z,
        "ood.vq_K": vq_K, "ood.vq_d": vq_d, "ood.vq_centroid": km.cluster_centers_,
        "ood.vq_mean": means, "ood.vq_basis": bases, "ood.vq_threshold": thr,
        "ood.n_landmarks": n_land, "ood.landmarks": land,
        "ood.landmark_threshold": max(float(np.quantile(d, quantile)), 1e-6),
        "ood.quantile": quantile, "ood.Z_st": Z_st,
    }


def nearest_distance(X, L, chunk=4096):
    out = np.empty(len(X))
    L2 = (L ** 2).sum(1)
    for i in range(0, len(X), chunk):
        x = X[i:i + chunk]
        d2 = (x ** 2).sum(1)[:, None] - 2 * x @ L.T + L2[None, :]
        out[i:i + chunk] = np.sqrt(np.maximum(d2.min(1), 0.0))
    return out


def ood(tables, scalers, A, Y, T, P, P_ref, opt=None):
    """Vectorized twin of cm_ood: returns dict(flags, Z, manifold_ratio, data_ratio)."""
    o = {**DEFAULT_OPTIONS, **(opt or {})}
    Y, T, P = np.atleast_2d(Y), np.atleast_1d(T).astype(float), np.broadcast_to(P, len(np.atleast_1d(T)))
    flags = np.where(np.abs(P / P_ref - 1.0) > o["p_tol"], OOD_P, 0)
    beta = (Y @ np.asarray(A).T) @ np.asarray(tables["ood.beta_coef"])
    Z = (beta - tables["ood.beta_ox"]) / (tables["ood.beta_fuel"] - tables["ood.beta_ox"])
    Tr = tables["ood.T_range"]
    flags |= np.where((T < Tr[0] - o["T_margin"]) | (T > Tr[1] + o["T_margin"]), OOD_T, 0)
    edges, nb = np.asarray(tables["ood.z_edges"]), int(tables["ood.n_zbins"])
    b = np.zeros(len(Z), dtype=int)                       # the same band search as the C code
    for i in range(1, nb):
        b += Z >= edges[i]
    b = np.minimum(b, nb - 1)
    flags |= np.where((T < np.asarray(tables["ood.T_min_z"])[b] - o["T_margin"])
                      | (T > np.asarray(tables["ood.T_max_z"])[b] + o["T_margin"]), OOD_TZ, 0)
    X = ood_features(Y, T, scalers)
    out_y = (X[:, :-1] < np.asarray(tables["ood.yt_min"]) - o["y_margin"]) | \
            (X[:, :-1] > np.asarray(tables["ood.yt_max"]) + o["y_margin"])
    flags |= np.where(out_y.any(1), OOD_SPECIES, 0)
    C = np.asarray(tables["ood.vq_centroid"])
    k = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(-1), axis=1)
    xc = X - np.asarray(tables["ood.vq_mean"])[k]
    U = np.asarray(tables["ood.vq_basis"])[k]             # (n, F, d)
    r = xc - np.einsum("nfd,nd->nf", U, np.einsum("nfd,nf->nd", U, xc))
    mr = np.linalg.norm(r, axis=1) / np.asarray(tables["ood.vq_threshold"])[k]
    dr = nearest_distance(X, np.asarray(tables["ood.landmarks"])) / tables["ood.landmark_threshold"]
    flags |= np.where(mr > 1, OOD_MANIFOLD, 0) | np.where(dr > 1, OOD_DATA, 0)
    return dict(flags=flags.astype(int), Z=Z, manifold_ratio=mr, data_ratio=dr)


def describe_flags(flags):
    f = int(flags)
    return [name for bit, name in FLAG_NAMES.items() if f & bit]


# --------------------------------------------------------------------------------------------
# Python twin of cm_advance

def formation_enthalpies(model):
    """h_k(298.15 K) [J/kg] from the model's NASA-7 tables (for the heat release rate)."""
    Tf = torch.tensor([298.15], dtype=torch.float64)
    return model.temperature.species_cp_h(Tf)[1][0].numpy()


@torch.no_grad()
def advance(model, Y, T, P, dt, dt_min, dt_max, opt=None, ood_flags=None):
    """One UDF call per state: sub-step dt inside [dt_min, dt_max] exactly as cm_advance.
    Returns Y_new (n, Ns), T_new (n,), flags (n,), n_sub (n,), hrr (n,) [W/kg]."""
    o = {**DEFAULT_OPTIONS, **(opt or {})}
    f64 = dict(dtype=torch.float64)
    Y = np.atleast_2d(np.asarray(Y, float))
    T = np.atleast_1d(np.asarray(T, float))
    n = len(T)
    dt = np.broadcast_to(np.asarray(dt, float), n)
    P_model = float(model.ctx_mu[1]) if float(model.ctx_sigma[1]) < 1e-6 * abs(float(model.ctx_mu[1])) + 1e-9 \
        else None
    hf = formation_enthalpies(model)
    Y_new, T_new = Y.copy(), T.copy()
    flags = np.zeros(n, dtype=int) if ood_flags is None else np.asarray(ood_flags, int).copy()
    n_sub, hrr = np.zeros(n, dtype=int), np.zeros(n)
    for i in range(n):
        if not dt[i] > 0:
            continue
        if T[i] < o["T_freeze"]:   # the C code also clears the OOD bits (and ratios) of frozen cells
            flags[i] = (flags[i] & ~OOD_ANY) | FROZEN
            continue
        if o["ood_action"] == 1 and flags[i] & OOD_ANY:
            flags[i] |= OOD_SKIPPED
            continue
        scale = 1.0
        if dt[i] < dt_min:
            m, dts, scale = 1, dt_min, dt[i] / dt_min
            flags[i] |= DT_SCALED
        else:
            m = max(1, int(np.ceil(dt[i] / dt_max * (1.0 - 1e-12))))
            if m > o["max_substeps"]:
                m, dts = o["max_substeps"], dt_max
                flags[i] |= DT_CAPPED
            else:
                dts = dt[i] / m
        y = torch.as_tensor(Y[i:i + 1], **f64)
        t = torch.as_tensor(T[i:i + 1], **f64)
        h = model.temperature.enthalpy(y, t)
        p = torch.full((1,), P_model if P_model is not None else float(np.broadcast_to(P, n)[i]), **f64)
        d = torch.full((1,), dts, **f64)
        tn = t
        for _ in range(m):
            out = model(y, tn, p, h, d)
            y, tn = out["Y"], out["T"]
        yn = y.numpy()[0]
        if not (np.all(np.isfinite(yn)) and np.isfinite(float(tn))):
            flags[i] |= INVALID
            continue
        if scale < 1.0:
            yn = Y[i] + scale * (yn - Y[i])
            tn = model.temperature(torch.as_tensor(yn[None], **f64), h, t)
        Y_new[i], T_new[i] = yn, float(tn)
        n_sub[i] = m
        hrr[i] = -np.dot(hf, Y_new[i] - Y[i]) / dt[i]
    return Y_new, T_new, flags, n_sub, hrr


# --------------------------------------------------------------------------------------------
# model file

def _fmt(values):
    return " ".join(f"{v:.17g}" for v in np.asarray(values, dtype=float).ravel())


def write_model_file(path, arch, model, scalers, thermo, cfg, dt_range, ood_tables=None):
    sd = {k: v.detach().cpu().double().numpy() for k, v in model.net.state_dict().items()}
    species = [str(s) for s in thermo["species"]]
    lines = [f"CHEMMANIFOLD_SURROGATE {FORMAT_VERSION}",
             f"S arch 1 {arch}",
             f"S species {len(species)} " + " ".join(species),
             f"S elements {len(thermo['elements'])} " + " ".join(str(e) for e in thermo["elements"])]

    def arr(name, v):
        v = np.atleast_1d(np.asarray(v, dtype=float))
        lines.append(f"A {name} {v.size} {_fmt(v)}")

    arr("n_species", len(species))
    arr("n_elements", len(thermo["elements"]))
    arr("boxcox_lambda", scalers["boxcox_lambda"])
    arr("dt_base", scalers["dt_base"])
    arr("dt_min", dt_range[0])
    arr("dt_max", dt_range[1])
    arr("P_ref", scalers["ctx_mu"][1])
    for k in ("mu_y", "sigma_y", "ctx_mu", "ctx_sigma"):
        arr(k, scalers[k])
    for k in ("A", "W", "T_mid", "a_lo", "a_hi"):
        arr(k, thermo[k])
    m = cfg["model"]
    arr("n_blocks", m["n_blocks"])
    arr("node_substeps", m["node_substeps"])
    for k, v in sd.items():
        arr(f"net.{k}", v)
    for k, v in (ood_tables or {}).items():
        arr(k, v)
    Path(path).write_text("\n".join(lines) + "\n")


def write_test_vectors(path, cases, expected):
    """Plain-text cases for cm_selftest: per line dt P T Y... | T_out Y_out... flags mr dr Z n_sub hrr."""
    Ns = cases["Y"].shape[1]
    lines = [f"CHEMMANIFOLD_TESTS 1 {len(cases['T'])} {Ns}"]
    for i in range(len(cases["T"])):
        row = [cases["dt"][i], cases["P"][i], cases["T"][i], *cases["Y"][i],
               expected["T"][i], *expected["Y"][i], expected["flags"][i], expected["manifold_ratio"][i],
               expected["data_ratio"][i], expected["Z"][i], expected["n_sub"][i], expected["hrr"][i]]
        lines.append(_fmt(row))
    Path(path).write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------------------------
# Fluent ASCII solution export

def read_fluent_ascii(path):
    """Read File > Export > Solution Data > ASCII (comma or space separated, one header line).
    Returns {lower-case column name: array}."""
    text = Path(path).read_text().splitlines()
    sep = "," if "," in text[0] else None
    names = [re.sub(r"\s+", "", c).lower() for c in (text[0].split(sep) if sep else text[0].split())]
    names = [c for c in names if c]
    rows = []
    for line in text[1:]:
        parts = [p for p in (line.split(sep) if sep else line.split()) if p.strip()]
        if len(parts) == len(names):
            rows.append([float(p) for p in parts])
    data = np.array(rows)
    return {n: data[:, j] for j, n in enumerate(names)}


def _find(cols, candidates):
    for c in candidates:
        if c in cols:
            return c
    return None


def fluent_state(cols, species, P_default=101325.0, column_map=None):
    """Mass fractions (n, Ns), T, absolute P and coordinates from an ASCII export.
    Species columns are found by Fluent's species name (h2, ch2<s>, ...), with or without a
    'mass-fraction-of-' style prefix; `column_map` {species: column} overrides the lookup."""
    column_map = column_map or {}
    n = len(next(iter(cols.values())))
    Y = np.zeros((n, len(species)))
    missing = []
    for k, s in enumerate(species):
        f = fluent_species_name(s)
        c = column_map.get(s) or _find(cols, [f, s.lower(), f"mass-fraction-of-{f}", f"{f}-mass-fraction",
                                               f"mass-fraction-{f}", f.replace("<", "(").replace(">", ")")])
        if c is None:
            missing.append(s)
        else:
            Y[:, k] = cols[c]
    if missing:
        last = species[-1]
        if missing == [last]:   # Fluent may leave out the last (bulk) species
            Y[:, -1] = np.clip(1.0 - Y[:, :-1].sum(1), 0.0, 1.0)
        else:
            raise KeyError(f"species columns not found in the Fluent export: {missing}; "
                           f"columns are {sorted(cols)}")
    Y = np.clip(Y, 0.0, 1.0)
    Y /= Y.sum(1, keepdims=True)
    T = cols[_find(cols, ["temperature", "static-temperature"]) or "temperature"]
    pc = _find(cols, ["absolute-pressure", "pressure", "static-pressure"])
    P = cols[pc] if pc == "absolute-pressure" else (cols[pc] + P_default if pc else np.full(n, P_default))
    out = dict(Y=Y, T=T, P=P)
    for key, cands in (("x", ["x-coordinate", "x"]), ("y", ["y-coordinate", "y"]),
                       ("cell", ["cellnumber", "cell-number"]), ("volume", ["cell-volume", "volume"]),
                       ("density", ["density"])):
        c = _find(cols, cands)
        if c:
            out[key] = cols[c]
    for j, name in enumerate(UDM_NAMES):
        c = _find(cols, [f"udm-{j}", f"user-memory-{j}", f"udm{j}"])
        if c:
            out[name] = cols[c]
    return out

"""Sets of surrogates used as one model (docs/ENSEMBLE-ROADMAP.md): gate variables and ensemble files.

The gate reads the input state only: temperature T and the normalised progress variable
c = Yc / Yc_eq(Z), with Yc the sum of `PROGRESS_SPECIES` and Yc_eq(Z) its value in adiabatic
equilibrium of the fresh mixture at mixture fraction Z (a 1-D table built from the two streams).
c is ~0 in fresh gas and ~1 in burnt gas, also for cooled products (their composition stays burnt).

The same functions build the training subsets of the experts (07_train.py `training.subset`) and the
ensemble file read by the C code (fluent/udf/chemmanifold_ensemble.c), so the two always agree.
"""

from pathlib import Path

import numpy as np

from .chemistry import make_gas
from .flame import BilgerZ, flame_pressure, stoichiometric_z, stream_states

PROGRESS_SPECIES = ("CO2", "H2O", "CO", "H2")
WIDE = (-1e9, 1e9, 0.0)                 # a box edge that never cuts


def gate_tables(cfg, species=None, n_z=121):
    """zlin (Z = zlin . Y + zlin_b), prog weights and the Yc_eq(Z) table, in the mechanism's species order
    (or `species`, which must be a permutation of it)."""
    gas = make_gas(cfg)
    names = list(gas.species_names)
    (Yf, hf), (Yo, ho) = stream_states(gas, cfg)
    bz = BilgerZ(gas, Yf, Yo)
    bf, bo = float(np.ravel(bz.b_f)[0]), float(np.ravel(bz.b_o)[0])
    a = (bz.A.T @ bz.coef) / (bf - bo)
    b = -bo / (bf - bo)
    prog = np.array([1.0 if s in PROGRESS_SPECIES else 0.0 for s in names])
    Zst = stoichiometric_z(gas, cfg)
    P = flame_pressure(cfg)
    zs = np.unique(np.concatenate([np.linspace(0, 1, n_z // 3), np.geomspace(1e-4, 1, n_z - n_z // 3),
                                   Zst * np.linspace(0.5, 1.5, 21)]))
    zs = np.clip(zs, 0, 1)
    yc = np.empty(len(zs))
    for i, Z in enumerate(zs):
        gas.HPY = Z * hf + (1 - Z) * ho, P, Z * Yf + (1 - Z) * Yo
        gas.equilibrate("HP")
        yc[i] = float(prog @ gas.Y)
    if species is not None:
        order = [names.index(s) for s in species]
        a, prog, names = a[order], prog[order], list(species)
    return dict(species=names, zlin=a, zlin_b=b, prog=prog, z=zs, yc_eq=yc, Z_st=Zst)


def gate_vars(tab, Y):
    """Z and c of states Y (n x Ns, in tab['species'] order)."""
    Y = np.atleast_2d(Y)
    Z = Y @ tab["zlin"] + tab["zlin_b"]
    yeq = np.interp(Z, tab["z"], tab["yc_eq"])
    return Z, (Y @ tab["prog"]) / np.maximum(yeq, 1e-12)


def soft_box(x, lo, hi, w):
    """1 inside [lo, hi], 0 outside, linear over a width w centred on each edge (as the C code)."""
    x = np.asarray(x, float)
    if not w > 0:
        return ((x >= lo) & (x < hi)).astype(float)
    return np.clip((x - lo) / w + 0.5, 0, 1) * np.clip((hi - x) / w + 0.5, 0, 1)


def box_weight(T, c, box):
    """Weight of one member's box {'T': [lo, hi, width], 'c': [lo, hi, width]} (missing = no cut)."""
    tb, cb = box.get("T", WIDE), box.get("c", WIDE)
    return soft_box(T, *tb) * soft_box(c, *cb)


def gate_weights(T, c, boxes, blend="gate"):
    """Normalised weights (n x members), as cme_weights. States outside every box get equal weights."""
    T = np.atleast_1d(T)
    if blend == "mean":
        return np.full((len(T), len(boxes)), 1.0 / len(boxes))
    w = np.stack([box_weight(T, c, b) for b in boxes], axis=1)
    s = w.sum(1, keepdims=True)
    return np.where(s > 0, w / np.where(s > 0, s, 1), 1.0 / len(boxes))


def write_ensemble_file(path, tab, members, blend="gate", note=""):
    """members: [{'path': model file (relative to the ensemble file or absolute), 'T': [...], 'c': [...]}]."""
    path = Path(path)
    L = ["chemmanifold_ensemble 1", f"# {note}" if note else "# ChemManifold ensemble (scripts/make_ensemble.py)",
         f"blend {blend}", f"n_species {len(tab['species'])}", "species " + " ".join(tab["species"]),
         "zlin " + " ".join(f"{v:.17g}" for v in tab["zlin"]) + f" {tab['zlin_b']:.17g}",
         "prog " + " ".join(f"{v:g}" for v in tab["prog"]),
         f"ceq {len(tab['z'])} " + " ".join(f"{z:.12g} {y:.12g}" for z, y in zip(tab["z"], tab["yc_eq"])),
         f"members {len(members)}"]
    for m in members:
        tb, cb = m.get("T", WIDE), m.get("c", WIDE)
        L.append(f"member {m['path']} " + " ".join(f"{v:.10g}" for v in (*tb, *cb)))
    path.write_text("\n".join(L) + "\n")
    return path


def subset_dataset(cfg, ds, species, box):
    """Pairs of a dataset dict (04_prep/dataset.npz) whose INPUT state has a weight > 0 in `box`
    ({'T': [lo, hi, width], 'c': [...]}): the training data and OOD tables of one expert."""
    tab = gate_tables(cfg, species=list(species))
    _, c_in = gate_vars(tab, ds["Y_in"])
    keep = box_weight(ds["T_in"], c_in, box) > 0
    n = len(keep)
    return {k: (v[keep] if isinstance(v, np.ndarray) and v.ndim and len(v) == n else v) for k, v in ds.items()}, \
        keep, tab

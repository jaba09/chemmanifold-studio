#!/usr/bin/env python3
"""Stage 21: one-step a-priori test at each cell's own chemistry step tau_cell (timescale roadmap).

Evaluation only: the CFD states are test points, never training data.

Takes the cells of a steady solution computed with direct GA18 chemistry over tau_cell (an OpenFOAM
time directory) and the per-cell tau_cell from stage 19 (cells.npz, same cell order). Each sampled
cell is advanced once by its own tau_cell as a homogeneous constant-(p, h) reactor:

  * reference: Cantera with the mechanism of the config;
  * surrogate: each exported model file through the UDF's C core (the same call OpenFOAM makes; a
    model trained on shorter steps chains its own sub-steps, as it does in the CFD).

The errors are then split two ways, to separate the two causes of a bad source term:
  * by step size (tau_cell bins): is the model accurate at the step the flow asks for?
  * by coverage: is the starting state inside the model's own training data (its OOD check)?
and by region (flame T > 1600 K, lean burnt gas Z < 0.03 and 600-1600 K, other hot gas).

Increment error = sum |surrogate - Cantera| / sum |Cantera - start| over the group (T, CO, OH).

    python scripts/21_tau_step_apriori.py --config configs/burner_openfoam_tix1.yaml \\
        --states /opt/ofb/tix/runs/di_tau/1500 --tau /opt/ofb/tix/stats/di_tau/cells.npz \\
        --models ood8=/path/model.txt tix1=/path/model.txt --out /path/out
"""

import ctypes
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from chemmanifold.chemistry import make_gas
from chemmanifold.flame import BilgerZ, stream_states
from chemmanifold.io import base_parser, load_config

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("s17", ROOT / "scripts" / "17_di_local_stability.py")
s17 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s17)

DT_BINS = [0, 4e-5, 1e-4, 3e-4, 1.0]
DT_LABELS = ["<=40 us", "40-100 us", "100-300 us", ">300 us"]


def region(Z, T):
    return np.where(T > 1600, "flame", np.where((Z < 0.03) & (T <= 1600), "lean burnt gas", "other hot gas"))


def sample(Zc, Tc, tau, hot, n_per, rng):
    """Up to n_per cells per (region, tau bin) group, so slow lean cells and long steps are all represented."""
    reg = region(Zc, Tc)
    b = np.digitize(tau, DT_BINS) - 1
    picks = []
    for r in ("flame", "lean burnt gas", "other hot gas"):
        for k in range(len(DT_LABELS)):
            g = np.flatnonzero(hot & (reg == r) & (b == k))
            if len(g):
                picks.append(rng.choice(g, size=min(n_per, len(g)), replace=False))
    return np.concatenate(picks)


def main(cfg, a):
    gas = make_gas(cfg)
    species = list(gas.species_names)
    (Yf, _), (Yo, _) = stream_states(gas, cfg)
    Y, T, P = s17.load_states(a.states, species)
    Y = np.clip(Y, 0.0, None)
    Y /= Y.sum(1, keepdims=True)
    Z = np.clip(BilgerZ(gas, Yf, Yo)(Y), 0.0, 1.0)
    c = np.load(a.tau)
    tau = c["tau_cell"]
    assert len(tau) == len(T) and np.allclose(c["T"], T, atol=1e-3), "cells.npz does not match the states"
    rng = np.random.default_rng(cfg.get("seed", 0))
    cells = sample(Z, T, tau, T > a.T_min, a.n_per_group, rng)
    print(f"  {len(cells)} cells sampled")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lib = s17.core_library(out)
    iCO, iOH = species.index("CO"), species.index("OH")
    ref = []
    for i in cells:
        Tr, Yr = s17.reference(gas, Y[i], T[i], P[i], float(tau[i]), 1, {0})
        ref.append((Tr[0], Yr[0]))
    rows = []
    for spec in a.models:
        name, path = spec.split("=", 1)
        err = ctypes.create_string_buffer(512)
        model = lib.cm_load(path.encode(), err, 512)
        if not model:
            raise RuntimeError(f"{path}: {err.value.decode()}")
        names = [lib.cm_species_name(model, k).decode() for k in range(lib.cm_n_species(model))]
        idx = [species.index(s) for s in names]
        opt = s17.CmOptions()
        lib.cm_default_options(ctypes.byref(opt))
        for j, i in enumerate(cells):
            Ts, Ys, flags = s17.surrogate(lib, model, opt, Y[i, idx], T[i], P[i], float(tau[i]), 1, {0})
            ys = Ys.get(0, np.full(len(names), np.nan))
            Tr, Yr = ref[j]
            rows.append(dict(model=name.split("_r")[0], run=name, cell=int(i), Z=Z[i], T0=T[i], tau=tau[i],
                             ood=int(flags != 0), dT=Ts[0] - Tr, incT=Tr - T[i],
                             dCO=ys[names.index("CO")] - Yr[iCO], incCO=Yr[iCO] - Y[i, iCO], CO0=Y[i, iCO], OH0=Y[i, iOH],
                             dOH=ys[names.index("OH")] - Yr[iOH], incOH=Yr[iOH] - Y[i, iOH]))
        print(f"  {name}: done")
    df = pd.DataFrame(rows)
    df["region"] = region(df.Z.values, df.T0.values)
    df["dt_bin"] = pd.cut(df.tau, DT_BINS, labels=DT_LABELS)
    df["coverage"] = np.where(df.ood == 1, "outside data", "inside data")

    def rel(e, i):
        return float(np.nansum(np.abs(e)) / max(np.nansum(np.abs(i)), 1e-30))

    def rate_ratio(e, i):
        """surrogate / Cantera net change, summed with sign: 1 = right mean source, >1 too strong."""
        s = np.nansum(i)
        return float(np.nansum(i + e) / s) if abs(s) > 1e-30 else float("nan")

    def summ(g):
        # level error: one-step error relative to the species' own mass fraction (median over cells), the
        # quantity that matters where increments are tiny because the gas is near its steady balance
        return dict(cells=int(len(g)), ood=float(g.ood.mean()), absdT=float(g.dT.abs().mean()),
                    rel_T=rel(g.dT, g.incT), rel_CO=rel(g.dCO, g.incCO), rel_OH=rel(g.dOH, g.incOH),
                    rate_CO=rate_ratio(g.dCO, g.incCO), rate_OH=rate_ratio(g.dOH, g.incOH),
                    lvl_CO=float(np.nanmedian(np.abs(g.dCO) / np.maximum(g.CO0, 1e-12))),
                    lvl_OH=float(np.nanmedian(np.abs(g.dOH) / np.maximum(g.OH0, 1e-12))),
                    bias_CO=float(np.nanmedian(g.dCO / np.maximum(g.CO0, 1e-12))))

    rep = dict(states=a.states, n_cells=int(len(cells)), models={})
    for m, g in df.groupby("model", sort=False):
        r = dict(all=summ(g))
        for key in ("region", "dt_bin", "coverage"):
            r[key] = {str(k): summ(gg) for k, gg in g.groupby(key, observed=True)}
        r["region_x_dt"] = {f"{k[0]} | {k[1]}": summ(gg) for k, gg in g.groupby(["region", "dt_bin"], observed=True)}
        r["region_x_coverage"] = {f"{k[0]} | {k[1]}": summ(gg) for k, gg in g.groupby(["region", "coverage"], observed=True)}
        r["dt_x_coverage"] = {f"{k[0]} | {k[1]}": summ(gg) for k, gg in g.groupby(["dt_bin", "coverage"], observed=True)}
        rep["models"][m] = r
    df.to_csv(out / "apriori_cells.csv", index=False)
    (out / "apriori.json").write_text(json.dumps(rep, indent=1))
    lines = ["| model | group | cells | outside data | mean abs dT [K] | incr. T | incr. CO | incr. OH | CO rate ratio | OH rate ratio | CO level err | OH level err |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m, r in rep["models"].items():
        for key in ("all", "region", "dt_bin", "coverage", "region_x_dt", "region_x_coverage"):
            items = {"all": r["all"]} if key == "all" else r[key]
            for k, s in items.items():
                lines.append(f"| {m} | {k} | {s['cells']} | {s['ood']:.0%} | {s['absdT']:.1f} | {s['rel_T']:.0%} "
                             f"| {s['rel_CO']:.0%} | {s['rel_OH']:.0%} | {s['rate_CO']:.2f} | {s['rate_OH']:.2f} "
                             f"| {s['lvl_CO']:.2%} | {s['lvl_OH']:.2%} |")
    (out / "apriori.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--states", required=True)
    p.add_argument("--tau", required=True, help="stage-19 cells.npz of the same solution")
    p.add_argument("--models", nargs="+", required=True, help="label=model.txt; label_rK groups training runs")
    p.add_argument("--out", required=True)
    p.add_argument("--n-per-group", type=int, default=250)
    p.add_argument("--T-min", dest="T_min", type=float, default=600.0)
    a = p.parse_args()
    main(load_config(a.config), a)

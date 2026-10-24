"""Stage 14: a-priori check of the surrogate on the states of a Fluent solution.

Takes the cells of a Fluent ASCII export (any run: the reference with GA18 chemistry or the
surrogate run), advances each sampled cell over dt with Cantera (GA18, constant p and h) and with
the surrogate exactly as the UDF does (same sub-stepping and options), and reports the single-step
error per cell, together with where the cells sit relative to the sampled training space:

  * the UDF's OOD checks (T, T|Z, p, species ranges, VQ-PCA manifold distance, landmark distance),
    recomputed in Python from the exported model tables;
  * stage 11's coverage distance: distance to the nearest training state in per-variable standard
    deviations (Box-Cox species + T), covered if <= coverage.radius.

This separates "the model is wrong here" from "the model was never trained here", and gives the
same maps as the UDF's UDMs for a run made without them.

Reads  the ASCII export, 04_prep/*, 06_models/<arch>/model.pt, 08_fluent/<arch>/chemmanifold_model.txt.
Writes 08_fluent/apriori_<label>_<arch>/apriori.json, apriori_cells.csv, apriori.png
"""

import json

import cantera as ct
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from chemmanifold.boxcox import boxcox
from chemmanifold.chemistry import advance_const_p, make_gas
from chemmanifold.fluent import (OOD_ANY, FLAG_NAMES, advance, fluent_state, formation_enthalpies, ood,
                                 ood_features, read_fluent_ascii)
from chemmanifold.io import base_parser, load_config, load_npz, require, stage_dir
from chemmanifold.loading import load_surrogate


def read_tables(path):
    """The OOD tables (A records named ood.*) of an exported model file."""
    tables = {}
    for line in require(path).read_text().splitlines():
        parts = line.split()
        if len(parts) > 3 and parts[0] == "A" and parts[1].startswith("ood."):
            v = np.array(parts[3:], dtype=float)
            tables[parts[1]] = v if v.size > 1 else v[0]
    F = None
    if "ood.vq_K" in tables:
        K, d = int(tables["ood.vq_K"]), int(tables["ood.vq_d"])
        F = tables["ood.vq_centroid"].size // K
        tables["ood.vq_centroid"] = tables["ood.vq_centroid"].reshape(K, F)
        tables["ood.vq_mean"] = tables["ood.vq_mean"].reshape(K, F)
        tables["ood.vq_basis"] = tables["ood.vq_basis"].reshape(K, F, d)
        tables["ood.vq_threshold"] = np.atleast_1d(tables["ood.vq_threshold"])
        tables["ood.landmarks"] = tables["ood.landmarks"].reshape(-1, F)
    return tables


def main(cfg, arch, run_path, label, dt, n_cells, T_min):
    model, scalers, thermo = load_surrogate(cfg, arch)
    model.net.double()                                  # as the UDF (double precision)
    gas = make_gas(cfg)
    species = list(gas.species_names)
    P0 = cfg["chemistry"]["P_atm"] * ct.one_atm
    st = fluent_state(read_fluent_ascii(run_path), species, P0)
    tables = read_tables(stage_dir(cfg, "fluent", arch) / "chemmanifold_model.txt")
    ds = load_npz(stage_dir(cfg, "prep") / "dataset.npz")
    dt_range = (float(ds["dt"].min()), float(ds["dt"].max()))
    dt = dt or dt_range[1]

    rng = np.random.default_rng(cfg["seed"] + 14)
    cand = np.flatnonzero(st["T"] >= T_min)
    idx = np.sort(rng.choice(cand, size=min(n_cells, len(cand)), replace=False))
    Y0, T0, P = st["Y"][idx], st["T"][idx], st["P"][idx]

    # Cantera reference over dt (constant p, h) at the cell's own pressure
    Y_ct, T_ct = np.zeros_like(Y0), np.zeros(len(idx))
    for i in range(len(idx)):
        gas.TPY = T0[i], P[i], Y0[i]
        advance_const_p(gas, dt)
        Y_ct[i], T_ct[i] = gas.Y, gas.T

    P_ref = float(scalers["ctx_mu"][1])
    o = ood(tables, scalers, thermo["A"], Y0, T0, P, P_ref)
    Y_ml, T_ml, flags, n_sub, hrr_ml = advance(model, Y0, T0, P, dt, *dt_range, ood_flags=o["flags"])
    hf = formation_enthalpies(model)
    hrr_ct = -(Y_ct - Y0) @ hf / dt

    # stage 11 coverage distance to the nearest training state
    X_d = ood_features(np.vstack([ds["Y_in"], ds["Y_out"]]), np.concatenate([ds["T_in"], ds["T_out"]]), scalers)
    X_c = ood_features(Y0, T0, scalers)
    d_cov = NearestNeighbors(n_neighbors=1).fit(X_d).kneighbors(X_c)[0][:, 0]
    covered = d_cov <= cfg["coverage"]["radius"]

    lam = scalers["boxcox_lambda"]
    sig = np.asarray(scalers["sigma_y"]) * np.asarray(scalers["sigma_dy"])
    dy_ml = (boxcox(Y_ml, lam) - boxcox(Y0, lam)) / sig
    dy_ct = (boxcox(Y_ct, lam) - boxcox(Y0, lam)) / sig
    e_inc = np.sqrt(np.mean((dy_ml - dy_ct) ** 2, axis=1))       # normalized increment error per cell
    eT = T_ml - T_ct
    flagged = (flags & OOD_ANY) > 0

    def summary(m):
        if not m.any():
            return None
        ss = np.sum((dy_ct[m] - dy_ct[m].mean(0)) ** 2)
        return dict(n_cells=int(m.sum()), T_mae_K=float(np.mean(np.abs(eT[m]))), T_max_K=float(np.max(np.abs(eT[m]))),
                    r2_increments=float(1 - np.sum((dy_ml[m] - dy_ct[m]) ** 2) / ss) if ss > 0 else None,
                    hrr_rel_error_of_total_pct=float((hrr_ml[m].sum() / hrr_ct[m].sum() - 1) * 100)
                    if abs(hrr_ct[m].sum()) > 0 else None,
                    median_increment_error=float(np.median(e_inc[m])))

    rep = dict(arch=arch, export=str(run_path), dt_s=dt, trained_dt_range=dt_range, cells_sampled=len(idx),
               T_min_sampled_K=T_min,
               all=summary(np.ones(len(idx), bool)), flagged_ood=summary(flagged), not_flagged=summary(~flagged),
               covered_by_training_data=summary(covered), not_covered=summary(~covered),
               fraction_flagged_ood=float(flagged.mean()), fraction_covered=float(covered.mean()),
               flag_counts={name: int(np.sum((flags & bit) > 0)) for bit, name in FLAG_NAMES.items()},
               coverage_radius=cfg["coverage"]["radius"])
    if arch == "chemnode":
        rep["warning"] = "Phy-ChemNODE is not stable on the burner flame yet (RESULTS.md)"
    out = stage_dir(cfg, "fluent", f"apriori_{label}_{arch}")
    with open(out / "apriori.json", "w") as f:
        json.dump(rep, f, indent=2)
    cols = dict(cell=st["cell"][idx] if "cell" in st else idx, T0=T0, T_cantera=T_ct, T_surrogate=T_ml,
                hrr_cantera=hrr_ct, hrr_surrogate=hrr_ml, increment_error=e_inc, flags=flags,
                Z=o["Z"], manifold_ratio=o["manifold_ratio"], data_ratio=o["data_ratio"], coverage_distance=d_cov)
    for k in ("x", "y"):
        if k in st:
            cols[k] = st[k][idx]
    pd.DataFrame(cols).to_csv(out / "apriori_cells.csv", index=False)

    fig, ax = plt.subplots(1, 4, figsize=(19, 4.2))
    ax[0].scatter(T_ct, T_ml, s=3, c=flagged, cmap="coolwarm", vmin=0, vmax=1)
    lim = [T_ct.min(), T_ct.max()]
    ax[0].plot(lim, lim, "k--", lw=0.8)
    ax[0].set(xlabel=f"T after {dt:.1e} s, Cantera [K]", ylabel="T surrogate [K]", title="red: flagged OOD")
    ax[1].scatter(hrr_ct, hrr_ml, s=3, c=flagged, cmap="coolwarm", vmin=0, vmax=1)
    lim = [min(hrr_ct.min(), 0), hrr_ct.max()]
    ax[1].plot(lim, lim, "k--", lw=0.8)
    ax[1].set(xlabel="HRR Cantera [W/kg]", ylabel="HRR surrogate [W/kg]")
    ax[2].scatter(np.maximum(o["data_ratio"], 1e-3), np.maximum(e_inc, 1e-6), s=3, c=covered, cmap="viridis")
    ax[2].axvline(1.0, c="r", lw=0.8)
    ax[2].set(xscale="log", yscale="log", xlabel="distance to training data / threshold",
              ylabel="increment error (normalized)", title="does the error grow outside? (yellow: covered)")
    if "x" in st:
        s = ax[3].scatter(st["x"][idx], st["y"][idx], s=4, c=np.minimum(o["data_ratio"], 3), cmap="magma_r")
        fig.colorbar(s, ax=ax[3], label="data_ratio (>1 = outside)")
        ax[3].set(xlabel="x (axis) [m]", ylabel="r [m]", title="sampled cells")
        ax[3].set_aspect("equal")
    fig.tight_layout()
    fig.savefig(out / "apriori.png", dpi=150)
    a = rep["all"]
    print(f"  {len(idx)} cells, dt {dt:.1e} s: T MAE {a['T_mae_K']:.2f} K (max {a['T_max_K']:.1f} K), "
          f"{rep['fraction_flagged_ood'] * 100:.1f}% flagged OOD, {rep['fraction_covered'] * 100:.1f}% covered")


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--arch", choices=["resnet_film", "chemnode"], default="resnet_film")
    p.add_argument("--run", required=True, help="Fluent ASCII export (cell centers)")
    p.add_argument("--label", default="run")
    p.add_argument("--dt", type=float, default=None, help="s; default: the largest trained dt")
    p.add_argument("--cells", type=int, default=3000, help="cells to sample")
    p.add_argument("--T-min", type=float, default=600.0, help="K; only cells at least this hot (the UDF's T_freeze)")
    a = p.parse_args()
    main(load_config(a.config), a.arch, a.run, a.label, a.dt, a.cells, a.T_min)

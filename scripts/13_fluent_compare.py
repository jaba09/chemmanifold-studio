"""Stage 13: a-posteriori comparison of a Fluent run with the surrogate against a reference Fluent
run with direct GA18 chemistry (same case, the stiff ODE solver instead of the UDF hook).

Both runs are exported with File > Export > Solution Data > ASCII (cell centers), with at least
temperature, absolute pressure and all species mass fractions; also cell-volume (volume-weighted
metrics), density and the heat release rate if you want HRR metrics (`--hrr-col`, Fluent's
"Heat of Reaction" field), and UDM 0-6 of the surrogate run (OOD fields). Cells are matched by
cell number when both files have the same cells, else by nearest cell center.

Reports
  * T: MAE, RMSE, max |error|, volume-weighted MAE, peak T and its location, in all cells and in
    the cells the UDF flagged as outside the sampled space;
  * species: NRMSE and max |error| per species;
  * heat release: total (volume integral) and peak, if a column is given;
  * flame length: largest axial position on the axis with Z >= Z_st;
  * conditional means <T|Z>, <Y_CO|Z>, <Y_OH|Z>, <Y_CO2|Z> of both runs.

Reads  the two ASCII exports (any path), 04_prep/thermo.npz.
Writes 08_fluent/compare_<label>/compare.json, compare.png, conditional_means.csv
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from chemmanifold.chemistry import make_gas
from chemmanifold.flame import BilgerZ, stoichiometric_z, stream_states
from chemmanifold.fluent import fluent_state, read_fluent_ascii
from chemmanifold.io import base_parser, load_config, save_json, stage_dir

MAIN_SPECIES = ["CH4", "O2", "CO2", "H2O", "CO", "H2", "OH", "CH2O"]


def align(ref, run):
    if "cell" in ref and "cell" in run and len(ref["T"]) == len(run["T"]) \
            and np.array_equal(np.sort(ref["cell"]), np.sort(run["cell"])):
        i_ref, i_run = np.argsort(ref["cell"]), np.argsort(run["cell"])
        return i_ref, i_run, "cell number"
    if not all(k in d for d in (ref, run) for k in ("x", "y")):
        raise ValueError("cannot match cells: export cellnumber or x/y-coordinate in both files")
    d, j = cKDTree(np.column_stack([ref["x"], ref["y"]])).query(np.column_stack([run["x"], run["y"]]))
    return j, np.arange(len(run["T"])), f"nearest cell center (max distance {d.max():.2e} m)"


def take(state, idx):
    return {k: v[idx] for k, v in state.items()}


def t_metrics(Ta, Tb, w, mask):
    if not mask.any():
        return None
    e = Ta[mask] - Tb[mask]
    return dict(n_cells=int(mask.sum()), mae_K=float(np.mean(np.abs(e))), rmse_K=float(np.sqrt(np.mean(e ** 2))),
                max_abs_K=float(np.max(np.abs(e))), bias_K=float(np.mean(e)),
                volume_weighted_mae_K=float(np.sum(w[mask] * np.abs(e)) / np.sum(w[mask])))


def flame_length(st, Z, Z_st, axis_tol):
    if "x" not in st or "y" not in st:
        return None
    on_axis = np.abs(st["y"]) <= axis_tol
    m = on_axis & (Z >= Z_st)
    return float(st["x"][m].max()) if m.any() else None


def main(cfg, ref_path, run_path, label, hrr_col, axis_tol):
    gas = make_gas(cfg)
    species = list(gas.species_names)
    ref_cols, run_cols = read_fluent_ascii(ref_path), read_fluent_ascii(run_path)
    P0 = cfg["chemistry"]["P_atm"] * 101325.0
    ref, run = fluent_state(ref_cols, species, P0), fluent_state(run_cols, species, P0)
    i_ref, i_run, how = align(ref, run)
    ref, run = take(ref, i_ref), take(run, i_run)
    if hrr_col:
        ref["hrr"], run["hrr"] = ref_cols[hrr_col.lower()][i_ref], run_cols[hrr_col.lower()][i_run]
    (Yf, _), (Yo, _) = stream_states(gas, cfg)
    bz = BilgerZ(gas, Yf, Yo)
    Z = np.clip(bz(ref["Y"]), 0, 1)
    Z_st = stoichiometric_z(gas, cfg)
    if "volume" in ref:
        w = ref["volume"]
    else:   # 2D axisymmetric without cell volumes: weight by radius (cell areas are not exported)
        w = np.abs(ref["y"]) + 1e-12 if "y" in ref else np.ones(len(Z))
    ood = run.get("ood_any")
    every = np.ones(len(Z), bool)

    report = dict(reference=str(ref_path), surrogate=str(run_path), cells=len(Z), matched_by=how,
                  T=dict(all=t_metrics(run["T"], ref["T"], w, every),
                         hot_cells_T_ref_above_1000K=t_metrics(run["T"], ref["T"], w, ref["T"] > 1000)))
    if ood is not None:
        report["T"]["cells_flagged_ood"] = t_metrics(run["T"], ref["T"], w, ood > 0.5)
        report["T"]["cells_not_flagged"] = t_metrics(run["T"], ref["T"], w, ood < 0.5)
        report["ood_fraction_of_cells"] = float(np.mean(ood > 0.5))
    k_ref, k_run = int(np.argmax(ref["T"])), int(np.argmax(run["T"]))
    report["peak_T"] = {"reference_K": float(ref["T"][k_ref]), "surrogate_K": float(run["T"][k_run])}
    if "x" in ref:
        report["peak_T"]["reference_xy_m"] = [float(ref["x"][k_ref]), float(ref["y"][k_ref])]
        report["peak_T"]["surrogate_xy_m"] = [float(run["x"][k_run]), float(run["y"][k_run])]
    sp = {}
    for s in species:
        k = species.index(s)
        a, b = run["Y"][:, k], ref["Y"][:, k]
        sp[s] = dict(nrmse_pct=float(np.linalg.norm(a - b) / max(np.linalg.norm(b), 1e-30) * 100),
                     max_abs=float(np.max(np.abs(a - b))), peak_ref=float(b.max()), peak_surrogate=float(a.max()))
    report["species"] = sp
    if hrr_col:
        report["heat_release"] = dict(
            total_reference=float(np.sum(w * ref["hrr"])), total_surrogate=float(np.sum(w * run["hrr"])),
            total_rel_error_pct=float((np.sum(w * run["hrr"]) / np.sum(w * ref["hrr"]) - 1) * 100),
            peak_reference=float(ref["hrr"].max()), peak_surrogate=float(run["hrr"].max()))
    Z_run = np.clip(bz(run["Y"]), 0, 1)
    report["flame_length_m"] = dict(Z_st=Z_st, reference=flame_length(ref, Z, Z_st, axis_tol),
                                    surrogate=flame_length(run, Z_run, Z_st, axis_tol))

    # conditional means on Z bands (stage 11 bands, finer around Z_st)
    edges = np.unique(np.concatenate([np.linspace(0, 4 * Z_st, 33), np.linspace(4 * Z_st, 1, 13)]))
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m_ref, m_run = (Z >= lo) & (Z < hi), (Z_run >= lo) & (Z_run < hi)
        if m_ref.sum() < 3 or m_run.sum() < 3:
            continue
        row = dict(Z_mid=0.5 * (lo + hi), n_ref=int(m_ref.sum()), n_run=int(m_run.sum()),
                   T_ref=np.average(ref["T"][m_ref], weights=w[m_ref]), T_run=np.average(run["T"][m_run], weights=w[m_run]))
        for s in ("CO", "OH", "CO2"):
            k = species.index(s)
            row[f"{s}_ref"] = np.average(ref["Y"][m_ref, k], weights=w[m_ref])
            row[f"{s}_run"] = np.average(run["Y"][m_run, k], weights=w[m_run])
        rows.append(row)
    cm = pd.DataFrame(rows)
    out = stage_dir(cfg, "fluent", f"compare_{label}")
    cm.to_csv(out / "conditional_means.csv", index=False)
    if len(cm):
        report["conditional_T_given_Z_max_abs_diff_K"] = float(np.max(np.abs(cm.T_run - cm.T_ref)))
    save_json(out / "compare.json", report)

    fig, ax = plt.subplots(2, 3, figsize=(15, 8))
    hot = ref["T"] > 400
    a = ax[0, 0]
    a.scatter(ref["T"][hot], run["T"][hot], s=1, c=(ood[hot] if ood is not None else "C0"), cmap="coolwarm",
              vmin=0, vmax=1, rasterized=True)
    lim = [ref["T"].min(), max(ref["T"].max(), run["T"].max())]
    a.plot(lim, lim, "k--", lw=0.8)
    a.set(xlabel="T reference (GA18 ODE) [K]", ylabel="T surrogate [K]",
          title="per cell" + (" (red: flagged OOD)" if ood is not None else ""))
    for a, col, lab in ((ax[0, 1], "T", "<T|Z> [K]"), (ax[0, 2], "CO", "<Y_CO|Z>"), (ax[1, 0], "OH", "<Y_OH|Z>"),
                        (ax[1, 1], "CO2", "<Y_CO2|Z>")):
        if len(cm):
            a.plot(cm.Z_mid, cm[f"{col}_ref"], "k-", label="reference")
            a.plot(cm.Z_mid, cm[f"{col}_run"], "C1--", label="surrogate")
        a.axvline(Z_st, c="0.5", lw=0.5, ls=":")
        a.set(xlim=(0, min(1, 6 * Z_st)), xlabel="Z", ylabel=lab)
        a.legend(fontsize=8)
    a = ax[1, 2]
    if "x" in ref:
        tc = a.tricontourf(ref["x"], ref["y"], run["T"] - ref["T"], levels=21, cmap="RdBu_r")
        fig.colorbar(tc, ax=a, label="T surrogate - T reference [K]")
        if ood is not None and (ood > 0.5).any():
            a.tricontour(ref["x"], ref["y"], ood, levels=[0.5], colors="k", linewidths=0.6)
        a.set(xlabel="x (axis) [m]", ylabel="r [m]", title="T error map (black: OOD region)")
        a.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(out / "compare.png", dpi=150)
    t = report["T"]["all"]
    print(f"  {len(Z)} cells ({how}): T MAE {t['mae_K']:.1f} K, max {t['max_abs_K']:.0f} K; peak T "
          f"{report['peak_T']['surrogate_K']:.0f} vs {report['peak_T']['reference_K']:.0f} K")
    print(json.dumps({s: round(sp[s]["nrmse_pct"], 2) for s in MAIN_SPECIES}, indent=None))


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--ref", required=True, help="ASCII export of the reference run (direct GA18 chemistry)")
    p.add_argument("--run", required=True, help="ASCII export of the surrogate run")
    p.add_argument("--label", default="run", help="name of the output folder 08_fluent/compare_<label>")
    p.add_argument("--hrr-col", default=None, help="column with the heat release rate in both exports")
    p.add_argument("--axis-tol", type=float, default=1e-4, help="m; cells with |y| below this are on the axis")
    a = p.parse_args()
    main(load_config(a.config), a.ref, a.run, a.label, a.hrr_col, a.axis_tol)

"""Stage 16 (flame mode, by hand): where does a Fluent solution leave the sampled space, and which
exploration settings would reach it?

Takes one or more Fluent ASCII exports (snapshots of the same run, or of different runs), recomputes
the UDF's OOD checks for every hot cell from the exported model tables (no network needed), and
places each cell in the coordinates the exploration of stages 0-4 is set with:

  * Z     Bilger mixture fraction (envelope.z_knots / u_knots);
  * psi   heat-loss fraction: 0 = the adiabatic mixing enthalpy at Z, 1 = the cell's composition
          cooled to envelope.T_wall (envelope.psi_max, pasr.loss_fraction_range); < 0 means more
          enthalpy than adiabatic mixing, which differential diffusion gives in a real flame;
  * c     progress: (Y_CO2+Y_CO+Y_H2O+Y_H2) over its value in the lowest-strain flamelet at Z;
  * strain, if the export has Fluent's strain rate: compared with the strain range of the stage-0
          flamelets (flame.mdot_fuel_min, strain_factor). Fluent's |S| and the counterflow's maximum
          axial velocity gradient are different measures, so read this as an order of magnitude.

The CFD solution is used only as a diagnostic: it says where the exploration should look. Nothing from
it goes into training; the proposals change the a-priori exploration (bounds, seed weights, strain
range), whose states then come from Cantera as before.

Reads  one or more Fluent ASCII exports, 00_flame/*, 08_fluent/<arch>/chemmanifold_model.txt (or --model).
Writes 08_fluent/gaps_<label>/gaps.json, gaps_cells.csv, gaps.png,
       proposed_exploration.yaml (suggested config changes; nothing is changed automatically)
"""

import json

import cantera as ct
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from chemmanifold.chemistry import make_gas
from chemmanifold.fluent import (DEFAULT_OPTIONS, FLAG_NAMES, OOD_ANY, OOD_SPECIES, fluent_state, model_file_scalers,
                                 ood, ood_features, read_fluent_ascii, read_ood_tables)
from chemmanifold.flame import BilgerZ, flame_pressure, is_flame, stream_states, wall_temperature
from chemmanifold.io import base_parser, load_config, load_json, load_npz, require, stage_dir

PROGRESS_SPECIES = ("CO2", "CO", "H2O", "H2")
STRAIN_COLUMNS = ("strain-rate-mag", "strain-rate", "strain_rate")


def read_ini(path):
    """The OOD margins of a chemmanifold.ini, so the offline flags match the run's."""
    opt = {}
    if path:
        for line in open(path):
            line = line.split("#", 1)[0]
            if "=" in line:
                k, v = (s.strip() for s in line.split("=", 1))
                if k in DEFAULT_OPTIONS:
                    opt[k] = float(v)
    return opt


def load_cells(paths, species, P0, T_min):
    frames = []
    for snap, path in enumerate(paths):
        cols = read_fluent_ascii(path)
        st = fluent_state(cols, species, P0)
        hot = st["T"] >= T_min
        f = dict(snapshot=np.full(hot.sum(), snap), T=st["T"][hot], P=st["P"][hot])
        for k in ("cell", "x", "y", "volume", "ood_flags"):
            if k in st:
                f[k] = st[k][hot]
        sc = next((c for c in STRAIN_COLUMNS if c in cols), None)
        if sc:
            f["strain"] = cols[sc][hot]
        frames.append((pd.DataFrame(f), st["Y"][hot]))
        print(f"  {path}: {len(st['T'])} cells, {hot.sum()} at T >= {T_min:.0f} K"
              + ("" if sc else " (no strain-rate column)"))
    return pd.concat([f for f, _ in frames], ignore_index=True), np.vstack([y for _, y in frames])


def enthalpy_coordinates(gas, cfg, Y, T, Z):
    """psi (heat-loss fraction towards T_wall) and the enthalpy deficit dh = h - h_mix(Z) [J/kg]."""
    P = flame_pressure(cfg)
    (_, hf), (_, ho) = stream_states(gas, cfg)
    arr = ct.SolutionArray(gas, len(T))
    arr.TPY = T, P, Y
    h = arr.enthalpy_mass.copy()
    arr.TPY = wall_temperature(cfg), P, Y
    h_wall = arr.enthalpy_mass.copy()
    h_mix = Z * hf + (1 - Z) * ho
    return (h_mix - h) / np.maximum(h_mix - h_wall, 1.0), h - h_mix


def progress(gas, cfg, Y, Z):
    """c = Y_c / Y_c(lowest-strain flamelet at Z), Y_c = sum of PROGRESS_SPECIES."""
    ref = load_npz(require(stage_dir(cfg, "flame") / "burnt_reference.npz"))
    idx = [gas.species_index(s) for s in PROGRESS_SPECIES]
    yc = Y[:, idx].sum(1)
    yc_b = np.interp(Z, ref["Z"], ref["Y"][:, idx].sum(1))
    return yc / np.maximum(yc_b, 1e-6)


def band_shares(Z, knots):
    b = np.clip(np.searchsorted(knots, Z, side="right") - 1, 0, len(knots) - 2)
    return np.bincount(b, minlength=len(knots) - 1) / max(len(Z), 1)


def proposals(cfg, cells, ood_mask, weight, fl_ref):
    """Suggested exploration settings, each with the reason, from the OOD cells."""
    env, pasr = cfg["envelope"], cfg["pasr"]
    out, why = {}, {}
    o = cells[ood_mask]
    if len(o) == 0:
        return out, {"none": "no hot cell is outside the sampled space"}

    # seed weights per Z band: blend the current shares with the OOD cells' shares
    zk, uk = np.asarray(env["z_knots"]), np.asarray(env["u_knots"])
    cur = np.diff(uk)
    new = (1 - weight) * cur + weight * band_shares(o.Z.values, zk)
    new = np.maximum(new, 0.02)
    new /= new.sum()
    out["envelope.u_knots"] = [0.0] + [round(float(v), 3) for v in np.cumsum(new)[:-1]] + [1.0]
    why["envelope.u_knots"] = ("seed share per z_knots band, now " + ", ".join(f"{v:.0%}" for v in cur)
                               + "; OOD cells per band " + ", ".join(f"{v:.0%}" for v in band_shares(o.Z.values, zk))
                               + f"; proposed {weight:.0%} towards the OOD cells")

    # heat loss: reach the 99th percentile of the OOD cells' psi
    q = float(np.quantile(o.psi, 0.99))
    if env.get("heat_loss", "absolute") == "fraction":
        cur_max = float(env.get("psi_max", 1.0))
        if q > cur_max + 0.02:
            prop = round(min(0.95, q + 0.03), 2)
            out["envelope.psi_max"] = prop
            out["pasr.loss_fraction_range"] = [float(pasr.get("loss_fraction_range", [0.0, cur_max])[0]), prop]
            why["envelope.psi_max"] = (f"99% of the OOD cells have psi <= {q:.2f}, above psi_max {cur_max:.2f}; "
                                       "above ~0.9 the seeds are close to frozen, so capped at 0.95")
    else:
        dq = float(np.quantile(-o.dh, 0.99))
        cur_max = float(env.get("heat_loss_max", 0.0))
        if dq > 1.05 * cur_max:
            out["envelope.heat_loss_max"] = float(f"{dq:.2g}")
            out["pasr.dh_range"] = [-float(f"{dq:.2g}"), 0.0]
            why["envelope.heat_loss_max"] = (f"99% of the OOD cells lost <= {dq:.3g} J/kg, above heat_loss_max "
                                             f"{cur_max:.3g}; or switch to heat_loss: fraction (configs/"
                                             "burner_fluent_nonadiabatic.yaml)")
    n_excess = int((o.psi < -0.02).sum())
    if n_excess:
        why["enthalpy_excess"] = (f"{n_excess} OOD cells ({n_excess / len(o):.0%}) have more enthalpy than "
                                  "adiabatic mixing at their Z (differential diffusion, which also makes Bilger Z "
                                  "non-conserved, or heat taken from a hotter wall). The exploration only removes "
                                  "heat; these states come only from the mixture-averaged flamelets, so more "
                                  "flamelets (a lower flame.strain_factor) or a bounded enthalpy excess in the seeds "
                                  "are the a-priori ways to reach them. Check the T-Z map first")

    # strain range of the flamelets
    if "strain" in o and fl_ref is not None:
        a = np.asarray(fl_ref["strain_rates"], float)
        near = o[(o.Z > 0.5 * fl_ref["Z_st"]) & (o.Z < 2.0 * fl_ref["Z_st"])]
        if len(near):
            lo, hi = np.quantile(near.strain, [0.05, 0.95])
            if lo < 0.7 * a.min():
                out["flame.mdot_fuel_min"] = float(f"{cfg['flame']['mdot_fuel_min'] * lo / a.min():.2g}")
                why["flame.mdot_fuel_min"] = (f"5% of the OOD cells near Z_st have strain < {lo:.3g} 1/s, below the "
                                              f"lowest flamelet ({a.min():.3g} 1/s); strain scales ~ with mdot")
            if hi > a.max():
                why["strain_above_extinction"] = (f"5% of the OOD cells near Z_st have strain > {hi:.3g} 1/s, above "
                                                  f"the last burning flamelet ({a.max():.3g} 1/s, extinction). Steady "
                                                  "flamelets cannot go there; those states come from the 0D/PaSR seeds "
                                                  "(partially burnt, alpha < 1), so check the c column")
    return out, why


def main(cfg, runs, label, arch, model_path, ini, T_min, weight):
    if not is_flame(cfg):
        raise SystemExit("stage 16 needs envelope.mode: flame")
    gas = make_gas(cfg)
    species = list(gas.species_names)
    P0 = flame_pressure(cfg)
    model_path = require(model_path or stage_dir(cfg, "fluent", arch) / "chemmanifold_model.txt")
    tables = read_ood_tables(model_path)
    if "ood.T_range" not in tables:
        raise SystemExit(f"{model_path} has no OOD tables (re-run stage 12)")
    scalers, A = model_file_scalers(model_path)
    if len(scalers["mu_y"]) != len(species):
        raise SystemExit(f"{model_path} has {len(scalers['mu_y'])} species, the mechanism {len(species)}")
    opt = read_ini(ini)

    cells, Y = load_cells(runs, species, P0, T_min)
    r = ood(tables, scalers, A, Y, cells["T"].values, cells["P"].values, float(scalers["ctx_mu"][1]), opt)
    cells["flags"], cells["Z"] = r["flags"], r["Z"]
    cells["manifold_ratio"], cells["data_ratio"] = r["manifold_ratio"], r["data_ratio"]
    cells["psi"], cells["dh"] = enthalpy_coordinates(gas, cfg, Y, cells["T"].values, r["Z"])
    cells["c"] = progress(gas, cfg, Y, np.clip(r["Z"], 0, 1))
    is_ood = (cells["flags"] & OOD_ANY).values > 0
    fl_ref = load_json(stage_dir(cfg, "flame") / "flame_reference.json")

    # which species leave their sampled range (the flag only says "some species")
    x = ood_features(Y, cells["T"].values, scalers)[:, :-1]
    m = opt.get("y_margin", DEFAULT_OPTIONS["y_margin"])
    below = x < np.asarray(tables["ood.yt_min"]) - m
    above = x > np.asarray(tables["ood.yt_max"]) + m
    sp_out = {s: dict(below=int(below[:, k].sum()), above=int(above[:, k].sum()))
              for k, s in enumerate(species) if below[:, k].any() or above[:, k].any()}

    # gap map: hot cells and OOD share per (Z band of the UDF tables, psi band)
    z_edges = np.asarray(tables["ood.z_edges"])
    psi_edges = np.array([-np.inf, 0.0, 0.2, 0.4, 0.6, 0.8, np.inf])
    zb = np.clip(np.searchsorted(z_edges, cells.Z, side="right") - 1, 0, len(z_edges) - 2)
    pb = np.searchsorted(psi_edges, cells.psi, side="right") - 1
    gap = (pd.DataFrame(dict(Z_lo=z_edges[zb], Z_hi=z_edges[zb + 1], psi_lo=psi_edges[pb], psi_hi=psi_edges[pb + 1],
                             ood=is_ood))
           .groupby(["Z_lo", "Z_hi", "psi_lo", "psi_hi"]).ood.agg(cells="size", ood_cells="sum").reset_index())
    gap["ood_fraction"] = gap.ood_cells / gap.cells
    gap = gap[gap.ood_cells > 0].sort_values("ood_cells", ascending=False)

    prop, why = proposals(cfg, cells, is_ood, weight, fl_ref)
    rep = dict(exports=[str(p) for p in runs], model=str(model_path), T_min_K=T_min, options=opt,
               hot_cells=int(len(cells)), ood_cells=int(is_ood.sum()), ood_fraction=float(is_ood.mean()),
               ood_fraction_per_snapshot=cells.assign(o=is_ood).groupby("snapshot").o.mean().round(4).tolist(),
               flag_counts={name: int(((cells["flags"] & bit) > 0).sum()) for bit, name in FLAG_NAMES.items()
                            if bit & OOD_ANY},
               species_out_of_range=sp_out,
               ood_cells_quantiles={k: dict(zip(["q05", "q50", "q95"], np.quantile(cells[k][is_ood], [.05, .5, .95])
                                                .round(4).tolist())) for k in ("Z", "T", "psi", "c")
                                    + (("strain",) if "strain" in cells else ())} if is_ood.any() else {},
               flamelet_strain_range=[min(fl_ref["strain_rates"]), max(fl_ref["strain_rates"])],
               largest_gaps=gap.head(15).round(4).to_dict("records"),
               proposals=prop, reasons=why)
    if "ood_flags" in cells:   # the run's own UDM 1, if exported: does the offline check agree?
        rep["agreement_with_udf_flags"] = float(np.mean(((cells.ood_flags.astype(int) & OOD_ANY) > 0) == is_ood))
    out = stage_dir(cfg, "fluent", f"gaps_{label}")
    with open(out / "gaps.json", "w") as f:
        json.dump(rep, f, indent=2, default=float)
    cells.to_csv(out / "gaps_cells.csv", index=False)
    with open(out / "proposed_exploration.yaml", "w") as f:
        f.write("# Suggested changes to the exploration (stage 16). Nothing is applied automatically:\n"
                "# copy what you accept into the config, then re-run stages 0-12.\n")
        for k, v in why.items():
            f.write(f"# {k}: {v}\n")
        yaml.safe_dump(prop, f, sort_keys=False, default_flow_style=None)
    plot(out / "gaps.png", cells, is_ood, tables, cfg, sp_out, fl_ref)

    print(f"  {len(cells)} hot cells, {is_ood.mean():.1%} outside the sampled space; "
          + ", ".join(f"{k} {v}" for k, v in rep["flag_counts"].items()))
    for k, v in why.items():
        print(f"  - {k}: {v}")
    print(f"  proposals -> {out / 'proposed_exploration.yaml'}")


def plot(path, cells, is_ood, tables, cfg, sp_out, fl_ref):
    has_strain, has_xy = "strain" in cells, "x" in cells
    n = 4 + has_strain + has_xy
    fig, ax = plt.subplots(1, n, figsize=(4.6 * n, 4.2))
    kw = dict(s=2, alpha=0.5, rasterized=True)
    zc = 0.5 * (np.asarray(tables["ood.z_edges"])[1:] + np.asarray(tables["ood.z_edges"])[:-1])
    for a in ax[:2]:
        a.scatter(cells.Z[~is_ood], cells[["T", "psi"][a is ax[1]]][~is_ood], c="0.7", label="inside", **kw)
        a.scatter(cells.Z[is_ood], cells[["T", "psi"][a is ax[1]]][is_ood], c="C3", label="OOD", **kw)
        a.set_xscale("symlog", linthresh=0.05)
        a.axvline(fl_ref["Z_st"], c="k", lw=0.6, ls=":")
    ax[0].step(zc, tables["ood.T_min_z"], "b-", where="mid", lw=1, label="sampled T range")
    ax[0].step(zc, tables["ood.T_max_z"], "b-", where="mid", lw=1)
    ax[0].set(xlabel="Z", ylabel="T [K]", title="T vs Z")
    ax[0].legend(markerscale=4, fontsize=8)
    env = cfg["envelope"]
    if env.get("heat_loss", "absolute") == "fraction":
        ax[1].axhline(env.get("psi_max", 1.0), c="b", lw=1, label="psi_max")
    ax[1].axhline(0.0, c="k", lw=0.6)
    ax[1].set(xlabel="Z", ylabel="psi (heat-loss fraction)", title="heat loss vs Z")
    bands = np.asarray(env["z_knots"])
    b = np.clip(np.searchsorted(bands, cells.Z, side="right") - 1, 0, len(bands) - 2)
    frac = [is_ood[b == i].mean() if (b == i).any() else 0 for i in range(len(bands) - 1)]
    ax[2].bar(range(len(frac)), frac, color="C3")
    ax[2].set_xticks(range(len(frac)), [f"{bands[i]:.3g}-{bands[i + 1]:.3g}" for i in range(len(frac))],
                     rotation=30, fontsize=8)
    ax[2].set(ylabel="OOD share of hot cells", title="per z_knots band")
    names = sorted(sp_out, key=lambda s: -(sp_out[s]["below"] + sp_out[s]["above"]))[:10]
    if not names:
        ax[3].text(0.5, 0.5, "none", ha="center", va="center", transform=ax[3].transAxes)
    ax[3].barh(names, [sp_out[s]["above"] for s in names], color="C3", label="above max")
    ax[3].barh(names, [-sp_out[s]["below"] for s in names], color="C0", label="below min")
    ax[3].set(xlabel="cells", title="species out of sampled range")
    ax[3].legend(fontsize=8)
    i = 4
    if has_strain:
        s = cells.strain.clip(lower=1e-3)
        bins = np.logspace(np.log10(s.min()), np.log10(s.max()), 40)
        ax[i].hist(s[~is_ood], bins, color="0.7", label="inside")
        ax[i].hist(s[is_ood], bins, color="C3", alpha=0.7, label="OOD")
        ax[i].axvspan(min(fl_ref["strain_rates"]), max(fl_ref["strain_rates"]), color="b", alpha=0.15,
                      label="flamelets")
        ax[i].set(xscale="log", xlabel="strain rate [1/s]", ylabel="cells", title="strain")
        ax[i].legend(fontsize=8)
        i += 1
    if has_xy:
        ax[i].scatter(cells.x[~is_ood], cells.y[~is_ood], c="0.8", **kw)
        ax[i].scatter(cells.x[is_ood], cells.y[is_ood], c="C3", **kw)
        ax[i].set(xlabel="x [m]", ylabel="r [m]", title="OOD cells (red)")
        ax[i].set_aspect("equal")
    fig.tight_layout()
    fig.savefig(path, dpi=140)


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--run", nargs="+", required=True, help="Fluent ASCII export(s), cell centers")
    p.add_argument("--label", default="run")
    p.add_argument("--arch", choices=["resnet_film", "chemnode"], default="resnet_film")
    p.add_argument("--model", default=None, help="chemmanifold_model.txt; default 08_fluent/<arch>/")
    p.add_argument("--ini", default=None, help="chemmanifold.ini of the run (its T_margin, y_margin, p_tol)")
    p.add_argument("--T-min", type=float, default=600.0, help="K; only cells at least this hot (the UDF's T_freeze)")
    p.add_argument("--weight", type=float, default=0.5,
                   help="how far the proposed Z seed shares move towards the OOD cells (0-1)")
    a = p.parse_args()
    main(load_config(a.config), a.run, a.label, a.arch, a.model, a.ini, a.T_min, a.weight)

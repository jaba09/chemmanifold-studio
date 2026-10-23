"""Stage 11 (flame mode only): does the sampled data cover the burner flame, without much excess?

Compares every state in the training data (inputs and targets) with every flamelet state from
stage 0, in the same standardized Box-Cox + temperature coordinates the surrogates see.

* covered: a flamelet state with a data state within `coverage.radius` (Euclidean distance in
  units of the per-variable standard deviation, over all species plus T). The headline number uses
  the held-out flamelets (`flame.holdout_every`), whose states are not in the data;
* beyond the flame: data states farther than the same radius from every flamelet state;
* bounds: T, Z and per-species maxima of the data vs the flamelets ("not less, not much more").

Reads  00_flame/*, 04_prep/dataset.npz, 04_prep/scalers.json.
Writes 07_eval/flame_coverage.json, 07_eval/flame_coverage.png
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.neighbors import NearestNeighbors

from chemmanifold.boxcox import boxcox
from chemmanifold.chemistry import make_gas
from chemmanifold.flame import BilgerZ, flamelet_split, stream_states
from chemmanifold.io import base_parser, load_config, load_json, load_npz, save_json, stage_dir


def features(Y, T, sc):
    y = (boxcox(Y, sc["boxcox_lambda"]) - np.asarray(sc["mu_y"])) / np.asarray(sc["sigma_y"])
    t = (T - sc["ctx_mu"][0]) / sc["ctx_sigma"][0]
    return np.column_stack([y, t])


def main(cfg):
    radius = cfg["coverage"]["radius"]
    rng = np.random.default_rng(cfg["seed"] + 4)
    sc = load_json(stage_dir(cfg, "prep") / "scalers.json")
    ds = load_npz(stage_dir(cfg, "prep") / "dataset.npz")
    fl = load_npz(stage_dir(cfg, "flame") / "flamelets.npz")
    ref = load_json(stage_dir(cfg, "flame") / "flame_reference.json")
    br = load_npz(stage_dir(cfg, "flame") / "burnt_reference.npz")
    gas = make_gas(cfg)
    (Yf, _), (Yo, _) = stream_states(gas, cfg)
    bz = BilgerZ(gas, Yf, Yo)

    Y_d = np.vstack([ds["Y_in"], ds["Y_out"]])
    T_d = np.concatenate([ds["T_in"], ds["T_out"]])
    Z_d = np.clip(bz(Y_d), 0, 1)
    X_d, X_f = features(Y_d, T_d, sc), features(fl["Y"], fl["T"], sc)

    d_f = NearestNeighbors(n_neighbors=1).fit(X_d).kneighbors(X_f)[0][:, 0]
    covered = d_f <= radius
    _, held = flamelet_split(cfg, int(fl["strain_id"].max()) + 1)
    is_held = np.isin(fl["strain_id"], held)
    test = is_held if is_held.any() else np.ones(len(covered), bool)
    d_d = NearestNeighbors(n_neighbors=1).fit(X_f).kneighbors(X_d)[0][:, 0]
    sub = rng.choice(len(X_d), size=min(len(X_d), 20000), replace=False)  # for plotting

    species = sc["species"]
    bins = [0, 0.5 * ref["Z_st"], ref["Z_st"], 2 * ref["Z_st"], 4 * ref["Z_st"], 1.0001]
    per_bin = {}
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (fl["Z"] >= lo) & (fl["Z"] < hi) & test
        if m.any():
            per_bin[f"{lo:.3f}-{min(hi, 1):.3f}"] = float(covered[m].mean())
    report = dict(
        n_data_states=len(X_d), n_flamelet_states=len(X_f), radius=radius,
        heldout_distance_quantiles={str(p): float(np.quantile(d_f[test], p)) for p in (0.5, 0.9, 0.95, 1.0)},
        heldout_flamelets=held, heldout_states_covered=float(covered[test].mean()),
        training_flamelet_states_covered=float(covered[~is_held].mean()) if (~is_held).any() else None,
        heldout_covered_by_Z_bin=per_bin, flamelet_strain_rates=ref["strain_rates"],
        data_states_beyond_flame=float(np.mean(d_d > radius)),
        T_range=dict(data=[float(T_d.min()), float(T_d.max())],
                     flamelets=[float(fl["T"].min()), float(fl["T"].max())],
                     adiabatic_max=ref["T_ad_max"]),
        Z_range=dict(data=[float(Z_d.min()), float(Z_d.max())],
                     flamelets=[float(fl["Z"].min()), float(fl["Z"].max())]),
        Y_max=dict(data={s: float(Y_d[:, k].max()) for k, s in enumerate(species)},
                   flamelets={s: float(fl["Y"][:, k].max()) for k, s in enumerate(species)}),
    )
    ratio = {s: report["Y_max"]["data"][s] / max(report["Y_max"]["flamelets"][s], 1e-30) for s in species}
    report["Y_max_ratio_data_over_flame"] = ratio
    out = stage_dir(cfg, "eval")
    save_json(out / "flame_coverage.json", report)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, xmax in zip(axes, (1.0, 4 * ref["Z_st"])):
        ax.scatter(Z_d[sub], T_d[sub], s=1, c="0.75", label="sampled data", rasterized=True)
        sc_ = ax.scatter(fl["Z"], fl["T"], s=3, c=fl["strain_id"], cmap="viridis", label="flamelets")
        ax.scatter(fl["Z"][~covered], fl["T"][~covered], s=12, facecolors="none", edgecolors="r",
                   label="flamelet state not covered")
        ax.plot(br["Z"], br["T_ad"], "k--", lw=0.8, label="adiabatic equilibrium")
        ax.axvline(ref["Z_st"], c="k", lw=0.5, ls=":")
        ax.set(xlim=(0, xmax), xlabel="mixture fraction Z", ylabel="T [K]")
    axes[0].legend(fontsize=7, markerscale=3, loc="upper right")
    axes[1].set_title(f"{covered[test].mean() * 100:.1f}% of held-out flamelet states covered")
    fig.colorbar(sc_, ax=axes[1], label="flamelet index (low -> high strain)")
    fig.tight_layout()
    fig.savefig(out / "flame_coverage.png", dpi=150)
    print(f"  {covered[test].mean() * 100:.1f}% of {test.sum()} held-out flamelet states covered; T data "
          f"{T_d.min():.0f}-{T_d.max():.0f} K vs flamelets {fl['T'].min():.0f}-{fl['T'].max():.0f} K; "
          f"{report['data_states_beyond_flame'] * 100:.1f}% of data beyond the steady flame")


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))

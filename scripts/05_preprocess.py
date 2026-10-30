"""Stage 5 (Sections 3.1, 3.2, 5.1): merge sampled pairs, split train/validation, fit the Box-Cox +
z-score scalers and increment scales, and export the thermodynamic tables used by the physics layers.

Reads  03_samples/pairs_0d.npz, 03_samples/pairs_pasr.npz (+ pairs_flamelet.npz, pairs_recirc.npz,
       pairs_unsteady.npz, pairs_vitiated.npz, pairs_relax.npz in flame mode).
Writes 04_prep/dataset.npz  (raw pairs + split mask + standardized arrays)
       04_prep/scalers.json (lambda, mu_y, sigma_y, ctx_mu, ctx_sigma, sigma_dy, dt_base)
       04_prep/thermo.npz   (A, W, NASA-7 tables, species/element names)
"""

import numpy as np

from chemmanifold.boxcox import boxcox
from chemmanifold.chemistry import make_gas, thermo_tables
from chemmanifold.io import base_parser, load_config, load_npz, save_json, save_npz, stage_dir


def main(cfg):
    pp = cfg["preprocess"]
    lam = pp["boxcox_lambda"]
    samples = stage_dir(cfg, "samples")
    parts = [load_npz(samples / "pairs_0d.npz"), load_npz(samples / "pairs_pasr.npz")]
    for extra in ("pairs_flamelet.npz", "pairs_recirc.npz", "pairs_unsteady.npz", "pairs_vitiated.npz",
                  "pairs_relax.npz"):  # flame mode
        if (samples / extra).exists():
            parts.append(load_npz(samples / extra))
    data = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    N = len(data["dt"])

    rng = np.random.default_rng(cfg["seed"] + 2)
    is_val = np.zeros(N, dtype=bool)
    is_val[rng.choice(N, size=int(round(pp["val_frac"] * N)), replace=False)] = True
    tr = ~is_val

    # Box-Cox + z-score statistics over stacked [Y_t; Y_t+dt] of the training split (Eq. 19)
    y_all = boxcox(np.vstack([data["Y_in"][tr], data["Y_out"][tr]]), lam)
    mu_y = y_all.mean(0)
    sigma_y = np.maximum(y_all.std(0), pp["sigma_y_min"])

    # context (T, P, h, log10 dt) statistics (Eq. 20)
    ctx = np.column_stack([data["T_in"], data["P_in"], data["h_in"], np.log10(data["dt"])])
    ctx_mu = ctx[tr].mean(0)
    ctx_sigma = np.maximum(ctx[tr].std(0), 1e-12)

    yt_in = (boxcox(data["Y_in"], lam) - mu_y) / sigma_y
    yt_out = (boxcox(data["Y_out"], lam) - mu_y) / sigma_y
    sigma_dy = np.maximum((yt_out - yt_in)[tr].std(0), pp["sigma_dy_min"])    # Eq. 42

    gas = make_gas(cfg)
    thermo = thermo_tables(gas)
    scalers = dict(
        boxcox_lambda=lam, mu_y=mu_y, sigma_y=sigma_y, ctx_mu=ctx_mu, ctx_sigma=ctx_sigma,
        sigma_dy=sigma_dy, dt_base=cfg["autoignition"]["dt_base"],
        T_scale=float(np.std(data["T_out"][tr])), species=list(gas.species_names),
    )

    out = stage_dir(cfg, "prep")
    save_npz(out / "dataset.npz", **data, is_val=is_val, yt_in=yt_in, yt_out=yt_out,
             ctx=(ctx - ctx_mu) / ctx_sigma)
    save_json(out / "scalers.json", scalers)
    save_npz(out / "thermo.npz", **thermo)
    print(f"  {tr.sum()} train / {is_val.sum()} validation pairs, {gas.n_species} species")


if __name__ == "__main__":
    main(load_config(base_parser(__doc__).parse_args().config))

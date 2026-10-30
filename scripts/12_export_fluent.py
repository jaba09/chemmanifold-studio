"""Stage 12: export a trained surrogate for the Ansys Fluent UDF (fluent/udf).

Writes one self-contained text file with the network weights, the encoding scalers, the
thermodynamic tables of the hard physics layers, and the out-of-distribution (OOD) tables the UDF
uses to flag cells outside the sampled space. Also writes test vectors computed with the PyTorch
model, which the compiled UDF checks itself against (`chemmanifold_selftest`, or fluent/tests).

Reads  04_prep/*, 05_manifold/manifold_report.json, 06_models/<arch>/model.pt.
Writes 08_fluent/<arch>/chemmanifold_model.txt, chemmanifold_tests.txt, export_report.json
"""

import numpy as np

from chemmanifold.chemistry import make_gas
from chemmanifold.fluent import advance, build_ood_tables, ood, write_model_file, write_test_vectors
from chemmanifold.io import base_parser, load_config, load_npz, save_json, stage_dir
from chemmanifold.loading import latent_dim, load_surrogate, model_dir_name


def test_cases(ds, rng, n=60):
    """Validation states at a spread of Fluent time steps (below, inside and above the trained dt
    range, and one that hits the sub-step cap), plus a few perturbed states for the OOD checks."""
    idx = rng.choice(np.flatnonzero(ds["is_val"]), size=n, replace=False)
    Y, T, P = ds["Y_in"][idx].copy(), ds["T_in"][idx].copy(), ds["P_in"][idx].copy()
    dts = np.array([5e-6, 1e-5, 2e-5, 3e-5, 4e-5, 1e-4, 1e-3, 1e-2])
    dt = dts[np.arange(n) % len(dts)] * ds["dt"].min() / 1e-5
    m = n // 6                                   # hotter than any training state at that Z
    T[:m] = T[:m] + 400.0
    Y[m:2 * m, :] = Y[m:2 * m, :] * rng.uniform(0.2, 5.0, size=Y[m:2 * m].shape)  # off-manifold mixes
    Y[m:2 * m] /= Y[m:2 * m].sum(1, keepdims=True)
    P[-3:] = P[-3:] * 1.2                        # pressure off the trained 1 atm
    return dict(Y=Y, T=T, P=P, dt=dt)


def main(cfg, arch, n_landmarks, quantile, tag=None):
    model, scalers, thermo = load_surrogate(cfg, arch, tag)
    ds = load_npz(stage_dir(cfg, "prep") / "dataset.npz")
    gas = make_gas(cfg)
    dt_range = (float(ds["dt"].min()), float(ds["dt"].max()))
    tables = build_ood_tables(gas, cfg, scalers, ds, vq_K=int(cfg["manifold"]["n_clusters"]),
                              vq_d=latent_dim(cfg), n_landmarks=n_landmarks, quantile=quantile,
                              seed=cfg["seed"])
    out = stage_dir(cfg, "fluent", model_dir_name(arch, tag))
    write_model_file(out / "chemmanifold_model.txt", arch, model, scalers, thermo, cfg, dt_range, tables)
    print(f"  wrote {out / 'chemmanifold_model.txt'}")

    # Test vectors from the float64 network (the C code runs in double precision)
    rng = np.random.default_rng(cfg["seed"] + 12)
    cases = test_cases(ds, rng)
    P_ref = float(scalers["ctx_mu"][1])
    o = ood(tables, scalers, thermo["A"], cases["Y"], cases["T"], cases["P"], P_ref)
    y32, T32, *_ = advance(model, cases["Y"], cases["T"], cases["P"], cases["dt"], *dt_range)
    model.net.double()
    Yn, Tn, flags, n_sub, hrr = advance(model, cases["Y"], cases["T"], cases["P"], cases["dt"], *dt_range,
                                        ood_flags=o["flags"])
    write_test_vectors(out / "chemmanifold_tests.txt", cases,
                       dict(Y=Yn, T=Tn, flags=flags, n_sub=n_sub, hrr=hrr, **{k: o[k] for k in
                                                                              ("Z", "manifold_ratio", "data_ratio")}))
    print(f"  wrote {out / 'chemmanifold_tests.txt'} ({len(Tn)} cases)")

    # How many training/validation states the OOD checks flag (should be ~1 - quantile)
    va = ds["is_val"]
    ov = ood(tables, scalers, thermo["A"], ds["Y_in"][va], ds["T_in"][va], ds["P_in"][va], P_ref)
    report = dict(
        arch=arch, dt_range=dt_range, P_ref=P_ref, n_parameters=sum(p.numel() for p in model.net.parameters()),
        ood_quantile=quantile, n_landmarks=int(tables["ood.n_landmarks"]), vq_K=int(tables["ood.vq_K"]),
        vq_d=int(tables["ood.vq_d"]), T_range=list(map(float, tables["ood.T_range"])),
        validation_flagged_fraction={
            "any": float(np.mean(ov["flags"] & 0x3F > 0)),
            "off_manifold": float(np.mean(ov["manifold_ratio"] > 1)),
            "far_from_data": float(np.mean(ov["data_ratio"] > 1)),
        },
        float32_vs_float64_max_dT_K=float(np.max(np.abs(T32 - Tn))),
        stable=arch == "resnet_film",
    )
    save_json(out / "export_report.json", report)
    if arch == "chemnode":
        print("  WARNING: Phy-ChemNODE is not stable on the burner flame yet (RESULTS.md); use it for tests only.")
    print(f"  validation states flagged OOD: {report['validation_flagged_fraction']['any'] * 100:.2f}%  "
          f"(float32 vs float64 max |dT| {report['float32_vs_float64_max_dT_K']:.2e} K)")


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--arch", choices=["resnet_film", "chemnode"], default="resnet_film")
    p.add_argument("--landmarks", type=int, default=1024, help="training-state landmarks for the distance check")
    p.add_argument("--quantile", type=float, default=0.999,
                   help="training quantile of the manifold/data distances used as the OOD threshold")
    p.add_argument("--tag", default=None, help="export 06_models/<arch>_<tag> (07_train.py --tag)")
    a = p.parse_args()
    main(load_config(a.config), a.arch, a.landmarks, a.quantile, a.tag)

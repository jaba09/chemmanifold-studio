"""Error map of one trained surrogate (stage E1 of docs/ENSEMBLE-ROADMAP.md).

Where in the thermochemical space does the single network make its error? The answer decides whether
partitioning the space between several networks (experts) can pay off: if most of the error sits in a
few regions that the input state alone can separate, an expert per region is worth trying; if it is
spread evenly, it is not.

Physics only: the pairs are the model's own validation split (is_val) of the a priori exploration
(04_prep/dataset.npz). No CFD state is used. Optionally the per-state table of the offline benchmark
(stage 18 per_state.csv) is broken down the same way for the closed-loop (50 ms) errors.

Per validation pair: one-step T error [K], scaled increment error of every species
e_k = (yt_hat_k - yt_true_k) / sigma_dy_k (the training loss space, as in stage 08), and the relative
increment error of OH, H and CO in mass fractions. Each pair is placed by input-state variables only:

  * T band, Z band (relative to Z_st), distance to equilibrium T_eq(h, P, Z) - T,
  * VQ-PCA cluster (K-means on Box-Cox yt_in fitted on the training split, as stage 06), K = 4 and 8,
  * regime (how the pair was generated; for information only, a CFD cell has no regime).

For each partition the report gives every bin's share of the pairs and its share of the error "mass"
(sum of squares), plus a concentration test: the smallest set of cells of the T x Z x distance grid
holding 60 % of the error, and their share of the data.

    python scripts/error_map.py --config configs/burner_openfoam_ood8.yaml --arch resnet_film \\
        --benchmark /mnt/project-files/chemmanifold/benchmark/resultados_v3_semillas/per_state.csv \\
        --benchmark-model ood8 --out /mnt/project-files/chemmanifold/ensemble/e1_error_map
"""

import json
from pathlib import Path

import cantera as ct
import numpy as np
import pandas as pd
import torch
from sklearn.cluster import MiniBatchKMeans

from chemmanifold.chemistry import make_gas
from chemmanifold.flame import BilgerZ, stoichiometric_z, stream_states
from chemmanifold.io import base_parser, load_config, load_npz, stage_dir
from chemmanifold.loading import load_surrogate

T_EDGES = [0, 800, 1200, 1600, 1900, 3000]
Z_EDGES_REL = [0, 0.5, 1.5, 4.0, 1e9]                 # multiples of Z_st
Z_NAMES = ["lean <0.5Zst", "near-st 0.5-1.5Zst", "rich 1.5-4Zst", "very rich >4Zst"]
DEQ_EDGES = [-1e9, 20, 200, 1e9]                      # T_eq - T [K]
DEQ_NAMES = ["near eq <20 K", "20-200 K", "far >200 K"]
REGIMES = {0: "0D adiabatic", 1: "PaSR", 2: "flamelet", 3: "0D wall-cooled", 4: "recirculation",
           5: "unsteady flamelet", 6: "equilibrium tail", 7: "vitiated ignition", 8: "burnt relaxation",
           9: "equilibrium fixed point"}
TRACK = ["OH", "H", "CO"]


def band_labels(x, edges, names=None):
    i = np.clip(np.digitize(x, edges[1:-1]), 0, len(edges) - 2)
    if names is None:
        names = [f"{edges[k]:g}-{edges[k + 1]:g}" for k in range(len(edges) - 1)]
        names[0], names[-1] = f"<{edges[1]:g}", f">{edges[-2]:g}"
    return np.array(names, dtype=object)[i]


def predict(model, ds, m, batch=20000):
    outs = dict(Y=[], T=[], yt=[])
    idx = np.flatnonzero(m)
    for a in range(0, len(idx), batch):
        j = idx[a:a + batch]
        t = {k: torch.as_tensor(ds[k][j], dtype=torch.float64) for k in ("Y_in", "T_in", "P_in", "h_in", "dt")}
        with torch.no_grad():
            o = model(t["Y_in"], t["T_in"], t["P_in"], t["h_in"], t["dt"])
            outs["Y"].append(o["Y"].numpy())
            outs["T"].append(o["T"].numpy())
            outs["yt"].append(model.encode_Y(o["Y"]).numpy())
    return {k: np.concatenate(v) for k, v in outs.items()}


def t_equilibrium(gas, Y, h, P):
    Teq = np.empty(len(h))
    for i in range(len(h)):
        gas.HPY = h[i], P[i], Y[i]
        gas.equilibrate("HP")
        Teq[i] = gas.T
    return Teq


def table(df, by, err_cols):
    g = df.groupby(by, sort=True)
    out = pd.DataFrame(dict(pairs=g.size()))
    out["data_share"] = out.pairs / len(df)
    for c in err_cols:
        out[f"{c}_share"] = g[c].sum() / df[c].sum()
    out["mean_absdT"] = g.absdT.mean()
    out["p99_absdT"] = g.absdT.quantile(0.99)
    for s in TRACK:
        out[f"inc{s}_rel"] = g[f"inc{s}_abserr"].sum() / g[f"inc{s}_absref"].sum().clip(lower=1e-30)
    out["leverage"] = out[f"{err_cols[0]}_share"] / out.data_share   # >1: more error than its share of data
    return out


def concentration(df, col, frac=0.6):
    """Smallest set of grid cells (T band x Z band x distance to eq) holding `frac` of the error mass."""
    g = df.groupby(["Tband", "Zband", "deq"]).agg(err=(col, "sum"), n=(col, "size"))
    g = g.sort_values("err", ascending=False)
    g["cum"] = g.err.cumsum() / g.err.sum()
    k = int(np.searchsorted(g.cum.to_numpy(), frac) + 1)
    top = g.iloc[:k]
    return dict(cells_total=len(g), cells_needed=k, data_share=float(top.n.sum() / g.n.sum()),
                cells=[dict(T=a, Z=b, deq=c, err_share=float(r.err / g.err.sum()), data_share=float(r.n / g.n.sum()))
                       for (a, b, c), r in top.iterrows()])


def md_table(t, cols, fmt):
    L = ["| bin | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for name, r in t.iterrows():
        name = " / ".join(map(str, name)) if isinstance(name, tuple) else str(name)
        L.append(f"| {name} | " + " | ".join(fmt.get(c, "{:.3g}").format(r[c]) for c in cols) + " |")
    return L


def main(cfg, args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    model, scalers, thermo = load_surrogate(cfg, args.arch, args.tag)
    ds = load_npz(stage_dir(cfg, "prep") / "dataset.npz")
    species = list(scalers["species"])
    m = ds["is_val"].copy()
    rng = np.random.default_rng(0)
    if args.max_pairs and m.sum() > args.max_pairs:
        keep = rng.choice(np.flatnonzero(m), args.max_pairs, replace=False)
        m[:] = False
        m[keep] = True
    print(f"  {int(m.sum())} validation pairs")
    pr = predict(model, ds, m)

    gas = make_gas(cfg)
    (Yf, _), (Yo, _) = stream_states(gas, cfg)
    Zst = stoichiometric_z(gas, cfg)
    Yin, Tin, Pin, hin = ds["Y_in"][m], ds["T_in"][m], ds["P_in"][m], ds["h_in"][m]
    Z = np.clip(BilgerZ(gas, Yf, Yo)(Yin), 0, 1)
    Teq = t_equilibrium(gas, Yin, hin, Pin)
    print(f"  equilibrium temperatures done, Z_st {Zst:.4f}")

    sdy = np.asarray(scalers["sigma_dy"])
    e = (pr["yt"] - ds["yt_out"][m]) / sdy
    df = pd.DataFrame(dict(T=Tin, Z=Z, Teq=Teq, regime=[REGIMES.get(int(r), str(r)) for r in ds["regime"][m]],
                           log10dt=np.log10(ds["dt"][m])))
    df["dT_err"] = pr["T"] - ds["T_out"][m]
    df["absdT"] = df.dT_err.abs()
    df["sqdT"] = df.dT_err ** 2
    df["sqY"] = (e ** 2).sum(1)
    # Same in physical mass fractions, each species scaled by the spread of its true increments over the
    # pairs: Box-Cox space amplifies trace species in cold gas, this one weighs what moves T and the flame.
    inc_true = ds["Y_out"][m] - Yin
    sphys = np.maximum(inc_true.std(0), 1e-30)
    df["sqYphys"] = (((pr["Y"] - ds["Y_out"][m]) / sphys) ** 2).sum(1)
    for k, s in enumerate(species):
        df[f"sq_{s}"] = e[:, k] ** 2
    for s in TRACK:
        k = species.index(s)
        df[f"inc{s}_abserr"] = np.abs(pr["Y"][:, k] - ds["Y_out"][m][:, k])
        df[f"inc{s}_absref"] = np.abs(ds["Y_out"][m][:, k] - Yin[:, k])
    df["Tband"] = band_labels(Tin, T_EDGES)
    df["Zband"] = band_labels(Z / Zst, Z_EDGES_REL, Z_NAMES)
    df["deq"] = band_labels(Teq - Tin, DEQ_EDGES, DEQ_NAMES)

    train = ds["yt_in"][~ds["is_val"]]
    if len(train) > 40000:
        train = train[rng.choice(len(train), 40000, replace=False)]
    for K in (4, 8):
        km = MiniBatchKMeans(n_clusters=K, random_state=int(cfg.get("seed", 0)), n_init=5).fit(train)
        df[f"vq{K}"] = [f"c{c}" for c in km.predict(ds["yt_in"][m])]

    errs = ["sqdT", "sqY", "sqYphys"]
    parts = {"T band": ["Tband"], "Z band": ["Zband"], "distance to equilibrium": ["deq"],
             "T band x distance to equilibrium": ["Tband", "deq"], "VQ-PCA K=4": ["vq4"], "VQ-PCA K=8": ["vq8"],
             "regime (generation process, information only)": ["regime"]}
    tabs = {name: table(df, by, errs) for name, by in parts.items()}
    conc = {c: concentration(df, c) for c in errs}
    sp_share = pd.Series({s: df[f"sq_{s}"].sum() for s in species}) / df.sqY.sum()

    bench = None
    if args.benchmark:
        b = pd.read_csv(args.benchmark)
        b = b[(b.model == args.benchmark_model) & (b["mode"] == "alone")].copy()
        b["T0band"] = band_labels(b.T0.to_numpy(), T_EDGES)
        bench = dict(family=b.groupby("family").agg(states=("dT_10ms", "size"), dT_10ms=("dT_10ms", "mean"),
                                                   dT_end=("dT_end", "mean"), drift100=("drift100", "mean"),
                                                   radOH_1ms=("radOH_1ms", "median")),
                     T0band=b.groupby("T0band").agg(states=("dT_10ms", "size"), dT_10ms=("dT_10ms", "mean"),
                                                   dT_end=("dT_end", "mean"), drift100=("drift100", "mean"),
                                                   radOH_1ms=("radOH_1ms", "median")))
        for t in bench.values():
            t["dT_end_share"] = t.dT_end * t.states / (t.dT_end * t.states).sum()

    df.drop(columns=[c for c in df.columns if c.startswith("sq_")]).to_csv(out / "pairs.csv.gz", index=False)
    rep = dict(config=cfg["_config_path"], arch=args.arch, tag=args.tag, n_pairs=int(m.sum()), Z_st=Zst,
               totals=dict(mean_absdT=float(df.absdT.mean()), rmse_dT=float(np.sqrt(df.sqdT.mean()))),
               partitions={k: v.reset_index().to_dict(orient="records") for k, v in tabs.items()},
               concentration=conc, species_share=sp_share.to_dict())
    (out / "error_map.json").write_text(json.dumps(rep, indent=1, default=str))

    pct = "{:.0%}"
    L = [f"# Error map: {Path(cfg['_config_path']).stem} / {args.arch}{('_' + args.tag) if args.tag else ''}", "",
         f"{int(m.sum())} validation pairs of the a priori exploration (no CFD data). Z_st = {Zst:.4f}. "
         f"One-step mean |dT| {df.absdT.mean():.2f} K, RMSE {np.sqrt(df.sqdT.mean()):.2f} K.", "",
         "Columns: data = share of the pairs; sqdT = share of the squared one-step T error; sqY = share of the "
         "squared species increment error in the training-loss space (Box-Cox / sigma_dy); sqYphys = the same in mass fractions, each species scaled by the spread of its true increments (weighs what moves the flame, not trace species in cold gas); leverage = sqdT share / "
         "data share (above 1 means the bin has more T error than its share of data); incX = relative one-step "
         "increment error of X (sum |err| / sum |true increment|).", "",
         "## Concentration test", ""]
    for c, r in conc.items():
        L.append(f"- **{c}**: {r['cells_needed']} of {r['cells_total']} cells (T band x Z band x distance to "
                 f"equilibrium) hold 60 % of the error, with {r['data_share']:.0%} of the data: " +
                 "; ".join(f"{x['T']} K, {x['Z']}, {x['deq']} ({x['err_share']:.0%} err, {x['data_share']:.0%} data)"
                           for x in r["cells"][:5]) + ("; ..." if len(r["cells"]) > 5 else ""))
    L.append("")
    cols = ["pairs", "data_share", "sqdT_share", "sqY_share", "sqYphys_share", "leverage", "mean_absdT", "p99_absdT", "incOH_rel",
            "incH_rel", "incCO_rel"]
    fmt = {"pairs": "{:.0f}", "data_share": pct, "sqdT_share": pct, "sqY_share": pct, "sqYphys_share": pct, "leverage": "{:.2f}",
           "mean_absdT": "{:.2f}", "p99_absdT": "{:.1f}", "incOH_rel": pct, "incH_rel": pct, "incCO_rel": pct}
    for name, t in tabs.items():
        L += [f"## {name}", ""] + md_table(t, cols, fmt) + [""]
    L += ["## Share of the species increment error per species", "",
          "| species | share |", "|---|---|"] + [f"| {s} | {v:.1%} |" for s, v in
                                                 sp_share.sort_values(ascending=False).items()] + [""]
    if bench is not None:
        bc = ["states", "dT_10ms", "dT_end", "dT_end_share", "drift100", "radOH_1ms"]
        bf = {"states": "{:.0f}", "dT_10ms": "{:.1f}", "dT_end": "{:.1f}", "dT_end_share": pct, "drift100": pct,
              "radOH_1ms": "{:.2f}"}
        L += [f"## Closed loop (offline benchmark, {args.benchmark_model}, surrogate alone, 50 ms)", "",
              "### Per family", ""] + md_table(bench["family"], bc, bf) + ["", "### Per start temperature", ""] + \
             md_table(bench["T0band"], bc, bf) + [""]
    (out / "error_map.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:20]))


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--arch", default="resnet_film")
    p.add_argument("--tag")
    p.add_argument("--out", required=True)
    p.add_argument("--max-pairs", type=int, default=0, help="subsample the validation pairs (0 = all)")
    p.add_argument("--benchmark", help="stage 18 per_state.csv to break down the same way")
    p.add_argument("--benchmark-model", default="ood8")
    a = p.parse_args()
    main(load_config(a.config), a)

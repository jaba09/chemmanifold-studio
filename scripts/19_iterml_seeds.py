"""Stage 19 (ITERML, docs/ITERML-ROADMAP.md): turn the states a CFD run caught into seeds for the
next physics exploration.

The run (OpenFOAM, userChemStep `isann` dictionary with startActive true, no daemon) keeps per rank,
in processor*/isannPairs.csv, grid-deduplicated states with their GA18 step:
  reason 1  OOD for the model,             2  cell of an untrusted (T, Z) bin,
         3  shadow DI check (any outcome), 4  sentinel induction cell.
This stage
  1. merges the ranks (and several runs), and runs the model's own step (the UDF C core) from every
     state, so each shadow/sentinel state gets its one-step error against GA18;
  2. rolls the sentinel states out 0D for --sentinel-steps steps, network vs Cantera, to catch the
     slow drift a one-step check misses (the early nozzle ignition of 2026-10-31);
  3. keeps as seeds: every OOD and untrusted-bin state, the shadow states that failed the check
     (T, OH, H, O or CO error above max(abs, rel |GA18 increment|)), the sentinels that drifted;
  4. removes near-duplicates by a radius of novelty in the model's OOD coordinates (as ISANN),
     each kept seed carrying the number of caught states it stands for (weight);
  5. describes each seed by its flame features (Z, heat-loss fraction psi, progress c, OH excess over
     HP equilibrium r_OH) and assigns the physics regime it seeds (10 PaSR, 11 relaxation,
     12 ignition, 13 cooling; rules in `assign_regime`).

The seeds are WHERE the next exploration starts. They are never training pairs, and neither is any
GA18 step written by the run: stage 4 (`pasr.seeded`) starts Cantera reactors from them.
The one-step comparison table is saved too (comparison.csv), as the standing DI-check rule asks.

Usage:
  python scripts/19_iterml_seeds.py --config <iteration config> --runs <case dir> [...] \\
      --model <chemmanifold_model.txt used in the run> --scalers <its 04_prep/scalers.json> --out <dir>
Writes <out>/seeds.npz, seeds.csv (no species), comparison.csv, seeds_report.md, seeds_ZT.png.
"""

import ctypes
import importlib.util
import json
import sys
from pathlib import Path

import cantera as ct
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "openfoam" / "isann"))

from chemmanifold.chemistry import make_gas  # noqa: E402
from chemmanifold.flame import BilgerZ, flame_pressure, stoichiometric_z, stream_states  # noqa: E402
from chemmanifold.io import base_parser, load_config  # noqa: E402
from isann_lib import features, landmark_threshold, radius_dedup, read_run_pairs  # noqa: E402


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


stage16 = _load("stage16", "16_coverage_gaps.py")
stage17 = _load("stage17", "17_di_local_stability.py")

REASON = {1: "ood", 2: "bin", 3: "err", 4: "drift"}
CHECK_SPECIES = ("OH", "H", "O", "CO")
DEFAULTS = dict(T_abs=1.0, rel=0.3, Y_abs=5e-5, sentinel_steps=25, drift_T=50.0, drift_OH=2.0,
                dedup_radius=0.05, T_min=600.0)


class Core:
    """The model through the UDF C core (same advance() as Fluent and OpenFOAM)."""

    def __init__(self, model_path, build_dir):
        self.lib = stage17.core_library(build_dir)
        err = ctypes.create_string_buffer(512)
        self.m = self.lib.cm_load(str(model_path).encode(), err, 512)
        if not self.m:
            raise RuntimeError(f"{model_path}: {err.value.decode()}")
        self.names = [self.lib.cm_species_name(self.m, k).decode() for k in range(self.lib.cm_n_species(self.m))]
        self.opt = stage17.CmOptions()
        self.lib.cm_default_options(ctypes.byref(self.opt))
        self.info = stage17.CmInfo()
        self.dp = ctypes.POINTER(ctypes.c_double)

    def step(self, Y, T, P, dt):
        y = np.ascontiguousarray(Y, dtype=float).copy()
        st = self.lib.cm_advance(self.m, ctypes.byref(self.opt), y.ctypes.data_as(self.dp), float(T), float(P),
                                 float(dt), ctypes.byref(self.info))
        return (y, float(self.info.T_out)) if st == 0 else (None, np.nan)


def one_step(core, df, species):
    """Network step from every caught state; errors against the GA18 step the run stored."""
    Y0 = df[[f"Y0_{s}" for s in species]].to_numpy()
    Y1 = df[[f"Y1_{s}" for s in species]].to_numpy()
    idx = [species.index(s) for s in core.names]
    Ya = np.full_like(Y0, np.nan)
    Ta = np.full(len(df), np.nan)
    for i, (y, T, P, dt) in enumerate(zip(Y0, df["T0"], df["p"], df["dt"])):
        out, Tn = core.step(y[idx], T, P, dt)
        if out is not None:
            Ya[i, idx] = out
            Ta[i] = Tn
    return Y0, Y1, Ya, Ta


def failed(df, Y0, Y1, Ya, Ta, species, o):
    dT_di = np.abs(df["T1"].to_numpy() - df["T0"].to_numpy())
    bad = ~np.isfinite(Ta) | (np.abs(Ta - df["T1"].to_numpy()) > np.maximum(o["T_abs"], o["rel"] * dT_di))
    for s in CHECK_SPECIES:
        if s in species:
            k = species.index(s)
            bad |= np.abs(Ya[:, k] - Y1[:, k]) > np.maximum(o["Y_abs"], o["rel"] * np.abs(Y1[:, k] - Y0[:, k]))
    return bad


def sentinel_drift(core, gas, Y0, T0, P0, dt, species, o):
    """0D rollouts network vs Cantera (adiabatic, constant p); drift flag and the largest |dT|."""
    n = int(o["sentinel_steps"])
    idx = [species.index(s) for s in core.names]
    iOH = species.index("OH")
    drift, dTmax = np.zeros(len(T0), bool), np.zeros(len(T0))
    for i in range(len(T0)):
        gas.TPY = T0[i], P0[i], Y0[i]
        r = ct.IdealGasConstPressureReactor(gas, clone=False)
        net = ct.ReactorNet([r])
        y, T = Y0[i][idx].copy(), T0[i]
        for k in range(1, n + 1):
            net.advance(k * dt[i])
            y, T = core.step(y, T, P0[i], dt[i])
            if y is None or not np.isfinite(T):
                drift[i] = True
                break
            d = abs(T - r.T)
            dTmax[i] = max(dTmax[i], d)
            oh_n, oh_c = y[core.names.index("OH")], r.phase.Y[iOH]
            ratio = max(oh_n, 1e-6) / max(oh_c, 1e-6)
            if d > o["drift_T"] or ratio > o["drift_OH"] or ratio < 1 / o["drift_OH"]:
                drift[i] = True
                break
    return drift, dTmax


def flame_features(cfg, gas, Y, T, P):
    (Yf, _), (Yo, _) = stream_states(gas, cfg)
    Z = BilgerZ(gas, Yf, Yo)(Y).clip(0, 1)
    psi, _ = stage16.enthalpy_coordinates(gas, cfg, Y, T, Z)
    c = stage16.progress(gas, cfg, Y, Z)
    iOH = gas.species_index("OH")
    r_oh, h = np.full(len(T), np.nan), np.zeros(len(T))
    for i in range(len(T)):
        gas.TPY = T[i], P[i], Y[i]
        h[i] = gas.enthalpy_mass
        y_oh = gas.Y[iOH]
        try:
            gas.equilibrate("HP")
            r_oh[i] = max(y_oh, 1e-12) / max(gas.Y[iOH], 1e-12)
        except ct.CanteraError:
            pass
    return Z, psi, c, r_oh, h


def assign_regime(T, c, psi, r_oh, flags):
    """10 PaSR (mixing between flame and streams, psi < 0, everything else),
    11 relaxation (burnt, c >= 0.8, T >= 1200 K), 12 ignition (drift flag, or c < 0.3 at
    900-1700 K), 13 cooling (psi > 0.5)."""
    reg = np.full(len(T), 10, int)
    reg[(c >= 0.8) & (T >= 1200)] = 11
    reg[psi > 0.5] = 13
    reg[((c < 0.3) & (T >= 900) & (T < 1700)) | np.array(["drift" in f for f in flags])] = 12
    return reg


def main(cfg, args):
    o = dict(DEFAULTS)
    o.update(cfg.get("iterml", {}).get("seeds", {}))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    gas = make_gas(cfg)
    species = list(gas.species_names)
    frames = []
    for k, run in enumerate(args.runs):
        df = read_run_pairs(run, species)
        if len(df):
            df["run"] = k
            frames.append(df)
            print(f"  {run}: {len(df)} caught states")
    if not frames:
        raise SystemExit("no processor*/isannPairs.csv in the runs")
    df = pd.concat(frames, ignore_index=True).drop_duplicates(["run", "id"]).reset_index(drop=True)
    df = df[(df["T0"] >= o["T_min"]) & df["reason"].isin([1, 2, 3, 4])].reset_index(drop=True)

    core = Core(args.model, out)
    Y0, Y1, Ya, Ta = one_step(core, df, species)
    bad = failed(df, Y0, Y1, Ya, Ta, species, o)
    comp = df[["run", "id", "step", "time", "reason", "T0", "Z", "dt", "T1"]].copy()
    comp["T_ann"] = Ta
    for s in CHECK_SPECIES:
        k = species.index(s)
        comp[f"{s}_0"], comp[f"{s}_DI"], comp[f"{s}_ann"] = Y0[:, k], Y1[:, k], Ya[:, k]
    comp["fail"] = bad
    comp.to_csv(out / "comparison.csv", index=False)

    reason = df["reason"].to_numpy()
    sen = np.flatnonzero(reason == 4)
    drift = np.zeros(len(df), bool)
    if len(sen):
        dr, dTm = sentinel_drift(core, gas, Y0[sen], df["T0"].to_numpy()[sen], df["p"].to_numpy()[sen],
                                 df["dt"].to_numpy()[sen], species, o)
        drift[sen] = dr
        print(f"  sentinels: {len(sen)}, drifted {dr.sum()} (max |dT| median {np.median(dTm):.1f} K)")
    keep = np.isin(reason, [1, 2]) | ((reason == 3) & bad) | ((reason == 4) & drift)
    flags = np.array(["ood" if r == 1 else "bin" if r == 2 else "err" if r == 3 else "drift" for r in reason])
    flags = np.where((reason != 3) & bad & (reason != 4), np.char.add(flags, "+err"), flags)
    print(f"  caught {len(df)}: OOD {np.sum(reason == 1)}, bin {np.sum(reason == 2)}, shadow {np.sum(reason == 3)} "
          f"(failed {np.sum((reason == 3) & bad)}), sentinel {len(sen)} (drifted {drift.sum()}) -> {keep.sum()} seed candidates")

    ids = np.flatnonzero(keep)
    Y, T, dt = Y0[ids] / Y0[ids].sum(1, keepdims=True), df["T0"].to_numpy()[ids], df["dt"].to_numpy()[ids]
    scalers = json.load(open(args.scalers))
    if list(scalers["species"]) != species:
        raise SystemExit("the scalers order the species differently from the mechanism")
    r = float(o["dedup_radius"]) * landmark_threshold(args.model)
    X = features(Y, T, dt, scalers)
    kept = radius_dedup(X, r)
    from sklearn.neighbors import BallTree
    _, nearest = BallTree(X[kept]).query(X, k=1)
    weight = np.bincount(nearest[:, 0], minlength=len(kept))
    ids, Y, T, dt = ids[kept], Y[kept], T[kept], dt[kept]
    P = np.full(len(T), flame_pressure(cfg))
    print(f"  radius dedup (r = {r:.4f}): {len(keep.nonzero()[0])} -> {len(ids)} seeds")

    Z, psi, c, r_oh, h = flame_features(cfg, gas, Y, T, P)
    fl = flags[ids]
    regime = assign_regime(T, c, psi, r_oh, fl)
    np.savez(out / "seeds.npz", Y=Y, T=T, P=P, h=h, dt=dt, Z=Z, psi=psi, c=c, r_OH=r_oh, regime=regime,
             reason=reason[ids], flags=fl.astype("U16"), weight=weight, step=df["step"].to_numpy()[ids],
             species=np.array(species))
    tab = pd.DataFrame(dict(T=T, Z=Z, psi=psi, c=c, r_OH=r_oh, regime=regime, flags=fl, weight=weight,
                            step=df["step"].to_numpy()[ids], time=df["time"].to_numpy()[ids]))
    tab.to_csv(out / "seeds.csv", index=False)
    report(out, tab, df, bad, drift, keep, r, cfg, gas)


def report(out, tab, df, bad, drift, keep, r, cfg, gas):
    Z_st = stoichiometric_z(gas, cfg)
    lines = ["# ITERML seeds", "", f"Caught states: {len(df)}; seed candidates {keep.sum()}; "
             f"after radius dedup (r = {r:.4f}): **{len(tab)} seeds** standing for {tab.weight.sum()} states.", "",
             "| regime | seeds | weight | T median K | Z median | psi median |", "|---|---|---|---|---|---|"]
    names = {10: "10 PaSR", 11: "11 relaxation", 12: "12 ignition", 13: "13 cooling"}
    for g, d in tab.groupby("regime"):
        lines.append(f"| {names.get(g, g)} | {len(d)} | {d.weight.sum()} | {d['T'].median():.0f} | {d.Z.median():.3f} | "
                     f"{d.psi.median():.2f} |")
    lines += ["", "| flag | seeds |", "|---|---|"]
    for f, n in tab.flags.value_counts().items():
        lines.append(f"| {f} | {n} |")
    sh = df["reason"].to_numpy() == 3
    lines += ["", f"Shadow checks: {sh.sum()}, failed {np.sum(sh & bad)} ({100 * np.mean(bad[sh]) if sh.any() else 0:.1f} %). "
              f"Sentinels drifted: {drift.sum()} of {np.sum(df['reason'].to_numpy() == 4)}.",
              f"Lean (Z < Z_st = {Z_st:.3f}) share of seeds: {100 * np.mean(tab.Z < Z_st):.0f} %.", "",
              "Seeds are starting points for Cantera reactors (stage 4 `pasr.seeded`); no state here is a training pair."]
    (out / "seeds_report.md").write_text("\n".join(lines) + "\n")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for g, d in tab.groupby("regime"):
            ax.scatter(d.Z, d["T"], s=6 + 2 * np.sqrt(d.weight), alpha=0.6, label=names.get(g, str(g)))
        ax.set_xscale("log")
        ax.set_xlabel("Z")
        ax.set_ylabel("T [K]")
        ax.axvline(Z_st, color="0.5", lw=0.8)
        ax.legend()
        fig.tight_layout()
        fig.savefig(out / "seeds_ZT.png", dpi=130)
    except Exception as e:  # the plot is a convenience
        print(f"  (no plot: {e})")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = base_parser(__doc__)
    ap.add_argument("--runs", nargs="+", required=True, help="OpenFOAM case directories of the collection run(s)")
    ap.add_argument("--model", required=True, help="chemmanifold_model.txt the run used")
    ap.add_argument("--scalers", required=True, help="04_prep/scalers.json of that model (OOD coordinates)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    main(load_config(a.config), a)

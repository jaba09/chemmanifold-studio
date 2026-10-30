"""Stage 18: offline benchmark of exported surrogates on Cantera states, with seeds and a CFD check.

Physics only: every starting state is built here with Cantera from the two inlet streams and the
mechanism (no CFD state, no OOD point, no training pair). The states are drawn with their own random
seed, so they are not the training seeds. Families:

  * equilibrium   adiabatic and non-adiabatic (heat-loss fraction psi) equilibrium over Z: the fixed
                  point. Cantera stays where it is; a surrogate should too.
  * cooled        adiabatic equilibrium products with enthalpy removed at frozen composition: radicals
                  above equilibrium that must recombine (gas leaving the flame towards the walls).
  * lean_hot      lean burnt gas (Z 0.012-0.04) cooled to 1250-1600 K: the kind of state that fills the
                  burner at start-up and in the far field, where the models over-produce OH and H.
  * vitiated      lean or stoichiometric products mixed with a little fuel or air, through ignition
                  (fresh jet entering hot gas).
  * partial       fresh mixture + burnt fraction alpha at the same Z (reaction progress), as 0D seeds.
  * flamelet      points of steady counterflow diffusion flames (mixture-averaged transport) at three
                  strain rates, T > 600 K.

Each state is advanced as a homogeneous constant-(p, h) reactor for `--steps` steps of `--dt` (default
2500 x 2e-5 s = 50 ms, the OpenFOAM flow step): Cantera is the reference; each model file
(chemmanifold_model.txt from stage 12) goes through the UDF's C core exactly as in Fluent/OpenFOAM
(see stage 17), in two modes:

  * alone   the surrogate on every step (as in Fluent, which has no per-cell fallback);
  * hybrid  steps whose state the model flags as out of its data go to Cantera, as userChemStep
            does in OpenFOAM with GA18. Reported with the share of such steps.

Metrics, per model, mode and family:
  * inc_T/OH/H/CO   one-step relative error of the chemical increment, sum|err| / sum|Cantera increment|
                    (not for the equilibrium family, whose increment is ~0);
  * fp_T, fp_OH, fp_H  equilibrium family only: |T - T_eq| [K] and median |log10(Y/Y_eq)| after the
                    horizon (fixed-point behaviour);
  * rad_OH, rad_H   median |log10(Y_model / Y_Cantera)| at 1 ms and at 10 ms (radical level error;
                    0.3 = factor 2, 1 = factor 10);
  * dT_1ms/10ms/end mean |T_model - T_Cantera| and drift100 = share of states off by > 100 K at any step.

Seeds: models are given as label=path, a label "name/s1" (or a directory .../name/seed1/...) is seed 1
of model "name". The report gives, per model, the mean over seeds and the [min, max] range.

Check against CFD (`--cfd-reference`, a CSV with column `model` and columns such as `flame_dT_25ms`):
Spearman rank correlation of every benchmark metric with each CFD column, over the models present in
both. The CFD numbers are only compared with, never used to build states or to train.

    python scripts/18_offline_benchmark.py --config configs/burner_openfoam_ood1.yaml \\
        --models-dir /mnt/project-files/chemmanifold/benchmark/modelos \\
        --cfd-reference /mnt/project-files/chemmanifold/benchmark/cfd_hibridos.csv --workers 4

Writes <out>/states.npz, reference.npz (cached, reused when the state settings match), per_state.csv,
benchmark.json, benchmark.md, and cfd_check.csv when a CFD reference is given.
"""

import ctypes
import importlib.util
import json
import re
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cantera as ct
import numpy as np
import pandas as pd

from chemmanifold.chemistry import make_gas
from chemmanifold.flame import BilgerZ, flame_pressure, heat_loss, stoichiometric_z, stream_states
from chemmanifold.io import base_parser, load_config, stage_dir

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ["equilibrium", "cooled", "lean_hot", "vitiated", "partial", "flamelet"]
RADICALS = ["OH", "H", "CO"]
Y_FLOOR = 1e-12                       # radical levels below this are not compared in log space

_spec = importlib.util.spec_from_file_location("stage17", ROOT / "scripts" / "17_di_local_stability.py")
stage17 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage17)


# ----------------------------------------------------------------------------------------------- states

def equilibrium(gas, Y, h, P):
    gas.HPY = h, P, Y
    gas.equilibrate("HP")
    return gas.Y.copy(), gas.T


def flamelet_states(gas, cfg, strains_mdot, n_per, rng):
    """Points of steady counterflow flames (T > 600 K) at a few inlet mass fluxes."""
    c, P = cfg["chemistry"], flame_pressure(cfg)
    gas.TPY = c["fuel_T"], P, c["fuel"]
    rho_f = gas.density
    gas.TPY = c["oxidizer_T"], P, c["oxidizer"]
    ratio = np.sqrt(gas.density / rho_f)
    f = ct.CounterflowDiffusionFlame(gas, width=0.02)
    f.transport_model = "mixture-averaged"
    f.P = P
    f.fuel_inlet.Y, f.fuel_inlet.T = c["fuel"], c["fuel_T"]
    f.oxidizer_inlet.Y, f.oxidizer_inlet.T = c["oxidizer"], c["oxidizer_T"]
    f.set_refine_criteria(ratio=3, slope=0.08, curve=0.15, prune=0.02)
    out = []
    for i, mdot in enumerate(strains_mdot):
        f.fuel_inlet.mdot, f.oxidizer_inlet.mdot = mdot, mdot * ratio
        f.solve(loglevel=0, auto=i == 0)
        a = float(f.strain_rate("max"))
        hot = np.flatnonzero(f.T > 600.0)
        pick = rng.choice(hot, size=min(n_per, len(hot)), replace=False)
        print(f"  flamelet mdot {mdot:g}: strain ~{a:.0f} 1/s, T_max {f.T.max():.0f} K, {len(pick)} points")
        for j in pick:
            out.append((f.Y[:, j].copy(), float(f.T[j]), dict(strain=a)))
    return out


def build_states(cfg, n, seed):
    """All benchmark starting states: arrays Y, T, P, family, Z and a tag string per state."""
    gas = make_gas(cfg)
    P = flame_pressure(cfg)
    T_wall = float(cfg["envelope"].get("T_wall", 300.0))
    (Yf, hf), (Yo, ho) = stream_states(gas, cfg)
    Z_st = stoichiometric_z(gas, cfg)
    rng = np.random.default_rng(seed)

    def fresh(Z):
        return Z * Yf + (1 - Z) * Yo, Z * hf + (1 - Z) * ho

    def burnt(Z, psi=0.0):
        Yu, hu = fresh(Z)
        Yb, _ = equilibrium(gas, Yu, hu, P)
        if psi > 0:
            Yb, _ = equilibrium(gas, Yb, hu + heat_loss(gas, Yb, hu, psi, P, T_wall), P)
        gas.HPY = gas.enthalpy_mass, P, Yb
        return Yb, gas.enthalpy_mass

    def z_lean_rich():
        """Z spread over lean, near-stoichiometric and rich (log-uniform 0.4 Z_st - 4 Z_st)."""
        return float(np.exp(rng.uniform(np.log(0.4 * Z_st), np.log(4.0 * Z_st))))

    rows = []

    def add(fam, Y, h, tag):
        gas.HPY = h, P, Y
        rows.append((fam, gas.Y.copy(), gas.T, tag))

    for _ in range(n):                                   # equilibrium (fixed point)
        Z, psi = z_lean_rich(), float(rng.choice([0.0, 0.0, 0.15, 0.3, 0.45]))
        Yb, hb = burnt(Z, psi)
        add("equilibrium", Yb, hb, f"Z={Z:.4f} psi={psi:.2f}")
    for _ in range(n):                                   # cooled products, frozen composition
        Z, psi = z_lean_rich(), float(rng.uniform(0.1, 0.5))
        Yb, hb = burnt(Z)
        add("cooled", Yb, hb + heat_loss(gas, Yb, hb, psi, P, T_wall), f"Z={Z:.4f} psi={psi:.2f}")
    for _ in range(n):                                   # lean hot gas 1250-1600 K
        Z, T_target = float(rng.uniform(0.012, 0.04)), float(rng.uniform(1250.0, 1600.0))
        Yb, hb = burnt(Z)
        gas.TPY = T_target, P, Yb
        if rng.random() < 0.5:                           # half re-equilibrated at the lower enthalpy
            Yb, _ = equilibrium(gas, Yb, gas.enthalpy_mass, P)
            gas.TPY = T_target, P, Yb
            kind = "eq"
        else:
            kind = "frozen"
        add("lean_hot", gas.Y.copy(), gas.enthalpy_mass, f"Z={Z:.4f} T={T_target:.0f} {kind}")
    for _ in range(n):                                   # vitiated: products + a little fuel or air
        Zp, psi = float(rng.uniform(0.015, 1.3 * Z_st)), float(rng.uniform(0.0, 0.4))
        Yb, hb = burnt(Zp, psi)
        stream = "fuel" if rng.random() < 0.6 else "air"
        beta = float(rng.uniform(0.02, 0.12) if stream == "fuel" else rng.uniform(0.1, 0.5))
        Ys, hs = (Yf, hf) if stream == "fuel" else (Yo, ho)
        add("vitiated", (1 - beta) * Yb + beta * Ys, (1 - beta) * hb + beta * hs,
            f"Zp={Zp:.4f} psi={psi:.2f} +{beta:.2f} {stream}")
    for _ in range(n):                                   # partially burnt mixtures
        Z, alpha = z_lean_rich(), float(rng.uniform(0.3, 0.9))
        Yu, hu = fresh(Z)
        Yb, hb = burnt(Z)
        add("partial", (1 - alpha) * Yu + alpha * Yb, (1 - alpha) * hu + alpha * hb, f"Z={Z:.4f} alpha={alpha:.2f}")
    for Y, T, meta in flamelet_states(gas, cfg, [0.05, 0.3, 1.2], max(1, n // 3 + 1), rng):
        gas.TPY = T, P, Y
        rows.append(("flamelet", gas.Y.copy(), T, f"strain={meta['strain']:.0f}"))

    bz = BilgerZ(gas, Yf, Yo)
    Y = np.array([r[1] for r in rows])
    keep = np.array([r[2] > 800.0 for r in rows])        # below ~800 K nothing happens in 50 ms
    return dict(family=np.array([r[0] for r in rows])[keep], Y=Y[keep], T=np.array([r[2] for r in rows])[keep],
                P=np.full(int(keep.sum()), P), Z=np.clip(bz(Y[keep]), 0, 1),
                tag=np.array([r[3] for r in rows])[keep], species=np.array(gas.species_names))


# ------------------------------------------------------------------------------------------- rollouts

def checkpoints(dt, steps):
    """Step indices (from 0) of 1 step, 1 ms, 10 ms and the end."""
    k = lambda t: min(steps, max(1, int(round(t / dt)))) - 1
    return dict(one=0, ms1=k(1e-3), ms10=k(1e-2), end=steps - 1)


def _reference_worker(job):
    cfg_path, Y, T, P, dt, steps = job
    gas = make_gas(load_config(cfg_path))
    cps = sorted(set(checkpoints(dt, steps).values()))
    T_out, Y_out = np.empty((len(T), steps)), np.empty((len(T), len(cps), Y.shape[1]))
    for i in range(len(T)):
        gas.TPY = T[i], P[i], Y[i]
        r = ct.IdealGasConstPressureReactor(gas, clone=False)
        net = ct.ReactorNet([r])
        net.rtol, net.atol = 1e-9, 1e-15
        for k in range(steps):
            net.advance((k + 1) * dt)
            T_out[i, k] = r.T
            if k in cps:
                Y_out[i, cps.index(k)] = r.phase.Y
    return T_out, Y_out


_LIB = {}


def _model_worker(job):
    """Roll one model over a chunk of states, alone and hybrid. Returns T (n, steps) and Y at checkpoints
    for both modes, the OOD flag of the start state and the share of hybrid steps sent to Cantera."""
    cfg_path, model_path, build_dir, Y0, T0, P0, dt, steps, species = job
    if "lib" not in _LIB:
        _LIB["lib"] = stage17.core_library(build_dir)
    lib = _LIB["lib"]
    err = ctypes.create_string_buffer(512)
    model = lib.cm_load(str(model_path).encode(), err, 512)
    if not model:
        raise RuntimeError(f"{model_path}: {err.value.decode()}")
    names = [lib.cm_species_name(model, k).decode() for k in range(lib.cm_n_species(model))]
    idx = [list(species).index(s) for s in names]
    opt = stage17.CmOptions()
    lib.cm_default_options(ctypes.byref(opt))
    gas = make_gas(load_config(cfg_path))
    cps = sorted(set(checkpoints(dt, steps).values()))
    n = len(T0)
    res = {m: (np.full((n, steps), np.nan), np.full((n, len(cps), len(species)), np.nan)) for m in ("alone", "hybrid")}
    ood0, ode_share = np.zeros(n, int), np.zeros(n)
    info = stage17.CmInfo()
    dp = ctypes.POINTER(ctypes.c_double)
    for i in range(n):
        y_full = np.zeros(len(species))
        for mode in ("alone", "hybrid"):
            y = np.ascontiguousarray(Y0[i, idx], dtype=float).copy()
            ptr = y.ctypes.data_as(dp)
            T, n_ode = float(T0[i]), 0
            for k in range(steps):
                lib.cm_ood(model, ctypes.byref(opt), ptr, T, P0[i], ctypes.byref(info))
                flagged = (info.flags & 0x3F) != 0
                if k == 0 and mode == "alone":
                    ood0[i] = int(flagged)
                if mode == "hybrid" and flagged:
                    y_full[:] = 0.0
                    y_full[idx] = y
                    gas.TPY = T, P0[i], y_full
                    r = ct.IdealGasConstPressureReactor(gas, clone=False)
                    ct.ReactorNet([r]).advance(dt)
                    y[:] = r.phase.Y[idx]
                    T = r.T
                    n_ode += 1
                else:
                    if lib.cm_advance(model, ctypes.byref(opt), ptr, T, P0[i], dt, ctypes.byref(info)) != 0:
                        break
                    T = info.T_out
                if not np.isfinite(T):
                    break
                res[mode][0][i, k] = T
                if k in cps:
                    res[mode][1][i, cps.index(k), idx] = y
            if mode == "hybrid":
                ode_share[i] = n_ode / steps
    lib.cm_free(ctypes.c_void_p(model)) if hasattr(lib, "cm_free") else None
    return res, ood0, ode_share


def chunks(n, k):
    return [a for a in np.array_split(np.arange(n), k) if len(a)]


# -------------------------------------------------------------------------------------------- metrics

def model_specs(args):
    """[(label, model, seed, path)] from --models label=path and --models-dir."""
    specs = []
    for s in args.models or []:
        label, path = s.split("=", 1)
        name, _, seed = label.partition("/")
        specs.append((label, name, int(re.sub(r"\D", "", seed) or 0), Path(path)))
    if args.models_dir:
        for f in sorted(Path(args.models_dir).glob("*/chemmanifold_model.txt")) + \
                 sorted(Path(args.models_dir).glob("*/seed*/chemmanifold_model.txt")):
            rel = f.parent.relative_to(args.models_dir).parts
            name, seed = rel[0], int(re.sub(r"\D", "", rel[1]) or 0) if len(rel) > 1 else 0
            specs.append((f"{name}/s{seed}", name, seed, f))
    if args.only:
        specs = [s for s in specs if s[1] in args.only]
    return specs


def log_err(Ym, Yr):
    ok = (Yr > Y_FLOOR) & np.isfinite(Ym)
    return np.where(ok, np.abs(np.log10(np.maximum(Ym, Y_FLOOR) / np.where(ok, Yr, 1.0))), np.nan)


def per_state_table(st, ref, out, label, name, seed, mode, cps_list, cp):
    sp = list(st["species"])
    T_m, Y_m = out
    T_r, Y_r = ref
    c = {k: cps_list.index(v) for k, v in cp.items()}
    d = T_m - T_r
    df = pd.DataFrame(dict(label=label, model=name, seed=seed, mode=mode, family=st["family"], Z=st["Z"],
                           T0=st["T"], tag=st["tag"]))
    df["failed"] = ~np.isfinite(T_m[:, -1])
    df["dT_1"], df["dT_1ms"], df["dT_10ms"], df["dT_end"] = (np.abs(d[:, cp[k]]) for k in ("one", "ms1", "ms10", "end"))
    df["drift100"] = np.nanmax(np.abs(np.where(np.isfinite(d), d, 1e4)), axis=1) > 100.0
    df["incT_ref"], df["incT_err"] = T_r[:, 0] - st["T"], d[:, 0]
    for s in RADICALS:
        k = sp.index(s)
        df[f"inc{s}_ref"] = Y_r[:, c["one"], k] - st["Y"][:, k]
        df[f"inc{s}_err"] = Y_m[:, c["one"], k] - Y_r[:, c["one"], k]
        df[f"rad{s}_1ms"] = log_err(Y_m[:, c["ms1"], k], Y_r[:, c["ms1"], k])
        df[f"rad{s}_10ms"] = log_err(Y_m[:, c["ms10"], k], Y_r[:, c["ms10"], k])
        df[f"fp{s}"] = log_err(Y_m[:, c["end"], k], st["Y"][:, k])      # vs the start (= equilibrium) state
    df["fpT"] = np.abs(T_m[:, -1] - st["T"])
    return df


def rel(err, inc):
    return float(np.nansum(np.abs(err)) / max(np.nansum(np.abs(inc)), 1e-30))


def summarize(g):
    """Metrics of one (label, mode, family-set) group of states."""
    reac = g[g.family != "equilibrium"]
    eq = g[g.family == "equilibrium"]
    m = dict(states=len(g), failed=int(g.failed.sum()),
             dT_1ms=float(g.dT_1ms.mean()), dT_10ms=float(g.dT_10ms.mean()), dT_end=float(g.dT_end.mean()),
             drift100=float(g.drift100.mean()), inc_T=rel(reac.incT_err, reac.incT_ref) if len(reac) else np.nan)
    for s in RADICALS:
        m[f"inc_{s}"] = rel(reac[f"inc{s}_err"], reac[f"inc{s}_ref"]) if len(reac) else np.nan
    for s in ("OH", "H"):
        m[f"rad_{s}_1ms"] = float(np.nanmedian(g[f"rad{s}_1ms"])) if g[f"rad{s}_1ms"].notna().any() else np.nan
        m[f"rad_{s}_10ms"] = float(np.nanmedian(g[f"rad{s}_10ms"])) if g[f"rad{s}_10ms"].notna().any() else np.nan
    if len(eq):
        m["fp_T"] = float(eq.fpT.mean())
        m["fp_OH"] = float(np.nanmedian(eq.fpOH))
        m["fp_H"] = float(np.nanmedian(eq.fpH))
    if "ode_share" in g:
        m["ode_share"] = float(g.ode_share.mean())
        m["ood_start"] = float(g.ood_start.mean())
    return m


HEADLINE = ["dT_10ms", "dT_end", "drift100", "inc_T", "inc_OH", "inc_H", "rad_OH_1ms", "rad_H_1ms", "fp_T", "fp_OH",
            "fp_H"]
# The composite score is fixed here, before looking at any CFD result: the mean rank over these
# metrics (lower is better), each covering one of the four aspects asked for (one-step increment,
# radicals, equilibrium fixed point, temperature drift).
SCORE_METRICS = ["inc_T", "inc_OH", "rad_OH_1ms", "rad_H_1ms", "fp_T", "fp_OH", "dT_10ms", "dT_end"]


def spearman(a, b):
    a, b = pd.Series(a).rank(), pd.Series(b).rank()
    return float(np.corrcoef(a, b)[0, 1]) if len(a) > 2 and a.std() > 0 and b.std() > 0 else np.nan


def main(cfg, args):
    out_dir = Path(args.out) if args.out else stage_dir(cfg, "eval", f"benchmark_{args.label}")
    out_dir.mkdir(parents=True, exist_ok=True)
    build_dir = out_dir / "build"
    build_dir.mkdir(exist_ok=True)
    stage17.core_library(build_dir)
    settings = dict(n=args.n_states, seed=args.state_seed, dt=args.dt, steps=args.steps,
                    mechanism=cfg["chemistry"]["mechanism"], fuel=cfg["chemistry"]["fuel"],
                    oxidizer=cfg["chemistry"]["oxidizer"])
    st_path, ref_path = out_dir / "states.npz", out_dir / "reference.npz"
    cached = st_path.exists() and ref_path.exists() and \
        json.loads(str(np.load(st_path, allow_pickle=False)["settings"])) == settings
    cp = checkpoints(args.dt, args.steps)
    cps_list = sorted(set(cp.values()))
    t0 = time.time()
    if cached:
        st = dict(np.load(st_path, allow_pickle=False))
        rf = dict(np.load(ref_path, allow_pickle=False))
        ref = (rf["T"], rf["Y"])
        print(f"  reusing {len(st['T'])} states and their Cantera reference from {out_dir}")
    else:
        st = build_states(cfg, args.n_states, args.state_seed)
        print(f"  {len(st['T'])} states: " + ", ".join(f"{f} {int((st['family'] == f).sum())}" for f in FAMILIES)
              + f" ({time.time() - t0:.0f} s)")
        jobs = [(cfg["_config_path"], st["Y"][c], st["T"][c], st["P"][c], args.dt, args.steps)
                for c in chunks(len(st["T"]), args.workers * 4)]
        with ProcessPoolExecutor(args.workers) as ex:
            parts = list(ex.map(_reference_worker, jobs))
        ref = (np.vstack([p[0] for p in parts]), np.vstack([p[1] for p in parts]))
        np.savez_compressed(st_path, settings=json.dumps(settings), **st)
        np.savez_compressed(ref_path, T=ref[0], Y=ref[1])
        print(f"  Cantera reference done ({time.time() - t0:.0f} s)")

    specs = model_specs(args)
    if not specs:
        raise SystemExit("no models given (--models or --models-dir)")
    tables = []
    for label, name, seed, path in specs:
        t1 = time.time()
        idx = chunks(len(st["T"]), args.workers * 2)
        jobs = [(cfg["_config_path"], path, build_dir, st["Y"][c], st["T"][c], st["P"][c], args.dt, args.steps,
                 st["species"]) for c in idx]
        with ProcessPoolExecutor(args.workers) as ex:
            parts = list(ex.map(_model_worker, jobs))
        ood0 = np.concatenate([p[1] for p in parts])
        share = np.concatenate([p[2] for p in parts])
        for mode in ("alone", "hybrid"):
            out = (np.vstack([p[0][mode][0] for p in parts]), np.vstack([p[0][mode][1] for p in parts]))
            df = per_state_table(st, ref, out, label, name, seed, mode, cps_list, cp)
            df["ood_start"], df["ode_share"] = ood0, share if mode == "hybrid" else 0.0
            tables.append(df)
        print(f"  {label}: {time.time() - t1:.0f} s, OOD at start {ood0.mean():.0%}, hybrid steps to Cantera "
              f"{share.mean():.1%}")
    df = pd.concat(tables, ignore_index=True)
    df.to_csv(out_dir / "per_state.csv", index=False)

    # per label (seed), mode and family; then mean and range over seeds per model
    per_seed = {}
    for (label, mode), g in df.groupby(["label", "mode"], sort=False):
        per_seed.setdefault(label, {})[mode] = dict(all=summarize(g),
                                                    **{f: summarize(gf) for f, gf in g.groupby("family", sort=False)})
    seeds_of = {}
    for label, name, seed, _ in specs:
        seeds_of.setdefault(name, []).append(label)
    agg = {}
    for name, labels in seeds_of.items():
        agg[name] = {}
        for mode in ("alone", "hybrid"):
            agg[name][mode] = {}
            for fam in ["all"] + FAMILIES:
                vals = [per_seed[lb][mode].get(fam) for lb in labels if fam in per_seed[lb][mode]]
                if not vals:
                    continue
                keys = vals[0].keys()
                agg[name][mode][fam] = {k: dict(mean=float(np.nanmean([v.get(k, np.nan) for v in vals])),
                                                min=float(np.nanmin([v.get(k, np.nan) for v in vals])),
                                                max=float(np.nanmax([v.get(k, np.nan) for v in vals])),
                                                n=len(vals)) for k in keys}
    # composite score: mean rank over SCORE_METRICS (all states), per mode
    for mode in ("alone", "hybrid"):
        tab = pd.DataFrame({n: {k: agg[n][mode]["all"].get(k, {}).get("mean", np.nan) for k in SCORE_METRICS}
                            for n in agg}).T
        score = tab.rank().mean(axis=1)
        for n in agg:
            agg[n][mode]["all"]["score"] = dict(mean=float(score[n]), min=float(score[n]), max=float(score[n]),
                                                n=agg[n][mode]["all"]["states"]["n"])

    report = dict(settings=settings, families={f: int((st["family"] == f).sum()) for f in FAMILIES},
                  score_metrics=SCORE_METRICS, per_seed=per_seed, models=agg)

    cfd = None
    if args.cfd_reference:
        cfd = pd.read_csv(args.cfd_reference).set_index("model")
        common = [n for n in agg if n in cfd.index]
        rows = []
        for mode in ("alone", "hybrid"):
            for fam in ["all"] + FAMILIES:
                for k in HEADLINE + ["score", "ode_share", "failed"]:
                    x = [agg[n][mode].get(fam, {}).get(k, {}).get("mean", np.nan) for n in common]
                    if not np.isfinite(x).any():
                        continue
                    row = dict(mode=mode, family=fam, metric=k, n_models=len(common))
                    for col in cfd.columns:
                        if pd.api.types.is_numeric_dtype(cfd[col]):
                            y = cfd.loc[common, col].to_numpy(float)
                            ok = np.isfinite(x) & np.isfinite(y)
                            row[f"rho_{col}"] = spearman(np.asarray(x)[ok], y[ok])
                    rows.append(row)
        cfd_df = pd.DataFrame(rows)
        cfd_df.to_csv(out_dir / "cfd_check.csv", index=False)
        report["cfd_check"] = dict(models=common, columns=[c for c in cfd.columns], rows=rows)

    (out_dir / "benchmark.json").write_text(json.dumps(report, indent=1, default=float))
    write_markdown(out_dir / "benchmark.md", report, agg, cfd, args)
    print((out_dir / "benchmark.md").read_text())


def fmt(v, k):
    m, lo, hi, n = v["mean"], v["min"], v["max"], v["n"]
    pct = k in ("drift100", "inc_T", "inc_OH", "inc_H", "inc_CO", "ode_share", "ood_start")
    f = (lambda x: f"{x:.0%}") if pct else (lambda x: f"{x:.2f}" if abs(x) < 10 else f"{x:.0f}")
    if not np.isfinite(m):
        return "-"
    return f(m) if n < 2 or lo == hi else f"{f(m)} [{f(lo)}, {f(hi)}]"


def write_markdown(path, report, agg, cfd, args):
    s = report["settings"]
    L = [f"# Offline benchmark on Cantera states", "",
         f"{sum(report['families'].values())} states ({', '.join(f'{k} {v}' for k, v in report['families'].items())}), "
         f"homogeneous constant-(p, h) reactors, {s['steps']} steps of {s['dt']:g} s "
         f"({s['steps'] * s['dt'] * 1e3:g} ms), state seed {s['seed']}. Physics only: no CFD state is used.", "",
         "Columns: dT = mean |T_model - T_Cantera| [K] at 10 ms and at the end; drift = share off by > 100 K; "
         "inc = one-step relative error of the chemical increment (sum|err| / sum|true|, non-equilibrium states); "
         "rad = median |log10(Y_model/Y_Cantera)| at 1 ms (0.3 = x2, 1 = x10); fp = equilibrium states after the "
         "horizon: |T - T_eq| [K] and median |log10(Y/Y_eq)|. Seeds: mean [min, max]. "
         f"Score = mean rank over {', '.join(report['score_metrics'])} (lower is better).", ""]
    cols = ["score"] + HEADLINE + ["failed"]
    for mode in ("alone", "hybrid"):
        L += [f"## {'Surrogate alone (as in Fluent)' if mode == 'alone' else 'Hybrid (flagged steps to Cantera, as OpenFOAM userChemStep)'}", ""]
        extra = ["ode_share"] if mode == "hybrid" else ["ood_start"]
        L += ["| model | seeds | " + " | ".join(cols + extra) + " |", "|---" * (len(cols) + len(extra) + 2) + "|"]
        order = sorted(agg, key=lambda n: agg[n][mode]["all"]["score"]["mean"])
        for n in order:
            a = agg[n][mode]["all"]
            L.append(f"| {n} | {a['states']['n']} | " + " | ".join(fmt(a[k], k) if k in a else "-" for k in cols + extra)
                     + " |")
        L.append("")
    L += ["## Per family (surrogate alone, mean over seeds)", "",
          "| model | family | dT 10 ms | dT end | drift | inc T | inc OH | rad OH 1 ms | rad H 1 ms |",
          "|---|---|---|---|---|---|---|---|---|"]
    for n in agg:
        for fam in FAMILIES:
            a = agg[n]["alone"].get(fam)
            if a:
                L.append(f"| {n} | {fam} | " + " | ".join(fmt(a[k], k) for k in
                                                         ("dT_10ms", "dT_end", "drift100", "inc_T", "inc_OH",
                                                          "rad_OH_1ms", "rad_H_1ms")) + " |")
    L.append("")
    if cfd is not None:
        rows = pd.DataFrame(report["cfd_check"]["rows"])
        rcols = [c for c in rows.columns if c.startswith("rho_")]
        L += ["## Check against the OpenFOAM hybrids", "",
              f"Spearman rank correlation (n = {len(report['cfd_check']['models'])} models: "
              f"{', '.join(report['cfd_check']['models'])}) between the benchmark metric and the CFD column. "
              "+1 = same order. With 9 models |rho| > 0.68 is significant at 5 %.", "",
              "| mode | family | metric | " + " | ".join(c[4:] for c in rcols) + " |", "|---" * (3 + len(rcols)) + "|"]
        show = rows[(rows.family == "all") | (rows.metric == "score")]
        for _, r in show.iterrows():
            L.append(f"| {r['mode']} | {r['family']} | {r['metric']} | " +
                     " | ".join("-" if not np.isfinite(r[c]) else f"{r[c]:+.2f}" for c in rcols) + " |")
        L.append("")
    Path(path).write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--models", nargs="*", help="label=path/to/chemmanifold_model.txt; label name/s1 = seed 1 of name")
    p.add_argument("--models-dir", help="directory of <name>/chemmanifold_model.txt or <name>/seed<k>/...")
    p.add_argument("--only", nargs="*", help="restrict to these model names")
    p.add_argument("--cfd-reference", help="CSV: model, and numeric CFD columns to rank against (evaluation only)")
    p.add_argument("--label", default="default")
    p.add_argument("--out", help="output directory (default <data_dir>/07_eval/benchmark_<label>)")
    p.add_argument("--n-states", type=int, default=40, help="states per family (flamelet: about n/3 per flame)")
    p.add_argument("--state-seed", type=int, default=12345)
    p.add_argument("--dt", type=float, default=2e-5)
    p.add_argument("--steps", type=int, default=2500)
    p.add_argument("--workers", type=int, default=2)
    a = p.parse_args()
    main(load_config(a.config), a)

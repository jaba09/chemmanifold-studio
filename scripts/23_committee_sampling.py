"""Stage 23 (M3, 2026-11-10): committee-driven adaptive sampling, physics only.

Where are the data still missing? Instead of a CFD run, the trained models themselves answer it:

1. Candidate starts are a random subsample of the a-priori training inputs of the config
   (03_samples/pairs_*.npz, ITERML seeded and ISANN pairs excluded): Cantera states only.
2. Every member (two or more seeds of one exploration, exported chemmanifold_model.txt files, run
   through the UDF's C core as in the CFD) rolls each start out for `--steps` steps of `--dt` at
   constant (p, h); Cantera rolls the same start out as reference.
3. At the checkpoints the committee's mean state is a candidate. Its score is the larger of
   (a) the members' spread (std T / dT_ref, std log10 Y / ln-ratio threshold for OH, H, CO), and
   (b) the drift of the committee mean from Cantera (|dT| / dT_ref, |log10 ratio| / threshold).
   These are the off-data states a coupled CFD run drifts into, found without running the CFD.
4. The `--top-frac` highest-scoring candidates with score > 1 become starts of Cantera adiabatic
   trajectories (t_max, n_pick states log-uniform in time, the candidate itself included); the
   states are paired with Cantera steps at the dt strides of the config (regime 21).

The candidate states are produced by the surrogates from Cantera starts; no CFD state is used.
Writes 03_samples/pairs_committee_r<round>.npz (+ .json summary), which stage 5 loads.

    python scripts/23_committee_sampling.py --config configs/burner_holes1.yaml --round 1 \\
        --models data/holes1/06_models/resnet_film/chemmanifold_model.txt \\
                 data/holes1/06_models/resnet_film_s1/chemmanifold_model.txt \\
                 data/holes1/06_models/resnet_film_s2/chemmanifold_model.txt --workers 16
"""

import ctypes
import importlib.util
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cantera as ct
import numpy as np

from chemmanifold.chemistry import advance_const_p, const_p_reactor, make_gas
from chemmanifold.flame import flame_pressure
from chemmanifold.io import base_parser, choose_strides, dt_strides, load_config, load_npz, save_json, save_npz, stage_dir

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("stage17", ROOT / "scripts" / "17_di_local_stability.py")
stage17 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage17)

PAIR_KEYS = ("Y_in", "T_in", "P_in", "h_in", "dt", "Y_out", "T_out", "regime", "traj_id")
WATCH = ("OH", "H", "CO")
EXCLUDED_REGIMES = {10, 11, 12, 13, 20, 21}       # seeded (CFD-seeded), ISANN online, earlier committee
Y_FLOOR = 1e-10
_LIB = {}


def candidate_starts(cfg, n, rng, T_min):
    samples = stage_dir(cfg, "samples")
    Ys, Ts, hs = [], [], []
    for f in sorted(samples.glob("pairs_*.npz")):
        if f.name.startswith(("pairs_seeded", "pairs_committee")):
            continue
        d = load_npz(f)
        keep = ~np.isin(d["regime"].astype(int), list(EXCLUDED_REGIMES)) & (d["T_in"] > T_min)
        Ys.append(d["Y_in"][keep])
        Ts.append(d["T_in"][keep])
        hs.append(d["h_in"][keep])
    Y, T, h = np.concatenate(Ys), np.concatenate(Ts), np.concatenate(hs)
    idx = rng.choice(len(T), size=min(n, len(T)), replace=False)
    return Y[idx], T[idx], h[idx]


def _worker(job):
    cfg_path, paths, build_dir, Y0, T0, h0, dt, steps, cps, th = job
    if "lib" not in _LIB:
        _LIB["lib"] = stage17.core_library(build_dir)
    lib = _LIB["lib"]
    err = ctypes.create_string_buffer(512)
    models = []
    for mp in paths:
        m = lib.cm_load(str(mp).encode(), err, 512)
        if not m:
            raise RuntimeError(f"{mp}: {err.value.decode()}")
        models.append(m)
    cfg = load_config(cfg_path)
    gas = make_gas(cfg)
    P = flame_pressure(cfg)
    names = [lib.cm_species_name(models[0], k).decode() for k in range(lib.cm_n_species(models[0]))]
    idx = [gas.species_index(s) for s in names]
    w = [names.index(s) for s in WATCH if s in names]
    opt = stage17.CmOptions()
    lib.cm_default_options(ctypes.byref(opt))
    info = stage17.CmInfo()
    dp = ctypes.POINTER(ctypes.c_double)
    out = []                                            # (score, spread, drift, Y_full, h, T, step)
    for i in range(len(T0)):
        # Cantera reference
        gas.HPY = h0[i], P, Y0[i]
        _, net = const_p_reactor(gas)
        ref = {}
        for k in range(1, steps + 1):
            net.advance(k * dt)
            if k in cps:
                ref[k] = (gas.Y.copy(), gas.T)
        # members, each on its own path; committee mean at the checkpoints
        ys = [np.ascontiguousarray(Y0[i, idx], dtype=float).copy() for _ in models]
        Ts = [float(T0[i])] * len(models)
        alive = [True] * len(models)
        for k in range(1, steps + 1):
            for j, m in enumerate(models):
                if not alive[j]:
                    continue
                if lib.cm_advance(m, ctypes.byref(opt), ys[j].ctypes.data_as(dp), Ts[j], P, dt, ctypes.byref(info)) != 0 \
                        or not np.isfinite(info.T_out):
                    alive[j] = False
                    continue
                Ts[j] = info.T_out
            if k not in cps:
                continue
            live = [j for j in range(len(models)) if alive[j]]
            if len(live) < 2:
                break
            Ym = np.clip(np.mean([ys[j] for j in live], axis=0), 0.0, None)
            Tm = np.array([Ts[j] for j in live])
            lY = np.log10(np.maximum(np.array([ys[j][w] for j in live]), Y_FLOOR))
            spread = max(np.std(Tm) / th["dT"], float(np.max(np.std(lY, axis=0))) / th["dlog"])
            Yr, Tr = ref[k]
            yfull = np.zeros(gas.n_species)
            yfull[idx] = Ym
            yfull /= yfull.sum()
            drift = max(abs(float(Tm.mean()) - Tr) / th["dT"],
                        float(np.max(np.abs(np.log10(np.maximum(yfull[[idx[q] for q in w]], Y_FLOOR)
                                                     / np.maximum(Yr[[idx[q] for q in w]], Y_FLOOR))))) / th["dlog"])
            try:
                gas.HPY = h0[i], P, yfull
            except ct.CanteraError:
                continue
            out.append((max(spread, drift), spread, drift, yfull, float(h0[i]), gas.T, k))
    for m in models:
        lib.cm_free(m)
    return out


def trajectory_pairs(cfg, cands, rng, t_max, n_pick, T_min):
    gas = make_gas(cfg)
    P, base = flame_pressure(cfg), cfg["autoignition"]["dt_base"]
    strides = dt_strides(cfg, "pasr")
    k_dt = min(int(cfg.get("dt_range", {}).get("per_state", 1)), len(strides))
    out = {k: [] for k in PAIR_KEYS}
    for e, (Y, h) in enumerate(cands):
        try:
            gas.HPY = h, P, Y
            _, net = const_p_reactor(gas)
            times = np.concatenate([[0.0], np.sort(10 ** rng.uniform(np.log10(base), np.log10(t_max), n_pick - 1))])
            states = [gas.Y.copy()]
            for t in times[1:]:
                net.advance(t)
                states.append(gas.Y.copy())
        except Exception:
            continue
        for Ys in states:
            for st in choose_strides(cfg, rng, strides, size=k_dt, replace=False):
                gas.HPY = h, P, Ys
                T_in = gas.T
                if T_in < T_min:
                    continue
                advance_const_p(gas, float(st) * base)
                for k, v in (("Y_in", Ys), ("T_in", T_in), ("P_in", P), ("h_in", h), ("dt", float(st) * base),
                             ("Y_out", gas.Y.copy()), ("T_out", gas.T), ("regime", 21), ("traj_id", e)):
                    out[k].append(v)
    return {k: np.asarray(v) for k, v in out.items()}


def main(cfg, a):
    rng = np.random.default_rng(cfg["seed"] + 2300 + a.round)
    Y0, T0, h0 = candidate_starts(cfg, a.n_candidates, rng, a.T_min)
    build = stage_dir(cfg, "eval") / "committee_build"
    build.mkdir(parents=True, exist_ok=True)
    stage17.core_library(build)
    cps = sorted({int(round(c * a.steps)) for c in (0.01, 0.05, 0.2, 0.5, 1.0)} - {0})
    th = dict(dT=a.dT, dlog=np.log10(a.ratio))
    chunks = np.array_split(np.arange(len(T0)), a.workers * 4)
    jobs = [(cfg["_config_path"], a.models, build, Y0[c], T0[c], h0[c], a.dt, a.steps, cps, th) for c in chunks if len(c)]
    with ProcessPoolExecutor(a.workers) as ex:
        res = [r for part in ex.map(_worker, jobs) for r in part]
    score = np.array([r[0] for r in res])
    n_hit = int((score > 1).sum())
    order = np.argsort(-score)
    n_take = min(n_hit, int(np.ceil(a.top_frac * len(res))), a.max_starts)
    take = order[:n_take]
    print(f"  {len(T0)} starts, {len(res)} candidates, {n_hit} with score > 1 "
          f"(spread or drift beyond {a.dT:g} K / x{a.ratio:g}); taking {n_take}")
    arrays = trajectory_pairs(cfg, [(res[i][3], res[i][4]) for i in take], rng, a.t_max, a.n_pick, a.T_min)
    name = f"pairs_committee_r{a.round}.npz"
    save_npz(stage_dir(cfg, "samples") / name, **arrays)
    Tc = np.array([res[i][5] for i in take]) if n_take else np.zeros(0)
    summary = dict(round=a.round, models=[str(m) for m in a.models], n_starts=int(len(T0)), n_candidates=len(res),
                   n_score_gt_1=n_hit, n_taken=int(n_take), n_pairs=int(len(arrays.get("dt", []))),
                   score_quantiles={q: float(np.quantile(score, q)) for q in (0.5, 0.9, 0.99)} if len(score) else {},
                   share_spread_dominant=float(np.mean([res[i][1] >= res[i][2] for i in take])) if n_take else 0.0,
                   taken_T_quantiles=[float(x) for x in np.quantile(Tc, [0.05, 0.5, 0.95])] if n_take else [],
                   settings=dict(dt=a.dt, steps=a.steps, dT=a.dT, ratio=a.ratio, top_frac=a.top_frac, t_max=a.t_max))
    save_json(stage_dir(cfg, "samples") / name.replace(".npz", ".json"), summary)
    print(f"  {summary['n_pairs']} committee pairs (regime 21) -> 03_samples/{name}")


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--models", nargs="+", required=True, help="two or more chemmanifold_model.txt (seeds)")
    p.add_argument("--round", type=int, default=1)
    p.add_argument("--n-candidates", type=int, default=3000, help="Cantera starts drawn from the a-priori pairs")
    p.add_argument("--T-min", type=float, default=450.0)
    p.add_argument("--dt", type=float, default=2e-5)
    p.add_argument("--steps", type=int, default=100)
    p.add_argument("--dT", type=float, default=10.0, help="T spread/drift threshold [K]")
    p.add_argument("--ratio", type=float, default=1.4, help="OH/H/CO ratio threshold (spread or drift)")
    p.add_argument("--top-frac", type=float, default=0.15)
    p.add_argument("--max-starts", type=int, default=1500)
    p.add_argument("--t-max", type=float, default=5e-3, help="Cantera trajectory length from each taken state [s]")
    p.add_argument("--n-pick", type=int, default=12)
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args()
    if len(a.models) < 2:
        p.error("a committee needs at least two models")
    main(load_config(a.config), a)

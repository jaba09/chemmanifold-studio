"""Stage 25: relabel an exploration with the ARC_GRI30_NOx22 kernel (between stages 4 and 5).

The states of stages 0-4 of a `chemistry.state_species` exploration (e.g. configs/ch4_arc22.yaml, run on
the 43-species skeletal GRI) are kept as inputs, projected onto the 22 ARC species (mass renormalised);
each pair's output is then what the ARC kernel gives over the pair's dt (chemmanifold/arc.py: the same C
kernel and element projection as OpenFOAM's arcChemStep), with T_out at the input's enthalpy in the
22-species thermo. Rollout segments (03_samples/segments.npz) are relabelled the same way from their first
state. The new pairs are already on the state species, so stage 5 takes them as they are.

Why: labels of skel43 + projection (stage 5) carry the enthalpy of the dropped QSS radicals into CO2/H2O
at every step (T_out 0.02-2.6 K hotter at p99), and the parent of configs/ch4_arc22.yaml ignited 18-28 %
early in closed loop. ARC labels are also exactly the chemistry the ISANN run's DI phase produces.

    python scripts/25_arc_relabel.py --config configs/ch4_arc22b.yaml --source /opt/ofb/isann/parent_arc22 \
        --workers 8                       # writes <data_dir>/03_samples, resumable per file
    python scripts/25_arc_relabel.py ... --test 1000      # labels 1000 random pairs, compares with the source

Reads  <source>/03_samples/pairs_*.npz, segments.npz (and links <source>/00_flame..02_autoignition).
Writes <data_dir>/03_samples/pairs_*.npz, segments.npz, relabel_report.json
"""

import json
import os
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from chemmanifold.chemistry import state_map
from chemmanifold.io import base_parser, load_config, stage_dir

_SM = None


def _init(cfg_path):
    global _SM
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    _SM = state_map(load_config(cfg_path))
    from chemmanifold import arc
    arc.lib()


def _label_chunk(args):
    """Pairs (Y_in[22], T_in, P_in, dt) -> (Y_out, T_out_ode, ok)."""
    from chemmanifold import arc
    Y, T, P, dt = args
    Yo, To, ok = np.empty_like(Y), np.empty(len(T)), np.ones(len(T), bool)
    for i in range(len(T)):
        try:
            y, t = arc.advance(Y[i], T[i], P[i], [dt[i]])
            Yo[i], To[i] = y[0], t[0]
        except Exception:       # noqa: BLE001 - a failed integration drops the pair
            ok[i] = False
    return Yo, To, ok


def _segment_chunk(args):
    from chemmanifold import arc
    Y0, T0, P, dt, K = args
    Ys, Ts, ok = np.empty((len(T0), K, Y0.shape[1])), np.empty((len(T0), K)), np.ones(len(T0), bool)
    for i in range(len(T0)):
        try:
            Ys[i], Ts[i] = arc.advance(Y0[i], T0[i], P[i], [k * dt[i] for k in range(1, K + 1)])
        except Exception:       # noqa: BLE001
            ok[i] = False
    return Ys, Ts, ok


def _chunks(n, size):
    return [slice(a, min(a + size, n)) for a in range(0, n, size)]


def relabel_pairs(sm, d, pool, chunk=200):
    Y_in = sm.project(d["Y_in"])
    T_in, P_in = np.asarray(d["T_in"], float), np.asarray(d["P_in"], float)
    h_in = sm.enthalpy(Y_in, T_in, P_in)
    sl = _chunks(len(T_in), chunk)
    res = pool.map(_label_chunk, [(Y_in[s], T_in[s], P_in[s], d["dt"][s]) for s in sl])
    Y_out = np.concatenate([r[0] for r in res])
    ok = np.concatenate([r[2] for r in res])
    out = {k: np.asarray(v)[ok] for k, v in d.items()}
    out.update(Y_in=Y_in[ok], h_in=h_in[ok], Y_out=Y_out[ok],
               T_out=sm.temperature(Y_out[ok], h_in[ok], P_in[ok]))
    return out, int((~ok).sum()), ok


def relabel_segments(sm, s, pool, chunk=100, steps=None):
    n, K1 = s["T"].shape
    if steps:       # longer segments from the same starts (the rollout loss then sees slow drifts)
        K1 = int(steps) + 1
    Y0 = sm.project(s["Y"][:, 0])
    T0, P = s["T"][:, 0], np.asarray(s["P"], float)
    h = sm.enthalpy(Y0, T0, P)
    sl = _chunks(n, chunk)
    res = pool.map(_segment_chunk, [(Y0[q], T0[q], P[q], s["dt"][q], K1 - 1) for q in sl])
    Ys = np.concatenate([r[0] for r in res])
    ok = np.concatenate([r[2] for r in res])
    Y = np.concatenate([Y0[:, None], Ys], 1)[ok]
    hk = np.repeat(h[ok], K1 - 1)
    Tk = sm.temperature(Ys[ok].reshape(-1, Y0.shape[1]), hk, np.repeat(P[ok], K1 - 1)).reshape(-1, K1 - 1)
    return dict(Y=Y, T=np.concatenate([T0[ok, None], Tk], 1), P=P[ok], h=h[ok], dt=s["dt"][ok]), int((~ok).sum())


def test(cfg, src, n, workers):
    """n random source pairs labelled by ARC, against their skel43 (+ projection) labels."""
    sm = state_map(cfg)
    files = sorted((src / "03_samples").glob("pairs_*.npz"))
    parts = [dict(np.load(f)) for f in files]
    d = {k: np.concatenate([p[k] for p in parts]) for k in ("Y_in", "T_in", "P_in", "h_in", "dt", "Y_out", "T_out", "regime")}
    rng = np.random.default_rng(0)
    idx = np.sort(rng.choice(len(d["dt"]), size=min(n, len(d["dt"])), replace=False))
    d = {k: v[idx] for k, v in d.items()}
    sk = sm.project_pairs(dict(d), report=False)          # the labels the first parent was trained on
    t0 = time.time()
    with Pool(workers, initializer=_init, initargs=(cfg["_config_path"],)) as pool:
        ar, n_fail, ok = relabel_pairs(sm, dict(d), pool, chunk=max(1, n // (4 * workers)))
    wall = time.time() - t0
    sk = {k: v[ok] for k, v in sk.items()}      # failed ARC integrations are dropped from both
    dT = ar["T_out"] - sk["T_out"]
    rise = sk["T_out"] - sk["T_in"]
    k_oh = sm.names.index("OH")
    rep = dict(n=len(idx), failed=n_fail, wall_s=wall, ms_per_pair_per_worker=1e3 * wall * workers / len(idx),
               dT_arc_minus_skel={q: float(np.quantile(dT, q)) for q in (0.01, 0.05, 0.5, 0.95, 0.99)},
               mean_dT=float(dT.mean()), mean_abs_dT=float(np.abs(dT).mean()), max_abs_dT=float(np.abs(dT).max()),
               by_regime={int(r): dict(n=int((sk["regime"] == r).sum()), mean_dT=float(dT[sk["regime"] == r].mean()),
                                       mean_abs_dT=float(np.abs(dT[sk["regime"] == r]).mean()))
                          for r in np.unique(sk["regime"])},
               reacting=dict(n=int((rise > 1).sum()), mean_dT=float(dT[rise > 1].mean()) if (rise > 1).any() else None,
                             mean_rel=float((dT[rise > 1] / rise[rise > 1]).mean()) if (rise > 1).any() else None),
               OH_rel_diff_median=float(np.median(np.abs(ar["Y_out"][:, k_oh] - sk["Y_out"][:, k_oh])
                                                  / np.maximum(sk["Y_out"][:, k_oh], 1e-12))))
    print(json.dumps(rep, indent=1))
    return rep


def main(cfg, src, workers, seg_steps=None):
    sm = state_map(cfg)
    if sm is None or sm.names != __import__("chemmanifold.arc", fromlist=["NAMES"]).NAMES:
        raise SystemExit("the config needs chemistry.state_species = the 22 ARC species in ARC order")
    root = Path(cfg["_config_path"]).parent / cfg["data_dir"]
    root.mkdir(parents=True, exist_ok=True)
    for sub in ("00_flame", "01_envelope", "02_autoignition"):      # the exploration itself is unchanged
        if (src / sub).exists() and not (root / sub).exists():
            (root / sub).symlink_to(src / sub)
    out = stage_dir(cfg, "samples")
    report = {}
    with Pool(workers, initializer=_init, initargs=(cfg["_config_path"],)) as pool:
        for f in sorted((src / "03_samples").glob("*.npz")):
            dst = out / f.name
            if dst.exists():
                print(f"  {f.name}: done before")
                continue
            t0 = time.time()
            d = dict(np.load(f))
            if f.name == "segments.npz":
                new, n_fail = relabel_segments(sm, d, pool, chunk=max(10, 2000 // (seg_steps or 8)), steps=seg_steps)
                n = len(new["dt"])
            elif "Y_in" in d:
                new, n_fail, _ = relabel_pairs(sm, d, pool)
                n = len(new["dt"])
            else:
                continue
            np.savez_compressed(out.parent / (f.stem + ".tmp.npz"), **new)
            os.replace(out.parent / (f.stem + ".tmp.npz"), dst)    # atomic: a killed run redoes only this file
            report[f.name] = dict(n=n, failed=n_fail, wall_s=round(time.time() - t0, 1))
            print(f"  {f.name}: {n} relabelled with ARC, {n_fail} failed, {time.time() - t0:.0f} s", flush=True)
    for extra in (src / "03_samples").glob("*.json"):
        if not (out / extra.name).exists():
            (out / extra.name).write_bytes(extra.read_bytes())
    prev = out / "relabel_report.json"
    if prev.exists():
        report = {**json.loads(prev.read_text()), **report}
    prev.write_text(json.dumps(dict(report, source=str(src)), indent=1))


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--source", required=True, help="data dir of the skel43 exploration (its 03_samples)")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--test", type=int, default=0, help="only compare N random pairs with the source labels")
    p.add_argument("--seg-steps", type=int, default=None, help="steps per rollout segment (default: the source's)")
    a = p.parse_args()
    cfg = load_config(a.config)
    if a.test:
        test(cfg, Path(a.source), a.test, a.workers)
    else:
        main(cfg, Path(a.source), a.workers, a.seg_steps)

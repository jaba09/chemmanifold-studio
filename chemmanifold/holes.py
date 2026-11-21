"""A-priori exploration sets aimed at the coverage holes of 2026-11-10 (stage 4, `pasr.holes`).

The holes were measured on the Fluent GA18 DI solution of the burner (diagnosis only): most of the
hot gas mass is warm lean burnt gas (Z 0.005-0.035, T 600-950 K) that the earlier explorations
sample 20-100 times more thinly than the flame zone, and where every surrogate gets CO and OH wrong.
The sets below are built from the mechanism, the two inlet streams, the training flamelets and
boundary physics only. No CFD state is used as data or as a start.

Regimes:
  15  dilution-cooling parcels (M1): burnt products of a flamelet at Z_p entrain air (or fuel)
      with a log-uniform mixing time tau_mix while they react and lose heat to T_wall with
      tau_q = q_ratio * tau_mix (q_ratio log-uniform, default 1-100).
      Z(t) = Z_p exp(-t / tau_mix): the slow CO burn-out and freeze-out of a diluting plume;
  16  dynamic multi-stream PaSR (M2): particles flow in from fuel, air and a burnt-product library
      (any Z), stay a mean residence time tau_res, mix by modified Curl (random pairs, so particles
      of different Z mix with each other) and react, optionally losing heat. States are recorded
      after a burn-in, so they carry a real mixing-and-reacting history;
  17  jet induction mixing layer (M5): an unsteady flamelet whose oxidizer side is hot lean
      products (800-1700 K) and whose fuel side is the cold CH4 jet (or rich products against cold
      air), started from the frozen linear mix and followed from first contact through ignition;
  18  hot-wall heating (M6): air or lean products heated toward a wall at T_hot (a wall that faces
      the flame) with a log-uniform tau_q while they react. The only physical source of more
      enthalpy than adiabatic mixing here, and only at Z < 0.03;
  19  near-equilibrium relaxation at the flame's own time steps (M4): stage 4's relaxation set
      (scripts/04_pasr_ensemble.relaxation_pairs) restricted to lean warm gas, paired only at the
      strides inside `dt_window`. Configured as `pasr.relaxation_flamedt`.

Every set pairs the picked states with adiabatic constant-(p, h) Cantera steps at the dt strides
of the config (the target is the true chemistry step; heat loss and mixing only move the starts).
"""

from multiprocessing import Pool

import numpy as np

from .chemistry import advance_const_p, make_gas
from .flame import FlameSeeds, flame_pressure, heat_loss, stoichiometric_z, wall_temperature
from .io import choose_strides, dt_strides, save_npz, stage_dir
from .unsteady_flamelet import ZFlamelet, chi_profile, run_transient

PAIR_KEYS = ("Y_in", "T_in", "P_in", "h_in", "dt", "Y_out", "T_out", "regime", "traj_id")

DEFAULTS = {
    "dilution": dict(n=800, Z_p=[0.03, 0.12], psi_p=[0.0, 0.3], tau_mix=[1e-3, 0.1], q_ratio=[1.0, 100.0],
                     f_no_loss=0.2, f_into_fuel=0.15, Z_end=0.003, Z_end_rich=0.5, T_end=450.0,
                     n_sub=40, dt_sub=[1e-5, 2e-3], n_pick=40, max_steps=3000),
    "dynamic_pasr": dict(n=40, particles=150, tau_res=[2e-3, 0.05], mix_ratio=[0.1, 1.0], Z_mean=[0.01, 0.2],
                         share_products=[0.1, 0.5], psi_products=[0.0, 0.5], f_loss=0.5, tau_q=[5e-3, 0.5],
                         burn_in=2.0, t_record=2.0, max_steps=400, record_every=4, pick=8, T_min=450.0),
    "induction_layer": dict(n=30, n_z=41, Z_p_lean=[0.005, 0.04], Z_p_rich=[0.08, 0.3], f_rich=0.25,
                            psi_p=[0.0, 0.6], T_ox=[800.0, 1700.0], strain=[1.0, 100.0], t_end_chi=3.0,
                            t_max=0.05, n_snapshots=30, points_per_snapshot=15, T_min=450.0,
                            dt_bounds=[1e-5, 5e-4], max_steps=1500),
    "hot_wall": dict(n=300, Z=[1e-4, 0.03], f_air=0.3, psi_p=[0.0, 0.6], T_hot=[600.0, 1000.0],
                     tau_q=[5e-3, 1.0], t_max_tau=3.0, n_steps=200, n_pick=30, T_min=450.0),
}

_G = {}


def _settings(cfg, name):
    s = dict(DEFAULTS[name])
    s.update(cfg["pasr"]["holes"].get(name) or {})
    return s


def _init(cfg):
    gas = make_gas(cfg)
    seeds = FlameSeeds(gas, cfg)
    _G.update(cfg=cfg, gas=gas, seeds=seeds, P=flame_pressure(cfg), T_wall=wall_temperature(cfg),
              dt_base=cfg["autoignition"]["dt_base"], strides=dt_strides(cfg, "pasr"),
              k_dt=min(int(cfg.get("dt_range", {}).get("per_state", 1)), len(dt_strides(cfg, "pasr"))),
              Z_st=stoichiometric_z(gas, cfg))


def _logu(rng, lo_hi):
    lo, hi = np.log10(lo_hi)
    return float(10 ** rng.uniform(lo, hi))


def _h_at(Y, T):
    g = _G["gas"]
    g.TPY = T, _G["P"], Y
    return g.enthalpy_mass


def _products(rng, Z, psi):
    """Burnt state of a random training flamelet at Z, minus a heat-loss fraction psi."""
    s = _G["seeds"]
    Y, h = s.burnt(Z, int(rng.choice(s.train_ids)))
    return Y, h + heat_loss(_G["gas"], Y, h, psi, _G["P"], _G["T_wall"])


def _pair(out, Y, h, regime, traj, rng, T_min=0.0):
    """Pair one state with adiabatic Cantera steps at k_dt strides of the dt range."""
    g, P, base = _G["gas"], _G["P"], _G["dt_base"]
    for st in choose_strides(_G["cfg"], rng, _G["strides"], size=_G["k_dt"], replace=False):
        try:
            g.HPY = h, P, Y
            T_in = g.T
            if T_in < T_min or not 280.0 < T_in < 3800.0:
                return
            Y_in = g.Y.copy()
            advance_const_p(g, float(st) * base)
        except Exception:
            return
        for k, v in (("Y_in", Y_in), ("T_in", T_in), ("P_in", P), ("h_in", h), ("dt", float(st) * base),
                     ("Y_out", g.Y.copy()), ("T_out", g.T), ("regime", regime), ("traj_id", traj)):
            out[k].append(v)


def _empty():
    return {k: [] for k in PAIR_KEYS}


# ---------------------------------------------------------------- regime 15: dilution-cooling parcels
def _dilution_job(job):
    i, rs = job
    rng = np.random.default_rng(rs)
    s, g, P = _settings(_G["cfg"], "dilution"), _G["gas"], _G["P"]
    seeds = _G["seeds"]
    into_fuel = rng.uniform() < s["f_into_fuel"]
    if into_fuel:                                      # rich products entraining the cold fuel jet
        Z_p = _logu(rng, [max(_G["Z_st"], s["Z_p"][0]), 0.3])
        Y_s, h_s, Z_s, Z_stop = seeds.Yf, seeds.hf, 1.0, s["Z_end_rich"]
    else:                                              # products entraining air: the plume
        Z_p = _logu(rng, s["Z_p"])
        Y_s, h_s, Z_s, Z_stop = seeds.Yo, seeds.ho, 0.0, s["Z_end"]
    psi = rng.uniform(*s["psi_p"])
    tau_mix = _logu(rng, s["tau_mix"])
    # heat-loss time as a multiple of the mixing time: a diluting plume loses part of its enthalpy
    # (Fluent DI lean gas: psi median 0.12-0.14), not all of it before it has mixed
    tau_q = np.inf if rng.uniform() < s["f_no_loss"] else tau_mix * _logu(rng, s["q_ratio"])
    Y, h = _products(rng, Z_p, psi)
    dt = float(np.clip(min(tau_mix, tau_q) / s["n_sub"], *s["dt_sub"]))
    a_mix, a_q = 1.0 - np.exp(-dt / tau_mix), (0.0 if np.isinf(tau_q) else 1.0 - np.exp(-dt / tau_q))
    rec, Z = [], Z_p
    try:
        g.HPY = h, P, Y
        for _ in range(int(s["max_steps"])):
            if g.T > 450.0:
                advance_const_p(g, dt)
            Y, h = g.Y.copy(), g.enthalpy_mass
            Y, h = Y + (Y_s - Y) * a_mix, h + (h_s - h) * a_mix
            Z = Z + (Z_s - Z) * a_mix
            if a_q:
                h = h - (h - _h_at(Y, _G["T_wall"])) * a_q
            g.HPY = h, P, Y / Y.sum()
            rec.append((g.Y.copy(), h, g.T, Z))
            if (Z < Z_stop if not into_fuel else Z > Z_stop) or g.T < s["T_end"]:
                break
    except Exception:
        pass
    out = _empty()
    if rec:
        idx = np.unique(rng.choice(len(rec), size=min(s["n_pick"], len(rec)), replace=False))
        for k in idx:
            _pair(out, rec[k][0], rec[k][1], 15, i, rng, s["T_end"])
    T_last = rec[-1][2] if rec else 0.0
    return out, dict(id=i, Z_p=Z_p, psi=psi, tau_mix=tau_mix, tau_q=float(tau_q), into_fuel=bool(into_fuel),
                     steps=len(rec), Z_end=float(Z), T_end=float(T_last))


# ---------------------------------------------------------------- regime 16: dynamic multi-stream PaSR
def _dynamic_pasr_job(job):
    i, rs = job
    rng = np.random.default_rng(rs)
    s, g, P, seeds = _settings(_G["cfg"], "dynamic_pasr"), _G["gas"], _G["P"], _G["seeds"]
    N = int(s["particles"])
    tau_res = _logu(rng, s["tau_res"])
    tau_mix = tau_res * _logu(rng, s["mix_ratio"])
    tau_q = _logu(rng, s["tau_q"]) if rng.uniform() < s["f_loss"] else np.inf
    Z_mean = _logu(rng, s["Z_mean"])
    f_prod = rng.uniform(*s["share_products"])
    # fresh fuel/air split so that the fresh inflow alone has mean Z_mean
    p_fuel = (1 - f_prod) * Z_mean

    def inflow():
        u = rng.uniform()
        if u < p_fuel:
            return seeds.Yf.copy(), seeds.hf
        if u < 1 - f_prod:
            return seeds.Yo.copy(), seeds.ho
        return _products(rng, _logu(rng, [0.005, 0.5]), rng.uniform(*s["psi_products"]))

    # lit start: the burnt state at Z_mean for every particle, so the reactor does not blow out at t = 0
    Y0, h0 = _products(rng, Z_mean, 0.0)
    Y = np.tile(Y0, (N, 1))
    h = np.full(N, h0)
    t_end = (s["burn_in"] + s["t_record"]) * tau_res
    dt = max(min(tau_mix / 4.0, tau_res / 20.0), t_end / s["max_steps"])
    n_steps = int(np.ceil(t_end / dt))
    n_burn = int(np.ceil(s["burn_in"] * tau_res / dt))
    out = _empty()
    T_rec = []
    for step in range(1, n_steps + 1):
        # flow: each particle leaves with probability dt / tau_res and is replaced by an inflow particle
        for k in np.flatnonzero(rng.uniform(size=N) < dt / tau_res):
            Y[k], h[k] = inflow()
        # modified Curl mixing: N dt / tau_mix random pairs move a random fraction towards their mean
        n_pairs = rng.poisson(N * dt / tau_mix / 2.0)
        for _ in range(n_pairs):
            a, b = rng.choice(N, size=2, replace=False)
            w = rng.uniform()
            Ym, hm = 0.5 * (Y[a] + Y[b]), 0.5 * (h[a] + h[b])
            Y[a], Y[b] = Y[a] + w * (Ym - Y[a]), Y[b] + w * (Ym - Y[b])
            h[a], h[b] = h[a] + w * (hm - h[a]), h[b] + w * (hm - h[b])
        for k in range(N):
            try:
                g.HPY = h[k], P, Y[k] / Y[k].sum()
                if g.T > s["T_min"]:
                    advance_const_p(g, dt)
                    Y[k] = g.Y
                if not np.isinf(tau_q):
                    h[k] -= (h[k] - _h_at(Y[k], _G["T_wall"])) * (1.0 - np.exp(-dt / tau_q))
            except Exception:
                Y[k], h[k] = inflow()
        if step > n_burn and step % s["record_every"] == 0:
            for k in rng.choice(N, size=min(s["pick"], N), replace=False):
                _pair(out, Y[k] / Y[k].sum(), float(h[k]), 16, i, rng, s["T_min"])
            T_rec.append(float(np.max([_T(Y[k], h[k]) for k in range(0, N, 10)])))
    return out, dict(id=i, tau_res=tau_res, tau_mix=tau_mix, tau_q=float(tau_q), Z_mean=Z_mean, f_prod=f_prod,
                     steps=n_steps, T_max_late=max(T_rec) if T_rec else 0.0)


def _T(Y, h):
    g = _G["gas"]
    g.HPY = h, _G["P"], Y / Y.sum()
    return g.T


# ---------------------------------------------------------------- regime 17: jet induction mixing layer
def _induction_job(job):
    i, rs = job
    rng = np.random.default_rng(rs)
    s, g, P, seeds = _settings(_G["cfg"], "induction_layer"), _G["gas"], _G["P"], _G["seeds"]
    rich = rng.uniform() < s["f_rich"]
    for _ in range(20):                                # hot side within T_ox
        Z_p = _logu(rng, s["Z_p_rich"] if rich else s["Z_p_lean"])
        Yh, hh = _products(rng, Z_p, rng.uniform(*s["psi_p"]))
        if s["T_ox"][0] <= _T(Yh, hh) <= s["T_ox"][1]:
            break
    else:
        return _empty(), dict(id=i, skipped=True)
    Yc, hc = (seeds.Yo, seeds.ho) if rich else (seeds.Yf, seeds.hf)
    xi = np.linspace(0.0, 1.0, int(s["n_z"]))
    # flamelet coordinate xi: 0 = hot side, 1 = cold stream; frozen linear mix at t = 0
    Y0 = (1 - xi)[:, None] * Yh + xi[:, None] * Yc
    h0 = (1 - xi) * hh + xi * hc
    a = _logu(rng, s["strain"])
    fl = ZFlamelet(g, xi, Y0, h0, P, _G["T_wall"])
    chi_mid = float(chi_profile(np.array([0.5]), a)[0])
    t_end = min(s["t_max"], s["t_end_chi"] / max(chi_mid, 1e-9))
    try:
        snaps, Tmax = run_transient(g, fl, "induction", a, t_end, 0.0, tuple(s["dt_bounds"]), s["n_snapshots"],
                                    s["max_steps"])
    except Exception:
        return _empty(), dict(id=i, failed=True)
    out = _empty()
    for _, Ys, hs in snaps:
        cand = [k for k in range(1, len(xi) - 1) if _T(Ys[k], hs[k]) > s["T_min"]]
        for k in rng.permutation(cand)[: s["points_per_snapshot"]]:
            _pair(out, Ys[k] / Ys[k].sum(), float(hs[k]), 17, i, rng, s["T_min"])
    return out, dict(id=i, rich=bool(rich), Z_p=Z_p, T_hot=_T(Yh, hh), strain=a, t_end=t_end,
                     T_max=[float(Tmax[0]), float(Tmax[-1])] if Tmax else [])


# ---------------------------------------------------------------- regime 18: heating toward a hot wall
def _hot_wall_job(job):
    i, rs = job
    rng = np.random.default_rng(rs)
    s, g, P, seeds = _settings(_G["cfg"], "hot_wall"), _G["gas"], _G["P"], _G["seeds"]
    if rng.uniform() < s["f_air"]:
        Y, h, Z = seeds.Yo.copy(), seeds.ho, 0.0
    else:                                              # lean burnt gas diluted with air to Z
        Z = _logu(rng, s["Z"])
        Z_p = _logu(rng, [max(Z, 0.02), 0.08])
        Yp, hp = _products(rng, Z_p, rng.uniform(*s["psi_p"]))
        b = Z / Z_p
        Y, h = b * Yp + (1 - b) * seeds.Yo, b * hp + (1 - b) * seeds.ho
    T_hot, tau_q = rng.uniform(*s["T_hot"]), _logu(rng, s["tau_q"])
    t_max = s["t_max_tau"] * tau_q
    dt = t_max / s["n_steps"]
    a_q = 1.0 - np.exp(-dt / tau_q)
    rec = []
    try:
        g.HPY = h, P, Y
        for _ in range(int(s["n_steps"])):
            if g.T > s["T_min"]:
                advance_const_p(g, dt)
            Y, h = g.Y.copy(), g.enthalpy_mass
            h = h - (h - _h_at(Y, T_hot)) * a_q            # towards the hot wall: h rises
            g.HPY = h, P, Y
            rec.append((g.Y.copy(), h))
    except Exception:
        pass
    out = _empty()
    if rec:
        for k in np.unique(rng.choice(len(rec), size=min(s["n_pick"], len(rec)), replace=False)):
            _pair(out, rec[k][0], rec[k][1], 18, i, rng, s["T_min"])
    return out, dict(id=i, Z=Z, T_hot=T_hot, tau_q=tau_q)


JOBS = {"dilution": (_dilution_job, "pairs_dilution.npz", 15),
        "dynamic_pasr": (_dynamic_pasr_job, "pairs_dynpasr.npz", 16),
        "induction_layer": (_induction_job, "pairs_induction.npz", 17),
        "hot_wall": (_hot_wall_job, "pairs_hotwall.npz", 18)}


def hole_sets(cfg, rng, only=None):
    """Write the enabled `pasr.holes` sets (or only those named) to 03_samples; returns their names."""
    from .io import save_json
    h = cfg["pasr"]["holes"]
    workers = int(h.get("workers", 4))
    done = []
    for name, (fn, fname, regime) in JOBS.items():
        if (only and name not in only) or (not only and not h.get(name)):
            continue
        s = _settings(cfg, name)
        jobs = [(i, int(rng.integers(2**31))) for i in range(int(s["n"]))]
        with Pool(workers, initializer=_init, initargs=(cfg,)) as pool:
            res = pool.map(fn, jobs, chunksize=max(1, len(jobs) // (8 * workers)))
        arrays = {k: np.asarray([v for r, _ in res for v in r[k]]) for k in PAIR_KEYS}
        log = [m for _, m in res]
        samples = stage_dir(cfg, "samples")
        save_npz(samples / fname, **arrays)
        save_json(samples / fname.replace(".npz", ".json"), log)
        n = len(arrays["dt"])
        T = arrays["T_in"] if n else np.zeros(1)
        print(f"  holes/{name} (regime {regime}): {n} pairs from {len(jobs)} runs, T_in {T.min():.0f}-{T.max():.0f} K")
        done.append(name)
    return done

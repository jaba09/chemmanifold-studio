"""ITERML seeded physics exploration (stage 4, `pasr.seeded`, regimes 10-13).

A seed is a gas state that a CFD run with the surrogate flagged: out of the training data (OOD),
in a (T, Z) bin where the shadow DI check failed, a failed shadow check itself, or an induction
cell whose 0D rollout drifted (scripts/19_iterml_seeds.py writes them, with their flame features
and a regime, to seeds.npz). The seed only sets WHERE the exploration starts: every training pair
written here comes from Cantera (the mechanism of the config) integrating a physics reactor started
from the seed or from a jittered copy of it. The seed state itself, and the first step out of it,
are never paired, so no CFD state enters the training set (docs/ITERML-ROADMAP.md, rule of
2026-10-27 kept: CFD states are seeds, not data).

Regimes:
  10  seeded PaSR: an IEM micromixing ensemble of a cluster of seeds (jittered) plus a share of
      the two inlet streams, reacting while it mixes for a log-uniform mixing time;
  11  seeded relaxation: the seed (radicals x 10^u, element-conserving) relaxing adiabatically;
  12  seeded ignition: the seed with a share of the opposite inlet stream mixed in (vitiated
      mixture), followed through ignition;
  13  seeded cooling: the seed reacting while it loses heat to T_wall with a log-uniform tau_q.

Jitter of each start j >= 1 (j = 0 is the seed itself, whose t = 0 state is not paired):
radicals x 10^u (u uniform in +-radical_decades, elements kept), enthalpy moved by dpsi (uniform
in +-dpsi) of the gap to the same composition at T_wall, and with probability p_mix a log-uniform
share of an inlet stream mixed in.
"""

from multiprocessing import Pool

import numpy as np

from .chemistry import advance_const_p, const_p_reactor, element_mass_matrix, make_gas
from .flame import flame_pressure, stoichiometric_z, stream_states, wall_temperature

PAIR_KEYS = ("Y_in", "T_in", "P_in", "h_in", "dt", "Y_out", "T_out", "regime", "traj_id")
RADICALS = ("H", "O", "OH", "HO2", "H2O2", "CH3", "HCO", "CH2", "CH2(S)", "CH3O", "CH2O")
MAJORS = ("N2", "O2", "H2O", "CO2", "CO", "H2", "CH4")
DEFAULTS = dict(
    starts_per_seed=3,           # jittered starts per seed (the first is the seed itself)
    radical_decades=0.5, dpsi=0.05, p_mix=0.5, mix_share=[1e-3, 0.1],
    n_pick=25,                   # states picked per trajectory (log-uniform in time)
    t_max={"10": 0.01, "11": 0.02, "12": 0.02, "13": 0.2},
    ignition_share=[0.01, 0.5],  # regime 12: log-uniform share of the opposite stream
    tau_q_range=[1e-3, 1.0],     # regime 13
    pasr=dict(cluster=12, particles=48, stream_share=0.15, tau_mix=[1e-4, 1e-2], steps=60),
    max_share=0.35,              # seeded pairs at most this share of all training pairs
    workers=4,
    T_min=450.0,                 # starts colder than this are skipped (frozen chemistry)
)

_G = {}


def settings(cfg):
    s = dict(DEFAULTS)
    s.update(cfg["pasr"]["seeded"])
    for k in ("t_max", "pasr"):
        d = dict(DEFAULTS[k])
        d.update(cfg["pasr"]["seeded"].get(k, {}))
        s[k] = d
    return s


def _init(cfg):
    gas = make_gas(cfg)
    (Yf, hf), (Yo, ho) = stream_states(gas, cfg)
    _G.update(cfg=cfg, gas=gas, P=flame_pressure(cfg), T_wall=wall_temperature(cfg), s=settings(cfg),
              streams={"fuel": (Yf, hf), "air": (Yo, ho)}, A=element_mass_matrix(gas),
              rad=[gas.species_index(r) for r in RADICALS if r in gas.species_names],
              maj=[gas.species_index(r) for r in MAJORS if r in gas.species_names],
              dt_base=cfg["autoignition"]["dt_base"], strides=_strides(cfg), Z_st=stoichiometric_z(gas, cfg))


def _strides(cfg):
    from .io import dt_strides
    return dt_strides(cfg, "pasr")


def perturb_radicals(Y, factor):
    """Radicals x factor, with the majors absorbing each element's change (least relative change),
    so elements and, at fixed h, enthalpy are kept; None if a major would go negative."""
    A, rad, maj = _G["A"], _G["rad"], _G["maj"]
    Y0, Y = Y.copy(), Y.copy()
    Y[rad] *= factor
    dE = A @ (Y - Y0)
    Am, w = A[:, maj], np.maximum(Y0[maj], 1e-12)
    rows = np.abs(Am).sum(1) > 0
    Am, dE = Am[rows], dE[rows]
    dYm = -w * (Am.T @ np.linalg.lstsq((Am * w) @ Am.T, dE, rcond=None)[0])
    Y[maj] += dYm
    if Y.min() < -1e-14:
        return None
    return np.clip(Y, 0.0, None)


def h_wall(Y):
    gas = _G["gas"]
    gas.TPY = _G["T_wall"], _G["P"], Y
    return gas.enthalpy_mass


def jitter(Y, h, rng, mix_share=None, stream=None):
    """A jittered copy of (Y, h); see the module docstring."""
    s = _G["s"]
    Y = perturb_radicals(Y, 10 ** rng.uniform(-s["radical_decades"], s["radical_decades"], size=len(_G["rad"])))
    if Y is None:
        return None
    h = h - rng.uniform(-s["dpsi"], s["dpsi"]) * max(h - h_wall(Y), 0.0)
    if mix_share is not None or rng.uniform() < s["p_mix"]:
        lo, hi = np.log10(mix_share or s["mix_share"])
        a = 10 ** rng.uniform(lo, hi)
        Ys, hs = _G["streams"][stream or ("fuel" if rng.uniform() < 0.5 else "air")]
        Y, h = (1 - a) * Y + a * Ys, (1 - a) * h + a * hs
    return Y / Y.sum(), h


def pairs_from_trajectory(times, Ys, h, regime, traj_id, rng, skip_first, out, adiabatic_h=True, hs=None):
    """Pair picked states of a trajectory with adiabatic steps of the dt strides."""
    gas, P, dt_base = _G["gas"], _G["P"], _G["dt_base"]
    k_dt = int(_G["cfg"].get("dt_range", {}).get("per_state", 1))
    for i in range(1 if skip_first else 0, len(times)):
        hi = h if hs is None else hs[i]
        for st in rng.choice(_G["strides"], size=min(k_dt, len(_G["strides"])), replace=False):
            gas.HPY = hi, P, Ys[i]
            T_in = gas.T
            if T_in < _G["s"]["T_min"]:
                continue
            advance_const_p(gas, float(st) * dt_base)
            for k, v in (("Y_in", Ys[i]), ("T_in", T_in), ("P_in", P), ("h_in", hi), ("dt", float(st) * dt_base),
                         ("Y_out", gas.Y.copy()), ("T_out", gas.T), ("regime", regime), ("traj_id", traj_id)):
                out[k].append(v)


def pick_times(t_max, n, rng):
    lo = np.log10(_G["dt_base"])
    return np.sort(10 ** rng.uniform(lo, np.log10(t_max), size=n))


def adiabatic_trajectory(Y, h, t_max, rng):
    gas = _G["gas"]
    gas.HPY = h, _G["P"], Y
    _, net = const_p_reactor(gas)
    times = np.concatenate([[0.0], pick_times(t_max, _G["s"]["n_pick"], rng)])
    Ys = [Y.copy()]
    for t in times[1:]:
        net.advance(t)
        Ys.append(gas.Y.copy())
    return times, Ys


def cooling_trajectory(Y, h, t_max, tau_q, rng):
    """Reacting gas losing heat to T_wall at rate (h - h_wall)/tau_q, as stage 2's cooling reactors."""
    gas, P = _G["gas"], _G["P"]
    n = 200
    dt = t_max / n
    decay = 1.0 - np.exp(-dt / tau_q)
    gas.HPY = h, P, Y
    rec_t, rec_Y, rec_h = [0.0], [Y.copy()], [h]
    for k in range(1, n + 1):
        advance_const_p(gas, dt)
        Yk, hk = gas.Y.copy(), gas.enthalpy_mass
        hk = hk - (hk - h_wall(Yk)) * decay
        gas.HPY = hk, P, Yk
        rec_t.append(k * dt)
        rec_Y.append(Yk)
        rec_h.append(hk)
        if gas.T < _G["T_wall"] + 50.0:
            break
    idx = np.unique(np.concatenate([[0], rng.choice(len(rec_t), size=min(_G["s"]["n_pick"], len(rec_t)), replace=False)]))
    return np.asarray(rec_t)[idx], [rec_Y[i] for i in idx], np.asarray(rec_h)[idx]


def _seed_job(job):
    """Regimes 11-13 for one seed: its jittered starts, each followed by its reactor."""
    sid, regime, Y, h, Z, rs = job
    rng = np.random.default_rng(rs)
    s = _G["s"]
    out = {k: [] for k in PAIR_KEYS}
    for j in range(int(s["starts_per_seed"])):
        try:
            if j == 0:
                Y0, h0 = Y.copy(), h
            else:
                jj = (jitter(Y, h, rng, s["ignition_share"], "fuel" if Z < _G["Z_st"] else "air") if regime == 12 else jitter(Y, h, rng))
                if jj is None:
                    continue
                Y0, h0 = jj
            t_max = float(s["t_max"][str(regime)])
            if regime == 13:
                tau = 10 ** rng.uniform(*np.log10(s["tau_q_range"]))
                times, Ys, hs = cooling_trajectory(Y0, h0, min(t_max, 5 * tau), tau, rng)
                pairs_from_trajectory(times, Ys, h0, regime, sid * 100 + j, rng, j == 0, out, hs=hs)
            else:
                times, Ys = adiabatic_trajectory(Y0, h0, t_max, rng)
                pairs_from_trajectory(times, Ys, h0, regime, sid * 100 + j, rng, j == 0, out)
        except Exception:
            continue
    return out


def _pasr_job(job):
    """Regime 10: IEM micromixing of a cluster of seeds and the inlet streams, with reaction."""
    eid, Ys_c, hs_c, rs = job
    rng = np.random.default_rng(rs)
    s, ps = _G["s"], _G["s"]["pasr"]
    gas, P = _G["gas"], _G["P"]
    out = {k: [] for k in PAIR_KEYS}
    n = int(ps["particles"])
    Y, h = [], []
    for k in range(n):
        u = rng.uniform()
        if u < ps["stream_share"]:
            Yk, hk = _G["streams"]["fuel" if u < ps["stream_share"] / 2 else "air"]
        else:
            i = rng.integers(len(Ys_c))
            jj = jitter(Ys_c[i], hs_c[i], rng)
            if jj is None:
                continue
            Yk, hk = jj
        Y.append(np.array(Yk, float))
        h.append(float(hk))
    Y, h = np.array(Y), np.array(h)
    tau_mix = 10 ** rng.uniform(*np.log10(ps["tau_mix"]))
    t_max = float(s["t_max"]["10"])
    dt = t_max / int(ps["steps"])
    decay = 1.0 - np.exp(-dt / (2.0 * tau_mix))
    rec_every = max(1, int(ps["steps"]) // 6)
    for step in range(1, int(ps["steps"]) + 1):
        Ym, hm = Y.mean(0), h.mean()
        Y = Y - (Y - Ym) * decay                    # IEM: relax to the ensemble mean
        h = h - (h - hm) * decay
        for k in range(len(h)):
            try:
                gas.HPY = h[k], P, Y[k] / Y[k].sum()
                if gas.T > s["T_min"]:
                    advance_const_p(gas, dt)
                    Y[k] = gas.Y
            except Exception:
                pass
        if step % rec_every == 0:
            pick = rng.choice(len(h), size=min(8, len(h)), replace=False)
            for k in pick:
                pairs_from_trajectory([0.0], [Y[k] / Y[k].sum()], float(h[k]), 10, 10_000_000 + eid, rng, False, out)
    return out


def seeded_pairs(cfg, seed_files, rng, n_existing, n_seeded_before=0):
    """All seeded pairs of the seed files. Together with the seeded pairs of earlier iterations
    (n_seeded_before) they are at most max_share of the final training set."""
    s = settings(cfg)
    seeds = [dict(np.load(f, allow_pickle=False)) for f in seed_files]
    d = {k: np.concatenate([x[k] for x in seeds]) for k in ("Y", "T", "h", "Z", "regime")}
    reg = d["regime"].astype(int)
    jobs = [(int(i), int(reg[i]), d["Y"][i], float(d["h"][i]), float(d["Z"][i]), int(rng.integers(2**31)))
            for i in np.flatnonzero(np.isin(reg, [11, 12, 13]))]
    pasr_ids = np.flatnonzero(reg == 10)
    pjobs = []
    if len(pasr_ids):
        from sklearn.neighbors import NearestNeighbors
        X = np.column_stack([np.log10(np.maximum(d["Y"][pasr_ids], 1e-10)), d["T"][pasr_ids] / 100.0])
        nn = NearestNeighbors(n_neighbors=min(int(s["pasr"]["cluster"]), len(pasr_ids))).fit(X)
        centres = rng.permutation(len(pasr_ids))[: max(1, len(pasr_ids) // max(1, int(s["pasr"]["cluster"]) // 3))]
        for e, c in enumerate(centres):
            nb = pasr_ids[nn.kneighbors(X[c:c + 1], return_distance=False)[0]]
            pjobs.append((e, d["Y"][nb], d["h"][nb], int(rng.integers(2**31))))
    print(f"  seeded exploration: {len(jobs)} seeds in regimes 11-13, {len(pjobs)} PaSR ensembles "
          f"from {len(pasr_ids)} regime-10 seeds, {s['workers']} workers")
    with Pool(int(s["workers"]), initializer=_init, initargs=(cfg,)) as pool:
        res = pool.map(_seed_job, jobs, chunksize=4) + pool.map(_pasr_job, pjobs, chunksize=1)
    arrays = {k: np.asarray([v for r in res for v in r[k]]) for k in PAIR_KEYS}
    # Frozen gas barely moves in the first steps: drop any pair that starts numerically AT a seed,
    # so not even a copy of a CFD state reaches training
    from sklearn.neighbors import NearestNeighbors
    dist, _ = NearestNeighbors(n_neighbors=1).fit(d["Y"]).kneighbors(arrays["Y_in"])
    near = dist[:, 0] < float(s.get("seed_tol", 1e-8))
    if near.any():
        arrays = {k: v[~near] for k, v in arrays.items()}
        print(f"  {near.sum()} pairs within {s.get('seed_tol', 1e-8):g} of a seed state dropped")
    n = len(arrays["dt"])
    cap = max(0, int(s["max_share"] / (1 - s["max_share"]) * n_existing) - int(n_seeded_before))
    if n > cap:
        keep = np.sort(rng.choice(n, size=cap, replace=False))
        arrays = {k: v[keep] for k, v in arrays.items()}
        print(f"  {n} seeded pairs, capped to {cap} ({100 * s['max_share']:.0f} % of the training set)")
    for r in (10, 11, 12, 13):
        print(f"    regime {r}: {(arrays['regime'] == r).sum() if len(arrays['dt']) else 0} pairs")
    return arrays

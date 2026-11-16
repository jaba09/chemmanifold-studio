"""Closed-loop surrogate rollouts, Cantera reference trajectories and trajectory metrics (Section 6)."""

import itertools

import numpy as np
import torch

from .chemistry import const_p_reactor
from .flame import flame_pressure, is_flame


def eval_case(cfg, spec):
    """Normalize an evaluation case from the config: flame -> Z, alpha (dh = 0) at the flame
    pressure; premixed -> phi, T0, P0 [Pa] (from P0_atm)."""
    if is_flame(cfg):
        return {"Z": float(spec["Z"]), "alpha": float(spec["alpha"]), "dh": 0.0, "P0": flame_pressure(cfg)}
    return {"phi": float(spec["phi"]), "T0": float(spec["T0"]), "P0": float(spec["P0_atm"]) * 101325.0}


def grid_cases(cfg):
    """Cartesian product of evaluation.envelope_grid, in the key order given in the config."""
    g = cfg["evaluation"]["envelope_grid"]
    keys = list(g)
    return keys, [eval_case(cfg, dict(zip(keys, vals))) for vals in itertools.product(*g.values())]


# chemistry.StateMap of the config (state_species), set by the evaluation stages: Cantera references
# are then projected onto the network's state species (and h0 is that of the projected start).
STATE_MAP = None


def cantera_trajectory(gas, init, case, dt, n_steps, smap=None):
    init(case)
    smap = smap or STATE_MAP
    if smap is not None and smap.reference == "arc":    # the ARC kernel from the projected start state
        Y0 = smap.project(gas.Y)
        h0 = float(smap.enthalpy(Y0[None], np.array([gas.T]), np.array([gas.P]))[0])
        Yk, Tk = smap.advance(Y0, gas.T, gas.P, [k * dt for k in range(1, n_steps + 1)])
        return np.vstack([Y0[None], Yk]), np.r_[gas.T, Tk], h0
    Y, T = [gas.Y.copy()], [gas.T]
    h0 = gas.enthalpy_mass
    _, net = const_p_reactor(gas)
    for k in range(1, n_steps + 1):
        net.advance(k * dt)
        Y.append(gas.Y.copy())
        T.append(gas.T)
    Y, T = np.array(Y), np.array(T)
    if smap is not None:
        Y = smap.project(Y)
        h0 = float(smap.enthalpy(Y[:1], T[:1], np.array([gas.P]))[0])
    return Y, T, h0


@torch.no_grad()
def surrogate_rollout(model, Y0, T0, P0, h0, dt, n_steps):
    """Autoregressive rollout (Eq. 46) for a batch of initial states; returns (B, n+1, Ns), (B, n+1)."""
    f64 = dict(dtype=torch.float64)
    Y = torch.as_tensor(np.atleast_2d(Y0), **f64)
    T = torch.as_tensor(np.atleast_1d(T0), **f64)
    B = len(T)
    P = torch.as_tensor(np.broadcast_to(P0, B).copy(), **f64)
    h = torch.as_tensor(np.broadcast_to(h0, B).copy(), **f64)
    dts = torch.full((B,), float(dt), **f64)
    Ys, Ts = [Y], [T]
    for _ in range(n_steps):
        out = model(Y, T, P, h, dts)
        Y, T = out["Y"], out["T"]
        Ys.append(Y)
        Ts.append(T)
    return torch.stack(Ys, 1).numpy(), torch.stack(Ts, 1).numpy()


def ignition_index(T, t):
    return int(np.argmax(np.gradient(T, t)))


def manifold_T_mae(T_ml, T_ct):
    """Progress-aligned temperature error (Eq. 48): compare the sorted temperature trajectories."""
    return float(np.mean(np.abs(np.sort(T_ml) - np.sort(T_ct))))


def phase_aligned_nrmse(Y_ml, Y_ct, i_ml, i_ct):
    """Species NRMSE (Eq. 49) after shifting the ML trajectory so that the ignition indices coincide."""
    lag = i_ml - i_ct
    n = len(Y_ct)
    k = np.arange(max(0, -lag), min(n, n - lag))
    Ya, Yc = Y_ml[k + lag], Y_ct[k]
    return float(np.linalg.norm(Ya - Yc) / np.linalg.norm(Yc) * 100.0)

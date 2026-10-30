"""Unsteady flamelets in mixture-fraction space: the states a non-premixed flame passes through when
its local strain rate (scalar dissipation rate chi) or heat loss changes faster than it can adapt.

Unity-Lewis-number flamelet equations (Peters 1984), solved by operator splitting on a fixed Z grid:

    dY_k/dt = chi(Z)/2 d2Y_k/dZ2 + w_k/rho        dh/dt = chi(Z)/2 d2h/dZ2 - (h - h_wall(Y))/tau_q

    chi(Z) = (a/pi) exp(-2 [erfc^-1(2Z)]^2)        (counterflow, strain rate a)

Each step diffuses Y and h implicitly (tridiagonal, Dirichlet at the pure streams), advances every
point's adiabatic constant-pressure chemistry by dt (Cantera/CVODES), then applies the optional heat
loss towards the wall temperature. The transients start from the stage-0 counterflow flamelets:

  * extinction: strain stepped above the highest burning strain -> partially extinguished states,
    hot radicals in cooling gas, the way a flame is torn by a strain peak;
  * reignition: a partially extinguished snapshot relaxed at low strain -> re-ignition or decay;
  * cooling:    a burning flamelet at its own strain losing heat with time constant tau_q -> flame
    states with an enthalpy defect at every Z (flame next to a cold wall, radiation);
  * strain jump: strain stepped down or up by a factor -> states between steady flamelets.

All transients are physics only (mechanism + stream conditions + a priori strain/heat-loss ranges).
"""

import numpy as np
from scipy.linalg import solve_banded
from scipy.special import erfcinv

from .chemistry import advance_const_p


def z_grid(n, z_st):
    """About n points on [0, 1]: half on [0, 2 Z_st], densest at Z_st (sinh clustering), half
    geometric on [2 Z_st, 1]."""
    s = np.linspace(-1.0, 1.0, n // 2 + 1)
    lo = z_st * (1 + np.sinh(2.5 * s) / np.sinh(2.5))
    hi = np.geomspace(2 * z_st, 1.0, n // 2 + 1)
    return np.unique(np.concatenate([lo, hi]))


def chi_profile(Z, a):
    """Counterflow scalar dissipation rate [1/s] at strain a [1/s]; zero at the pure streams."""
    Zc = np.clip(Z, 1e-12, 1 - 1e-12)
    chi = a / np.pi * np.exp(-2.0 * erfcinv(2.0 * Zc) ** 2)
    chi[(Z <= 0) | (Z >= 1)] = 0.0
    return chi


class ZFlamelet:
    """State (Y[n, Ns], h[n]) of an unsteady flamelet on the grid Z, with pure streams at both ends."""

    def __init__(self, gas, Z, Y, h, P, T_wall):
        self.gas, self.Z, self.Y, self.h, self.P, self.T_wall = gas, Z, Y.copy(), h.copy(), P, T_wall
        dz = np.diff(Z)
        self.hm, self.hp = dz[:-1], dz[1:]                     # spacing left/right of interior points

    def T(self):
        out = np.empty(len(self.Z))
        for i, (Y, h) in enumerate(zip(self.Y, self.h)):
            self.gas.HPY = h, self.P, Y
            out[i] = self.gas.T
        return out

    def _diffuse(self, a, dt):
        chi = chi_profile(self.Z, a)[1:-1]
        cm = chi * dt / (self.hm * (self.hm + self.hp))        # implicit (I - dt chi/2 d2/dZ2)
        cp = chi * dt / (self.hp * (self.hm + self.hp))
        n = len(chi)
        ab = np.zeros((3, n))
        ab[0, 1:] = -cp[:-1]
        ab[1] = 1 + cm + cp
        ab[2, :-1] = -cm[1:]
        F = np.column_stack([self.Y, self.h])
        rhs = F[1:-1].copy()
        rhs[0] += cm[0] * F[0]
        rhs[-1] += cp[-1] * F[-1]
        F[1:-1] = solve_banded((1, 1), ab, rhs)
        Y = np.clip(F[:, :-1], 0.0, None)
        self.Y, self.h = Y / Y.sum(1, keepdims=True), F[:, -1]

    def step(self, a, dt, tau_q=0.0, T_frozen=450.0):
        self._diffuse(a, dt)
        g = self.gas
        for i in range(1, len(self.Z) - 1):
            g.HPY = self.h[i], self.P, self.Y[i]
            if g.T > T_frozen:
                advance_const_p(g, dt)
                self.Y[i] = g.Y
            if tau_q > 0:
                g.TPY = self.T_wall, self.P, self.Y[i]
                self.h[i] -= (self.h[i] - g.enthalpy_mass) * (1.0 - np.exp(-dt / tau_q))


def run_transient(gas, fl, kind, a, t_end, tau_q=0.0, dt_bounds=(1e-5, 1e-3), n_snapshots=40,
                  max_steps=2000, T_ext=800.0, dT_snap=40.0):
    """Integrate one transient; return ([(t, Y, h) snapshots], [T_max per snapshot]).
    dt is 2% of the shortest diffusion time 1/chi_max (and 5% of tau_q), within dt_bounds. A snapshot
    is kept every n_steps / n_snapshots steps and whenever the peak temperature has moved by more than
    dT_snap since the last one, so fast extinctions are resolved too."""
    chi_max = float(chi_profile(fl.Z, a).max())
    dt = min(0.02 / max(chi_max, 1e-12), dt_bounds[1])
    if tau_q > 0:
        dt = min(dt, 0.05 * tau_q)
    dt = max(dt, dt_bounds[0])
    n = int(min(max_steps, np.ceil(t_end / dt)))
    every = max(1, n // n_snapshots)
    snaps, Tmax, T_last = [], [], float(fl.T().max())
    for k in range(1, n + 1):
        fl.step(a, dt, tau_q)
        T = float(fl.T().max())
        if k % every == 0 or k == n or abs(T - T_last) > dT_snap:
            snaps.append((k * dt, fl.Y.copy(), fl.h.copy()))
            Tmax.append(T)
            T_last = T
            if kind == "extinction" and T < T_ext:
                break
            if kind == "cooling" and T < fl.T_wall + 100.0:
                break
    return snaps, Tmax

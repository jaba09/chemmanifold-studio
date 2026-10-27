"""Non-premixed (burner) flame support: fuel/oxidizer streams, Bilger mixture fraction, and the
flamelet-based burnt reference used to seed states inside the flame's thermochemical space."""

import cantera as ct
import numpy as np

from .io import load_npz, stage_dir

W_ELEM = {"C": 12.011, "H": 1.008, "O": 15.999}


def is_flame(cfg):
    return cfg["envelope"].get("mode", "premixed") == "flame"


def flame_pressure(cfg):
    return cfg["chemistry"]["P_atm"] * ct.one_atm


def stream_states(gas, cfg):
    """(Y, h) of the fuel and oxidizer streams at their inlet temperatures and the flame pressure."""
    c, P = cfg["chemistry"], flame_pressure(cfg)
    gas.TPY = c["fuel_T"], P, c["fuel"]
    fuel = (gas.Y.copy(), gas.enthalpy_mass)
    gas.TPY = c["oxidizer_T"], P, c["oxidizer"]
    ox = (gas.Y.copy(), gas.enthalpy_mass)
    return fuel, ox


class BilgerZ:
    """Vectorized Bilger mixture fraction from mass fractions, Z = (beta - beta_ox)/(beta_f - beta_ox)."""

    def __init__(self, gas, Y_fuel, Y_ox):
        names = gas.element_names
        self.coef = np.zeros(gas.n_elements)
        for el, w in (("C", 2.0), ("H", 0.5), ("O", -1.0)):
            if el in names:
                self.coef[names.index(el)] = w / W_ELEM[el]
        A = np.zeros((gas.n_elements, gas.n_species))
        for k in range(gas.n_species):
            for m in range(gas.n_elements):
                A[m, k] = gas.n_atoms(k, m) * gas.atomic_weights[m] / gas.molecular_weights[k]
        self.A = A
        self.b_f = self._beta(Y_fuel)
        self.b_o = self._beta(Y_ox)

    def _beta(self, Y):
        return (np.atleast_2d(Y) @ self.A.T) @ self.coef

    def __call__(self, Y):
        return (self._beta(Y) - self.b_o) / (self.b_f - self.b_o)


def stoichiometric_z(gas, cfg):
    (Yf, _), (Yo, _) = stream_states(gas, cfg)
    bz = BilgerZ(gas, Yf, Yo)
    return float(-bz.b_o[0] / (bz.b_f[0] - bz.b_o[0]))


def z_from_unit(u, knots_z, knots_u):
    """Map u in [0,1] to Z through a piecewise-linear CDF (refines Z where knots are dense)."""
    return np.interp(u, knots_u, knots_z)


def flamelet_split(cfg, n_flamelets):
    """Training / held-out flamelet indices: every `holdout_every`-th flamelet (starting at 1) is
    kept out of the training data so stage 11 can test coverage on flame states it never saw."""
    k = cfg["flame"].get("holdout_every", 0)
    ids = np.arange(n_flamelets)
    held = ids[(ids % k) == 1] if k and n_flamelets > 2 else ids[:0]
    return np.setdiff1d(ids, held), held


def wall_temperature(cfg):
    """Coldest wall (or stream) the flame gas can lose heat to [K]: the lower bound of the
    physically reachable enthalpy at a given composition."""
    return float(cfg["envelope"].get("T_wall", 300.0))


def heat_loss(gas, Y, h, psi, P, T_wall):
    """Enthalpy change dh <= 0 that takes the gas (Y, h) a fraction psi in [0, 1] of the way from its
    current enthalpy to the same composition cooled to T_wall (psi = 1: cooled to the wall)."""
    gas.TPY = T_wall, P, Y
    return -float(psi) * max(h - gas.enthalpy_mass, 0.0)


class FlameSeeds:
    """Builds physical states at (Z, alpha, dh, flamelet j): a mix of the fresh stream mixture and
    the burnt state of training flamelet j at the same mixture fraction, plus an enthalpy loss
    dh <= 0. Flamelet 0 (lowest strain, nearest equilibrium) is the default burnt state.
    The loss can instead be given as a fraction psi of the largest physical loss (heat_loss)."""

    def __init__(self, gas, cfg):
        self.gas, self.cfg = gas, cfg
        self.P = flame_pressure(cfg)
        self.T_wall = wall_temperature(cfg)
        (self.Yf, self.hf), (self.Yo, self.ho) = stream_states(gas, cfg)
        fl = load_npz(stage_dir(cfg, "flame") / "flamelets.npz")
        self.flamelets, self.raw = [], []
        for j in range(int(fl["strain_id"].max()) + 1):
            m = fl["strain_id"] == j
            self.raw.append((fl["Y"][m], fl["h"][m]))
            order = np.argsort(fl["Z"][m])
            Z, Y, h = fl["Z"][m][order], fl["Y"][m][order], fl["h"][m][order]
            keep = np.concatenate([[True], np.diff(Z) > 1e-9])
            Z = np.concatenate([[0.0], Z[keep], [1.0]])     # pure streams at the ends
            Y = np.vstack([self.Yo, Y[keep], self.Yf])
            h = np.concatenate([[self.ho], h[keep], [self.hf]])
            self.flamelets.append((Z, Y, h))
        self.train_ids, self.heldout_ids = flamelet_split(cfg, len(self.flamelets))

    def fresh(self, Z):
        return Z * self.Yf + (1 - Z) * self.Yo, Z * self.hf + (1 - Z) * self.ho

    def burnt(self, Z, flamelet=0):
        Zg, Yg, hg = self.flamelets[int(flamelet)]
        Y = np.array([np.interp(Z, Zg, Yg[:, k]) for k in range(Yg.shape[1])])
        return Y / Y.sum(), float(np.interp(Z, Zg, hg))

    def set_state(self, Z, alpha, dh=0.0, flamelet=0, psi=None):
        """Set self.gas to the seed state; returns (Y, h). A given psi overrides dh."""
        Yu, hu = self.fresh(Z)
        Yb, hb = self.burnt(Z, flamelet)
        Y = (1 - alpha) * Yu + alpha * Yb
        h = (1 - alpha) * hu + alpha * hb
        if psi is not None:
            dh = heat_loss(self.gas, Y, h, psi, self.P, self.T_wall)
        h = h + dh
        self.gas.HPY = h, self.P, Y
        return Y, h


def make_initializer(gas, cfg):
    """Return init(case) that puts `gas` in the initial state of a case (a dict or DataFrame row):
    premixed cases carry phi, T0, P0; flame cases carry Z, alpha and optionally dh or psi."""
    if is_flame(cfg):
        seeds = FlameSeeds(gas, cfg)

        def init(c):
            psi = c.get("psi")
            psi = None if psi is None or not np.isfinite(float(psi)) else float(psi)
            return seeds.set_state(float(c["Z"]), float(c["alpha"]), float(c.get("dh", 0.0)),
                                   int(c.get("flamelet", 0)), psi)
        return init
    from .chemistry import set_unburnt

    return lambda c: set_unburnt(gas, cfg, float(c["phi"]), float(c["T0"]), float(c["P0"]))


def case_label(case):
    keys = (("Z", "alpha") + tuple(k for k in ("psi", "tau_q") if case.get(k, 0) == case.get(k, 0)
                                   and case.get(k, 0) > 0)) if "Z" in case else ("phi", "T0", "P0")
    fmt = {"Z": "Z={:.3f}", "alpha": "alpha={:.2f}", "phi": "phi={:.2f}", "T0": "T0={:.0f}K",
           "P0": "P0={:.2f}atm", "psi": "psi={:.2f}", "tau_q": "tau_q={:.2g}s"}
    return " ".join(fmt[k].format(case[k] / (101325.0 if k == "P0" else 1.0)) for k in keys)

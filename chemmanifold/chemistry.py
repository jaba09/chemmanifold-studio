"""Cantera helpers: gas setup, elemental mass matrix (Eq. 5) and NASA-7 coefficient tables."""

from pathlib import Path

import cantera as ct
import numpy as np

RU = 8314.462618  # J/(kmol K)


def mechanism_path(cfg):
    """A mechanism path relative to the config file or the repository, else a Cantera built-in name."""
    mech = cfg["chemistry"]["mechanism"]
    for base in (Path(cfg["_config_path"]).parent, Path(__file__).resolve().parents[1]):
        if (base / mech).is_file():
            return str(base / mech)
    return mech


def make_gas(cfg):
    return ct.Solution(mechanism_path(cfg))


def set_unburnt(gas, cfg, phi, T0, P0):
    c = cfg["chemistry"]
    gas.set_equivalence_ratio(phi, c["fuel"], c["oxidizer"], basis=c.get("composition_basis", "mole"))
    gas.TP = T0, P0


def element_mass_matrix(gas):
    """A[m, k] = n_atoms(k, m) * W_m^elem / W_k ; columns sum to one (Eq. 6)."""
    Ne, Ns = gas.n_elements, gas.n_species
    A = np.zeros((Ne, Ns))
    W_elem = gas.atomic_weights
    W = gas.molecular_weights
    for k in range(Ns):
        for m in range(Ne):
            A[m, k] = gas.n_atoms(k, m) * W_elem[m] / W[k]
    return A


def nasa7_tables(gas):
    """Return (T_mid[Ns], a_lo[Ns,7], a_hi[Ns,7]) for NASA-7 (NasaPoly2) species."""
    Ns = gas.n_species
    T_mid = np.zeros(Ns)
    a_lo = np.zeros((Ns, 7))
    a_hi = np.zeros((Ns, 7))
    for k, sp in enumerate(gas.species()):
        if not isinstance(sp.thermo, ct.NasaPoly2):
            raise ValueError(f"species {sp.name} does not use NASA-7 polynomials")
        c = sp.thermo.coeffs
        T_mid[k] = c[0]
        a_hi[k] = c[1:8]
        a_lo[k] = c[8:15]
    return T_mid, a_lo, a_hi


def thermo_tables(gas):
    T_mid, a_lo, a_hi = nasa7_tables(gas)
    return dict(
        species=np.array(gas.species_names),
        elements=np.array(gas.element_names),
        A=element_mass_matrix(gas),
        W=gas.molecular_weights.copy(),
        T_mid=T_mid,
        a_lo=a_lo,
        a_hi=a_hi,
    )


def const_p_reactor(gas):
    """Adiabatic constant-pressure reactor sharing `gas` (its state tracks the reactor)."""
    r = ct.IdealGasConstPressureReactor(gas, clone=False)
    return r, ct.ReactorNet([r])


def advance_const_p(gas, dt):
    """Advance the current gas state adiabatically at constant pressure by dt (in place)."""
    _, net = const_p_reactor(gas)
    net.advance(dt)


# --- Network state on a subset of the exploration mechanism's species ------------------------------
# `chemistry.state_species: [names]` makes the exploration (stages 0-4) run on the full mechanism
# (e.g. the 43-species skeletal GRI of ARC_GRI30_NOx22) while the network's state is only those
# species (the 22 species the ARC kernel transports; its 21 QSS radicals are dropped). Stage 5
# projects every pair onto them, and every later Cantera reference is projected the same way.


def state_species(cfg):
    return cfg["chemistry"].get("state_species")


class StateMap:
    """Projection between the exploration mechanism `gas` and the network's state species.

    project: Y[..., idx] renormalised to unit mass (the dropped species, QSS radicals, carry
             < ~1e-4 of the mass; their elements are not redistributed).
    lift:    a state composition into `gas` with the dropped species at zero (for Cantera
             references started from a network state; the QSS radicals rebuild in ~1 us).
    sgas:    a thermo-only ideal gas of the state species with the same NASA-7 data: the
             thermodynamics of the network's physics layers and of the CFD case (arcChemStep)."""

    def __init__(self, gas, names):
        bad = [n for n in names if not isinstance(n, str)]
        if bad:
            raise ValueError(f"state species must be quoted strings (YAML reads a bare NO as false): {bad}")
        missing = [n for n in names if n not in gas.species_names]
        if missing:
            raise ValueError(f"state species not in the mechanism: {missing}")
        self.gas, self.names = gas, list(names)
        self.idx = np.array([gas.species_index(n) for n in names])
        self.sgas = ct.Solution(thermo="ideal-gas", species=[gas.species(n) for n in names])
        self.A = element_mass_matrix(self.sgas)
        # element fix of a projected output, as arcChemStep (arc_project) does after each DI step
        self.fix_idx = [self.names.index(n) for n in ("CO2", "H2O", "O2", "N2") if n in self.names]
        self.fix_inv = np.linalg.pinv(self.A[:, self.fix_idx]) if len(self.fix_idx) == self.A.shape[0] else None

    def project(self, Y):
        Y = np.asarray(Y)
        if Y.shape[-1] == len(self.idx):        # already a state composition
            return Y.copy()
        Ys = np.maximum(Y[..., self.idx], 0.0)
        return Ys / Ys.sum(-1, keepdims=True)

    def fix_elements(self, Ys, Y_ref):
        """Restore the element mass fractions of Y_ref in Ys by moving CO2, H2O, O2, N2 (the QSS
        species the projection drops carry ~1e-4 of the mass, and their C/H/O/N would otherwise be
        missing from the output: the network's physics layer conserves elements exactly)."""
        if self.fix_inv is None:
            return Ys
        r = Y_ref @ self.A.T - Ys @ self.A.T
        Ys = Ys.copy()
        Ys[..., self.fix_idx] += r @ self.fix_inv.T
        return np.maximum(Ys, 0.0)

    def lift(self, Ys):
        Ys = np.asarray(Ys)
        Y = np.zeros(Ys.shape[:-1] + (self.gas.n_species,))
        Y[..., self.idx] = Ys
        return Y

    def enthalpy(self, Ys, T, P):
        a = ct.SolutionArray(self.sgas, len(T))
        a.TPY = T, P, Ys
        return a.enthalpy_mass

    def temperature(self, Ys, h, P):
        a = ct.SolutionArray(self.sgas, len(h))
        a.HPY = h, P, Ys
        return a.T

    def project_pairs(self, d, report=True):
        """Pairs {Y_in, T_in, P_in, h_in, Y_out, T_out, ...} onto the state species, in place-safe
        copies: h_in is the enthalpy of the projected input at T_in, and T_out the temperature of
        the projected output at that enthalpy, so every pair conserves h in the state thermo, as the
        network's physics layers do (the shift of T_out is reported)."""
        if d["Y_in"].shape[-1] == len(self.idx):
            return d
        d = dict(d)
        T_out0 = d["T_out"]
        lost = 1.0 - d["Y_in"][:, self.idx].sum(1)
        d["Y_in"] = self.project(d["Y_in"])
        d["Y_out"] = self.fix_elements(self.project(d["Y_out"]), d["Y_in"])
        d["h_in"] = self.enthalpy(d["Y_in"], d["T_in"], d["P_in"])
        T_out = self.temperature(d["Y_out"], d["h_in"], d["P_in"])
        if report:
            dT = np.abs(T_out - T_out0)
            print(f"  projected {len(dT)} pairs onto {len(self.idx)} state species: dropped mass "
                  f"max {lost.max():.2e} (p99 {np.quantile(lost, 0.99):.2e}), |dT_out| max {dT.max():.3f} K "
                  f"(p99 {np.quantile(dT, 0.99):.3f} K)")
        d["T_out"] = T_out
        return d

    def project_segments(self, s):
        """Rollout-loss segments {Y (n, K+1, Ns), T (n, K+1), P, h, dt}: same projection, h from the
        first state and every step's T from that h."""
        if s["Y"].shape[-1] == len(self.idx):
            return s
        s = dict(s)
        n, K1 = s["T"].shape
        Y = self.project(s["Y"])
        Y[:, 1:] = self.fix_elements(Y[:, 1:], Y[:, :1])
        P = np.repeat(np.asarray(s["P"], float), K1)
        h = self.enthalpy(Y[:, 0], s["T"][:, 0], s["P"])
        T = self.temperature(Y.reshape(n * K1, -1), np.repeat(h, K1), P).reshape(n, K1)
        T[:, 0] = s["T"][:, 0]
        s.update(Y=Y, T=T, h=h)
        return s

    def advance(self, Ys, T, P, times, rtol=1e-8, atol=1e-14):
        """Cantera constant-pressure reference from a state composition: lifted into the full
        mechanism, advanced to each of `times` [s], projected back. Returns (Ys[len(times)], T[...])."""
        self.gas.TPY = T, P, self.lift(Ys)
        r = ct.IdealGasConstPressureReactor(self.gas, clone=True)
        net = ct.ReactorNet([r])
        net.rtol, net.atol = rtol, atol
        Yo, To = [], []
        for t in times:
            net.advance(t)
            Yo.append(self.fix_elements(self.project(r.thermo.Y), np.asarray(Ys)))
            To.append(r.T)
        Yo = np.array(Yo)
        # the state thermo's T at the reactor's enthalpy (the dropped species' share of h is tiny)
        To = self.temperature(Yo, np.full(len(Yo), self.enthalpy(Ys[None], np.array([T]), np.array([P]))[0]),
                              np.full(len(Yo), P))
        return Yo, To


def state_map(cfg, gas=None):
    """StateMap of the config's state species, or None when the network state is the whole mechanism."""
    names = state_species(cfg)
    return StateMap(gas if gas is not None else make_gas(cfg), names) if names else None


def make_state_gas(cfg):
    """The gas whose species are the network's state (thermo only when state_species is set)."""
    sm = state_map(cfg)
    return sm.sgas if sm else make_gas(cfg)

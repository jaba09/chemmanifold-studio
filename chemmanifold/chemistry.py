"""Cantera helpers: gas setup, elemental mass matrix (Eq. 5) and NASA-7 coefficient tables."""

import cantera as ct
import numpy as np

RU = 8314.462618  # J/(kmol K)


def make_gas(cfg):
    return ct.Solution(cfg["chemistry"]["mechanism"])


def set_unburnt(gas, cfg, phi, T0, P0):
    gas.set_equivalence_ratio(phi, cfg["chemistry"]["fuel"], cfg["chemistry"]["oxidizer"])
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

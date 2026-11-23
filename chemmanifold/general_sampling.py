"""COVLOOP step 1: general (not flame-specific) sampling of the CH4/air thermochemical space with ARC22 labels.

docs/COVERAGE-LOOP-ROADMAP.md section 4. Every set needs only the mechanism, the streams (CH4, air and premixed
CH4/air between the flammability limits), p = 1 atm and a stream-temperature range. No heat-loss model, no
wall temperature, no jet/entrainment law, no strain or time taken from a CFD run.

Families (each state keeps its `family` tag):
  R1 autoignition      R2 low-T ignition   R3 PSR S-curves (+ extinction transients through the middle branch)
  R4 generic PaSR      R5 vitiated ignition R6 equilibrium + relaxation
  F1 free premixed     F2 counterflow diffusion (strain to extinction; unstable branch by two-point control)
  F3 counterflow premixed (fresh-to-burnt and twin)  F4 counterflow partially premixed
  F5 unsteady flamelets (extinction, re-ignition, strain jumps; tau_q = 0)  F6 = transport variants of F1-F4
  P1 off-manifold perturbations  P2 multi-scale (Box-Cox space)  P3 random-pair mixing  P4 low-T mixtures
States are produced with Cantera on the 43-species skeleton of ARC22 (gri30_skel43.yaml), projected onto the
22 transported species with the ARC element projection, and labelled with the ARC22 C kernel itself
(`label_arc`). The pairs are physics-exploration data: they may be used for training.
"""

import ctypes
import os
import subprocess

import cantera as ct
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ARC_DIR = os.path.join(HERE, "..", "mechanisms", "arc_gri30_nox22")
SKEL = os.path.join(ARC_DIR, "gri30_skel43.yaml")
AIR = "O2:0.21, N2:0.79"
P0 = ct.one_atm
FAMILIES = ["R1", "R2", "R3", "R4", "R5", "R6", "F1", "F2", "F3", "F4", "F5", "P1", "P2", "P3", "P4"]


# ----------------------------------------------------------------------------------------------- ARC22 kernel

class ARC:
    """ctypes binding of the ARC22 C core (built on first use with gcc -O2)."""

    def __init__(self, lib=None):
        lib = lib or os.environ.get("ARC_LIB") or os.path.join(os.environ.get("TMPDIR", "/tmp"), "libarc22.so")
        if not os.path.exists(lib):
            subprocess.check_call(["gcc", "-O2", "-shared", "-fPIC", "-o", lib,
                                   os.path.join(ARC_DIR, "arc_gri30_nox22.c"), "-lm"])
        self.lib = ctypes.CDLL(lib)
        self.lib.arc_species_name.restype = ctypes.c_char_p
        self.lib.arc_species_W.restype = ctypes.c_double
        self.names = [self.lib.arc_species_name(k).decode() for k in range(43)]
        self.ode = self.names[:22]
        self.W = np.array([self.lib.arc_species_W(k) for k in range(43)])
        self._D = ctypes.POINTER(ctypes.c_double)

    def _p(self, a):
        return a.ctypes.data_as(self._D)

    def rhs(self, y, p=P0):
        y = np.ascontiguousarray(y, float)
        d = np.zeros(23)
        self.lib.arc_rhs(ctypes.c_double(p), self._p(y), self._p(d))
        return d

    def elements(self, Y22):
        Y22 = np.ascontiguousarray(Y22, float)
        e = np.zeros(4)
        self.lib.arc_elements(self._p(Y22), self._p(e))
        return e

    def project(self, Y22, el0):
        Y = np.array(Y22, float)
        self.lib.arc_project(self._p(Y), self._p(np.ascontiguousarray(el0, float)))
        return Y

    def elements43(self, Y43):
        """kmol C, H, O, N per kg of a 43-species state (mechanism order = arc order)."""
        el = np.zeros(4)
        for k in range(43):
            ek = np.zeros(4)
            self.lib.arc_species_elements(k, self._p(ek))
            el += Y43[k] / self.W[k] * ek
        return el


class Projector:
    """Map Cantera skel43 states onto the 22 ARC transported species (QSS element mass -> CO2/H2O/O2/N2)."""

    def __init__(self, gas, arc):
        self.arc = arc
        self.idx43 = [gas.species_index(s) for s in arc.names]        # cantera index of each arc species
        self.idx22 = self.idx43[:22]

    def __call__(self, Y43c):
        Y43c = np.atleast_2d(Y43c)
        out = np.empty((len(Y43c), 22))
        for i, y in enumerate(Y43c):
            ya = y[self.idx43]
            out[i] = self.arc.project(ya[:22], self.arc.elements43(ya))
        return out


def label_arc(arc, T, Y22, dts, rtol=1e-8, atol=1e-14):
    """Y(t + dt) for each dt in dts (one BDF integration per state). Returns array (len(dts), 22) and T."""
    from scipy.integrate import solve_ivp
    dts = np.sort(np.atleast_1d(dts))
    y0 = np.append(Y22, T)
    sol = solve_ivp(lambda t, y: arc.rhs(y), (0.0, dts[-1]), y0, method="BDF", t_eval=dts, rtol=rtol, atol=atol)
    if not sol.success or sol.y.shape[1] != len(dts):
        return None, None
    Y = np.maximum(sol.y[:22].T, 0.0)
    el0 = arc.elements(Y22)
    Y = np.array([arc.project(y, el0) for y in Y])
    return dts, Y, sol.y[22]


# ----------------------------------------------------------------------------------------------- helpers

class Streams:
    def __init__(self, gas, T_fuel=298.0, T_ox=298.0):
        self.gas = gas
        gas.TPX = T_fuel, P0, "CH4:1"
        self.Yf, self.hf = gas.Y.copy(), gas.enthalpy_mass
        gas.TPX = T_ox, P0, AIR
        self.Yo, self.ho = gas.Y.copy(), gas.enthalpy_mass
        # stoichiometric Z for CH4/air
        gas.set_equivalence_ratio(1.0, "CH4", AIR)
        self.z_st = gas.mixture_fraction("CH4:1", AIR)

    def mix(self, Z):
        return Z * self.Yf + (1 - Z) * self.Yo

    def z_of_phi(self, phi):
        self.gas.set_equivalence_ratio(phi, "CH4", AIR)
        return self.gas.mixture_fraction("CH4:1", AIR)


def z_samples(rng, n, z_st, z_max=1.0):
    """Log-spaced in (1e-4, z_max) with half of the draws within a factor 3 of Z_st."""
    a = 10 ** rng.uniform(-4, np.log10(z_max), n // 2)
    b = z_st * 3.0 ** rng.uniform(-1, 1, n - n // 2)
    return np.clip(np.concatenate([a, b]), 0.0, z_max)


def arclength_pick(T, Y, n):
    """n states evenly spaced in arc length of (T/1000, Y_CO2, Y_H2O, 10 Y_OH, Y_CO, Y_CH4) along a trajectory."""
    if len(T) <= n:
        return np.arange(len(T))
    f = np.column_stack([T / 1000.0, Y])
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(f, axis=0), axis=1))])
    return np.unique(np.searchsorted(s, np.linspace(0, s[-1], n)).clip(0, len(T) - 1))


def reactor_traj(gas, T, Y, t_end, n_keep=40, mode="arc"):
    gas.TPY = T, P0, Y
    r = ct.IdealGasConstPressureReactor(gas, clone=True)
    net = ct.ReactorNet([r])
    net.rtol, net.atol = 1e-8, 1e-15
    Ts, Ys = [r.phase.T], [r.phase.Y.copy()]
    while net.time < t_end and len(Ts) < 20000:
        net.step()
        Ts.append(r.phase.T), Ys.append(r.phase.Y.copy())
    Ts, Ys = np.array(Ts), np.array(Ys)
    key = Ys[:, [gas.species_index(s) for s in ("CO2", "H2O", "OH", "CO", "CH4")]] * [1, 1, 10, 1, 1]
    i = arclength_pick(Ts, key, n_keep // 2)
    j = np.unique(np.linspace(0, len(Ts) - 1, n_keep - n_keep // 2).astype(int))   # by step count (log-ish time)
    k = np.union1d(i, j)
    return Ts[k], Ys[k]


# ----------------------------------------------------------------------------------------------- families

def fam_R1(gas, st, rng, n_traj, T0=(600.0, 1800.0), t_end=0.05, n_keep=40, z_max=1.0):
    out = []
    for Z, T in zip(z_samples(rng, n_traj, st.z_st, z_max), rng.uniform(*T0, n_traj)):
        out.append(reactor_traj(gas, T, st.mix(Z), t_end, n_keep))
    return out


def fam_R2(gas, st, rng, n_traj, n_keep=30):
    return fam_R1(gas, st, rng, n_traj, T0=(600.0, 1000.0), t_end=1.0, n_keep=n_keep)


def fam_R3(gas, st, rng, n_mix, tau=np.geomspace(1.0, 1e-5, 25), Tin=(298.0, 800.0), n_keep=20):
    """PSR S-curves: steady burning branch for decreasing residence time, plus the extinction transient at
    the first tau that blows out (its states cross the unstable middle branch)."""
    out = []
    for _ in range(n_mix):
        phi = 10 ** rng.uniform(np.log10(0.4), np.log10(2.5))
        Ti = rng.uniform(*Tin)
        gas.TP = Ti, P0
        gas.set_equivalence_ratio(phi, "CH4", AIR)
        inlet = ct.Reservoir(gas, clone=True)
        gas.equilibrate("HP")
        r = ct.IdealGasReactor(gas, clone=True, energy="on")
        exhaust = ct.Reservoir(gas, clone=True)
        mfc = ct.MassFlowController(inlet, r, mdot=lambda t: r.mass / res_t[0])
        ct.PressureController(r, exhaust, primary=mfc, K=1e-5)
        net = ct.ReactorNet([r])
        res_t = [tau[0]]
        Ts, Ys = [], []
        for tt in tau:
            res_t[0] = tt
            try:
                net.advance(net.time + 20 * tt)
            except ct.CanteraError:
                break
            Ts.append(r.phase.T), Ys.append(r.phase.Y.copy())
            if r.phase.T < Ti + 200:          # blown out: the transient states are kept below
                break
        # extinction transient at the blow-out residence time, recorded densely
        t0 = net.time
        while net.time < t0 + 50 * res_t[0] and len(Ts) < 400:
            try:
                net.step()
            except ct.CanteraError:
                break
            Ts.append(r.phase.T), Ys.append(r.phase.Y.copy())
        if Ts:
            Ts, Ys = np.array(Ts), np.array(Ys)
            k = arclength_pick(Ts, Ys[:, [gas.species_index("CO2"), gas.species_index("OH")]] * [1, 10], n_keep)
            out.append((Ts[k], Ys[k]))
    return out


def fam_R4(gas, st, rng, n_runs, n_part=60, n_steps=150, n_keep=200):
    """Adiabatic stochastic PaSR, modified Curl mixing, inflow from fuel, air and a premixed stream."""
    out = []
    for _ in range(n_runs):
        tau_res = 10 ** rng.uniform(-4, -1)
        tau_mix = tau_res * 10 ** rng.uniform(-2, 1)
        dt = min(tau_res, tau_mix) / 5
        phi_p = 10 ** rng.uniform(np.log10(0.5), np.log10(1.6))
        w = rng.dirichlet([1, 1, 1])
        gas.TP = 298.0, P0
        gas.set_equivalence_ratio(phi_p, "CH4", AIR)
        Yp, hp = gas.Y.copy(), gas.enthalpy_mass
        srcs = [(st.Yf, st.hf), (st.Yo, st.ho), (Yp, hp)]
        # start: burnt premixed gas everywhere
        gas.HPY = hp, P0, Yp
        gas.equilibrate("HP")
        Y = np.tile(gas.Y, (n_part, 1)); h = np.full(n_part, gas.enthalpy_mass)
        Ts, Ys = [], []
        for k in range(n_steps):
            n_in = rng.binomial(n_part, min(1.0, dt / tau_res))
            for i in rng.choice(n_part, n_in, replace=False):
                Y[i], h[i] = srcs[rng.choice(3, p=w)]
            n_pairs = rng.binomial(n_part // 2, min(1.0, dt / tau_mix))
            for _ in range(n_pairs):
                i, j = rng.choice(n_part, 2, replace=False)
                a = rng.uniform()
                Ym, hm = 0.5 * (Y[i] + Y[j]), 0.5 * (h[i] + h[j])
                Y[i], Y[j] = (1 - a) * Y[i] + a * Ym, (1 - a) * Y[j] + a * Ym
                h[i], h[j] = (1 - a) * h[i] + a * hm, (1 - a) * h[j] + a * hm
            for i in range(n_part):
                gas.HPY = h[i], P0, Y[i]
                r = ct.IdealGasConstPressureReactor(gas, clone=True)
                net = ct.ReactorNet([r])
                try:
                    net.advance(dt)
                except ct.CanteraError:
                    continue
                Y[i] = r.phase.Y
                if k > n_steps // 3:
                    Ts.append(r.phase.T), Ys.append(Y[i].copy())
        if Ts:
            sel = rng.choice(len(Ts), min(n_keep, len(Ts)), replace=False)
            out.append((np.array(Ts)[sel], np.array(Ys)[sel]))
    return out


def eq_state(gas, st, Z, dh=0.0):
    gas.HPY = Z * st.hf + (1 - Z) * st.ho + dh, P0, st.mix(Z)
    gas.equilibrate("HP")
    return gas.T, gas.Y.copy(), gas.enthalpy_mass


def fam_R5(gas, st, rng, n, n_keep=25):
    out = []
    for _ in range(n):
        Zf, Zp, f = rng.uniform(0.0, 0.2), rng.uniform(0.005, 0.15), rng.uniform(0.0, 0.9)
        _, Yb, hb = eq_state(gas, st, Zp)
        Y = (1 - f) * st.mix(Zf) + f * Yb
        h = (1 - f) * (Zf * st.hf + (1 - Zf) * st.ho) + f * hb
        gas.HPY = h, P0, Y
        out.append(reactor_traj(gas, gas.T, gas.Y, 0.1, n_keep))
    return out


RADICALS = ("H", "O", "OH", "HO2", "H2O2", "CH3", "CH2O")


def fam_R6(gas, st, rng, n, n_keep=15):
    out = []
    for Z in z_samples(rng, n, st.z_st, 0.5):
        T, Y, h = eq_state(gas, st, Z, dh=rng.uniform(-300e3, 50e3))
        Y = Y.copy()
        for s in RADICALS:
            Y[gas.species_index(s)] *= 10 ** rng.uniform(-1, 1)
        Y *= 1 + rng.uniform(-0.03, 0.03, len(Y)) * (Y > 1e-3)
        gas.HPY = h, P0, Y / Y.sum()
        out.append(reactor_traj(gas, gas.T, gas.Y, 0.02, n_keep))
    return out


def _flame_states(fl, gas, n_keep):
    T, Y = fl.T, fl.Y.T
    k = arclength_pick(T, Y[:, [gas.species_index(s) for s in ("CO2", "OH", "CH4")]] * [1, 10, 1], n_keep)
    return T[k], Y[k]


def fam_F1(gas, st, rng, phis=None, Tu=(298.0, 800.0), transports=("mixture-averaged", "unity-Lewis-number"),
           n_keep=60, width=0.03):
    phis = np.linspace(0.5, 1.7, 9) if phis is None else phis
    out = []
    for phi in phis:
        for T in np.atleast_1d(rng.uniform(*Tu)):
            for tr in transports:
                gas.TP = T, P0
                gas.set_equivalence_ratio(phi, "CH4", AIR)
                fl = ct.FreeFlame(gas, width=width)
                fl.transport_model = tr
                fl.set_refine_criteria(ratio=3, slope=0.1, curve=0.2)
                try:
                    fl.solve(loglevel=0, auto=True)
                except ct.CanteraError:
                    continue
                out.append(_flame_states(fl, gas, n_keep) + (tr,))
    return out


def fam_F2(gas, st, rng, T_streams=(298.0, 600.0), transports=("mixture-averaged", "unity-Lewis-number"),
           n_strain=12, n_keep=50, two_point_steps=0, fuel="CH4:1"):
    """Counterflow diffusion flames from low strain to extinction (strain loop); optional two-point control
    continuation past the turning point gives unstable-branch states."""
    out = []
    for Ts in T_streams:
        for tr in transports:
            gas.TP = Ts, P0
            fl = ct.CounterflowDiffusionFlame(gas, width=0.02)
            fl.transport_model = tr
            fl.fuel_inlet.X, fl.fuel_inlet.T = fuel, Ts
            fl.oxidizer_inlet.X, fl.oxidizer_inlet.T = AIR, Ts
            gas.TPX = Ts, P0, fuel; rf = gas.density
            gas.TPX = Ts, P0, AIR; ro = gas.density
            m0 = 0.05
            fl.fuel_inlet.mdot, fl.oxidizer_inlet.mdot = m0, m0 * np.sqrt(ro / rf)
            fl.set_refine_criteria(ratio=4, slope=0.2, curve=0.3, prune=0.03)
            try:
                fl.solve(loglevel=0, auto=True)
            except ct.CanteraError:
                continue
            fac = 1.0
            for k in range(n_strain):
                if fl.T.max() < Ts + 500:
                    break
                out.append(_flame_states(fl, gas, n_keep) + (tr,))
                fac *= 2.0
                fl.fuel_inlet.mdot *= 2.0; fl.oxidizer_inlet.mdot *= 2.0
                try:
                    fl.solve(loglevel=0, auto=False)
                except ct.CanteraError:
                    break
            if two_point_steps:
                try:
                    fl.two_point_control_enabled = True
                    for _ in range(two_point_steps):
                        fl.left_control_point_temperature -= 20.0
                        fl.right_control_point_temperature -= 20.0
                        fl.solve(loglevel=0)
                        if fl.T.max() < Ts + 300:
                            break
                        out.append(_flame_states(fl, gas, n_keep) + (tr + "+2pt",))
                except (ct.CanteraError, AttributeError):
                    pass
    return out


def fam_F3(gas, st, rng, phis=(0.6, 0.8, 1.0, 1.2, 1.5), mdots=(0.2, 0.6, 1.5, 3.0), n_keep=40,
           transports=("mixture-averaged",)):
    out = []
    for phi in phis:
        for tr in transports:
            for md in mdots:
                for kind in ("burnt", "twin"):
                    gas.TP = 298.0, P0
                    gas.set_equivalence_ratio(phi, "CH4", AIR)
                    try:
                        if kind == "burnt":
                            X0 = gas.X.copy()
                            fl = ct.CounterflowPremixedFlame(gas, width=0.02)
                            fl.reactants.mdot = md
                            gas.equilibrate("HP")
                            fl.products.T, fl.products.X = gas.T, gas.X
                            fl.products.mdot = md
                            gas.TPX = 298.0, P0, X0
                        else:
                            fl = ct.CounterflowTwinPremixedFlame(gas, width=0.02)
                            fl.reactants.mdot = md
                        fl.transport_model = tr
                        fl.set_refine_criteria(ratio=3, slope=0.2, curve=0.3, prune=0.03)
                        fl.solve(loglevel=0, auto=True)
                    except ct.CanteraError:
                        continue
                    out.append(_flame_states(fl, gas, n_keep) + (tr,))
    return out


def fam_F4(gas, st, rng, phis_rich=(1.3, 1.8, 2.5, 3.0), phis_lean=(0.5, 0.8), n_strain=6, n_keep=50):
    """Partially premixed counterflow: rich premixed vs air, and lean premixed vs fuel."""
    out = []
    for phi in phis_rich:
        gas.set_equivalence_ratio(phi, "CH4", AIR)
        fuel = {gas.species_name(k): x for k, x in enumerate(gas.X) if x > 0}
        out += fam_F2(gas, st, rng, T_streams=(298.0,), transports=("mixture-averaged",),
                      n_strain=n_strain, n_keep=n_keep, fuel=fuel)
    for phi in phis_lean:
        gas.set_equivalence_ratio(phi, "CH4", AIR)
        lean = ",".join("%s:%g" % (gas.species_name(k), x) for k, x in enumerate(gas.X) if x > 0)
        # lean premixed on the oxidizer side, pure CH4 on the fuel side
        out += _counterflow_custom(gas, "CH4:1", lean, n_strain, n_keep)
    return out


def _counterflow_custom(gas, fuel, ox, n_strain, n_keep):
    out = []
    gas.TP = 298.0, P0
    fl = ct.CounterflowDiffusionFlame(gas, width=0.02)
    fl.fuel_inlet.X, fl.fuel_inlet.T = fuel, 298.0
    fl.oxidizer_inlet.X, fl.oxidizer_inlet.T = ox, 298.0
    fl.fuel_inlet.mdot, fl.oxidizer_inlet.mdot = 0.05, 0.07
    fl.set_refine_criteria(ratio=4, slope=0.2, curve=0.3, prune=0.03)
    try:
        fl.solve(loglevel=0, auto=True)
    except ct.CanteraError:
        return out
    for _ in range(n_strain):
        if fl.T.max() < 800:
            break
        out.append(_flame_states(fl, gas, n_keep) + ("mixture-averaged",))
        fl.fuel_inlet.mdot *= 2.0; fl.oxidizer_inlet.mdot *= 2.0
        try:
            fl.solve(loglevel=0, auto=False)
        except ct.CanteraError:
            break
    return out


def fam_F5(gas, st, rng, f2_flames, n_runs=6, n_keep=40):
    """Unsteady flamelets (tau_q = 0) from F2 steady flamelets mapped to Z: extinction by a strain step up,
    re-ignition / decay at low strain, strain jumps. Uses chemmanifold.unsteady_flamelet."""
    from .unsteady_flamelet import ZFlamelet, run_transient, z_grid
    out = []
    zg = z_grid(41, st.z_st)
    for _ in range(n_runs):
        T, Y = f2_flames[rng.integers(len(f2_flames))][:2]
        gas_Z = np.array([_z_elem(gas, y) for y in Y])
        o = np.argsort(gas_Z)
        Yz = np.array([np.interp(zg, gas_Z[o], Y[o, k]) for k in range(Y.shape[1])]).T
        Yz[0], Yz[-1] = st.Yo, st.Yf
        h = np.array([zz * st.hf + (1 - zz) * st.ho for zz in zg])
        fl = ZFlamelet(gas, zg, Yz, h, P0, T_wall=298.0)
        kind = rng.choice(["extinction", "reignition", "strain"])
        a = {"extinction": 10 ** rng.uniform(3, 4), "reignition": 10 ** rng.uniform(0, 1.5),
             "strain": 10 ** rng.uniform(1, 3)}[kind]
        try:
            snaps, _ = run_transient(gas, fl, kind, a, t_end=0.02, tau_q=0.0)
        except Exception:
            continue
        for t, Ys, hs in snaps[:: max(1, len(snaps) // 8)]:
            Ts = []
            for y, hh in zip(Ys, hs):
                gas.HPY = hh, P0, y
                Ts.append(gas.T)
            out.append((np.array(Ts), Ys.copy()))
    return out


def _z_elem(gas, Y):
    """Bilger mixture fraction of a state (CH4 / air streams)."""
    gas.TPY = 300.0, P0, Y
    return float(np.clip(gas.mixture_fraction("CH4:1", AIR), 0.0, 1.0))


def perturb(gas, T, Y, rng, scale_major=0.03, scale_rad=0.25, dh=65.0):
    """P1: off-manifold perturbation (majors +/-3 %, radicals +/-0.25 decade, enthalpy box +/-dh K equivalent)."""
    Y = Y.copy()
    big = Y > 1e-3
    Y[big] *= 1 + rng.uniform(-scale_major, scale_major, big.sum())
    rad = (Y > 1e-12) & ~big
    Y[rad] *= 10 ** rng.uniform(-scale_rad, scale_rad, rad.sum())
    Y = np.maximum(Y, 0) / Y.sum()
    return T + rng.uniform(-dh, dh), Y


def fam_P1(gas, base, rng, n):
    idx = rng.integers(len(base[0]), size=n)
    out = [perturb(gas, base[0][i], base[1][i], rng) for i in idx]
    return [(np.array([o[0] for o in out]), np.array([o[1] for o in out]))]


def fam_P2(gas, base, rng, n, scales=(0.01, 0.05, 0.2), lam=0.1, eps=1e-10):
    """Multi-scale sampling in Box-Cox space (after Zhang et al. 2022): y' = y (1 + s xi), back-transform."""
    T0, Y0 = base
    out_T, out_Y = [], []
    for i in rng.integers(len(T0), size=n):
        s = scales[rng.integers(len(scales))]
        bc = ((Y0[i] + eps) ** lam - 1) / lam
        bc = bc * (1 + s * rng.standard_normal(len(bc)))
        Y = np.maximum((np.maximum(lam * bc + 1, 0)) ** (1 / lam) - eps, 0.0)
        out_T.append(T0[i] * (1 + s * 0.1 * rng.standard_normal())), out_Y.append(Y / Y.sum())
    return [(np.array(out_T), np.array(out_Y))]


def fam_P3(gas, base, rng, n, t_react=(1e-5, 1e-2), n_keep=8):
    T0, Y0 = base
    out = []
    for _ in range(n):
        i, j = rng.integers(len(T0), size=2)
        a = rng.uniform()
        gas.TPY = T0[i], P0, Y0[i]; hi = gas.enthalpy_mass
        gas.TPY = T0[j], P0, Y0[j]; hj = gas.enthalpy_mass
        Y = a * Y0[i] + (1 - a) * Y0[j]
        gas.HPY = a * hi + (1 - a) * hj, P0, Y
        out.append(reactor_traj(gas, gas.T, gas.Y, 10 ** rng.uniform(*np.log10(t_react)), n_keep))
    return out


def fam_P4(gas, st, rng, n, n_keep=6):
    out = []
    for Z in z_samples(rng, n, st.z_st):
        f = rng.uniform(0, 0.12) if rng.uniform() < 0.5 else 0.0
        _, Yb, _ = eq_state(gas, st, rng.uniform(0.01, 0.1))
        Y = (1 - f) * st.mix(Z) + f * Yb
        out.append(reactor_traj(gas, rng.uniform(298.0, 950.0), Y, 0.05, n_keep))
    return out


# ----------------------------------------------------------------------------------------------- driver

def collect(sets):
    """Concatenate [(T, Y[, tag]), ...] into arrays."""
    T = np.concatenate([s[0] for s in sets]) if sets else np.zeros(0)
    Y = np.concatenate([s[1] for s in sets]) if sets else np.zeros((0, 43))
    return T, Y

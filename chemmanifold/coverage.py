"""Coverage grid, holes and the coverage number C of COVLOOP (docs/COVERAGE-LOOP-ROADMAP.md, section 5).

Every cell state is placed in a bin of a fixed, case-independent grid:
  Z  (Bilger, CH4 / air streams): bin 0 = Z < 1e-3, then log-spaced 1e-3..1 with extra edges around Z_st;
  T  300-2400 K, 100 K bins;
  c  = (Y_CO + Y_CO2) / (Y_CO + Y_CO2 at HP equilibrium of the adiabatic mixture at this Z), 5 bins;
  dh = h - h_mix(Z) in kJ/kg, 3 bins (< -50, -50..50, > 50). A measurement, not a heat-loss model.

A bin is a HOLE when (a) > 5 % of its mass is OOD, (b) > 10 % of its one-step shadow checks fail,
(c) any sentinel (multi-step) check fails, or (d) it has fewer than `min_checks` shadow checks
(unverified). C = trusted reacting mass / reacting mass. C_data uses only (a).
Shadow / sentinel results are comparison data: they decide trust, they are never training data.
"""

import json

import cantera as ct
import numpy as np

from .flame import BilgerZ

DEFAULT_GRID = {
    "z_edges": None,              # built in CoverageGrid from z_st
    "T_edges": list(np.arange(300.0, 2401.0, 100.0)),
    "c_edges": [-np.inf, 0.02, 0.3, 0.7, 0.98, np.inf],
    "dh_edges": [-np.inf, -50.0, 50.0, np.inf],
}


class CoverageGrid:
    def __init__(self, mech, fuel="CH4:1", oxidizer="O2:0.21, N2:0.79", T_fuel=300.0, T_ox=300.0,
                 P=ct.one_atm, grid=None):
        self.gas = ct.Solution(mech)
        g = self.gas
        g.TPX = T_fuel, P, fuel
        self.Yf, self.hf = g.Y.copy(), g.enthalpy_mass
        g.TPX = T_ox, P, oxidizer
        self.Yo, self.ho = g.Y.copy(), g.enthalpy_mass
        self.P = P
        self.bz = BilgerZ(g, self.Yf, self.Yo)
        self.z_st = float(-self.bz.b_o[0] / (self.bz.b_f[0] - self.bz.b_o[0]))
        grid = dict(DEFAULT_GRID, **(grid or {}))
        if grid["z_edges"] is None:
            ze = np.unique(np.concatenate([np.geomspace(1e-3, 1.0, 12), self.z_st * np.array([0.7, 0.9, 1.1, 1.4])]))
            grid["z_edges"] = [-np.inf] + list(ze[:-1]) + [np.inf]
        self.grid = {k: np.asarray(v, float) for k, v in grid.items()}
        self._eq_table()
        self.names = list(g.species_names)

    def _eq_table(self, n=200):
        """Adiabatic-mixing equilibrium Y_CO + Y_CO2 on a Z grid (for the progress variable c)."""
        z = np.concatenate([[0.0], np.geomspace(1e-4, 1.0, n)])
        yc = np.zeros_like(z)
        g, ico, ico2 = self.gas, self.gas.species_index("CO"), self.gas.species_index("CO2")
        for i, zi in enumerate(z):
            Y = zi * self.Yf + (1 - zi) * self.Yo
            h = zi * self.hf + (1 - zi) * self.ho
            g.HPY = h, self.P, Y
            try:
                g.equilibrate("HP")
            except ct.CanteraError:
                pass
            yc[i] = g.Y[ico] + g.Y[ico2]
        self.z_tab, self.yc_tab = z, yc

    def coordinates(self, T, Y, species=None, h=None):
        """(Z, T, c, dh[kJ/kg]) for states given as mass fractions over `species` (default: mechanism order)."""
        Y = np.atleast_2d(np.asarray(Y, float))
        if species is not None and list(species) != self.names:
            full = np.zeros((len(Y), len(self.names)))
            for j, s in enumerate(species):
                full[:, self.names.index(s)] = Y[:, j]
            Y = full
        T = np.asarray(T, float)
        Z = np.clip(self.bz(Y), 0.0, 1.0)
        yc_eq = np.interp(Z, self.z_tab, self.yc_tab)
        c = (Y[:, self.names.index("CO")] + Y[:, self.names.index("CO2")]) / np.maximum(yc_eq, 1e-12)
        if h is None:
            h = np.empty(len(T))
            for i in range(len(T)):
                self.gas.TPY = T[i], self.P, Y[i]
                h[i] = self.gas.enthalpy_mass
        dh = (h - (Z * self.hf + (1 - Z) * self.ho)) / 1e3
        return Z, T, c, dh

    def bin_index(self, Z, T, c, dh):
        g = self.grid
        iz = np.clip(np.searchsorted(g["z_edges"], Z, side="right") - 1, 0, len(g["z_edges"]) - 2)
        it = np.clip(np.searchsorted(g["T_edges"], T, side="right") - 1, 0, len(g["T_edges"]) - 2)
        ic = np.clip(np.searchsorted(g["c_edges"], c, side="right") - 1, 0, len(g["c_edges"]) - 2)
        ih = np.clip(np.searchsorted(g["dh_edges"], dh, side="right") - 1, 0, len(g["dh_edges"]) - 2)
        dims = (len(g["z_edges"]) - 1, len(g["T_edges"]) - 1, len(g["c_edges"]) - 1, len(g["dh_edges"]) - 1)
        return np.ravel_multi_index((iz, it, ic, ih), dims), dims


def reacting_mask(T, c, T_min=450.0):
    return (T > T_min) | ((c > 0.02) & (c < 0.98))


def coverage(cells, shadow=None, sentinel=None, ood_max=0.05, fail_max=0.10, min_checks=6):
    """Coverage of one leg.

    cells:    dict with 'bin' (N,), 'mass' (N,), 'ood' (N, bool), 'reacting' (N, bool)
    shadow:   dict with 'bin' (M,), 'pass' (M, bool) of one-step DI checks (or None)
    sentinel: dict with 'bin', 'pass' of multi-step checks (or None)
    Returns (summary dict, per-bin table dict).
    """
    r = cells["reacting"]
    b, m, ood = cells["bin"][r], cells["mass"][r], cells["ood"][r]
    bins, inv = np.unique(b, return_inverse=True)
    mass = np.bincount(inv, weights=m)
    mass_ood = np.bincount(inv, weights=m * ood)
    f_ood = mass_ood / np.maximum(mass, 1e-300)

    def checks(d):
        n = np.zeros(len(bins)); nf = np.zeros(len(bins))
        if d is not None and len(d["bin"]):
            pos = np.searchsorted(bins, d["bin"])
            ok = (pos < len(bins))
            ok[ok] = bins[pos[ok]] == d["bin"][ok]
            np.add.at(n, pos[ok], 1)
            np.add.at(nf, pos[ok], ~d["pass"][ok])
        return n, nf

    n_sh, nf_sh = checks(shadow)
    n_se, nf_se = checks(sentinel)
    hole_ood = f_ood > ood_max
    hole_shadow = nf_sh > fail_max * np.maximum(n_sh, 1)
    hole_sent = nf_se > 0
    unverified = n_sh < min_checks
    in_dist = ~hole_ood
    trusted = in_dist & ~hole_shadow & ~hole_sent & ~unverified
    tot = mass.sum()
    summary = {"C": float(mass[trusted].sum() / tot), "C_data": float(mass[in_dist].sum() / tot),
               "mass_ood": float(mass[hole_ood].sum() / tot), "mass_shadow_fail": float(mass[hole_shadow].sum() / tot),
               "mass_sentinel_fail": float(mass[hole_sent].sum() / tot),
               "mass_unverified": float(mass[unverified & ~hole_ood & ~hole_shadow & ~hole_sent].sum() / tot),
               "n_bins_visited": int(len(bins)), "n_holes": int((~trusted).sum())}
    table = {"bin": bins, "mass_share": mass / tot, "f_ood": f_ood, "n_shadow": n_sh, "n_shadow_fail": nf_sh,
             "n_sentinel": n_se, "n_sentinel_fail": nf_se, "trusted": trusted, "hole_ood": hole_ood,
             "hole_shadow": hole_shadow, "hole_sentinel": hole_sent, "unverified": unverified}
    return summary, table


def headline(legs):
    """Headline C of an iteration: mean over legs within a case, then mean of the two cases (weights 1/2)."""
    by_case = {}
    for (case, _leg), s in legs.items():
        by_case.setdefault(case, []).append(s["C"])
    return float(np.mean([np.mean(v) for v in by_case.values()]))


def plateau(history, spread=0.0, min_gain=0.01, patience=2, target=0.98, max_iter=8):
    """Stop rule of section 8: True when the last `patience` iterations each failed to beat the best by
    max(min_gain, 2 * spread), or the target is reached, or max_iter iterations were run."""
    if not history:
        return False
    if history[-1] >= target or len(history) - 1 >= max_iter:
        return True
    thr = max(min_gain, 2.0 * spread)
    best, misses = history[0], 0
    for c in history[1:]:
        if c > best + thr:
            best, misses = c, 0
        else:
            misses += 1
    return misses >= patience


def save_table(path, table, dims):
    idx = np.array(np.unravel_index(table["bin"], dims)).T
    cols = [k for k in table if k != "bin"]
    with open(path, "w") as f:
        f.write("iz,iT,ic,idh," + ",".join(cols) + "\n")
        order = np.argsort(-table["mass_share"])
        for i in order:
            f.write(",".join(str(v) for v in idx[i]) + "," + ",".join(
                ("%d" % table[k][i]) if table[k].dtype == bool else ("%.6g" % table[k][i]) for k in cols) + "\n")


def save_summary(path, summary):
    with open(path, "w") as f:
        json.dump(summary, f, indent=1)

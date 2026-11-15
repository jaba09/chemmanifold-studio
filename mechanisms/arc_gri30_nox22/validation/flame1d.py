#!/usr/bin/env python3
"""Laminar flame speed of ARC_GRI30_NOx22 vs the 43-species skeletal set and GRI-Mech 3.0.

Cantera cannot run a mechanism with quasi-steady species, so the ARC flame speed comes from
a small 1D solver of our own: an unsteady premixed flame in the mass coordinate psi
(d psi = rho dx), closed ends, constant pressure, so the flame moves through psi at
d psi_f/dt = rho_u S_L. Transport is the OpenFOAM case's (constant Lewis numbers, the same
Le as the burner; lambda(T) fitted to the Cantera GRI flame), so both mechanisms run with
identical transport:
    dY_k/dt = -d j_k/dpsi + w_k W_k/rho,    j_k = -(rho lambda/(cp Le_k)) dY_k/dpsi + Y_k j_c
    cp dT/dt = d/dpsi(rho lambda dT/dpsi) - sum_k j_k cp_k dT/dpsi + (chemistry)
The chemistry (and its dT/dt) is the C core: ARC (22 species + QSSA) or skeletal43 (all 43).
Reference: Cantera FreeFlame, mixture-averaged, GRI-Mech 3.0 and skeletal43.
Usage: python3 flame1d.py [phi ...]       (default 0.7 1.0 1.3), writes flame1d.csv
"""
import os, sys, time
import numpy as np, cantera as ct
from scipy.integrate import solve_ivp
from scipy.sparse import kron, diags, csr_matrix
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import arcpy
import ctypes
MECH = os.path.join(HERE, "..", "gri30_skel43.yaml")
AIR = "O2:0.21, N2:0.79"; P = ct.one_atm; TU = 300.0
LE = dict(H2=0.309, H=0.185, O=0.712, O2=1.084, OH=0.729, H2O=0.816, HO2=1.086, H2O2=1.081,
          CH3=1.014, CH4=0.870, CO=1.120, CO2=1.370, CH2O=1.290, N2=1.151, CH3OH=1.332, C2H2=1.338,
          C2H4=1.346, C2H6=1.454, NO=1.126, NO2=1.221, N2O=1.367, HCN=1.298,
          CH2=0.995, HCO=1.281, CH3O=1.323)  # CH2(S) 0.995 too; other radicals 1
LE["CH2(S)"] = 0.995
lib = arcpy._lib
D = ctypes.POINTER(ctypes.c_double)


def cantera_SL(mech, phi):
    g = ct.Solution(mech); g.set_equivalence_ratio(phi, "CH4", AIR); g.TP = TU, P
    f = ct.FreeFlame(g, width=0.03); f.set_refine_criteria(ratio=3, slope=0.06, curve=0.12)
    f.transport_model = "mixture-averaged"; f.solve(loglevel=0, auto=True)
    return f.velocity[0], f


def lam_fit(flame):
    T = flame.T; lam = flame.thermal_conductivity
    b, a = np.polyfit(np.log(T), np.log(lam), 1)
    return lambda TT: np.exp(a) * TT ** b


class Model:
    def __init__(self, kind, phi, lam, N=1200, psiL=0.008):
        self.kind = kind
        names = arcpy.names[:22] if kind == "arc" else arcpy.names
        self.names = names; self.ns = len(names); self.nv = self.ns + 1
        self.W = arcpy.W[:self.ns]
        self.Le = np.array([LE.get(n, 1.0) for n in names])
        g = ct.Solution("gri30.yaml")
        self.nasa = np.array([g.species(n).thermo.coeffs for n in names])
        self.lam = lam; self.N = N; self.dpsi = psiL / (N - 1)
        self.psi = np.linspace(0, psiL, N)
        g.set_equivalence_ratio(phi, "CH4", AIR); g.TP = TU, P
        self.rho_u = g.density
        Yu = np.array([g[n].Y[0] for n in names]); Yu /= Yu.sum()
        g.equilibrate("HP"); Yb = np.array([g[n].Y[0] for n in names]); Yb /= Yb.sum(); Tb = g.T
        self.Tb = Tb
        s = 0.5 * (1 + np.tanh((self.psi - 0.0015) / 1.5e-4))  # 0 burnt -> 1 unburnt
        Y = Yb[None, :] * (1 - s[:, None]) + Yu[None, :] * s[:, None]
        T = Tb * (1 - s) + TU * s
        self.y0 = np.hstack([Y, T[:, None]]).ravel()
        self.fn = lib.arc_rhs_many if kind == "arc" else lib.arc_rhs_skeletal_many
        self.fn.argtypes = [ctypes.c_double, ctypes.c_int, D, D]

    def cp_k(self, T):  # J/kg/K per species, (N, ns)
        lo = T[:, None] <= self.nasa[None, :, 0]
        a = np.where(lo[..., None], self.nasa[None, :, 8:15], self.nasa[None, :, 1:8])
        TT = T[:, None]
        cpR = a[..., 0] + a[..., 1] * TT + a[..., 2] * TT**2 + a[..., 3] * TT**3 + a[..., 4] * TT**4
        return cpR * 8314.462618 / self.W[None, :]

    def rhs(self, t, y):
        N, nv, ns = self.N, self.nv, self.ns
        y = np.ascontiguousarray(y)
        d = np.empty_like(y)
        self.fn(P, N, y.ctypes.data_as(D), d.ctypes.data_as(D))
        Y = y.reshape(N, nv)[:, :ns]; T = y.reshape(N, nv)[:, ns]
        sYW = (Y / self.W).sum(1); rho = P / (8314.462618 * T * sYW)
        cpk = self.cp_k(T); cp = (Y * cpk).sum(1); lam = self.lam(T)
        # face values
        rf = 0.5 * (rho[1:] + rho[:-1]); lf = 0.5 * (lam[1:] + lam[:-1]); cf = 0.5 * (cp[1:] + cp[:-1])
        Yf = 0.5 * (Y[1:] + Y[:-1])
        dY = (Y[1:] - Y[:-1]) / self.dpsi; dT = (T[1:] - T[:-1]) / self.dpsi
        j = -(rf * lf / cf)[:, None] / self.Le[None, :] * dY
        j = j - Yf * j.sum(1)[:, None]
        qT = rf * lf * dT
        J = np.zeros((N + 1, ns)); J[1:-1] = j
        Q = np.zeros(N + 1); Q[1:-1] = qT
        dYdt = -(J[1:] - J[:-1]) / self.dpsi
        # sum_k j_k cp_k dT/dpsi at nodes (average of faces)
        jc = np.zeros((N + 1)); jc[1:-1] = (j * 0.5 * (cpk[1:] + cpk[:-1])).sum(1) * dT
        enth = 0.5 * (jc[1:] + jc[:-1])
        dTdt = ((Q[1:] - Q[:-1]) / self.dpsi - enth) / cp
        dd = d.reshape(N, nv)
        dd[:, :ns] += dYdt; dd[:, ns] += dTdt
        return d

    def sparsity(self):
        blk = np.ones((self.nv, self.nv))
        band = diags([1, 1, 1], [-1, 0, 1], shape=(self.N, self.N))
        return csr_matrix(kron(band, blk))

    def front(self, y):
        T = y.reshape(self.N, self.nv)[:, self.ns]
        Tm = 0.5 * (TU + self.Tb)
        i = np.argmax(T < Tm)  # first node below Tm from the burnt end
        return self.psi[i - 1] + (Tm - T[i - 1]) / (T[i] - T[i - 1]) * self.dpsi

    def run(self, tend=6e-3, nout=25):
        ts = np.linspace(0, tend, nout + 1)
        t0 = time.time()
        sol = solve_ivp(self.rhs, (0, tend), self.y0, method="BDF", t_eval=ts, rtol=1e-5, atol=1e-10,
                        jac_sparsity=self.sparsity())
        fr = np.array([self.front(sol.y[:, k]) for k in range(sol.y.shape[1])])
        v = np.gradient(fr, sol.t) / self.rho_u
        return sol.t, fr, v, time.time() - t0, sol


def main():
    phis = [float(a) for a in sys.argv[1:]] or [0.7, 1.0, 1.3]
    rows = []
    for phi in phis:
        SLg, fg = cantera_SL("gri30.yaml", phi)
        SLs, _ = cantera_SL(MECH, phi)
        lam = lam_fit(fg)
        res = {}
        for kind in ("skel", "arc"):
            m = Model(kind, phi, lam)
            t, fr, v, wall, sol = m.run()
            late = v[len(v) // 2:]
            res[kind] = (late.mean(), late.std())
            print("phi %.2f %-4s S_L history (cm/s):" % (phi, kind),
                  " ".join("%.1f" % (100 * x) for x in v[::3]), " wall %.0f s" % wall, flush=True)
        r = (phi, SLg, SLs, res["skel"][0], res["arc"][0], res["arc"][1])
        rows.append(r)
        print("phi %.2f  Cantera GRI %.2f  skel43 %.2f cm/s (%.2f %%) | own solver: skel43 %.2f  ARC %.2f cm/s "
              "(ARC vs skel %.2f %%, +-%.2f)" % (phi, 100 * SLg, 100 * SLs, 100 * (SLs / SLg - 1), 100 * r[3],
              100 * r[4], 100 * (r[4] / r[3] - 1), 100 * r[5]), flush=True)
    np.savetxt(os.path.join(HERE, "flame1d_%s.csv" % "_".join(sys.argv[1:])), np.array(rows), delimiter=",", comments="",
               header="phi,SL_cantera_GRI,SL_cantera_skel43,SL_own_skel43,SL_own_ARC,SL_own_ARC_std")


if __name__ == "__main__":
    main()

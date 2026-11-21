#!/usr/bin/env python3
"""0D constant-pressure ignition: ARC_GRI30_NOx22 (C core) vs GRI-Mech 3.0 and
the 43-species skeletal set (Cantera). Ignition delay = time of max dT/dt.
Writes validation/ignition.csv and prints a summary."""
import os, sys, time
import numpy as np, cantera as ct
from scipy.integrate import solve_ivp
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import arcpy
MECH = os.path.join(HERE, "..", "gri30_skel43.yaml")
AIR = "O2:0.21, N2:0.79"

def cantera_run(mech, T0, P, phi, tend):
    g = ct.Solution(mech); g.set_equivalence_ratio(phi, "CH4", AIR); g.TP = T0, P
    r = ct.IdealGasConstPressureReactor(g, clone=False); net = ct.ReactorNet([r])
    net.rtol, net.atol = 1e-9, 1e-15
    t, T, NO, CO = [0.0], [T0], [0.0], [0.0]
    while net.time < tend:
        net.step(); t.append(net.time); T.append(r.T)
        NO.append(g["NO"].X[0]); CO.append(g["CO"].X[0])
    return np.array(t), np.array(T), np.array(NO), np.array(CO)

def arc_run(T0, P, phi, tend):
    g = ct.Solution("gri30.yaml"); g.set_equivalence_ratio(phi, "CH4", AIR); g.TP = T0, P
    Y0 = np.array([g[n].Y[0] for n in arcpy.names[:22]])
    y0 = np.append(Y0, T0)
    sol = solve_ivp(lambda t, y: arcpy.rhs(P, y), (0, tend), y0, method="BDF",
                    rtol=1e-8, atol=1e-14, dense_output=False)
    Y = sol.y[:22]; T = sol.y[22]
    Wm = 1 / np.sum(Y / arcpy.W[:22, None], axis=0)
    X = Y * Wm / arcpy.W[:22, None]
    iNO, iCO = arcpy.names.index("NO"), arcpy.names.index("CO")
    el0 = arcpy.elements(Y0); el1 = arcpy.elements(Y[:, -1])
    return sol.t, T, X[iNO], X[iCO], np.max(np.abs(el1 - el0) / np.maximum(el0, 1e-30))

def tign(t, T):
    d = np.diff(T) / np.maximum(np.diff(t), 1e-30); return t[np.argmax(d)]

def at(t, v, tq): return np.interp(tq, t, v)

rows = []
cases = [(T0, 1.0, phi) for T0 in (1000, 1200, 1400, 1600) for phi in (0.5, 1.0, 2.0)]
cases += [(T0, 5.0, phi) for T0 in (1100, 1400) for phi in (0.5, 1.0, 2.0)]
print("%6s %4s %4s | %10s %10s %10s | %7s %7s | %7s %7s %7s | %8s %8s %6s" % (
    "T0", "atm", "phi", "tau_GRI", "tau_skel", "tau_ARC", "err_sk%", "err_A%",
    "Tf_GRI", "dTf_A", "maxT_er", "NO_GRI", "NO_ARC", "elem"))
for T0, atm, phi in cases:
    P = atm * ct.one_atm
    tg, Tg, NOg, COg = cantera_run("gri30.yaml", T0, P, phi, 0.5)
    tau = tign(tg, Tg); tend = tau + 3e-3
    tg, Tg, NOg, COg = cantera_run("gri30.yaml", T0, P, phi, tend)
    ts, Ts, _, _ = cantera_run(MECH, T0, P, phi, tend)
    t0 = time.time(); ta, Ta, NOa, COa, el = arc_run(T0, P, phi, tend); ct_ = time.time() - t0
    taug, taus, taua = tign(tg, Tg), tign(ts, Ts), tign(ta, Ta)
    grid = np.linspace(0, tend, 4000)
    # temperature error in time (shifted by nothing): max |T_ARC - T_GRI| after ignition hold
    Tf_g, Tf_a = Tg[-1], at(ta, Ta, tend)
    NOf_g, NOf_a = NOg[-1], at(ta, NOa, tend)
    post = grid[grid > max(taug, taua) + 2e-4]
    maxTerr = np.max(np.abs(at(ta, Ta, post) - at(tg, Tg, post))) if len(post) else np.nan
    rows.append((T0, atm, phi, taug, taus, taua, Tf_g, Tf_a, NOf_g, NOf_a, maxTerr, el))
    print("%6d %4.0f %4.1f | %10.3e %10.3e %10.3e | %7.2f %7.2f | %7.1f %7.2f %7.2f | %8.2e %8.2e %6.0e" % (
        T0, atm, phi, taug, taus, taua, 100 * (taus / taug - 1), 100 * (taua / taug - 1),
        Tf_g, Tf_a - Tf_g, maxTerr, NOf_g, NOf_a, el), flush=True)
np.savetxt(os.path.join(HERE, "ignition.csv"), np.array(rows), delimiter=",",
           header="T0,atm,phi,tau_GRI,tau_skel43,tau_ARC,Tend_GRI,Tend_ARC,XNO_end_GRI,XNO_end_ARC,maxTerr_post,elem_drift_rel", comments="")

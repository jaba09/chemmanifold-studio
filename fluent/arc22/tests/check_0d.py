"""Offline checks of the Fluent ARC22 chemistry step (no Fluent needed; needs Cantera >= 3.0):

  python fluent/arc22/tests/check_0d.py

1. ignition at constant pressure, the cell advanced in Fluent-like calls of dt = 10 us (transient run)
   vs Cantera GRI-Mech 3.0 (gri30.yaml) with tight tolerances: ignition delay, final T, NO;
2. single long calls (dt = 1 ms ... 0.2 s, what a steady run passes) vs the same reference;
3. element conservation and enthalpy conservation of every call, and the cost per call.
"""
import sys, time, pathlib
import numpy as np
import cantera as ct

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from arc22py import ARC22

P = ct.one_atm
arc = ARC22()
gri = ct.Solution("gri30.yaml")
idx = [gri.species_index(n) for n in arc.names]


def mix(phi, T):
    gri.TP = T, P
    gri.set_equivalence_ratio(phi, "CH4", "O2:0.21, N2:0.79")
    return gri.Y[idx] / gri.Y[idx].sum()


def cantera_run(phi, T0, times):
    gri.TP = T0, P
    gri.set_equivalence_ratio(phi, "CH4", "O2:0.21, N2:0.79")
    r = ct.IdealGasConstPressureReactor(gri, energy="on", clone=False)
    net = ct.ReactorNet([r]); net.rtol, net.atol = 1e-9, 1e-15
    out = []
    for t in times:
        net.advance(t)
        out.append((r.T, r.phase.Y[gri.species_index("NO")], r.phase.Y[gri.species_index("CO")]))
    return np.array(out)


def tau(times, T, T0):
    """time of maximum dT/dt; None if the mixture did not ignite (T rose < 400 K)"""
    return times[np.argmax(np.gradient(T, times))] if T[-1] - T0 > 400 else float("nan")


lines = ["# ARC22 Fluent chemistry step: offline checks vs GRI-Mech 3.0 (Cantera)", ""]
lines += ["## 1. Ignition with 10 us calls (as in a transient run)", "",
          "| phi | T0 [K] | tau ARC [ms] | tau GRI [ms] | diff | T end ARC/GRI [K] | NO end ARC/GRI [ppm mass] | max elem fix | us/call |",
          "|---|---|---|---|---|---|---|---|---|"]
dt = 1e-5
worst_tau = 0
for phi, T0, tend in [(0.6, 1300, 0.012), (1.0, 1250, 0.08), (1.0, 1400, 0.006), (2.0, 1300, 0.03),
                      (1.5, 1500, 0.006), (0.5, 1600, 0.004)]:
    n = int(round(tend / dt))
    times = dt * np.arange(1, n + 1)
    Y = mix(phi, T0); T = T0; h0 = arc.h_mass(Y, T0)
    Ts, NOs, fix, t_cpu = [], [], 0.0, 0.0
    for i in range(n):
        c0 = time.perf_counter()
        Y, info = arc.advance(Y, T, P, dt)
        t_cpu += time.perf_counter() - c0
        assert info.status in (0, 2), info.status
        # Fluent recomputes T from the conserved enthalpy: do the same (Newton on h(Y,T) = h0)
        T = info.T_out
        for _ in range(5):
            gri.TPY = T, P, {n_: y for n_, y in zip(arc.names, Y)}
            T -= (gri.enthalpy_mass - h0) / gri.cp_mass
        Ts.append(T); NOs.append(Y[arc.names.index("NO")]); fix = max(fix, info.elem_fix)
    ref = cantera_run(phi, T0, times)
    ta, tg = tau(times, np.array(Ts), T0), tau(times, ref[:, 0], T0)
    worst_tau = max(worst_tau, abs(ta / tg - 1))
    lines.append(f"| {phi} | {T0} | {ta*1e3:.3f} | {tg*1e3:.3f} | {100*(ta/tg-1):+.2f} % | {Ts[-1]:.1f} / {ref[-1,0]:.1f} | "
                 f"{NOs[-1]*1e6:.1f} / {ref[-1,1]*1e6:.1f} | {fix:.1e} | {1e6*t_cpu/n:.0f} |")

lines += ["", "## 2. One long call (as in a steady run's pseudo time step)", "",
          "| phi | T0 [K] | dt [s] | T after ARC / GRI [K] | NO ARC / GRI [ppm] | CO ARC / GRI | steps | rejects | ms/call |",
          "|---|---|---|---|---|---|---|---|---|"]
for phi, T0 in [(1.0, 1500), (0.7, 1800), (1.6, 1700), (1.0, 900)]:
    for dtl in [1e-3, 1e-2, 0.2]:
        Y = mix(phi, T0)
        c0 = time.perf_counter(); Y2, info = arc.advance(Y, T0, P, dtl); c1 = time.perf_counter()
        ref = cantera_run(phi, T0, [dtl])[0]
        lines.append(f"| {phi} | {T0} | {dtl:g} | {info.T_out:.1f} / {ref[0]:.1f} | {Y2[arc.names.index('NO')]*1e6:.1f} / {ref[1]*1e6:.1f} | "
                     f"{Y2[arc.names.index('CO')]:.4f} / {ref[2]:.4f} | {info.n_steps} | {info.n_reject} | {1e3*(c1-c0):.2f} |")

lines += ["", "## 3. Cold cells", ""]
for name, Y in [("pure CH4 300 K", np.eye(22)[arc.names.index("CH4")]), ("air 300 K", mix(0.0, 300)),
                ("phi 1 mix 300 K", mix(1.0, 300)), ("phi 1 mix 450 K", mix(1.0, 450))]:
    c0 = time.perf_counter()
    for _ in range(200): Y2, info = arc.advance(Y, float(name.split()[-2]), P, 0.1)
    c1 = time.perf_counter()
    lines.append(f"- {name}, dt 0.1 s: status {info.status} (2 = quiet explicit), max |dY| {np.abs(Y2-Y).max():.1e}, {1e6*(c1-c0)/200:.0f} us/call")

text = "\n".join(lines) + "\n"
print(text)
out = pathlib.Path(__file__).resolve().parent / "CHECKS.md"
out.write_text(text)
print("max ignition delay difference vs GRI-Mech 3.0: %.2f %%" % (100 * worst_tau))

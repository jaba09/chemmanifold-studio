#!/usr/bin/env python3
"""Stage 19: flow statistics of a burner solution, for flow-informed exploration (timescale roadmap).

From one solution (OpenFOAM case at a given time, or a Fluent ASCII cell export) this computes, per cell,

  Z         Bilger mixture fraction (C, H, O of whatever species the solution carries)
  theta     (T - T_mix) / (T_eq(Z) - T_mix), T_ad = Burke-Schumann adiabatic temperature at Z
  psi       heat-loss fraction: 0 = adiabatic mixing enthalpy at Z, 1 = same composition at T_wall (<0 = excess)
  chi       scalar dissipation 2 D_eff |grad Z|^2, D_eff = D_lam(T) + alphat / rho   [1/s]
  strain    sqrt(2 S:S), S = sym(grad U)                                           [1/s]
  age       mean gas age (OpenFOAM `age` function object)                          [s]
  tau_conv  dx / |U|, tau_diff = dx^2 / D_eff, tau_cell = 0.1 min(tau_conv, tau_diff)  [s]
            (Fluent's chemistry time scale; dx = in-plane cell size, wedge: sqrt(V / (r theta_w)))

and writes mass-weighted statistics of the reacting cells (T > --T-min), overall and conditioned on Z bands:

  <out>/<label>/cells.npz     per-cell values (all cells) - flow statistics only
  <out>/<label>/stats.json    percentiles (1, 5, 25, 50, 75, 95, 99, 99.5) per quantity and per Z band,
                              log10(tau_cell) histogram
  <out>/<label>/stats.png     conditional plots

Only these flow and heat-loss statistics are passed on (stage 20 turns them into exploration settings).
No thermochemical state of a CFD solution is ever used as training data.

A Fluent export without velocities gives only the thermochemical quantities (Z, theta, psi).

  python scripts/19_flow_statistics.py case  <case dir> --time 4250 --label wd2   [--out data/timescale]
  python scripts/19_flow_statistics.py fluent <export.csv> --label fluent_di
  python scripts/19_flow_statistics.py compare --ref di_lts --labels wd2 ws1      (step 3 gate)
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "openfoam" / "tools"))

W_EL = {"C": 12.011, "H": 1.008, "O": 15.999, "N": 14.007}
P0 = 101325.0
T_STREAM = 300.0
T_WALL = 300.0
FUEL = {"CH4": 1.0}
AIR = {"O2": 0.233, "N2": 0.767}            # O2 0.21 by mole, as in the Fluent case
Z_EDGES = np.array([0.0, 0.01, 0.02, 0.035, 0.045, 0.065, 0.08, 0.12, 0.2, 0.4, 1.0001])
Z_ST = (0.045, 0.065)                       # band around Z_st = 0.055
PCTS = [1, 5, 25, 50, 75, 95, 99, 99.5]
QUANT = ["chi", "strain", "age", "psi", "theta", "tau_conv", "tau_diff", "tau_cell"]
WEDGE_DEG = 5.0


# ----------------------------------------------------------------------------------- thermo helpers
def gas():
    import cantera as ct
    return ct.Solution(str(REPO / "mechanisms" / "ga18.yaml"))


def comp_of_species(g, name):
    """element counts (C, H, O) of a species (any capitalisation, Fluent's ch2<s> too)."""
    n = name.upper().replace("<", "(").replace(">", ")")
    k = g.species_index(n)
    return np.array([g.n_atoms(k, e) for e in ("C", "H", "O")]), g.molecular_weights[k], n


def bilger(g, Y):
    """Y: dict GA18-name -> array."""
    # beta = 2 Z_C/W_C + Z_H/(2 W_H) - Z_O/W_O, Z_e/W_e = sum_k Y_k a_ek / W_k
    def beta(comp):
        out = 0.0
        for s, y in comp.items():
            e, w, _ = comp_of_species(g, s)
            out = out + y * (2 * e[0] + 0.5 * e[1] - e[2]) / w
        return out
    bf, bo = beta(FUEL), beta(AIR)
    return (beta(Y) - bo) / (bf - bo)


def stream_enthalpies(g):
    g.TPY = T_STREAM, P0, FUEL
    hf = g.enthalpy_mass
    g.TPY = T_STREAM, P0, AIR
    ho = g.enthalpy_mass
    return hf, ho


def equilibrium_table(g, n=201):
    """Burke-Schumann adiabatic temperature vs Z: complete combustion of the limiting reactant to
    CO2 + H2O at the mixing enthalpy (no dissociation). Full equilibrium is not used because on the
    rich side it drops to ~1000 K (CH4 + CO2 + H2O), far below any flame state."""
    zs = np.linspace(0, 1, n)
    hf, ho = stream_enthalpies(g)
    W = {s: g.molecular_weights[g.species_index(s)] for s in ("CH4", "O2", "N2", "CO2", "H2O")}
    Teq = np.empty(n)
    for i, z in enumerate(zs):
        nf = z * FUEL["CH4"] / W["CH4"]
        no = (1 - z) * AIR["O2"] / W["O2"]
        burnt = min(nf, no / 2)
        mol = {"CH4": nf - burnt, "O2": no - 2 * burnt, "CO2": burnt, "H2O": 2 * burnt,
               "N2": (1 - z) * AIR["N2"] / W["N2"]}
        Y = {s: m * W[s] for s, m in mol.items()}
        g.HPY = z * hf + (1 - z) * ho, P0, Y
        Teq[i] = g.T
    return zs, Teq


def thermo_coordinates(g, Y, T, Z):
    """theta and psi for every cell."""
    import cantera as ct
    names = list(Y)
    idx = [g.species_index(s) for s in names]
    Ym = np.zeros((len(T), g.n_species))
    for s, i in zip(names, idx):
        Ym[:, i] = Y[s]
    Ym = np.clip(Ym, 0, 1)
    Ym /= np.maximum(Ym.sum(1, keepdims=True), 1e-12)
    arr = ct.SolutionArray(g, len(T))
    arr.TPY = np.clip(T, 200, 3400), P0, Ym
    h = arr.enthalpy_mass.copy()
    arr.TPY = T_WALL, P0, Ym
    h_wall = arr.enthalpy_mass.copy()
    hf, ho = stream_enthalpies(g)
    h_mix = Z * hf + (1 - Z) * ho
    psi = (h_mix - h) / np.maximum(h_mix - h_wall, 1.0)
    zs, Teq = equilibrium_table(g)
    Te = np.interp(np.clip(Z, 0, 1), zs, Teq)
    theta = (T - T_STREAM) / np.maximum(Te - T_STREAM, 1.0)
    return theta, psi


def d_lam(T):
    """laminar diffusivity, unity Lewis as in the OpenFOAM case (same fit as foam_snapshot.py)."""
    return 2.2e-5 * (np.maximum(T, 200) / 300.0) ** 1.7


# ----------------------------------------------------------------------------------- readers
def run(cmd, cwd, log):
    with open(Path(cwd) / log, "w") as f:
        subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, check=True)


def from_openfoam(case, tname, work):
    from foam_snapshot import prepare_pp, read_field, write_scalar
    case = Path(case).resolve()
    if (case / "processor0").exists() and not (case / tname / "T").exists():
        run(["reconstructPar", "-time", tname], case, "log.reconstruct_19")
    pp = Path(work)
    prepare_pp(case, pp)
    dst = pp / tname
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(case / tname, dst)
    run(["foamFormatConvert", "-time", tname], pp, "log.convert")
    C = read_field(pp / "0" / "C", 0)
    n = len(C)
    V = read_field(pp / "0" / "V", n)
    T = read_field(dst / "T", n)
    p = read_field(dst / "p", n)
    U = read_field(dst / "U", n)
    alphat = read_field(dst / "alphat", n) if (dst / "alphat").exists() else np.zeros(n)
    age = read_field(dst / "age", n) if (dst / "age").exists() else np.full(n, np.nan)
    g = gas()
    Y = {}
    for f in dst.iterdir():
        try:
            k = g.species_index(f.name)
        except Exception:
            continue
        Y[g.species_name(k)] = read_field(f, n)
    Z = bilger(g, Y)
    write_scalar(dst / "Zmix", "Zmix", Z)
    run(["postProcess", "-func", "grad(Zmix)", "-time", tname], pp, "log.gradZ")
    run(["postProcess", "-func", "grad(U)", "-time", tname], pp, "log.gradU")
    gZ = read_field(dst / "grad(Zmix)", n)
    G = read_field(dst / "grad(U)", n).reshape(n, 3, 3)
    # density from the ideal gas law with the cell's mean molar mass
    W = np.zeros(n)
    for s, y in Y.items():
        W += y / g.molecular_weights[g.species_index(s)]
    W = 1.0 / np.maximum(W, 1e-12)
    rho = p * W / (8314.46 * T)
    S = 0.5 * (G + G.transpose(0, 2, 1))
    r = np.hypot(C[:, 1], C[:, 2])
    dx = np.sqrt(V / np.maximum(r * np.radians(WEDGE_DEG), 1e-12))
    out = dict(x=C[:, 0], r=r, V=V, T=T, rho=rho, Umag=np.linalg.norm(U, axis=1), alphat=alphat, age=age,
               strain=np.sqrt(2 * (S * S).sum((1, 2))), gradZ2=(gZ ** 2).sum(1), dx=dx, Z=Z)
    out["Deff"] = d_lam(T) + alphat / rho
    out["chi"] = 2 * out["Deff"] * out["gradZ2"]
    out["tau_conv"] = dx / np.maximum(out["Umag"], 1e-9)
    out["tau_diff"] = dx ** 2 / out["Deff"]
    out["tau_cell"] = 0.1 * np.minimum(out["tau_conv"], out["tau_diff"])
    out["theta"], out["psi"] = thermo_coordinates(g, Y, T, Z)
    shutil.rmtree(dst)
    return out


def from_fluent(path):
    import pandas as pd
    d = pd.read_csv(path, skipinitialspace=True)
    d.columns = [c.strip() for c in d.columns]
    g = gas()
    Y = {}
    for c in d.columns:
        try:
            k = g.species_index(c.upper().replace("<", "(").replace(">", ")"))
        except Exception:
            continue
        Y[g.species_name(k)] = d[c].values
    T = d["temperature"].values
    Z = bilger(g, Y)
    out = dict(x=d["axial-coordinate"].values if "axial-coordinate" in d else d["x-coordinate"].values,
               r=d["radial-coordinate"].values if "radial-coordinate" in d else d["y-coordinate"].values,
               V=d["cell-volume"].values, T=T, rho=d["density"].values, Z=Z)
    out["theta"], out["psi"] = thermo_coordinates(g, Y, T, Z)
    for q in ("chi", "strain", "age", "tau_conv", "tau_diff", "tau_cell"):
        out[q] = np.full(len(T), np.nan)
    return out


# ----------------------------------------------------------------------------------- statistics
def wpct(x, w, pcts):
    ok = np.isfinite(x) & (w > 0)
    if ok.sum() < 5:
        return None
    x, w = x[ok], w[ok]
    o = np.argsort(x)
    cw = np.cumsum(w[o])
    cw /= cw[-1]
    return [float(np.interp(p / 100.0, cw, x[o])) for p in pcts]


def statistics(c, T_min):
    w = c["rho"] * c["V"]
    hot = c["T"] > T_min
    st = dict(T_min=T_min, n_cells=int(len(c["T"])), n_hot=int(hot.sum()), T_max=float(np.max(c["T"])),
              pcts=PCTS, overall={}, z_st={}, by_z={}, z_edges=Z_EDGES.tolist())
    zst = hot & (c["Z"] >= Z_ST[0]) & (c["Z"] < Z_ST[1])
    for q in QUANT:
        st["overall"][q] = wpct(c[q][hot], w[hot], PCTS)
        st["z_st"][q] = wpct(c[q][zst], w[zst], PCTS)
    for i in range(len(Z_EDGES) - 1):
        m = hot & (c["Z"] >= Z_EDGES[i]) & (c["Z"] < Z_EDGES[i + 1])
        st["by_z"][f"{Z_EDGES[i]:.3f}-{min(Z_EDGES[i + 1], 1):.3f}"] = dict(
            mass_share=float(w[m].sum() / max(w[hot].sum(), 1e-30)), n=int(m.sum()),
            **{q: wpct(c[q][m], w[m], PCTS) for q in QUANT})
    # tau_cell histogram (log10 bins of 0.1 from 1e-8 to 1 s), hot cells, mass weighted
    edges = np.arange(-8, 0.05, 0.1)
    tc = c["tau_cell"][hot]
    ok = np.isfinite(tc) & (tc > 0)
    if ok.any():
        h, _ = np.histogram(np.log10(tc[ok]), edges, weights=w[hot][ok])
        st["tau_cell_hist"] = dict(log10_edges=edges.round(2).tolist(), mass=(h / h.sum()).tolist())
    # burnt-gas relaxation zone (theta > 0.8) and cooled zone (psi > 0.1): ages
    for key, m in (("age_burnt", hot & (c["theta"] > 0.8)), ("age_cooled", hot & (c["psi"] > 0.1))):
        st[key] = wpct(c["age"][m], w[m], PCTS)
    st["psi_negative_mass_share"] = float(w[hot & (c["psi"] < -0.02)].sum() / max(w[hot].sum(), 1e-30))
    return st


def plot(c, st, path, label, T_min):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    hot = c["T"] > T_min
    fig, ax = plt.subplots(2, 3, figsize=(14, 8))
    pairs = [("chi", True), ("strain", True), ("age", True), ("tau_cell", True), ("psi", False), ("theta", False)]
    for a, (q, lg) in zip(ax.flat, pairs):
        v = c[q][hot]
        ok = np.isfinite(v) & ((v > 0) if lg else True)
        if ok.any():
            a.scatter(c["Z"][hot][ok], v[ok], s=1, c=c["T"][hot][ok], cmap="inferno", vmin=300, vmax=2100)
            if lg:
                a.set_yscale("log")
        a.set_xscale("symlog", linthresh=0.01)
        a.axvline(0.055, c="b", lw=0.8)
        a.set(xlabel="Z", ylabel=q, title=f"{label}: {q} (T > {T_min:.0f} K)")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


# ----------------------------------------------------------------------------------- gate (step 3)
def compare(out, ref, labels, factor=2.0, psi_tol=0.05):
    R = json.loads((out / ref / "stats.json").read_text())
    rep = dict(reference=ref, factor=factor, psi_tol=psi_tol, runs={})
    checks = [("chi", "z_st"), ("age", "overall"), ("tau_cell", "overall"), ("strain", "z_st")]
    for lab in labels:
        S = json.loads((out / lab / "stats.json").read_text())
        res = {}
        for q, where in checks:
            a, b = S[where].get(q), R[where].get(q)
            if not a or not b:
                res[f"{q}@{where}"] = dict(ok=None)
                continue
            ratios = {p: a[PCTS.index(p)] / max(b[PCTS.index(p)], 1e-30) for p in (1, 50, 99)}
            ok = all(1 / factor <= v <= factor for v in ratios.values())
            res[f"{q}@{where}"] = dict(ok=bool(ok), ratio_p1=ratios[1], ratio_p50=ratios[50], ratio_p99=ratios[99])
        a, b = S["overall"]["psi"], R["overall"]["psi"]
        d = {p: a[PCTS.index(p)] - b[PCTS.index(p)] for p in (1, 50, 99)}
        res["psi@overall"] = dict(ok=bool(all(abs(v) <= psi_tol for v in d.values())),
                                  diff_p1=d[1], diff_p50=d[50], diff_p99=d[99])
        verdict = [v["ok"] for v in res.values() if v["ok"] is not None]
        rep["runs"][lab] = dict(checks=res, passed=bool(verdict and all(verdict)),
                                n_fail=int(sum(1 for v in verdict if not v)), T_max=S["T_max"])
    (out / f"gate_{ref}.json").write_text(json.dumps(rep, indent=1))
    lines = [f"# Step 3 gate vs {ref} (factor {factor} on p1/p50/p99, psi within {psi_tol})", "",
             "| run | check | ok | p1 | p50 | p99 |", "| --- | --- | --- | --- | --- | --- |"]
    for lab, r in rep["runs"].items():
        for k, v in r["checks"].items():
            if v["ok"] is None:
                lines.append(f"| {lab} | {k} | n/a | | | |")
            elif "ratio_p1" in v:
                lines.append(f"| {lab} | {k} | {v['ok']} | x{v['ratio_p1']:.2f} | x{v['ratio_p50']:.2f} | x{v['ratio_p99']:.2f} |")
            else:
                lines.append(f"| {lab} | {k} | {v['ok']} | {v['diff_p1']:+.3f} | {v['diff_p50']:+.3f} | {v['diff_p99']:+.3f} |")
        lines.append(f"| {lab} | **passed** | **{r['passed']}** | T_max {r['T_max']:.0f} K | | |")
    (out / f"gate_{ref}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("case")
    a1.add_argument("case")
    a1.add_argument("--time", required=True)
    a2 = sub.add_parser("fluent")
    a2.add_argument("csv")
    for a in (a1, a2):
        a.add_argument("--label", required=True)
        a.add_argument("--out", default=str(REPO / "data" / "timescale"))
        a.add_argument("--T-min", type=float, default=600.0)
    a3 = sub.add_parser("compare")
    a3.add_argument("--ref", required=True)
    a3.add_argument("--labels", nargs="+", required=True)
    a3.add_argument("--out", default=str(REPO / "data" / "timescale"))
    a3.add_argument("--factor", type=float, default=2.0)
    a3.add_argument("--psi-tol", type=float, default=0.05)
    a = ap.parse_args()
    out = Path(a.out)
    if a.cmd == "compare":
        compare(out, a.ref, a.labels, a.factor, a.psi_tol)
        return
    d = out / a.label
    d.mkdir(parents=True, exist_ok=True)
    c = from_openfoam(a.case, a.time, d / ".pp") if a.cmd == "case" else from_fluent(a.csv)
    np.savez_compressed(d / "cells.npz", **c)
    st = statistics(c, a.T_min)
    st["source"] = str(a.case if a.cmd == "case" else a.csv) + (f" @ {a.time}" if a.cmd == "case" else "")
    (d / "stats.json").write_text(json.dumps(st, indent=1))
    plot(c, st, d / "stats.png", a.label, a.T_min)
    o = st["overall"]
    print(f"{a.label}: {st['n_cells']} cells, {st['n_hot']} > {a.T_min:.0f} K, T_max {st['T_max']:.0f} K")
    for q in QUANT:
        if o[q]:
            print(f"  {q:9s} p1 {o[q][0]:.3g}  p50 {o[q][3]:.3g}  p99 {o[q][6]:.3g}")
    print(f"  psi < -0.02 mass share {st['psi_negative_mass_share']:.3f}")


if __name__ == "__main__":
    main()

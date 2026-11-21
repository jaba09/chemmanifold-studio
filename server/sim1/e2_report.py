#!/usr/bin/env python3
"""E2 report: ISAT vs networks over the full protocol v2 (results/sim1/E2/long.md + long.png).

Scores: score_v2.json of the ISAT runs (results/sim1/E2/<isat>) and of the networks already scored in phase B / C4
(results/sim1/B/<label>). Error growth: per-snapshot flame abs dT (T > 1600 K) against A1r from each flame-phase
protocol_report.json. ISAT table statistics: processor*/TDAC/{size,found,add,growth}_isat.out and cpu_*.out of the
flame runs (one line per step per rank), summed over ranks. Chemistry share = (s/step - flow only) / s/step, flow only
= 1.32 s/step (phase E, same case and ranks)."""
import glob
import json
import os
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
E2 = REPO / "results" / "sim1" / "E2"
B = REPO / "results" / "sim1" / "B"
RUNS = Path("/opt/ofb/runs/E2")
FLOW = 1.32
ISAT = ["isat1e-3", "isat1e-4"]
NETS = ["tix2h_s0", "P0_ood8", "P_tix2h", "P_mix"]


def load(label):
    d = E2 if label in ISAT else B
    p = d / label / "score_v2.json"
    return json.load(open(p)) if p.exists() else None


def growth(label):
    d = E2 if label in ISAT else B
    p = d / "flame" / label / "protocol_report.json"
    if not p.exists():
        return [], []
    s = sorted(json.load(open(p))["snapshots"], key=lambda r: r["t_ms"])
    return [r["t_ms"] for r in s], [r.get("absdT_llama") for r in s]


def tdac(label):
    out = {}
    for key in ("size", "found", "add", "growth"):
        acc = {}
        for f in glob.glob(str(RUNS / label / "flame" / "processor*" / "TDAC" / f"{key}_isat.out")):
            for line in open(f):
                a = line.split()
                if len(a) == 2:
                    acc[float(a[0])] = acc.get(float(a[0]), 0.0) + float(a[1])
        out[key] = acc
    t = np.array(sorted(out["size"]))
    if not len(t):
        return None
    g = lambda k: np.array([out[k].get(x, 0.0) for x in t])
    size, found, add, grow = g("size"), g("found"), g("add"), g("growth")
    q = found + add + grow
    return t * 1e3, size, found / np.maximum(q, 1), add / np.maximum(q, 1), grow / np.maximum(q, 1)


def main():
    rows = []
    for lab in ISAT + NETS:
        r = load(lab)
        if r is None:
            continue
        s = r.get("flame_s_per_step")
        rows.append(dict(label=lab, kind="ISAT" if lab in ISAT else "network", S=r["S"], F=r["F"], I=r["I"], C=r["C"],
                         dT=r["flame_absdT_K"], dtign=r["d_t_ign_ms"], drift=r.get("drift_K_per_10ms"),
                         oh=r.get("L1_oh"), co=r.get("L1_co"), V=r.get("V_hot_ratio"), s=s,
                         chem=(s - FLOW) / s if s else None, valid=r["valid"]))
    f = lambda v, fmt="{:.2f}": "-" if v is None or (isinstance(v, float) and not np.isfinite(v)) else fmt.format(v)
    L = ["# E2: ISAT vs networks over the full protocol v2 (longer run)\n",
         "Same case, radiation and scoring for every row: ignition phase 0-25 ms against A2r (GA18 DI), flame phase 50 ms "
         "from the A1r state at 0.1 s against the A1r DI snapshots 0.1-0.15 s. 4 ranks. ISAT = OpenFOAM TDAC, no mechanism "
         "reduction, GA18 seulex for the direct integrations. Networks: the phase B / C4 runs (same protocol, pure mode). "
         "S = max(F, I, C), 1 = target (flame abs dT 5 K, ignition 0.3 ms, CO/OH x1.4).\n",
         "| Method | S | F (flame abs dT) | I (ignition shift) | C | drift [K/10 ms] | L1 OH / CO (flame) | V(T>1500) xDI | s/step (flame) | chemistry share |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['label']} ({r['kind']}) | **{f(r['S'])}** | {f(r['F'])} ({f(r['dT'], '{:.1f}')} K) | {f(r['I'])} "
                 f"({f(r['dtign'], '{:+.1f}')} ms) | {f(r['C'])} | {f(r['drift'], '{:+.1f}')} | "
                 f"{f(100 * r['oh'] if r['oh'] is not None else None, '{:.1f}')} % / {f(100 * r['co'] if r['co'] is not None else None, '{:.1f}')} % | "
                 f"{f(r['V'], '{:.3f}')} | {f(r['s'])} | {f(100 * r['chem'] if r['chem'] is not None else None, '{:.0f} %')} |")
    # error growth table (every 10 ms)
    L += ["", "## Flame abs dT against A1r over the 50 ms (K, flame cells T > 1600 K)\n",
          "| t [ms] | " + " | ".join(r["label"] for r in rows) + " |", "|---|" + "---|" * len(rows)]
    G = {r["label"]: dict(zip(*growth(r["label"]))) for r in rows}
    for t in (102.5, 110.0, 120.0, 130.0, 140.0, 150.0):
        L.append(f"| {t:.1f} | " + " | ".join(f(G[r['label']].get(t), "{:.1f}") for r in rows) + " |")
    # ISAT table
    L += ["", "## ISAT table over the flame phase (summed over the 4 ranks)\n",
          "| run | t [ms] | table size (leaves) | retrieve | grow | add |", "|---|---|---|---|---|---|"]
    T = {lab: tdac(lab) for lab in ISAT}
    for lab, d in T.items():
        if d is None:
            continue
        t, size, fr, ad, gr = d
        for tt in (100.02, 101.0, 105.0, 110.0, 125.0, 150.0):
            i = int(np.argmin(np.abs(t - tt)))
            L.append(f"| {lab} | {t[i]:.2f} | {size[i]:.0f} | {100 * fr[i]:.1f} % | {100 * gr[i]:.1f} % | {100 * ad[i]:.2f} % |")
    (E2 / "long.md").write_text("\n".join(L) + "\n")
    # figure
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    for r in rows:
        t, v = growth(r["label"])
        ax[0].plot(t, v, "o-" if r["kind"] == "ISAT" else "s--", ms=3, label=f"{r['label']} (S {r['S']:.2f})")
    ax[0].axhline(5, color="k", lw=0.8, ls=":")
    ax[0].set(xlabel="t [ms]", ylabel="flame abs dT vs A1r DI [K]", title="Error growth over the flame phase")
    ax[0].legend(fontsize=7)
    for lab, d in T.items():
        if d is None:
            continue
        t, size, fr, ad, gr = d
        ax[1].plot(t, 100 * fr, label=f"{lab} retrieve %")
        ax2 = ax[1] if False else None
    ax[1].set(xlabel="t [ms]", ylabel="share of ISAT queries [%]", title="ISAT retrieve share (flame phase)")
    ax[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(E2 / "long.png", dpi=130)
    print("\n".join(L))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Figures and tables for papers 1, 2 and 5 from the protocol v2 results of the sim1 campaign.

usage: make_v2_figs.py <results/sim1 dir> <paper dir> [p2|p5|p1]
Reads protocol_report.json / score_v2.json (protocol v2, pure mode, against GA18 DI with wall radiation)
and offline_v2/benchmark.json. CFD states are only compared with; nothing here is training data.
"""
import json, glob, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

R, OUT, WHICH = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(os.path.join(OUT, "figs"), exist_ok=True)
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3, "figure.dpi": 150})

def find(label, phase):
    for p in glob.glob(f"{R}/**/{phase}/{label}/protocol_report.json", recursive=True):
        return json.load(open(p))["snapshots"]
    raise FileNotFoundError(label + " " + phase)

def scores():
    S = {}
    for p in glob.glob(f"{R}/**/score_v2.json", recursive=True):
        d = json.load(open(p)); S.setdefault(d["label"], d)
    return S

def series(label, phase, key):
    s = find(label, phase); return np.array([x["t_ms"] for x in s]), np.array([x[key] for x in s], float)

def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "figs", name), bbox_inches="tight"); plt.close(fig)

STY = {"isat1e-4": ("ISAT 1e-4", "k", "--"), "isann_D": ("ISANN (isann_D)", "C0", "-"),
       "P_tix2c": ("a priori parent P_tix2c", "C7", "-"), "C3_iter1": ("ITERML warm, it. 1", "C1", "-"),
       "C3_iter2": ("ITERML warm, it. 2", "C1", ":"), "C3b_iter1": ("ITERML scratch, it. 1", "C3", "-"),
       "C3b_iter2": ("ITERML scratch, it. 2", "C3", ":")}

if WHICH == "p2":
    fig, ax = plt.subplots(1, 3, figsize=(10, 3.2))
    for lab, (nm, c, ls) in STY.items():
        t, y = series(lab, "flame", "absdT_llama"); m = t > 100.01
        ax[0].semilogy(t[m], y[m], color=c, ls=ls, label=nm)
        t, y = series(lab, "flame", "L1_co"); ax[2].semilogy(t[m], 100 * y[m], color=c, ls=ls)
        t, y = series(lab, "ign", "Tmax_run"); m2 = t <= 6; ax[1].plot(t[m2], y[m2], color=c, ls=ls)
    t, y = series("isann_D", "ign", "Tmax_DI"); m2 = t <= 6
    ax[1].plot(t[m2], y[m2], color="g", lw=2.5, alpha=0.5, label="GA18 DI", zorder=0)
    ax[1].axhline(1600, color="gray", lw=0.8, ls="--")
    ax[0].axhline(5, color="gray", lw=0.8, ls="--")
    ax[0].set(xlabel="t [ms]", ylabel="flame |T - T$_{DI}$| [K]", title="(a) established flame")
    ax[1].set(xlabel="t [ms]", ylabel="domain T$_{max}$ [K]", title="(b) ignition from the lean start")
    ax[2].set(xlabel="t [ms]", ylabel="CO L1 error, hot cells [%]", title="(c) CO")
    h, l = ax[0].get_legend_handles_labels(); h2, l2 = ax[1].get_legend_handles_labels()
    fig.legend(h + h2[-1:], l + l2[-1:], loc="lower center", ncol=4, fontsize=7.5, bbox_to_anchor=(0.5, -0.08))
    save(fig, "fig_v2_runs.pdf")

if WHICH == "p5":
    S = scores()
    fam = lambda k: ("ISAT" if k.startswith("isat") else "ISANN (CFD-adapted)" if k.startswith("isann") else
                     "ensemble" if k.startswith("P") else "ITERML" if k.startswith("C3") else "single network")
    col = {"ISAT": "k", "ISANN (CFD-adapted)": "C0", "ensemble": "C2", "ITERML": "C1", "single network": "C7"}
    ks = sorted([k for k in S if S[k].get("valid") and k != "isann_D_online"], key=lambda k: S[k]["S"])
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.bar(range(len(ks)), [S[k]["S"] for k in ks], color=[col[fam(k)] for k in ks])
    ax.axhline(1, color="r", lw=1, ls="--"); ax.set_yscale("log")
    ax.set_xticks(range(len(ks))); ax.set_xticklabels(ks, rotation=75, fontsize=7)
    ax.set_ylabel("protocol v2 score S (1 = all targets)")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, label=f) for f, c in col.items()], fontsize=7, ncol=2)
    save(fig, "fig_scores.pdf")
    # repeats
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    for i, f in enumerate(["ood8", "tix2", "tix2h"]):
        v = [S[f"{f}_s{j}"]["S"] for j in range(3) if f"{f}_s{j}" in S and S[f"{f}_s{j}"].get("valid")]
        ax.plot([i] * len(v), v, "o", color="C7"); ens = {"ood8": "P0_ood8", "tix2": "P_tix2all", "tix2h": "P_tix2h"}[f]
        ax.plot(i, S[ens]["S"], "*", ms=12, color="C2")
    ax.plot([], [], "o", color="C7", label="training repeats"); ax.plot([], [], "*", color="C2", ms=10, label="mean ensemble")
    ax.set_xticks(range(3)); ax.set_xticklabels(["ood8", "tix2", "tix2h"]); ax.set_yscale("log")
    ax.set_ylabel("S"); ax.axhline(1, color="r", lw=1, ls="--"); ax.legend(fontsize=7)
    save(fig, "fig_repeats.pdf")
    # offline vs CFD
    B = json.load(open(f"{R}/offline_v2/benchmark.json"))["models"]
    common = [k for k in ks if k in B]
    rows = []
    fig, ax = plt.subplots(1, 2, figsize=(7, 3.0))
    for j, (mode, met) in enumerate([("hybrid", "dT_10ms"), ("alone", "score")]):
        x = [B[k][mode]["all"][met]["mean"] if isinstance(B[k][mode]["all"][met], dict) else B[k][mode]["all"][met] for k in common]
        y = [S[k]["S"] for k in common]
        r, p = spearmanr(x, y)
        ax[j].scatter(x, y, c=[col[fam(k)] for k in common], s=18)
        ax[j].set(xlabel=f"offline {met} ({mode})", ylabel="protocol v2 S", yscale="log",
                  title=f"rho = {r:+.2f}, p = {p:.2f}, n = {len(common)}")
    save(fig, "fig_offline_vs_cfd.pdf")
    # table of all scores
    L = ["model,family,S,F,I,C,flame_absdT_K,d_t_ign_ms,L1_oh,L1_co,drift_K_per_10ms,s_per_step"]
    for k in ks:
        d = S[k]; L.append(",".join([k, fam(k)] + ["%.3g" % d[c] for c in ["S", "F", "I", "C", "flame_absdT_K", "d_t_ign_ms",
                                                                          "L1_oh", "L1_co", "drift_K_per_10ms", "flame_s_per_step"]]))
    open(os.path.join(OUT, "scores_v2.csv"), "w").write("\n".join(L) + "\n")

#!/usr/bin/env python3
"""Paper 1 figures: coverage by exploration source and protocol v2 score by data family.
usage: make_figs.py <papers/data/coverage/coverage_ood8.md> <results/sim1> <out figs dir>
Evaluation only: DI states are measured against the data, never added to it."""
import sys, re, json, glob, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
cov, R, out = sys.argv[1:4]
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3})
rows = [l for l in open(cov).read().split("## Leave")[0].splitlines() if l.startswith("| +")]
lab = [re.sub(r"^\| \+\d+ ", "", r.split("|")[1].strip()).replace("+", "") for r in rows]
lab = [r.split("|")[1].strip()[1:] for r in rows]
r05 = [float(r.split("|")[3]) for r in rows]; tz = [float(r.split("|")[9]) for r in rows]
fig, ax = plt.subplots(1, 2, figsize=(9, 3.3))
x = np.arange(len(lab))
ax[0].plot(x, tz, "o-", label="in (Z, T) bins with $\\geq$200 data states")
ax[0].plot(x, r05, "s--", label="within distance 0.5 of a data state")
ax[0].set_xticks(x); ax[0].set_xticklabels(["+" + l for l in lab], rotation=60, ha="right", fontsize=7)
ax[0].set_ylabel("share of hot DI mass"); ax[0].set_ylim(0, 1.02); ax[0].legend(fontsize=7)
ax[0].set_title("(a) ood8 data, sources added one by one", fontsize=9)
t = open(f"{R}/offline_v2/a1r_regime_coverage.md").read().split("## By")[0]
rr = [l.split("|") for l in t.splitlines() if re.match(r"\| \d+ \|", l)]
names = [f"{r[1].strip()} {r[2].strip()}" for r in rr]; vw = [float(r[4].strip(" %")) for r in rr]; ts = [float(r[8].strip(" %")) for r in rr]
y = np.arange(len(names))
ax[1].barh(y - 0.2, vw, 0.4, label="hot cells nearest to it (vol.-weighted)")
ax[1].barh(y + 0.2, ts, 0.4, label="share of training pairs")
ax[1].set_yticks(y); ax[1].set_yticklabels(names, fontsize=7); ax[1].invert_yaxis(); ax[1].set_xlabel("%")
ax[1].legend(fontsize=7); ax[1].set_title("(b) tix2c data vs DI flame: nearest source", fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(out, "fig_coverage.pdf"), bbox_inches="tight")
# family scores
S = {}
for p in glob.glob(f"{R}/**/score_v2.json", recursive=True):
    d = json.load(open(p)); S[d["label"]] = d
fams = [("ood8", ["ood8_s0", "ood8_s1", "ood8_s2"], "P0_ood8"), ("tix1", ["tix1_s0"], None),
        ("tix2", ["tix2_s0", "tix2_s2"], "P_tix2all"), ("tix2h", ["tix2h_s0", "tix2h_s1", "tix2h_s2"], "P_tix2h"),
        ("tix2c", [], "P_tix2c")]
fig, ax = plt.subplots(figsize=(4.5, 3.0))
for i, (f, mem, ens) in enumerate(fams):
    v = [S[m]["S"] for m in mem if m in S and S[m].get("valid")]
    ax.plot([i] * len(v), v, "o", color="C7")
    if ens: ax.plot(i, S[ens]["S"], "*", ms=12, color="C2")
ax.axhline(S["isat1e-4"]["S"], color="k", ls="--", lw=1, label="ISAT 1e-4")
ax.axhline(1, color="r", ls="--", lw=1, label="all targets")
ax.plot([], [], "o", color="C7", label="training repeat"); ax.plot([], [], "*", color="C2", ms=10, label="mean ensemble")
ax.set_xticks(range(len(fams))); ax.set_xticklabels([f[0] for f in fams]); ax.set_yscale("log"); ax.set_ylabel("protocol v2 S")
ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(os.path.join(out, "fig_families.pdf"), bbox_inches="tight")

"""Figures of the Y(t+dt) vs dY paper.

  python make_figs.py <data dir with bands.csv> <figs dir>

Inputs (project files): the metrics_<label>.json / isann_<label>.json of the two ISANN runs
(hybrid_metrics.py, isann_report.py), run 1 of the earlier ISANN paper (for reproducibility), the
stage-18 offline benchmark (per_state.csv) and the 50 ms snapshots for the CO maps.
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

P = Path("/mnt/project-files/chemmanifold/isann")
RUN = {"Y": (P / "delta-output/carrera_y", "isanny"), "dY": (P / "delta-output/carrera_dy", "isanndy")}
STYLE = {"Y": dict(c="#1f5fa8", marker="o", ms=3, lw=1.6, label=r"state output $Y(t+\Delta t)$"),
         "dY": dict(c="#c4512b", marker="s", ms=3, lw=1.6, label=r"increment output $\Delta Y$")}
DATA, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def runs():
    for k, (d, lab) in RUN.items():
        f = d / f"metrics_{lab}.json"
        if f.exists():
            yield k, json.load(open(f))["snapshots"], json.load(open(d / f"isann_{lab}.json"))


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=170)
    plt.close(fig)


# 1. accuracy against DI over time
fig, ax = plt.subplots(2, 2, figsize=(7.2, 5.2), constrained_layout=True)
ref = json.load(open(P / "carrera1/metrics_isann1.json"))["snapshots"]
for k, snaps, rep in runs():
    t = [s["t_ms"] for s in snaps]
    ax[0, 0].plot(t, [s["flame_mean_abs_dT"] for s in snaps], **STYLE[k])
    ax[0, 1].plot(t, [s["mean_abs_dT"] for s in snaps], **STYLE[k])
    ax[1, 0].semilogy(t, [max(100 * s["rel_err_oh"], 0.1) for s in snaps], **STYLE[k])
    ax[1, 1].semilogy(t, [max(100 * s["rel_err_co"], 0.1) for s in snaps], **STYLE[k])
    for a in ax.flat:
        a.axvline(rep["first_switch_ms"], c=STYLE[k]["c"], lw=0.7, ls=":")
t = [s["t_ms"] for s in ref]
kw = dict(c="0.55", lw=1, ls="--", label="state output, earlier run (other machine)")
ax[0, 0].plot(t, [s["flame_mean_abs_dT"] for s in ref], **kw)
ax[0, 1].plot(t, [s["mean_abs_dT"] for s in ref], **kw)
ax[1, 0].semilogy(t, [max(100 * s["rel_err_oh"], 0.1) for s in ref], **kw)
ax[1, 1].semilogy(t, [max(100 * s["rel_err_co"], 0.1) for s in ref], **kw)
ax[0, 0].set_ylabel(r"flame, mean $|T-T_{DI}|$ [K]")
ax[0, 1].set_ylabel(r"hot cells, mean $|T-T_{DI}|$ [K]")
ax[1, 0].set_ylabel("OH mean relative error [%]")
ax[1, 1].set_ylabel("CO mean relative error [%]")
for a in ax.flat:
    a.set_xlabel("t [ms]")
ax[0, 0].legend(fontsize=7, frameon=False)
save(fig, "fig_accuracy_time")

# 2. error by temperature band at 25 and 50 ms
b = pd.read_csv(DATA / "bands.csv")
fig, ax = plt.subplots(1, 4, figsize=(7.4, 2.8), constrained_layout=True)
labels = [f"{lo}-{hi}" for lo, hi in [(600, 1000), (1000, 1300), (1300, 1600), (1600, 2300)]]
x = np.arange(4)
for j, (k, off) in enumerate([("Y", -0.2), ("dY", 0.2)]):
    g = b[(b.run == k) & (b.t_ms == 50.0)].sort_values("T_lo")
    if g.empty:
        continue
    c = STYLE[k]["c"]
    ax[0].bar(x + off, g.mean_dT, 0.4, color=c, label=STYLE[k]["label"])
    for i, s in enumerate(("co", "oh", "h")):
        ax[i + 1].bar(x + off, g[f"{s}_ratio"], 0.4, color=c)
ax[0].axhline(0, c="k", lw=0.6)
ax[0].set_ylabel(r"mean $T-T_{DI}$ [K]")
for i, s in enumerate(("CO", "OH", "H")):
    ax[i + 1].set_yscale("log")
    ax[i + 1].axhline(1, c="k", lw=0.6)
    ax[i + 1].set_ylabel(f"{s} mass, run / DI")
for a in ax:
    a.set_xticks(x, labels, rotation=45, fontsize=7)
    a.set_xlabel("T band [K]", fontsize=8)
ax[0].legend(fontsize=6.5, frameon=False, loc="lower left")
save(fig, "fig_bands")

# 3. CO maps at 50 ms (log10 CO / CO_DI), lower part of the domain
di = pd.read_csv(Path("/mnt/project-files/chemmanifold/protocolo-cfd/de-bucle-ood/snap_di/di_t0050.00ms.csv"))
snapdir = {"Y": Path("/opt/ofb/snap/isann_y/isanny_t0050.00ms.csv"), "dY": Path("/opt/ofb/snap/isann_dy/isanndy_t0050.00ms.csv")}
have = {k: f for k, f in snapdir.items() if f.exists()}
if have:
    fig, ax = plt.subplots(1, len(have) + 1, figsize=(7.4, 3.0), constrained_layout=True, sharey=True)
    m = (di["x-coordinate"] < 0.11) & (di["y-coordinate"] < 0.10)
    sc = ax[0].scatter(di["y-coordinate"][m], di["x-coordinate"][m], c=di.temperature[m], s=0.3, cmap="inferno", rasterized=True)
    fig.colorbar(sc, ax=ax[0], shrink=0.8, label="DI temperature [K]")
    ax[0].set_ylabel("x (axial) [m]")
    for a, (k, f) in zip(ax[1:], have.items()):
        r = pd.read_csv(f)
        hot = m & (np.maximum(di.temperature, r.temperature) > 600)
        v = np.log10(np.maximum(r.co[hot], 1e-12) / np.maximum(di.co[hot], 1e-12))
        sc = a.scatter(di["y-coordinate"][hot], di["x-coordinate"][hot], c=v, s=0.3, cmap="RdBu_r", vmin=-3, vmax=3, rasterized=True)
        a.set_title(STYLE[k]["label"], fontsize=8)
    fig.colorbar(sc, ax=ax[-1], shrink=0.8, label=r"$\log_{10}(Y_{CO}/Y_{CO,DI})$, $T>600$ K")
    for a in ax:
        a.set_xlabel("r [m]")
        a.set_aspect("equal")
    save(fig, "fig_co_maps")

# 4. offline benchmark (surrogate alone, physics-only Cantera states)
ps = pd.read_csv(Path("/mnt/project-files/chemmanifold/isann/delta-output/benchmark/per_state.csv"))
ps = ps[ps["mode"] == "alone"]
fams = ["equilibrium", "cooled", "lean_hot", "vitiated", "partial", "flamelet"]
models = [("ood7", "#1f5fa8", "state, a priori"), ("ood7dy", "#c4512b", "increment, a priori"),
          ("isann_y_v5", "#8fb3dd", "state, after ISANN"), ("isann_dy_v6", "#eba58c", "increment, after ISANN")]
fig, ax = plt.subplots(1, 3, figsize=(7.4, 2.9), constrained_layout=True)
x = np.arange(len(fams))
for j, (mname, c, lab) in enumerate(models):
    g = ps[ps.model == mname].groupby("family")
    off = (j - 1.5) * 0.2
    ax[0].bar(x + off, g.dT_end.mean().reindex(fams), 0.2, color=c, label=lab)
    ax[1].bar(x + off, g.radOH_1ms.median().reindex(fams), 0.2, color=c)
    ax[2].bar(x + off, g.radH_1ms.median().reindex(fams), 0.2, color=c)
ax[0].set_ylabel(r"mean $|T-T_{Cantera}|$ at 50 ms [K]")
ax[1].set_ylabel(r"median $|\log_{10}(Y_{OH}/Y_{OH,ref})|$, 1 ms")
ax[2].set_ylabel(r"median $|\log_{10}(Y_{H}/Y_{H,ref})|$, 1 ms")
for a in ax:
    a.set_xticks(x, [f.replace("_", " ") for f in fams], rotation=45, fontsize=7)
fig.legend(*ax[0].get_legend_handles_labels(), fontsize=7, frameon=False, ncol=4, loc="outside upper center")
save(fig, "fig_benchmark")

# 5. DI share and cost per step
fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.7), constrained_layout=True)
for k, snaps, rep in runs():
    w = [x for x in rep["windows"] if x["s_step"] > 0]
    tm = [(x["t0_ms"] + x["t1_ms"]) / 2 for x in w]
    ax[0].semilogy(tm, [max(100 * x["ga18"], 0.05) for x in w], **STYLE[k])
    ax[1].plot(tm, [x["s_step"] for x in w], **STYLE[k])
ax[0].set_ylabel("hot cells on DI (GA18) [%]")
ax[1].set_ylabel("wall time per step [s]")
for a in ax:
    a.set_xlabel("t [ms]")
ax[0].legend(fontsize=7, frameon=False)
save(fig, "fig_share_cost")
print("figures in", OUT)

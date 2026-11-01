"""Figures of the ISANN vs ITERML paper, built from the CFD protocol v1 reports (pure runs) and the
ISANN run-1 metrics. Every value is measured against GA18 direct integration (DI) from the same lit start.

Usage: python make_figs.py [OUT_DIR]
ITERML iteration 2 is drawn automatically once iterml/iter2/eval_protocol_report.md exists.
"""
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

P = Path("/mnt/project-files/chemmanifold")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "figs"
OUT.mkdir(parents=True, exist_ok=True)


def num(s):
    s = s.replace("%", "").replace("+", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def from_md(f):
    """Snapshot table ('Por instantánea') of a protocol v1 report."""
    rows, on = [], False
    for line in open(f, encoding="utf-8"):
        if line.startswith("## Por instant"):
            on = True
            continue
        if on and line.startswith("## "):
            break
        c = [x.strip() for x in line.split("|")[1:-1]]
        if on and len(c) >= 12 and re.match(r"^[0-9.]+$", c[0]):
            tm = [num(x) for x in c[11].split("/")]
            rows.append(dict(t=float(c[0]), dT=num(c[3]), bias=num(c[4]), oh=num(c[7]), co=num(c[8]),
                             hrr=num(c[10]), tdi=tm[0], tmod=tm[1]))
    return rows


def from_json(f):
    rows = []
    for s in json.load(open(f))["snapshots"]:
        rows.append(dict(t=s["t_ms"], dT=s.get("absdT_llama") if s.get("n_llama") else None,
                         bias=s.get("biasdT_llama") if s.get("n_llama") else None,
                         oh=100 * s["L1_oh"], co=100 * s["L1_co"], hrr=s.get("HRR_ratio"),
                         tdi=s["Tmax_DI"], tmod=s["Tmax_run"]))
    return rows


def load(stem):
    j, m = Path(str(stem) + ".json"), Path(str(stem) + ".md")
    if j.exists():
        return from_json(j)
    if m.exists():
        return from_md(m)
    return None


def isann_run1():
    s = json.load(open(P / "isann/carrera1/metrics_isann1.json"))["snapshots"]
    return [dict(t=x["t_ms"], dT=x["flame_mean_abs_dT"], oh=100 * x["rel_err_oh"]) for x in s]


RUNS = {
    "ISANN run 1 (DI phase, then v1-v6, GA18 fallback)": (isann_run1(), dict(c="#2a6fdb", lw=2)),
    "ISANN v6 network, pure": (load(P / "isann/pruebas2/protocolo_pure_v6/pure_v6/protocol_report"),
                               dict(c="#7a4fd0", ls="--", lw=1.6)),
    "ITERML iteration 1, pure": (load(P / "iterml/iter1/eval_protocol_report"), dict(c="#e0622a", lw=2)),
    "ITERML iteration 2, pure": (load(P / "iterml/iter2/eval_protocol_report"), dict(c="#b5179e", lw=2)),
    "a priori ood1, pure": (load(P / "protocolo-cfd/informes/pure_ood1/protocol_report"),
                            dict(c="0.55", ls=":", lw=1.4)),
}
RUNS = {k: v for k, v in RUNS.items() if v[0]}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

# Fig. 2: flame-zone error and species errors over time ------------------------------------------
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3), constrained_layout=True)
for name, (r, st) in RUNS.items():
    pts = [(x["t"], x["dT"]) for x in r if x.get("dT") is not None]
    ax[0].semilogy(*zip(*pts), marker=".", label=name, **st)
    if "co" in r[0]:
        pts = [(x["t"], x["co"]) for x in r if x.get("co") is not None]
        ax[1].semilogy(*zip(*pts), marker=".", **st)
ax[0].axvspan(25, 50, color="0.93", zorder=0)
ax[0].axhline(5, c="0.4", lw=0.7, ls="--")
ax[0].text(0.8, 3.6, "ITERML target 5 K", ha="left", fontsize=8, color="0.3")
ax[0].set_ylabel(r"flame-zone mean $|T-T_\mathrm{DI}|$ [K]  ($T>1600$ K)")
ax[1].set_ylabel(r"CO L1 error, hot cells ($T>600$ K) [%]")
for a in ax:
    a.set_xlabel("time [ms]")
    a.set_xlim(0, 50.5)
ax[1].axvspan(25, 50, color="0.93", zorder=0)
fig.legend(*ax[0].get_legend_handles_labels(), fontsize=8, frameon=False, loc="outside lower center", ncol=3)
fig.savefig(OUT / "fig_flame_error.pdf")
fig.savefig(OUT / "fig_flame_error.png", dpi=200)
plt.close(fig)

# Fig. 3: ignition, domain Tmax over 0-5 ms ------------------------------------------------------
fig, ax = plt.subplots(figsize=(5.6, 3.6), constrained_layout=True)
ref = RUNS["ITERML iteration 1, pure"][0]
ax.plot([x["t"] for x in ref if x["t"] <= 5], [x["tdi"] for x in ref if x["t"] <= 5], c="k", lw=2.2,
        label="GA18 DI (reference)")
for name, (r, st) in RUNS.items():
    if "tmod" not in r[0]:
        continue
    pts = [(x["t"], x["tmod"]) for x in r if x["t"] <= 5]
    ax.plot(*zip(*pts), marker="o", ms=3, label=name, **st)
ax.axhline(1600, c="0.5", lw=0.7, ls="--")
ax.text(0.1, 1612, "ignition criterion 1600 K", fontsize=7.5, color="0.35")
ax.set_xlabel("time [ms]")
ax.set_ylabel(r"domain $T_\mathrm{max}$ [K]")
ax.legend(fontsize=7.5, frameon=False, loc="lower right")
fig.savefig(OUT / "fig_ignition.pdf")
fig.savefig(OUT / "fig_ignition.png", dpi=200)
plt.close(fig)

# Fig. 4: heat-release ratio in the flame phase -------------------------------------------------
fig, ax = plt.subplots(figsize=(5.6, 3.4), constrained_layout=True)
for name, (r, st) in RUNS.items():
    if "hrr" not in r[0] or name.startswith("a priori"):
        continue
    pts = [(x["t"], x["hrr"]) for x in r if x["t"] >= 5 and x.get("hrr") is not None]
    ax.plot(*zip(*pts), marker=".", label=name, **st)
ax.axhline(1, c="k", lw=0.8)
ax.set_xlabel("time [ms]")
ax.set_ylabel("heat release (GA18 on the state), model / DI")
ax.legend(fontsize=7.5, frameon=False)
fig.savefig(OUT / "fig_hrr.pdf")
fig.savefig(OUT / "fig_hrr.png", dpi=200)
plt.close(fig)

# Window means quoted in the text -----------------------------------------------------------------
for name, (r, _) in RUNS.items():
    w = [x["dT"] for x in r if 25 <= x["t"] <= 50 and x.get("dT") is not None]
    print(f"{name}: flame |dT| 25-50 ms mean {sum(w) / len(w):.2f} K over {len(w)} snapshots"
          if w else f"{name}: no 25-50 ms snapshots")

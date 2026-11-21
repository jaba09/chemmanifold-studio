"""Figures of the single vs multiple ANN paper, from the protocol and benchmark reports.

  python make_figs.py --e4 <dir with pure_ood8/ and pure_p0/ protocol_report.json> --out ../figs
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUNS = [("pure_ood8", "single network (ood8)", "#c0392b", "o"),
        ("pure_p0", "mean of 3 seeds (P0)", "#1f6fb2", "s")]


def snaps(d, label):
    rep = json.load(open(Path(d) / label / "protocol_report.json"))
    return sorted(rep["snapshots"], key=lambda s: s["t_ms"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--e4", required=True)
    ap.add_argument("--out", default=str(Path(__file__).parents[1] / "figs"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    data = {lab: snaps(a.e4, lab) for lab, *_ in RUNS}

    # Fig. 1: flame-zone error and CO/OH totals over time
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    for lab, name, col, m in RUNS:
        s = [x for x in data[lab] if x.get("absdT_llama") is not None]
        ax[0].plot([x["t_ms"] for x in s], [x["absdT_llama"] for x in s], m + "-", color=col, ms=3, label=name)
        s = [x for x in data[lab] if x["t_ms"] >= 5 and x.get("ratio_co")]
        ax[1].plot([x["t_ms"] for x in s], [x["ratio_co"] for x in s], m + "-", color=col, ms=3, label=f"CO, {name}")
        ax[1].plot([x["t_ms"] for x in s], [x["ratio_oh"] for x in s], m + "--", color=col, ms=3, mfc="none",
                   label=f"OH, {name}")
    ax[0].axvspan(25, 50, color="0.92", zorder=0)
    ax[0].axhline(5, color="0.4", lw=0.8, ls=":")
    ax[0].set(xlabel="t [ms]", ylabel=r"mean $|T-T_\mathrm{DI}|$, $T>1600$ K [K]", yscale="log")
    ax[0].legend(frameon=False, fontsize=8)
    ax[1].axhspan(1 / 1.4, 1.4, color="0.92", zorder=0)
    ax[1].set(xlabel="t [ms]", ylabel="domain total, model / DI", yscale="log")
    ax[1].legend(frameon=False, fontsize=7, ncol=1)
    fig.tight_layout()
    fig.savefig(out / "fig_cfd_flame.pdf")

    # Fig. 2: start-up, maximum temperature
    fig, ax = plt.subplots(figsize=(4.5, 3.2))
    s = [x for x in data["pure_ood8"] if x["t_ms"] <= 7.5]
    ax.plot([x["t_ms"] for x in s], [x["Tmax_DI"] for x in s], "k-", lw=1.5, label="DI (GA18)")
    for lab, name, col, m in RUNS:
        s = [x for x in data[lab] if x["t_ms"] <= 7.5]
        ax.plot([x["t_ms"] for x in s], [x["Tmax_run"] for x in s], m + "-", color=col, ms=3, label=name)
    ax.axhline(1600, color="0.4", lw=0.8, ls=":")
    ax.set(xlabel="t [ms]", ylabel=r"$T_\mathrm{max}$ [K]")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig_ignition.pdf")
    print("figures in", out)


if __name__ == "__main__":
    main()

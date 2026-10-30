#!/usr/bin/env python3
"""Report of an ISANN run: GA18 share, network versions, cost per step and training rounds.

Reads <run>/processor*/isannStatus.csv, the solver logs (ExecutionTime per step), and the daemon's
<run>/isann/state.json; with --metrics, the metrics_<label>.json of hybrid_metrics.py (accuracy
against the DI run at each snapshot). Writes isann_<label>.md, isann_<label>.json and
isann_<label>.png (GA18 share and s/step against time, with the model switches).

  python3 isann_report.py --run <run dir> --label isann1 --out <dir> [--metrics metrics_isann1.json]
"""

import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from isann_lib import read_status  # noqa: E402

DT = 2e-5


def step_times(run):
    """{time index: wall seconds of that step} from the solver logs (ExecutionTime differences)."""
    out = {}
    for log in sorted(Path(run).glob("log.run*")):
        prev, k = None, None
        for line in open(log, errors="replace"):
            if line.startswith("Time = "):
                k = int(round(float(line.split()[2]) / DT))
            m = re.match(r"ExecutionTime = ([\d.e+-]+) s", line)
            if m and k is not None:
                t = float(m.group(1))
                if prev is not None:
                    out[k] = t - prev
                prev = t
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--metrics", default=None)
    ap.add_argument("--window", type=int, default=125, help="steps per row of the table (2.5 ms)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    st = read_status(a.run)
    state = json.load(open(Path(a.run) / "isann" / "state.json")) if (Path(a.run) / "isann" / "state.json").exists() \
        else dict(rounds=[])
    sec = step_times(a.run)
    st["ga18"] = st["di_phase"] + st["ood"] + st["untrusted"]
    st["s_step"] = [sec.get(int(k), np.nan) for k in st["step"]]
    phase_di = st["version"] == 0

    rows = []
    for s0 in range(0, int(st["step"].max()), a.window):
        w = st[(st["step"] > s0) & (st["step"] <= s0 + a.window)]
        if w.empty:
            continue
        hot = w["hot"].sum()
        rows.append(dict(t0_ms=s0 * DT * 1e3, t1_ms=(s0 + a.window) * DT * 1e3,
                         versions=f"{int(w['version'].min())}-{int(w['version'].max())}",
                         ga18=float(w["ga18"].sum() / hot), ood=float(w["ood"].sum() / hot),
                         untrusted=float(w["untrusted"].sum() / hot), s_step=float(np.nanmean(w["s_step"])),
                         shadow_bad=float(w["shadow_bad"].sum() / max(w["shadow"].sum(), 1))))
    di_cost = float(np.nanmean(st.loc[phase_di & (st["step"] > 5), "s_step"])) if phase_di.any() else np.nan
    ann = st[~phase_di]
    ann_cost = float(np.nanmean(ann["s_step"])) if len(ann) else np.nan
    summary = dict(
        label=a.label, steps=int(st["step"].max()), t_ms=float(st["step"].max() * DT * 1e3),
        di_phase_steps=int(phase_di.sum()), first_switch_ms=float(ann["step"].min() * DT * 1e3) if len(ann) else None,
        ga18_share_total=float(st["ga18"].sum() / st["hot"].sum()),
        ga18_share_network_phase=float(ann["ga18"].sum() / ann["hot"].sum()) if len(ann) else None,
        s_per_step_di_phase=di_cost, s_per_step_network_phase=ann_cost,
        speedup_network_phase=di_cost / ann_cost if len(ann) else None,
        wall_h=float(np.nansum(st["s_step"]) / 3600),
        stored_pairs_end=int(st["stored"].iloc[-1]), candidates=int(st["candidates"].iloc[-1]),
        rounds=[{k: r.get(k) for k in ("round", "why", "step", "n_online", "n_replay", "train_s", "gate_s",
                                        "version", "from_step")} | dict(
            accepted=r["gate"]["accepted"], T_mae_cand=r["gate"]["candidate"]["T_mae"],
            T_mae_cur=r["gate"]["current"]["T_mae"], roll_cand=r["gate"]["candidate"]["roll_T"],
            roll_cur=r["gate"]["current"]["roll_T"]) for r in state["rounds"]],
        windows=rows)
    acc = json.load(open(a.metrics)) if a.metrics else None
    if acc:
        summary["accuracy"] = acc["snapshots"]
    json.dump(summary, open(out / f"isann_{a.label}.json", "w"), indent=1, default=float)

    with open(out / f"isann_{a.label}.md", "w") as f:
        f.write(f"# ISANN {a.label}: {summary['t_ms']:.1f} ms simulados\n\n")
        f.write(f"- Fase DI: {summary['di_phase_steps']} pasos; primera red en uso a "
                f"{summary['first_switch_ms'] or float('nan'):.2f} ms\n")
        f.write(f"- Coste: {di_cost:.2f} s/paso en fase DI, {ann_cost:.2f} s/paso con red "
                f"(x{(summary['speedup_network_phase'] or float('nan')):.2f})\n")
        f.write(f"- Fracción GA18 de celdas calientes: {100 * summary['ga18_share_total']:.1f} % en total, "
                f"{100 * (summary['ga18_share_network_phase'] or float('nan')):.2f} % en fase red\n")
        f.write(f"- Pares guardados al final (rejilla): {summary['stored_pairs_end']} de {summary['candidates']} candidatos\n\n")
        f.write("## Rondas de entrenamiento\n\n| ronda | motivo | paso | pares online | replay | entrenamiento [s] | "
                "dT 1 paso cand / actual [K] | rollout cand / actual [K] | aceptada | versión |\n|---|---|---|---|---|---|---|---|---|---|\n")
        for r in summary["rounds"]:
            f.write(f"| {r['round']} | {r['why']} | {r['step']} | {r['n_online']} | {r['n_replay']} | {r['train_s']:.0f} | "
                    f"{r['T_mae_cand']:.3f} / {r['T_mae_cur']:.3f} | {r['roll_cand']:.2f} / {r['roll_cur']:.2f} | "
                    f"{'sí' if r['accepted'] else 'no'} | {r.get('version') or '-'} |\n")
        f.write("\n## Por ventana\n\n| t [ms] | versiones | GA18 | OOD | no fiable | s/paso | sombra mal |\n"
                "|---|---|---|---|---|---|---|\n")
        for r in rows:
            f.write(f"| {r['t0_ms']:.1f}-{r['t1_ms']:.1f} | {r['versions']} | {100 * r['ga18']:.2f} % | "
                    f"{100 * r['ood']:.2f} % | {100 * r['untrusted']:.2f} % | {r['s_step']:.2f} | "
                    f"{100 * r['shadow_bad']:.1f} % |\n")
        if acc:
            f.write("\n## Error frente a DI\n\n| t [ms] | media abs dT [K] | llama abs dT [K] | Tmax DI | Tmax ISANN | err OH | err CO |\n"
                    "|---|---|---|---|---|---|---|\n")
            for r in acc["snapshots"]:
                f.write(f"| {r['t_ms']:.1f} | {r['mean_abs_dT']:.1f} | {r['flame_mean_abs_dT']:.1f} | {r['Tmax_DI']:.0f} | "
                        f"{r['Tmax_run']:.0f} | {r['rel_err_oh']:.0%} | {r['rel_err_co']:.0%} |\n")

    t = st["step"] * DT * 1e3
    fig, ax = plt.subplots(2 + bool(acc), 1, figsize=(8, 7 + 2 * bool(acc)), sharex=True)
    ax[0].semilogy(t, np.maximum(st["ga18"] / st["hot"], 1e-5), lw=0.8, label="GA18 total")
    ax[0].semilogy(t, np.maximum(st["ood"] / st["hot"], 1e-5), lw=0.6, label="OOD")
    ax[0].semilogy(t, np.maximum(st["untrusted"] / st["hot"], 1e-5), lw=0.6, label="casilla no fiable")
    ax[0].set(ylabel="fracción de celdas calientes")
    ax[0].legend(fontsize=8)
    ax[1].plot(t, st["s_step"], lw=0.6)
    ax[1].set(ylabel="s / paso")
    for r in summary["rounds"]:
        if r.get("version"):
            for x in ax:
                x.axvline(r["from_step"] * DT * 1e3, color="k", ls=":", lw=0.8)
    if acc:
        ax[2].plot([r["t_ms"] for r in acc["snapshots"]], [r["flame_mean_abs_dT"] for r in acc["snapshots"]], "o-",
                   label="llama T>1600 K")
        ax[2].plot([r["t_ms"] for r in acc["snapshots"]], [r["mean_abs_dT"] for r in acc["snapshots"]], "s-",
                   label="celdas calientes")
        ax[2].set(ylabel="|T - T_DI| [K]")
        ax[2].legend(fontsize=8)
    ax[-1].set_xlabel("t [ms]")
    fig.tight_layout()
    fig.savefig(out / f"isann_{a.label}.png", dpi=130)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("windows", "accuracy")}, indent=1, default=float))


if __name__ == "__main__":
    main()

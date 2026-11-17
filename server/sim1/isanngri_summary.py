#!/usr/bin/env python3
"""Summary of the ISANN ARC22 run (server/sim1/isanngri_score.sh): protocol v2 flame scores against the ARC22
DI flame and against GA18 DI (A1r), NOx in the hot cells and at the outlets against the ARC22 DI flame, the
ISANN rounds and costs, and the GA18 ISANN numbers for context. Writes <out>/summary.md and summary.json.

  isanngri_summary.py --run /opt/ofb/run/isann_arc22 --di-arc /opt/ofb/runs/arc22/flame --out results/sim1/ISANN_ARC22
"""

import argparse
import glob
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
NOX = ["no", "no2", "n2o", "hcn"]
T_HOT = 600.0


def snaps(d):
    out = {}
    for f in sorted(Path(d).glob("*_t*ms.csv")):
        m = re.search(r"_t([0-9.]+)ms\.csv$", f.name)
        if m:
            out[round(float(m.group(1)), 2)] = f
    return out


def nox_scores(run_snap, di_snap, t0=100.05, t1=150.0):
    """Per common snapshot in (t0, t1] ms: hot-cell (DI or run above 600 K) volume-weighted totals of
    NO, NO2, N2O, HCN in the run against DI (total ratio) and the volume-weighted L1 relative error."""
    a, b = snaps(run_snap), snaps(di_snap)
    rows = []
    for t in sorted(set(a) & set(b)):
        if not t0 < t <= t1:
            continue
        r = pd.read_csv(a[t]).sort_values("cellnumber").reset_index(drop=True)
        d = pd.read_csv(b[t]).sort_values("cellnumber").reset_index(drop=True)
        if len(r) != len(d):
            continue
        hot = (r["temperature"] > T_HOT) | (d["temperature"] > T_HOT)
        V = d["cell-volume"][hot]
        row = dict(t_ms=t)
        for s in NOX:
            if s not in r or s not in d:
                continue
            yr, yd = r[s][hot], d[s][hot]
            row[f"ratio_{s}"] = float((V * yr).sum() / max((V * yd).sum(), 1e-300))
            row[f"L1_{s}"] = float((V * (yr - yd).abs()).sum() / max((V * yd.abs()).sum(), 1e-300))
        rows.append(row)
    return pd.DataFrame(rows)


def outlet_nox(case, t0=0.1, t1=0.15):
    """Mean of the outletNOx function objects (weighted averages) over [t0, t1] s, per patch."""
    frames = {}
    for f in sorted(glob.glob(f"{case}/postProcessing/outletNOx_*/*/surfaceFieldValue.dat")):  # one dir per restart
        name = Path(f).parents[1].name.replace("outletNOx_", "")
        lines = [l for l in open(f) if not l.startswith("#") or l.startswith("# Time")]
        cols = lines[0].lstrip("# ").split()
        d = pd.DataFrame([l.split() for l in lines[1:]], columns=cols).apply(pd.to_numeric, errors="coerce")
        d.columns = [c.replace("weightedAverage(", "").rstrip(")") for c in d.columns]
        frames.setdefault(name, []).append(d)
    out = {}
    for name, fs in frames.items():
        d = pd.concat(fs).drop_duplicates("Time", keep="last").sort_values("Time")
        w = d[(d.Time >= t0) & (d.Time <= t1 + 1e-9)]
        out[name] = {c: float(w[c].mean()) for c in w.columns if c != "Time"}
        out[name]["_n"] = len(w)
    return out


def llama(report_json):
    if not Path(report_json).exists():
        return None
    d = json.load(open(report_json))
    return d["summary"].get("llama", {}), d.get("info", {})


def fmt(v, f="{:.2f}"):
    return "–" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f.format(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--di-arc", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="isann_arc22")
    ap.add_argument("--compare", default=None, help="results dir of an earlier ISANN run (its summary.json): extra column")
    a = ap.parse_args()
    out = Path(a.out)
    vs_arc = llama(out / "vs_arc22_di" / a.label / "protocol_report.json")
    vs_a1r = llama(out / "vs_ga18_di" / a.label / "protocol_report.json")
    prev = json.load(open(Path(a.compare) / "summary.json")) if a.compare else None
    try:
        import yaml
        parent = yaml.safe_load(open(Path(a.run) / "isann" / "isann.yaml"))["parent"]["data_dir"]
    except Exception:   # noqa: BLE001
        parent = "?"
    arc_vs_a1r = llama(REPO / "results/sim1/ARC22/flame/arc22_flame/protocol_report.json") or \
        llama("/opt/ofb/arc22-src/results/sim1/ARC22/flame/arc22_flame/protocol_report.json")
    v6 = llama(REPO / "results/sim1/B/flame/isann_v6/protocol_report.json")
    nox = nox_scores(Path(a.run) / "snap", Path(a.di_arc) / "snap")
    onox_run, onox_di = outlet_nox(a.run), outlet_nox(a.di_arc)
    isj = out / "isann" / f"isann_{a.label}.json"
    isann = json.load(open(isj)) if isj.exists() else {}
    state = json.load(open(Path(a.run) / "isann" / "state.json"))
    rounds = state.get("rounds", [])

    keys = [("absdT_llama", "flame mean abs dT (T > 1600 K) [K]", "{:.1f}"),
            ("biasdT_llama", "flame bias dT [K]", "{:+.1f}"),
            ("absdT_caliente", "hot-cell mean abs dT [K]", "{:.1f}"),
            ("p95_absdT_caliente", "hot-cell p95 abs dT [K]", "{:.0f}"),
            ("V_hot_ratio", "hot volume ratio run/ref", "{:.3f}"),
            ("L1_oh", "OH L1 (hot cells)", "{:.1%}"), ("ratio_oh", "OH total ratio", "{:.2f}"),
            ("L1_co", "CO L1 (hot cells)", "{:.1%}"), ("ratio_co", "CO total ratio", "{:.2f}"),
            ("HRR_ratio", "HRR ratio (GA18 rates on each state)", "{:.2f}"),
            ("GA18_share", "DI (ODE) share reported by the solver", "{:.1%}"),
            ("s_per_step", "s per step", "{:.2f}")]
    cols = [(f"{a.label} vs ARC22 DI", vs_arc)]
    if prev:
        cols.append((f"earlier run ({Path(a.compare).name}) vs ARC22 DI", (prev.get("vs_arc") or {}, {}) if prev.get("vs_arc") else None))
    cols += [(f"{a.label} vs GA18 DI (A1r)", vs_a1r),
            ("ARC22 DI vs GA18 DI (A1r)", arc_vs_a1r), ("GA18 isann_v6 (pure) vs GA18 DI", v6)]
    L = [f"# ISANN with ARC_GRI30_NOx22: {a.label}", "",
         f"Run `{a.run}`: protocol v2 flame base (A1r state at 0.1 s, LeFoam + wall radiation), "
         "0.1-0.15 s on 8 ranks; DI on the ARC kernel (libuserChemStepArc) until the daemon publishes a network, "
         "then the network in the cells it does not flag OOD or untrusted. Parent: `" + parent + "` "
         "(physics only; parent_arc22 = skel43 labels projected to 22 species, parent_arc22b = ARC labels). Reference: the ARC22 DI "
         "flame (`/opt/ofb/runs/arc22/flame`, same base; it crashed at 0.185 s, so 0.1-0.15 s is complete). "
         "Protocol v2 flame scores (`openfoam/protocol/score_protocol.py`, window 100.05-150 ms; ranks differ: "
         "the protocol's s/step are on 4 ranks, this run 8). Every CFD state is a diagnostic, never training data "
         "for the a priori models (ISANN's own online pairs are its method).", "",
         "## Protocol v2 flame window (100-150 ms)", "",
         "| metric | " + " | ".join(c for c, _ in cols) + " |", "|---|" + "---|" * len(cols)]
    for k, label, f in keys:
        vals = [fmt(r[0].get(k), f) if r else "–" for _, r in cols]
        L.append(f"| {label} | " + " | ".join(vals) + " |")
    L += ["", "## NOx in the hot cells, ISANN ARC22 vs ARC22 DI (volume-weighted, T > 600 K in either)", ""]
    if len(nox):
        pn = pd.DataFrame(prev["nox"]) if prev and prev.get("nox") else None
        extra = " earlier run: ratio / L1 mean / L1 last 10 ms |" if pn is not None else ""
        L += ["| species | total ratio mean (min-max) | L1 mean | L1 last 10 ms |" + extra,
              "|---|---|---|---|" + ("---|" if pn is not None else "")]
        last = nox[nox.t_ms > 140]
        for s in NOX:
            if f"ratio_{s}" in nox:
                row = (f"| {s.upper()} | {nox[f'ratio_{s}'].mean():.3f} ({nox[f'ratio_{s}'].min():.3f}-"
                       f"{nox[f'ratio_{s}'].max():.3f}) | {nox[f'L1_{s}'].mean():.1%} | {last[f'L1_{s}'].mean():.1%} |")
                if pn is not None and f"ratio_{s}" in pn:
                    pl = pn[pn.t_ms > 140]
                    row += f" {pn[f'ratio_{s}'].mean():.3f} / {pn[f'L1_{s}'].mean():.1%} / {pl[f'L1_{s}'].mean():.1%} |"
                L.append(row)
        L.append(f"\n{len(nox)} common snapshots.")
    else:
        L.append("no common snapshots")
    L += ["", "## Outlet NOx, mean over 0.1-0.15 s (weighted averages of the outletNOx function objects)", ""]
    for patch in sorted(set(onox_run) | set(onox_di)):
        r, d = onox_run.get(patch, {}), onox_di.get(patch, {})
        L += [f"**{patch}** ({r.get('_n', 0)} / {d.get('_n', 0)} samples)", "", "| field | ISANN ARC22 | ARC22 DI | ratio |",
              "|---|---|---|---|"]
        for c in sorted(k for k in set(r) | set(d) if k != "_n"):
            rv, dv = r.get(c), d.get(c)
            ratio = rv / dv if rv is not None and dv not in (None, 0) else None
            L.append(f"| {c} | {fmt(rv, '{:.4g}')} | {fmt(dv, '{:.4g}')} | {fmt(ratio, '{:.3f}')} |")
        L.append("")
    L += ["## ISANN rounds", "",
          "Gate on held-out online pairs: one-step T MAE and 0D 2 ms rollout mean |dT| against the reference "
          "chemistry (current network -> candidate).", "",
          "| round | step | why | online / replay pairs | one-step T MAE [K] | rollout mean [K] | failed rollouts | result |",
          "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rounds, 1):
        g = r.get("gate") or {}
        c, n = g.get("current", {}), g.get("candidate", {})
        res = f"accepted, v{r.get('version')} from step {r.get('from_step')}" if g.get("accepted") else "rejected"
        L.append(f"| {r.get('round', i)} | {r.get('step', '–')} | {r.get('why', '–')} | {r.get('n_online', '–')} / "
                 f"{r.get('n_replay', '–')} | {fmt(c.get('T_mae'))} -> {fmt(n.get('T_mae'))} | "
                 f"{fmt(c.get('roll_T'), '{:.1f}')} -> {fmt(n.get('roll_T'), '{:.1f}')} | "
                 f"{c.get('roll_fail', '–')} -> {n.get('roll_fail', '–')} | {res} |")
    L += ["", f"Final version: {state.get('version')}; daemon log: `{a.run}/isann/daemon.log`.", ""]
    if isann:
        L += ["## DI share and cost (isann_report.py)", "", f"See `isann/isann_isann_arc22.md` and `.png`."]
        for k, v in isann.items():     # scalars of isann_report.py ("ga18" there = the DI chemistry, here ARC)
            if isinstance(v, (int, float, str)) or v is None:
                L.append(f"- {k}: {fmt(v, '{:.4g}') if isinstance(v, float) else v}")
        L.append("")
    L += ["## GA18 ISANN for context", "",
          "- ISANN run 1 (GA18, 30 Oct, lit start 0-50 ms, 2 ranks, parent ood7): six accepted networks of 12 rounds; "
          "flame (T > 1600 K) mean |T - T_DI| 2.0-3.4 K at 25-50 ms, OH error 33-90 %; GA18 share 0.14-0.5 % of the hot "
          "cells with the network; 7.9 s/step DI, 4.2 s/step with the network (openfoam/isann/README.md).",
          "- isann_v6 (that run's last network, frozen, pure mode) under protocol v2: column 4 above.", ""]
    (out / "summary.md").write_text("\n".join(L))
    json.dump(dict(vs_arc=vs_arc[0] if vs_arc else None, vs_a1r=vs_a1r[0] if vs_a1r else None,
                   nox=nox.to_dict("list"), outlet_nox_run=onox_run, outlet_nox_di=onox_di, rounds=rounds,
                   final_version=state.get("version")), open(out / "summary.json", "w"), indent=1, default=float)
    print(f"wrote {out / 'summary.md'}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Protocol v2 score of one candidate: S = max(F, I, C) (openfoam/iterml/rules.py terms, same targets).

  F  mean flame |dT| (T > 1600 K) over the flame-phase window (R2 snapshots 102.5-150 ms) / flame_dT
  I  |ignition time - A2r's| / ignition_ms, from the ignition-phase report: per-step domain Tmax curves
     (minMaxT, summary arranque.d_t_ign_ms) when both are there, else snapshot interpolation (rules._ignition)
  C  mean over the flame window of max(|ln CO ratio|, |ln OH ratio|) / ln(species_ratio)

    score_v2.py --label ood8_s0 --ign <dir>/protocol_report.json --flame <dir>/protocol_report.json --out <dir>
    score_v2.py --table <dir>/*/score_v2.json --out <dir>        (ranking table)
"""
import argparse, json, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "iterml"))
from rules import _ignition  # noqa: E402

R = dict(flame_window_ms=[102.5, 150.0], flame_dT=5.0, ignition_ms=0.3, T_ign=1600.0, species_ratio=1.4)


def score(a):
    ig, fl = json.load(open(a.ign)), json.load(open(a.flame))
    snaps = sorted(fl["snapshots"], key=lambda s: s["t_ms"])
    lo, hi = R["flame_window_ms"]
    win = [s for s in snaps if lo - 1e-9 <= s["t_ms"] <= hi + 1e-9]
    valid = bool(win) and max(s["t_ms"] for s in snaps) >= hi - 1e-9 and ig["summary"].get("valida", False)
    dT = [s["absdT_llama"] for s in win if s.get("absdT_llama") is not None]
    F = float(np.mean(dT)) / R["flame_dT"] if dT else float("inf")
    lr = [max(abs(math.log(s[k])) for k in ("ratio_co", "ratio_oh") if s.get(k) and s[k] > 0) for s in win
          if any(s.get(k) and s[k] > 0 for k in ("ratio_co", "ratio_oh"))]
    C = float(np.mean(lr)) / math.log(R["species_ratio"]) if lr else float("inf")
    d = ig["summary"]["arranque"].get("d_t_ign_ms")
    src = "minMaxT"
    if d is None or not np.isfinite(d):
        s2 = sorted(ig["snapshots"], key=lambda s: s["t_ms"]); t = [s["t_ms"] for s in s2]
        d = _ignition(t, [s.get("Tmax_run") for s in s2], R["T_ign"]) - _ignition(t, [s.get("Tmax_DI") for s in s2], R["T_ign"])
        src = "snapshots"
    I = abs(d) / R["ignition_ms"] if np.isfinite(d) else float("inf")
    ll = fl["summary"].get("llama", {})
    out = dict(label=a.label, S=max(F, I, C), F=F, I=I, C=C, valid=valid, flame_absdT_K=F * R["flame_dT"],
               d_t_ign_ms=d, ign_source=src, t_ign_DI_ms=ig["summary"]["arranque"].get("t_ign_DI_ms"),
               flame_OOD_share=ll.get("OOD_share"), flame_s_per_step=ll.get("s_per_step"),
               ign_OOD_share=ig["summary"]["arranque"].get("OOD_share"), drift_K_per_10ms=ll.get("deriva_absdT_llama_K_por_10ms"),
               L1_oh=ll.get("L1_oh"), L1_co=ll.get("L1_co"), V_hot_ratio=ll.get("V_hot_ratio"), rules=R)
    o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(o / "score_v2.json", "w"), indent=1, default=float)
    print(json.dumps(out, default=float))


def table(a):
    rows = sorted((json.load(open(p)) for p in a.table), key=lambda r: (not r["valid"], r["S"]))
    f = lambda v, s="{:.2f}": "–" if v is None or (isinstance(v, float) and not np.isfinite(v)) else s.format(v)
    L = ["# Protocol v2 ranking (pure mode, vs A1r/A2r GA18 DI with radiation)\n",
         "S = max(F, I, C); each term is 1 at its target (flame abs dT 5 K, ignition 0.3 ms, CO/OH within x1.4).\n",
         "| Model | S | F | I | C | flame abs dT [K] | d t_ign [ms] | drift [K/10 ms] | V(T>1500) xDI | OOD (flame) | s/step | valid |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['label']} | **{f(r['S'])}** | {f(r['F'])} | {f(r['I'])} | {f(r['C'])} | {f(r['flame_absdT_K'], '{:.1f}')} | "
                 f"{f(r['d_t_ign_ms'], '{:+.2f}')} | {f(r.get('drift_K_per_10ms'), '{:+.2f}')} | {f(r.get('V_hot_ratio'))} | "
                 f"{f(100 * r['flame_OOD_share'] if r.get('flame_OOD_share') is not None else None, '{:.1f} %')} | "
                 f"{f(r.get('flame_s_per_step'))} | {'yes' if r['valid'] else 'no'} |")
    o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    (o / "ranking_v2.md").write_text("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--label"); p.add_argument("--ign"); p.add_argument("--flame"); p.add_argument("--table", nargs="+")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    table(a) if a.table else score(a)

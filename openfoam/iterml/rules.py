"""ITERML frozen decision rules (docs/ITERML-ROADMAP.md, section 11): what the automatic loop decides
without anyone looking. Every number comes from the settings file (`rules:`), fixed before the run.

score(report)       one number per pure protocol run, from its protocol_report.json:
                    S = max(F, I, C), each term 1.0 at its target
                      F  mean flame |dT| (T > 1600 K) over the scoring window / flame_dT
                      I  |ignition time - DI's| / ignition_ms, ignition = first time Tmax > T_ign
                         (linear interpolation between snapshots)
                      C  mean over the window of max(|ln CO ratio|, |ln OH ratio|) / ln(species_ratio)
                    S <= 1: every target met.
accept(best, cands) elitism: the candidates are the training seeds of one iteration. They replace the
                    best model so far only if EVERY seed beats it by more than the seeds' own spread
                    (max S - min S), so a lucky seed is not taken for progress. The new parent is the
                    best seed. Otherwise the loop continues from the unchanged best model.
stop(history)       targets met (best S <= 1), `patience` iterations in a row without acceptance, or
                    `max_iterations`.
"""

import json
import math

import numpy as np


def _ignition(t, Tmax, T_ign):
    for i in range(len(t)):
        if Tmax[i] is not None and Tmax[i] > T_ign:
            if i == 0 or Tmax[i - 1] is None:
                return t[i]
            a = (T_ign - Tmax[i - 1]) / (Tmax[i] - Tmax[i - 1])
            return t[i - 1] + a * (t[i] - t[i - 1])
    return float("nan")


def score(report_path, r):
    rep = json.load(open(report_path))
    snaps = sorted(rep["snapshots"], key=lambda s: s["t_ms"])
    t = [s["t_ms"] for s in snaps]
    lo, hi = r["window_ms"]
    win = [s for s in snaps if lo - 1e-9 <= s["t_ms"] <= hi + 1e-9]
    if not win or max(t) < hi - 1e-9:
        return dict(S=float("inf"), F=float("inf"), I=float("inf"), C=float("inf"), valid=False,
                    reason=f"run ends at {max(t) if t else 0} ms, before {hi} ms")
    dT = [s["absdT_llama"] for s in win if s.get("absdT_llama") is not None]
    F = float(np.mean(dT)) / r["flame_dT"]
    t_di = _ignition(t, [s.get("Tmax_DI") for s in snaps], r["T_ign"])
    t_m = _ignition(t, [s.get("Tmax_run") for s in snaps], r["T_ign"])
    I = abs(t_m - t_di) / r["ignition_ms"] if np.isfinite(t_m) and np.isfinite(t_di) else float("inf")
    lr = []
    for s in win:
        v = [abs(math.log(s[k])) for k in ("ratio_co", "ratio_oh") if s.get(k) and s[k] > 0]
        if v:
            lr.append(max(v))
    C = float(np.mean(lr)) / math.log(r["species_ratio"]) if lr else float("inf")
    return dict(S=max(F, I, C), F=F, I=I, C=C, t_ign_ms=t_m, t_ign_DI_ms=t_di, flame_dT=F * r["flame_dT"],
                valid=True)


def accept(best_S, cand):
    """cand: {tag: S}. Returns (accepted, chosen tag, spread, reason)."""
    vals = [v for v in cand.values() if np.isfinite(v)]
    if len(vals) < len(cand):
        return False, None, float("nan"), "a seed has no valid score"
    spread = max(vals) - min(vals) if len(vals) > 1 else 0.0
    tag = min(cand, key=cand.get)
    if all(v < best_S - spread for v in vals):
        return True, tag, spread, f"every seed beats the best ({best_S:.2f}) by more than the spread {spread:.2f}"
    return False, tag, spread, (f"not every seed beats the best ({best_S:.2f}) by more than the spread {spread:.2f}: "
                                + ", ".join(f"{a or 'seed0'} {b:.2f}" for a, b in cand.items()))


def stop(best_S, rejections_in_row, k, r):
    if best_S <= 1.0:
        return "targets met"
    if rejections_in_row >= int(r["patience"]):
        return f"{rejections_in_row} iterations in a row without an accepted model"
    if k >= int(r["max_iterations"]):
        return f"{k} iterations (maximum)"
    return None

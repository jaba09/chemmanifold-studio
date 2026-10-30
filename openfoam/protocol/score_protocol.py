#!/usr/bin/env python3
"""Standard report of one run of the fixed CFD evaluation protocol (PROTOCOL.md) against GA18 DI.

The run and the DI reference start from the same lit state, with the same mesh, dt and writes, so
at each common snapshot time the two fields differ only by the chemistry. The snapshots are the
CSV tables of openfoam/tools/foam_snapshot.py (<label>_t<ms>ms.csv). Every number is a diagnostic
of the run; none of these CFD states is ever used as training data.

Phases (protocol.yaml): start-up 0-5 ms (snapshots every 0.5 ms), transition 5-25 ms (reported,
not scored), established flame 25-100 ms (every 2.5 ms). Per snapshot it measures, against DI:

  T       mean |dT| and bias in fixed state zones (classified on the DI state) and in the nozzle box
  species volume-weighted L1 relative error and total-amount ratio of OH, CO, CH4, H in hot cells
  flame   volume above 1500 K, flame tip and base on the axis, heat release of GA18 evaluated on
          each state (Cantera), its total ratio and L1 error
  cost    GA18 share (ODE fallback), OOD share, s per time step (from log.run)

and from the per-step Tmax curve (postProcessing/minMaxT) the ignition time (first Tmax > 1600 K).
The shadow DI checks of the run (shadowDI.csv) are summarized per phase.

  score_protocol.py --di <DI csv dir>... --run <run csv dir> --label ood1_pure \
      --run-dir <run case> --di-dir <DI start-up case> --out <report dir>
  score_protocol.py --compare <report dir>/*/protocol_report.json --out <dir>
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))


def load_protocol(path=None):
    return yaml.safe_load(open(path or HERE / "protocol.yaml"))


def snapshots(dirs, label):
    out = {}
    for d in dirs:
        for p in Path(d).glob(f"{label}_t*ms.csv"):
            out.setdefault(round(float(p.stem.split("_t")[-1][:-2]), 2), p)
    return out


# ---------------------------------------------------------------- heat release of GA18 on a state
_GAS = None


def heat_release(df, mech):
    """Volumetric heat release [W/m3] of the mechanism evaluated on each row (T, p, Y)."""
    global _GAS
    import cantera as ct
    if _GAS is None:
        _GAS = ct.Solution(str(mech))
    g = _GAS
    cols = [s.lower().replace("(", "<").replace(")", ">") for s in g.species_names]
    Y = np.clip(df[cols].to_numpy(), 0, None)
    Y /= Y.sum(1, keepdims=True)
    arr = ct.SolutionArray(g, len(df))
    arr.TPY = df["temperature"].to_numpy(), df["absolute-pressure"].to_numpy(), Y
    return np.asarray(arr.heat_release_rate)


# ---------------------------------------------------------------- one snapshot
def zone_masks(A, B, P):
    """Fixed zones. State zones are classified on the DI state, so a run cannot move cells between them."""
    TA, TB = A["temperature"].to_numpy(), B["temperature"].to_numpy()
    Z = A["mixture-fraction"].to_numpy()
    x, r = A["x-coordinate"].to_numpy(), A["y-coordinate"].to_numpy()
    hot = (TA > P["T_hot"]) | (TB > P["T_hot"])
    flame = (TA > P["T_flame"]) | (TB > P["T_flame"])
    zs = P["zones"]
    m = {"caliente": hot, "llama": flame}
    m["reactiva"] = hot & ~flame & (Z >= zs["reactiva"]["Z"][0]) & (Z < zs["reactiva"]["Z"][1])
    m["quemado_pobre"] = hot & ~flame & (Z < zs["quemado_pobre"]["Z"][1])
    m["rica"] = hot & ~flame & (Z >= zs["rica"]["Z"][0])
    bx = zs["boquilla"]
    m["boquilla"] = hot & (x < bx["x_max"]) & (r < bx["r_max"])
    return m


def axis_flame(df, P):
    """Base and tip (x, m) of T > T_iso along the axis (r < r_axis); nan if none."""
    a = P["flame_shape"]
    ax = df[(df["y-coordinate"] < a["r_axis"]) & (df["temperature"] > a["T_iso"])]
    if ax.empty:
        return float("nan"), float("nan")
    return float(ax["x-coordinate"].min()), float(ax["x-coordinate"].max())


def snapshot_metrics(A, B, P, mech):
    m = zone_masks(A, B, P)
    V = A["cell-volume"].to_numpy()
    dT = (B["temperature"] - A["temperature"]).to_numpy()
    r = {}
    for z, mk in m.items():
        n = int(mk.sum())
        r[f"n_{z}"] = n
        r[f"absdT_{z}"] = float(np.abs(dT[mk]).mean()) if n else float("nan")
        r[f"biasdT_{z}"] = float(dT[mk].mean()) if n else float("nan")
    hot = m["caliente"]
    r["p95_absdT_caliente"] = float(np.quantile(np.abs(dT[hot]), 0.95)) if hot.any() else float("nan")
    r["max_absdT"] = float(np.abs(dT[hot]).max()) if hot.any() else float("nan")
    r["Tmax_DI"], r["Tmax_run"] = float(A["temperature"].max()), float(B["temperature"].max())
    for s in P["species"]:
        ya, yb = A[s].to_numpy()[hot], B[s].to_numpy()[hot]
        w = V[hot]
        den = (w * ya).sum()
        r[f"L1_{s}"] = float((w * np.abs(yb - ya)).sum() / den) if den > 0 else float("nan")
        r[f"ratio_{s}"] = float((w * yb).sum() / den) if den > 0 else float("nan")
        fl = m["llama"]
        dfl = (V[fl] * A[s].to_numpy()[fl]).sum()
        r[f"L1_{s}_llama"] = float((V[fl] * np.abs(B[s].to_numpy()[fl] - A[s].to_numpy()[fl])).sum() / dfl) \
            if fl.any() and dfl > 0 else float("nan")
    Ti = P["flame_shape"]["T_iso"]
    va, vb = V[A["temperature"] > Ti].sum(), V[B["temperature"] > Ti].sum()
    r["V_hot_DI"], r["V_hot_run"] = float(va), float(vb)
    r["V_hot_ratio"] = float(vb / va) if va > 0 else float("nan")
    (ba, ta), (bb, tb) = axis_flame(A, P), axis_flame(B, P)
    r.update(axis_base_DI=ba, axis_base_run=bb, axis_tip_DI=ta, axis_tip_run=tb,
             d_axis_base_mm=(bb - ba) * 1e3, d_axis_tip_mm=(tb - ta) * 1e3)
    if mech is not None and hot.any():
        qa = heat_release(A[hot], mech)
        qb = heat_release(B[hot], mech)
        w = V[hot]
        Qa, Qb = (w * qa).sum(), (w * qb).sum()
        r["HRR_DI"], r["HRR_run"] = float(Qa), float(Qb)
        r["HRR_ratio"] = float(Qb / Qa) if Qa else float("nan")
        r["HRR_L1"] = float((w * np.abs(qb - qa)).sum() / (w * np.abs(qa)).sum())
    return r


# ---------------------------------------------------------------- logs
COUNTERS = re.compile(r"userChemStep: (\d+) calls, (\d+) advanced, (\d+) frozen, OOD (\d+).*?ODE fallback (\d+)"
                      r".*?invalid (\d+)")


def read_log(path):
    """Per time step: time, s/step, advanced, OOD, ODE fallback, invalid (summed over ranks)."""
    rows, t, prev_exec, cur = [], None, None, None
    if not path or not Path(path).exists():
        return pd.DataFrame(columns=["t", "s_step", "advanced", "ood", "fallback", "invalid"])
    for line in open(path, errors="replace"):
        if line.startswith("Time = "):
            t = float(line.split()[2])
            cur = dict(t=t, s_step=np.nan, advanced=0, ood=0, fallback=0, invalid=0)
            rows.append(cur)
        elif line.startswith("ExecutionTime") and cur is not None:
            e = float(line.split()[2])
            if prev_exec is not None and e >= prev_exec:
                cur["s_step"] = e - prev_exec
            prev_exec = e
        elif cur is not None:
            mm = COUNTERS.search(line)
            if mm:
                cur["advanced"] += int(mm.group(2))
                cur["ood"] += int(mm.group(4))
                cur["fallback"] += int(mm.group(5))
                cur["invalid"] += int(mm.group(6))
    return pd.DataFrame(rows).drop_duplicates("t", keep="last")


def read_minmax(case):
    """Per-step domain Tmax from postProcessing/minMaxT (all restarts)."""
    out = []
    for f in sorted(Path(case).glob("postProcessing/minMaxT/*/fieldMinMax.dat")):
        for line in open(f):
            if line.startswith("#"):
                continue
            p = [x.strip() for x in line.split("\t")]
            if len(p) > 5 and p[1] == "T":
                out.append((float(p[0]), float(p[5])))
    return pd.DataFrame(out, columns=["t", "Tmax"]).drop_duplicates("t", keep="last").sort_values("t")


def ignition_time(curve, T_ign):
    hit = curve[curve.Tmax > T_ign]
    return float(hit.t.iloc[0]) if len(hit) else float("nan")


# ---------------------------------------------------------------- shadow DI
def shadow_by_phase(run_dir, phases):
    try:
        from shadow_report import increment_errors, load
        d = load(run_dir)
    except (SystemExit, ImportError, FileNotFoundError):
        return {}
    d = pd.concat([d, increment_errors(d)], axis=1)
    d["ood"] = (d.ood_flags.astype(int) & 63) > 0
    out = {}
    for name, (t0, t1) in phases.items():
        s = d[(d.time * 1e3 > t0) & (d.time * 1e3 <= t1)]
        if s.empty:
            continue
        out[name] = dict(checks=int(len(s)), ood_checks=int(s.ood.sum()),
                         abs_dT_median=float(s.abs_dT.median()),
                         rel_inc_T_median=float(s.rel_inc_T.median()),
                         rel_inc_OH_median=float(s.rel_inc_OH.median()),
                         rel_inc_CO_median=float(s.rel_inc_CO.median()))
    return out


# ---------------------------------------------------------------- phase summaries
def phase_of(t, phases):
    for name, (t0, t1) in phases.items():
        if t0 < t <= t1 + 1e-9:
            return name
    return None


def summarize(snap, log, curve_run, curve_di, P, status):
    phases = {k: tuple(v) for k, v in P["phases"].items()}
    s = pd.DataFrame(snap).sort_values("t_ms")
    res = {}
    st = s[s.phase == "arranque"]
    t_ign_di = ignition_time(curve_di, P["T_ignition"]) if curve_di is not None else float("nan")
    t_ign_run = ignition_time(curve_run, P["T_ignition"]) if curve_run is not None else float("nan")
    over = float("nan")
    if curve_run is not None and curve_di is not None and len(curve_run) and len(curve_di):
        c = curve_run.merge(curve_di, on="t", suffixes=("_run", "_DI"))
        c = c[c.t <= phases["arranque"][1] * 1e-3 + 1e-9]
        if len(c):
            over = float((c.Tmax_run - c.Tmax_DI).max())
    res["arranque"] = dict(
        snapshots=int(len(st)),
        t_ign_DI_ms=t_ign_di * 1e3, t_ign_run_ms=t_ign_run * 1e3, d_t_ign_ms=(t_ign_run - t_ign_di) * 1e3,
        Tmax_overshoot_K=over,
        absdT_caliente_mean=float(st.absdT_caliente.mean()),
        absdT_boquilla_mean=float(st.absdT_boquilla.mean()),
        biasdT_boquilla_max=float(st.biasdT_boquilla.abs().max()) if len(st) else float("nan"),
        biasdT_boquilla_at_max=float(st.biasdT_boquilla.iloc[st.biasdT_boquilla.abs().argmax()]) if len(st) else float("nan"),
        L1_oh_mean=float(st.L1_oh.mean()),
    )
    for name in ("transicion", "llama"):
        w = s[s.phase == name]
        r = dict(snapshots=int(len(w)))
        for k in ("absdT_llama", "biasdT_llama", "absdT_caliente", "p95_absdT_caliente", "absdT_reactiva",
                  "absdT_quemado_pobre", "absdT_rica", "V_hot_ratio", "d_axis_tip_mm", "d_axis_base_mm",
                  "HRR_ratio", "HRR_L1") + tuple(f"L1_{x}" for x in P["species"]) + \
                tuple(f"L1_{x}_llama" for x in P["species"]) + tuple(f"ratio_{x}" for x in P["species"]):
            if k in w:
                r[k] = float(w[k].mean())
        if name == "llama" and len(w) >= 3:
            a, b = P["drift_window_ms"]
            dw = w[(w.t_ms >= a) & (w.t_ms <= b)]
            if len(dw) >= 3:
                r["deriva_absdT_llama_K_por_10ms"] = float(np.polyfit(dw.t_ms, dw.absdT_llama, 1)[0] * 10)
            f0 = P["final_window_ms"][0]
            fw = w[w.t_ms >= f0]
            r["absdT_llama_final"] = float(fw.absdT_llama.mean()) if len(fw) else float("nan")
        res[name] = r
    for name, (t0, t1) in phases.items():
        lw = log[(log.t * 1e3 > t0) & (log.t * 1e3 <= t1 + 1e-9)]
        adv = lw.advanced.sum()
        res.setdefault(name, {}).update(
            GA18_share=float(lw.fallback.sum() / adv) if adv else float("nan"),
            OOD_share=float(lw.ood.sum() / adv) if adv else float("nan"),
            invalid=int(lw.invalid.sum()),
            s_per_step=float(lw.s_step.median()) if len(lw) else float("nan"),
        )
    res["estado"] = status
    res["t_final_ms"] = float(s.t_ms.max()) if len(s) else 0.0
    res["valida"] = bool(status.startswith("completed") and res["t_final_ms"] >= P["t_min_valid_ms"] - 1e-6)
    return res


# ---------------------------------------------------------------- report
def fmt(v, f="{:.1f}"):
    return "–" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f.format(v)


def write_report(out, label, info, summ, snap, shadow, P):
    s = pd.DataFrame(snap).sort_values("t_ms")
    a, l, tr = summ["arranque"], summ["llama"], summ.get("transicion", {})
    pc = lambda v: fmt(v * 100 if v is not None and np.isfinite(v) else v, "{:.0f} %")
    pc1 = lambda v: fmt(v * 100 if v is not None and np.isfinite(v) else v, "{:.1f} %")
    L = [f"# Protocolo CFD: {label}\n",
         f"Modo: **{info['mode']}**. Modelo: `{info.get('model') or 'GA18 (DI)'}`. "
         f"Estado: {summ['estado']} (hasta {summ['t_final_ms']:.1f} ms). "
         f"Puntuación {'**válida**' if summ['valida'] else '**no válida** (no llega a ' + str(P['t_min_valid_ms']) + ' ms)'}.\n",
         "Todo se mide frente a GA18 DI desde el mismo arranque encendido. Estos estados CFD son solo diagnóstico, "
         "nunca datos de entrenamiento.\n",
         "## (a) Arranque, 0-5 ms\n",
         "| Métrica | Valor |", "|---|---|",
         f"| Tiempo de ignición (Tmax > {P['T_ignition']:.0f} K): DI / modelo / diferencia | "
         f"{fmt(a['t_ign_DI_ms'], '{:.2f}')} / {fmt(a['t_ign_run_ms'], '{:.2f}')} / {fmt(a['d_t_ign_ms'], '{:+.2f}')} ms |",
         f"| Máximo exceso de Tmax del dominio sobre DI | {fmt(a['Tmax_overshoot_K'], '{:+.0f}')} K |",
         f"| Sesgo de T en la boquilla, peor instantánea | {fmt(a['biasdT_boquilla_at_max'], '{:+.0f}')} K |",
         f"| Media abs dT en la boquilla | {fmt(a['absdT_boquilla_mean'])} K |",
         f"| Media abs dT, celdas calientes | {fmt(a['absdT_caliente_mean'])} K |",
         f"| Error L1 de OH, celdas calientes | {pc(a['L1_oh_mean'])} |",
         f"| GA18 / OOD | {pc1(a['GA18_share'])} / {pc1(a['OOD_share'])} |\n",
         "## (b) Llama establecida, 25-100 ms\n",
         "| Métrica | Valor |", "|---|---|",
         f"| **Media abs dT en la llama** (T > {P['T_flame']:.0f} K) | **{fmt(l.get('absdT_llama'))} K** "
         f"(sesgo {fmt(l.get('biasdT_llama'), '{:+.1f}')} K) |",
         f"| Deriva de ese error ({P['drift_window_ms'][0]}-{P['drift_window_ms'][1]} ms) | "
         f"{fmt(l.get('deriva_absdT_llama_K_por_10ms'), '{:+.2f}')} K cada 10 ms |",
         f"| Media abs dT en la llama, últimos 10 ms | {fmt(l.get('absdT_llama_final'))} K |",
         f"| Media abs dT por zona: caliente / reactiva / gas quemado pobre / rica | "
         f"{fmt(l.get('absdT_caliente'))} / {fmt(l.get('absdT_reactiva'))} / {fmt(l.get('absdT_quemado_pobre'))} / "
         f"{fmt(l.get('absdT_rica'))} K |",
         f"| p95 abs dT, celdas calientes | {fmt(l.get('p95_absdT_caliente'), '{:.0f}')} K |"]
    for x in P["species"]:
        L.append(f"| {x.upper()}: error L1 (calientes / llama), cantidad total modelo/DI | "
                 f"{pc(l.get(f'L1_{x}'))} / {pc(l.get(f'L1_{x}_llama'))}, ×{fmt(l.get(f'ratio_{x}'), '{:.2f}')} |")
    L += [f"| Volumen por encima de {P['flame_shape']['T_iso']:.0f} K, modelo/DI | ×{fmt(l.get('V_hot_ratio'), '{:.2f}')} |",
          f"| Punta / base de la llama en el eje, modelo - DI | {fmt(l.get('d_axis_tip_mm'), '{:+.1f}')} / "
          f"{fmt(l.get('d_axis_base_mm'), '{:+.1f}')} mm |",
          f"| Calor liberado (GA18 evaluado en el estado): total modelo/DI, error L1 | "
          f"×{fmt(l.get('HRR_ratio'), '{:.2f}')}, {pc(l.get('HRR_L1'))} |",
          f"| GA18 / OOD | {pc1(l.get('GA18_share'))} / {pc1(l.get('OOD_share'))} |",
          f"| Coste | {fmt(l.get('s_per_step'), '{:.2f}')} s por paso ({info.get('np', '?')} procesos) |\n"]
    L.append(f"Transición 5-25 ms (no puntúa): media abs dT llama {fmt(tr.get('absdT_llama'))} K, "
             f"caliente {fmt(tr.get('absdT_caliente'))} K, GA18 {pc1(tr.get('GA18_share'))}.\n")
    if shadow:
        L += ["## DI en sombra (un paso del modelo frente a un paso de GA18 desde el mismo estado)\n",
              "| Fase | comprobaciones (OOD) | mediana abs dT [K] | error incremento T | OH | CO |", "|---|---|---|---|---|---|"]
        for k, v in shadow.items():
            L.append(f"| {k} | {v['checks']} ({v['ood_checks']}) | {v['abs_dT_median']:.3g} | "
                     f"{pc(v['rel_inc_T_median'])} | {pc(v['rel_inc_OH_median'])} | {pc(v['rel_inc_CO_median'])} |")
        L.append("")
    L += ["## Por instantánea\n",
          "| t [ms] | fase | celdas llama | abs dT llama | sesgo llama | abs dT caliente | abs dT boquilla | "
          "L1 OH | L1 CO | V>1500 ×DI | HRR ×DI | Tmax DI / modelo |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in s.iterrows():
        L.append(f"| {r.t_ms:.1f} | {r.phase} | {r.n_llama} | {fmt(r.absdT_llama)} | {fmt(r.biasdT_llama, '{:+.1f}')} | "
                 f"{fmt(r.absdT_caliente)} | {fmt(r.absdT_boquilla)} | {pc(r.L1_oh)} | {pc(r.L1_co)} | "
                 f"{fmt(r.V_hot_ratio, '{:.2f}')} | {fmt(r.get('HRR_ratio', np.nan), '{:.2f}')} | "
                 f"{r.Tmax_DI:.0f} / {r.Tmax_run:.0f} |")
    (out / "protocol_report.md").write_text("\n".join(L) + "\n")


def plot(out, label, snap, log):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    s = pd.DataFrame(snap).sort_values("t_ms")
    fig, ax = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
    ax[0, 0].plot(s.t_ms, s.absdT_llama, "o-", label="llama")
    ax[0, 0].plot(s.t_ms, s.absdT_caliente, "s-", label="caliente")
    ax[0, 0].plot(s.t_ms, s.absdT_boquilla, "^-", label="boquilla")
    ax[0, 0].set(ylabel="media |dT| [K]")
    ax[0, 0].legend()
    for x in ("oh", "co", "ch4"):
        if f"L1_{x}" in s:
            ax[0, 1].plot(s.t_ms, 100 * s[f"L1_{x}"], "o-", label=x.upper())
    ax[0, 1].set(ylabel="error L1 [%]", yscale="log")
    ax[0, 1].legend()
    ax[1, 0].plot(s.t_ms, s.V_hot_ratio, "o-", label="V(T>1500) ×DI")
    if "HRR_ratio" in s:
        ax[1, 0].plot(s.t_ms, s.HRR_ratio, "s-", label="calor liberado ×DI")
    ax[1, 0].axhline(1, color="k", lw=0.7)
    ax[1, 0].set(xlabel="t [ms]")
    ax[1, 0].legend()
    if len(log) and log.advanced.sum():
        lg = log.copy()
        lg["w"] = (lg.t * 1e3 // 0.5) * 0.5
        g = lg.groupby("w")[["advanced", "ood", "fallback"]].sum()
        ax[1, 1].plot(g.index, 100 * g.fallback / g.advanced, label="GA18")
        ax[1, 1].plot(g.index, 100 * g.ood / g.advanced, label="OOD")
        ax[1, 1].set(ylabel="% de celdas avanzadas")
        ax[1, 1].legend()
    ax[1, 1].set(xlabel="t [ms]")
    for a in ax.flat:
        a.axvline(5, color="0.6", ls=":")
        a.axvline(25, color="0.6", ls=":")
    fig.suptitle(f"{label} frente a GA18 DI")
    fig.tight_layout()
    fig.savefig(out / "protocol_timeseries.png", dpi=120)


def score(a):
    P = load_protocol(a.protocol)
    out = Path(a.out) / a.label
    out.mkdir(parents=True, exist_ok=True)
    di, rn = snapshots(a.di, a.di_label), snapshots([a.run], a.label)
    phases = {k: tuple(v) for k, v in P["phases"].items()}
    mech = None if a.no_hrr else Path(a.mech)
    snap = []
    for t in sorted(set(di) & set(rn)):
        ph = phase_of(t, phases)
        if ph is None:
            continue
        A, B = pd.read_csv(di[t]), pd.read_csv(rn[t])
        r = snapshot_metrics(A, B, P, mech)
        r.update(t_ms=t, phase=ph)
        snap.append(r)
        print(f"{a.label} {t:6.1f} ms: llama {r['absdT_llama']:.1f} K, caliente {r['absdT_caliente']:.1f} K",
              flush=True)
    if not snap:
        raise SystemExit("no common snapshots")
    run_dir = Path(a.run_dir) if a.run_dir else None
    log = read_log(run_dir / "log.run" if run_dir else None)
    curve_run = read_minmax(run_dir) if run_dir else None
    curve_di = read_minmax(a.di_dir) if a.di_dir else None
    status = (run_dir / "protocol_status").read_text().strip() if run_dir and (run_dir / "protocol_status").exists() \
        else "running"
    info = dict(label=a.label, mode="di", model=None, np=None)
    if run_dir and (run_dir / "protocol_run").exists():
        p = (run_dir / "protocol_run").read_text().split()
        info["mode"] = p[0]
        info["model"] = next((x for x in p[1:] if "/" in x), None)
        info["np"] = next((x.split("=")[1] for x in p if x.startswith("np=")), None)
    summ = summarize(snap, log, curve_run, curve_di, P, status)
    shadow = shadow_by_phase(run_dir, phases) if run_dir else {}
    rep = dict(info=info, protocol=P, summary=summ, shadow=shadow, snapshots=snap)
    json.dump(rep, open(out / "protocol_report.json", "w"), indent=1, default=float)
    write_report(out, a.label, info, summ, snap, shadow, P)
    plot(out, a.label, snap, log)
    print((out / "protocol_report.md").read_text())


def compare(a):
    reps = [json.load(open(p)) for p in a.compare]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pc = lambda v: fmt(v * 100 if v is not None and np.isfinite(v) else v, "{:.0f} %")
    pc1 = lambda v: fmt(v * 100 if v is not None and np.isfinite(v) else v, "{:.1f} %")
    L = ["# Protocolo CFD: comparación de modelos\n",
         "Mismo arranque encendido, dt 2e-5 s, frente a GA18 DI. (a) arranque 0-5 ms; (b) llama establecida 25-100 ms. "
         "Datos CFD solo para diagnóstico.\n",
         "| Corrida | modo | hasta [ms] | (a) dt ignición [ms] | (a) sesgo boquilla [K] | (a) abs dT caliente [K] | "
         "(b) **abs dT llama [K]** | (b) deriva [K/10 ms] | (b) últimos 10 ms [K] | (b) abs dT caliente [K] | "
         "(b) L1 OH | (b) L1 CO | (b) L1 CH4 | (b) calor ×DI | (b) GA18 | (b) OOD | s/paso |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in reps:
        s, i = r["summary"], r["info"]
        aa, ll = s["arranque"], s["llama"]
        L.append(f"| {i['label']} | {i['mode']} | {s['t_final_ms']:.0f}{'' if s['valida'] else ' (no válida)'} | "
                 f"{fmt(aa['d_t_ign_ms'], '{:+.2f}')} | {fmt(aa['biasdT_boquilla_at_max'], '{:+.0f}')} | "
                 f"{fmt(aa['absdT_caliente_mean'])} | **{fmt(ll.get('absdT_llama'))}** | "
                 f"{fmt(ll.get('deriva_absdT_llama_K_por_10ms'), '{:+.2f}')} | {fmt(ll.get('absdT_llama_final'))} | "
                 f"{fmt(ll.get('absdT_caliente'))} | {pc(ll.get('L1_oh'))} | {pc(ll.get('L1_co'))} | "
                 f"{pc(ll.get('L1_ch4'))} | ×{fmt(ll.get('HRR_ratio'), '{:.2f}')} | {pc1(ll.get('GA18_share'))} | "
                 f"{pc1(ll.get('OOD_share'))} | {fmt(ll.get('s_per_step'), '{:.2f}')} |")
    (out / "comparacion.md").write_text("\n".join(L) + "\n")
    print((out / "comparacion.md").read_text())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--di", nargs="+", help="DI snapshot dirs (first one wins at a repeated time)")
    ap.add_argument("--di-label", default="di")
    ap.add_argument("--run", help="snapshot dir of the run")
    ap.add_argument("--label")
    ap.add_argument("--run-dir", help="case dir of the run (log.run, minMaxT, shadowDI.csv, protocol_status)")
    ap.add_argument("--di-dir", help="case dir of the DI start-up run (minMaxT for the ignition time)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--protocol", default=None)
    ap.add_argument("--mech", default=str(HERE.parents[1] / "mechanisms" / "ga18.yaml"))
    ap.add_argument("--no-hrr", action="store_true")
    ap.add_argument("--compare", nargs="+", help="protocol_report.json files: write the comparison table")
    a = ap.parse_args()
    compare(a) if a.compare else score(a)


if __name__ == "__main__":
    main()

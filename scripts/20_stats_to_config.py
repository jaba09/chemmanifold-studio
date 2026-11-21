#!/usr/bin/env python3
"""Stage 20: turn the flow statistics of a cheap flame (stage 19) into exploration settings.

Timescale roadmap, step 4. Starts from a base exploration config (the current best, e.g.
configs/burner_openfoam_ood8.yaml) and changes only what the flow statistics say, by fixed rules
(no hand tuning). Bounds are only WIDENED, never narrowed below the base config: the statistics add
what the flow needs (time steps, excess-enthalpy gas, low strain, long relaxation times) and set the
sampling density, but the regimes that fixed earlier failures stay as they are.

Rules (stats = mass-weighted percentiles of the reacting cells, T > 600 K):

  dt_range        min = p1 of tau_cell, max = p99.5 of tau_cell, n = 10 log-spaced, 2 per state;
                  strides drawn with the tau_cell histogram's weight mixed with 30 % uniform
                  (chemmanifold.io.stride_probs); arclength.max_slice_stride 4 (longer dt re-integrated)
  envelope Z      seed density in each z_knots interval = 50 % base + 50 % hot-gas mass share
  psi             envelope.psi_max, pasr.loss_fraction_range[1], burnt_relaxation*.psi_max
                  = max(base, min(0.9, p99.5 psi)); if > 1 % of the hot mass has psi < -0.02,
                  burnt_relaxation_lean.psi_min = max(-0.5, p1 psi of hot cells with Z < 0.06)
  flamelet strain lowest strain a_min = pi chi_st(p1) / exp(-2 erfcinv(2 Z_st)^2); if below the base
                  sweep's start (~0.6 1/s), flame.mdot_fuel_min is scaled down in proportion
  relaxation time burnt_relaxation(_lean).t_max = clip(p50 age of burnt gas (theta > 0.8), base, 0.2 s)

Only flow statistics are read (stats.json; cells.npz for the Z mass shares). No CFD state is
used as a training state.

  python scripts/20_stats_to_config.py --base configs/burner_openfoam_ood8.yaml \\
      --stats data/timescale/wd2 --out configs/burner_openfoam_tix1.yaml --data-dir ../data/openfoam_tix1
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import yaml
from scipy.special import erfcinv

Z_ST = 0.055
A_REF, MDOT_REF = 0.6, 0.004      # base sweep: mdot_fuel_min 0.004 kg/m2/s ~ strain 0.6 1/s (width 0.15 m)


def pct(st, where, q, p):
    v = st[where].get(q)
    return None if v is None else v[st["pcts"].index(p)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--stats", required=True, help="stage-19 output folder of the proxy run")
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    base_text = Path(a.base).read_text()
    cfg = yaml.safe_load(base_text)
    st = json.loads((Path(a.stats) / "stats.json").read_text())
    cells = np.load(Path(a.stats) / "cells.npz")
    why = {}
    cfg["data_dir"] = a.data_dir
    cfg["seed"] = a.seed

    # --- dt range from tau_cell
    t1, t995 = pct(st, "overall", "tau_cell", 1), pct(st, "overall", "tau_cell", 99.5)
    h = st["tau_cell_hist"]
    e = np.asarray(h["log10_edges"])
    m = np.asarray(h["mass"])
    keep = m > 0
    cfg["dt_range"] = dict(min=float(f"{t1:.3g}"), max=float(f"{t995:.3g}"), n=10, per_state=2,
                           uniform_share=0.3,
                           histogram=dict(log10_dt=[round(float(x), 2) for x in (0.5 * (e[1:] + e[:-1]))[keep]],
                                          mass=[round(float(x), 5) for x in m[keep]]))
    cfg["arclength"]["max_slice_stride"] = 4
    why["dt_range"] = f"tau_cell p1 {t1:.3g} s .. p99.5 {t995:.3g} s (p50 {pct(st, 'overall', 'tau_cell', 50):.3g} s)"

    # --- Z seed density
    env = cfg["envelope"]
    zk, uk = np.asarray(env["z_knots"]), np.asarray(env["u_knots"])
    hot = cells["T"] > st["T_min"]
    w = (cells["rho"] * cells["V"])[hot]
    Z = cells["Z"][hot]
    share = np.array([w[(Z >= zk[i]) & (Z < zk[i + 1] + (1e-9 if i == len(zk) - 2 else 0))].sum()
                      for i in range(len(zk) - 1)])
    share = share / share.sum()
    base_share = np.diff(uk)
    new = 0.5 * base_share + 0.5 * share
    env["u_knots"] = [0.0] + [round(float(x), 4) for x in np.cumsum(new)[:-1]] + [1.0]
    why["envelope.u_knots"] = (f"hot-gas mass per Z interval {np.round(share, 3).tolist()} blended 50/50 with base "
                               f"{np.round(base_share, 3).tolist()}")

    # --- heat loss
    p995 = pct(st, "overall", "psi", 99.5)
    target = min(0.9, p995)
    for path in (("envelope", "psi_max"), ("pasr", "burnt_relaxation", "psi_max"),
                 ("pasr", "burnt_relaxation_lean", "psi_max")):
        d = cfg
        for k in path[:-1]:
            d = d[k]
        if path[-1] in d and target > d[path[-1]]:
            d[path[-1]] = round(target, 3)
            why[".".join(path)] = f"psi p99.5 {p995:.3f}"
    lf = cfg["pasr"]["loss_fraction_range"]
    if target > lf[1]:
        lf[1] = round(target, 3)
        why["pasr.loss_fraction_range"] = f"psi p99.5 {p995:.3f}"
    neg = st.get("psi_negative_mass_share", 0.0)
    if neg > 0.01:
        lean = hot & (cells["Z"] < 0.06)
        wl = (cells["rho"] * cells["V"])[lean]
        o = np.argsort(cells["psi"][lean])
        cw = np.cumsum(wl[o]) / wl.sum()
        p1 = float(np.interp(0.01, cw, cells["psi"][lean][o]))
        cfg["pasr"]["burnt_relaxation_lean"]["psi_min"] = round(max(-0.5, p1), 3)
        why["pasr.burnt_relaxation_lean.psi_min"] = (f"{100 * neg:.1f} % of the hot mass has psi < -0.02 "
                                                    f"(excess enthalpy); p1 of lean hot gas {p1:.3f}")

    # --- lowest flamelet strain
    chi1 = pct(st, "z_st", "chi", 1)
    if chi1:
        a_min = math.pi * chi1 / math.exp(-2 * erfcinv(2 * Z_ST) ** 2)
        mdot_base = cfg["flame"]["mdot_fuel_min"]
        a_base = A_REF * mdot_base / MDOT_REF
        if a_min < a_base:
            cfg["flame"]["mdot_fuel_min"] = float(f"{mdot_base * a_min / a_base:.3g}")
            cfg["flame"]["max_flamelets"] = int(cfg["flame"]["max_flamelets"]
                                                + math.ceil(math.log(a_base / a_min) / math.log(cfg["flame"]["strain_factor"])))
            why["flame.mdot_fuel_min"] = f"chi_st p1 {chi1:.3g} 1/s -> strain {a_min:.3g} 1/s < base {a_base:.3g} 1/s"
        else:
            why["flame"] = f"chi_st p1 {chi1:.3g} 1/s -> strain {a_min:.3g} 1/s, inside the base sweep (from {a_base:.3g})"

    # --- relaxation time of burnt gas
    ab = st.get("age_burnt")
    if ab:
        a50 = ab[st["pcts"].index(50)]
        for key in ("burnt_relaxation", "burnt_relaxation_lean"):
            v = cfg["pasr"][key]
            t = float(np.clip(a50, v["t_max"], 0.2))
            if t > v["t_max"]:
                v["t_max"] = round(t, 3)
                why[f"pasr.{key}.t_max"] = f"burnt-gas age p50 {a50:.3g} s (capped at 0.2 s)"

    header = (f"# ChemManifold Studio configuration - flow-informed exploration (timescale roadmap, step 4).\n"
              f"# Written by scripts/20_stats_to_config.py from {a.base} and the flow statistics of\n"
              f"# {st.get('source', a.stats)}. Changes (bounds only widened):\n"
              + "".join(f"#   {k}: {v}\n" for k, v in why.items())
              + "# No CFD state is used as training data; only the statistics above.\n\n")
    Path(a.out).write_text(header + yaml.safe_dump(cfg, sort_keys=False, width=110))
    (Path(a.out).with_suffix(".why.json")).write_text(json.dumps(why, indent=1))
    print(header)


if __name__ == "__main__":
    main()

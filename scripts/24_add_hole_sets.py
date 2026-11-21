#!/usr/bin/env python3
"""Add the 2026-11-10 coverage-hole sets (chemmanifold/holes.py, regimes 15-19) to any exploration config.

Used to turn a stage-20 config (e.g. configs/burner_openfoam_tix2.yaml from the sim1 A3 statistics)
into its "holes" variant without editing it by hand. It copies `pasr.holes` and
`pasr.relaxation_flamedt` from configs/burner_holes1.yaml (or --template), and:

  * scales envelope.n_traj by --regime0-scale (default 0.7: regime 0 was 40 % of tix1's pairs; the new
    sets take its room instead of growing the data set again);
  * sets pasr.burnt_relaxation_lean.psi_min = max(psi_min, 0): the Fluent GA18 DI solution has no hot
    cell with more enthalpy than adiabatic mixing, the excess came from OpenFOAM's Sc = 1 transport.
    Pass --keep-psi-min to keep a negative value (e.g. if a constantLewis reference shows real excess);
  * narrows relaxation_flamedt.dt_window to the config's dt range if that is narrower.

    python scripts/24_add_hole_sets.py --base configs/burner_openfoam_tix2.yaml \\
        --out configs/burner_openfoam_tix2h.yaml --data-dir ../data/openfoam_tix2h
"""

import argparse
import copy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main(a):
    base = yaml.safe_load(open(a.base))
    tpl = yaml.safe_load(open(a.template))
    cfg = copy.deepcopy(base)
    notes = []
    cfg["data_dir"] = a.data_dir
    for key in ("holes", "relaxation_flamedt"):
        cfg["pasr"][key] = copy.deepcopy(tpl["pasr"][key])
    cfg["pasr"]["holes"]["workers"] = a.workers
    n0 = int(cfg["envelope"]["n_traj"])
    cfg["envelope"]["n_traj"] = max(1, int(round(n0 * a.regime0_scale)))
    notes.append(f"envelope.n_traj {n0} -> {cfg['envelope']['n_traj']}")
    lean = cfg["pasr"].get("burnt_relaxation_lean")
    if lean and lean.get("psi_min", 0.0) < 0 and not a.keep_psi_min:
        notes.append(f"pasr.burnt_relaxation_lean.psi_min {lean['psi_min']} -> 0.0")
        lean["psi_min"] = 0.0
    r = cfg.get("dt_range")
    if r:
        w = cfg["pasr"]["relaxation_flamedt"]["dt_window"]
        cfg["pasr"]["relaxation_flamedt"]["dt_window"] = [max(w[0], r["min"]), min(w[1], r["max"])]
    notes.append("pasr.holes (regimes 15-18) and pasr.relaxation_flamedt (regime 19) from " + Path(a.template).name)
    head = "".join(f"#   {n}\n" for n in notes)
    with open(a.out, "w") as f:
        f.write(f"# {Path(a.out).name}: {Path(a.base).name} + coverage-hole sets (scripts/24_add_hole_sets.py)\n"
                f"{head}# No CFD state is used as training data or as a start.\n\n")
        yaml.safe_dump(cfg, f, sort_keys=False)
    print(f"wrote {a.out}:\n{head}", end="")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--data-dir", required=True)
    p.add_argument("--template", default=str(ROOT / "configs" / "burner_holes1.yaml"))
    p.add_argument("--regime0-scale", type=float, default=0.7)
    p.add_argument("--workers", type=int, default=12)
    p.add_argument("--keep-psi-min", action="store_true")
    main(p.parse_args())

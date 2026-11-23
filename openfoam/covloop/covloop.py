#!/usr/bin/env python3
"""COVLOOP driver (docs/COVERAGE-LOOP-ROADMAP.md). Frozen rules in configs/covloop/rules.yaml.

Layout under ROOT:
  general/pairs.npz                       step 1 (scripts/26_general_sampling.py)
  iterK/train_r{0,1}/                     MoE repeats (scripts/27_train_moe.py); r0 is used in the runs
  iterK/runs/<case>_<leg>/{cells,shadow,sentinel}.npz   written by the OpenFOAM post-processing of each leg
  iterK/coverage/<case>_<leg>/            scripts/25_coverage.py output
  iterK/seeded/                           scripts/28_hole_sampling.py output (pairs for iteration K+1)
  STATE.json, DECISIONS.md

Subcommands:
  step1  --config configs/covloop_general.yaml
  train  K                 (iteration K trains on general + all seeded pairs of iterations < K)
  coverage K               (all legs present under iterK/runs) -> headline C, appended to STATE.json
  seed   K                 (hole states of iteration K -> seeded pairs used from iteration K+1)
  decide                   apply the plateau rule, write the verdict in DECISIONS.md
The OpenFOAM legs themselves run on sim1 (openfoam/covloop/run_leg.sh); this driver never launches them.
"""
import argparse, json, os, subprocess, sys, time
import numpy as np
import yaml

ROOT_REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, ROOT_REPO)
from chemmanifold.coverage import plateau   # noqa: E402

PY = sys.executable
MECH = os.path.join(ROOT_REPO, "mechanisms", "arc_gri30_nox22", "gri30_skel43.yaml")


def sh(cmd):
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd)


def state(root):
    p = os.path.join(root, "STATE.json")
    return json.load(open(p)) if os.path.exists(p) else {"iterations": {}}


def save_state(root, s):
    json.dump(s, open(os.path.join(root, "STATE.json"), "w"), indent=1)


def log_decision(root, text):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    with open(os.path.join(root, "DECISIONS.md"), "a") as f:
        f.write(datetime.now(ZoneInfo("Europe/Madrid")).strftime("- %Y-%m-%d %H:%M %Z (Spain): ") + text + "\n")
    print(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--rules", default=os.path.join(ROOT_REPO, "configs", "covloop", "rules.yaml"))
    ap.add_argument("--np", type=int, default=8)
    ap.add_argument("--smoke", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("step1"); s1.add_argument("--config", required=True)
    for c in ("train", "coverage", "seed"):
        sub.add_parser(c).add_argument("K", type=int)
    sub.add_parser("decide")
    a = ap.parse_args()
    R = yaml.safe_load(open(a.rules))
    os.makedirs(a.root, exist_ok=True)
    S = state(a.root)
    smoke = ["--smoke"] if a.smoke else []

    if a.cmd == "step1":
        sh([PY, "-I", os.path.join(ROOT_REPO, "scripts", "26_general_sampling.py"), a.config,
            os.path.join(a.root, "general"), "--np", str(a.np)])

    elif a.cmd == "train":
        pairs = [os.path.join(a.root, "general", "pairs.npz")]
        pairs += [os.path.join(a.root, f"iter{k}", "seeded", "pairs_seeded.npz") for k in range(a.K)]
        pairs = [p for p in pairs if os.path.exists(p)]
        tr = R["training"]
        for r in range(tr["repeats"]):
            sh([PY, "-I", os.path.join(ROOT_REPO, "scripts", "27_train_moe.py"),
                os.path.join(a.root, f"iter{a.K}", f"train_r{r}"), *pairs, "--seed", str(r),
                "--threads", str(a.np), "--experts", str(tr["experts"]),
                "--dt-min", str(tr["dt_min"]), "--dt-max", str(tr["dt_max"]), *smoke])

    elif a.cmd == "coverage":
        it = os.path.join(a.root, f"iter{a.K}")
        legs = {}
        for case, leg in R["legs"]:
            run = os.path.join(it, "runs", f"{case}_{leg}")
            if not os.path.exists(os.path.join(run, "cells.npz")):
                print(f"[coverage] leg {case}_{leg} missing, skipped")
                continue
            out = os.path.join(it, "coverage", f"{case}_{leg}")
            cmd = [PY, "-I", os.path.join(ROOT_REPO, "scripts", "25_coverage.py"), "--mech", MECH,
                   "--cells", os.path.join(run, "cells.npz"), "--out", out]
            for k in ("shadow", "sentinel"):
                if os.path.exists(os.path.join(run, f"{k}.npz")):
                    cmd += [f"--{k}", os.path.join(run, f"{k}.npz")]
            sh(cmd)
            legs[f"{case}_{leg}"] = json.load(open(os.path.join(out, "coverage.json")))
        by_case = {}
        for name, s in legs.items():
            by_case.setdefault(name.split("_")[0], []).append(s["C"])
        C = float(np.mean([np.mean(v) for v in by_case.values()])) if by_case else float("nan")
        S["iterations"][str(a.K)] = {"C": C, "legs": legs, "cases": sorted(by_case)}
        save_state(a.root, S)
        log_decision(a.root, f"iteration {a.K}: headline C = {C:.4f} (" +
                     ", ".join(f"{k} {v['C']:.3f}" for k, v in legs.items()) + ")")

    elif a.cmd == "seed":
        it = os.path.join(a.root, f"iter{a.K}")
        holes = [os.path.join(it, "coverage", d, "hole_states.npz")
                 for d in sorted(os.listdir(os.path.join(it, "coverage")))]
        prev = [os.path.join(a.root, f"iter{k}", "seeded", "starts_used.npz") for k in range(a.K)]
        sd = R["seeding"]
        sh([PY, "-I", os.path.join(ROOT_REPO, "scripts", "28_hole_sampling.py"), os.path.join(it, "seeded"),
            *[h for h in holes if os.path.exists(h)], "--general", os.path.join(a.root, "general", "pairs.npz"),
            "--previous", *[p for p in prev if os.path.exists(p)], "--max-starts", str(sd["max_starts"]),
            "--per-start", str(sd["per_start"]), "--np", str(a.np),
            "--dt-min", str(R["training"]["dt_min"]), "--dt-max", str(R["training"]["dt_max"])])

    elif a.cmd == "decide":
        ks = sorted(int(k) for k in S["iterations"])
        hist = [S["iterations"][str(k)]["C"] for k in ks]
        spread = S.get("repeat_spread", 0.0)
        st = R["stop"]
        stop = plateau(hist, spread=spread * st["spread_factor"] / 2.0, min_gain=st["min_gain"],
                       patience=st["patience"], target=st["target"], max_iter=st["max_iterations"])
        log_decision(a.root, f"decide after iterations {ks}: C = {[round(c, 4) for c in hist]} -> "
                     + ("STOP (plateau / target / max iterations): run the final evaluation" if stop
                        else f"CONTINUE with iteration {ks[-1] + 1}"))
        S["stop"] = bool(stop)
        save_state(a.root, S)


if __name__ == "__main__":
    main()

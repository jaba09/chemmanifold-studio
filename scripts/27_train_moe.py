#!/usr/bin/env python3
"""COVLOOP: train the top-2 MoE (dt in, dY out, CPU) on physics-exploration pairs and export it.

  python scripts/27_train_moe.py OUT_DIR pairs.npz [more_pairs.npz ...] [--segments segments.npz ...]
         [--seed 0] [--threads 8] [--smoke] [--no-rollout]
Writes OUT_DIR/moe.npz (+ .json) and OUT_DIR/chemmanifold_model.txt (C core, arch moe_top2).
Refuses any pairs file whose `origin` says CFD/DI (javier-methodology): starting states from CFD are flagged
`excluded` by step 4 and never reach this script.
"""
import argparse, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from chemmanifold.moe import MoEConfig, MoESurrogate, RolloutThermo, write_core_model

SKEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mechanisms", "arc_gri30_nox22",
                    "gri30_skel43.yaml")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("pairs", nargs="+")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--experts", type=int, default=6)
    ap.add_argument("--dt-min", type=float, default=1e-6)
    ap.add_argument("--dt-max", type=float, default=1e-3)
    ap.add_argument("--segments", nargs="*", default=[], help="reference segments for the rollout loss")
    ap.add_argument("--no-rollout", action="store_true")
    ap.add_argument("--mech", default=SKEL, help="thermo source for the rollout T inversion")
    ap.add_argument("--smoke", action="store_true", help="tiny network and epochs (pipeline test only)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    D = {k: [] for k in ("T", "Y", "dt", "dY")}
    species = None
    for p in a.pairs:
        d = np.load(p, allow_pickle=True)
        if "origin" in d and any(str(o).lower() in ("cfd", "di", "shadow") for o in np.unique(d["origin"])):
            sys.exit(f"{p}: contains CFD/DI pairs; COVLOOP trains on physics exploration only")
        keep = ~d["excluded"] if "excluded" in d else np.ones(len(d["T"]), bool)
        sp = [str(s) for s in d["species"]]
        if species is None:
            species = sp
        elif sp != species:
            sys.exit(f"{p}: species order differs")
        for k in D:
            D[k].append(d[k][keep])
    D = {k: np.concatenate(v) for k, v in D.items()}
    cfg = MoEConfig(n_experts=a.experts, seed=a.seed, threads=a.threads, species=species,
                    dt_min=a.dt_min, dt_max=a.dt_max)
    if a.smoke:
        cfg.expert_hidden, cfg.router_hidden = 32, 16
        cfg.epochs_router, cfg.epochs_expert, cfg.epochs_joint = 3, 5, 5
    seg = None
    if a.segments and not a.no_rollout:
        parts = [np.load(p, allow_pickle=True) for p in a.segments]
        for p, d in zip(a.segments, parts):
            if [str(x) for x in d["species"]] != species:
                sys.exit(f"{p}: species order differs")
        seg = {k: np.concatenate([d[k] for d in parts]) for k in ("T0", "Y0", "dt", "Tref", "Yref")}
    else:
        cfg.w_rollout = 0.0
    t0 = time.time()
    log = open(os.path.join(a.out, "train.log"), "w")
    m = MoESurrogate(cfg).fit(D["T"], D["Y"], D["dt"], D["dY"],
                              log=lambda s: (print(s, flush=True), log.write(s + "\n"), log.flush()),
                              segments=seg, thermo=RolloutThermo(species, a.mech) if seg is not None else None)
    m.history["train_s"] = time.time() - t0
    m.history["n_pairs"] = int(len(D["T"]))
    m.save(os.path.join(a.out, "moe.npz"))
    write_core_model(os.path.join(a.out, "chemmanifold_model.txt"), m.arrays, species)
    print(f"trained on {len(D['T'])} pairs in {m.history['train_s']:.0f} s -> {a.out}")


if __name__ == "__main__":
    main()

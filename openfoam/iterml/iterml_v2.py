#!/usr/bin/env python3
"""ITERML on the radiation reference (sim1 C3): openfoam/iterml/iterml.py's loop, adapted to

  - the corrected LeFoam + constantLewis + fvDOM case and protocol v2 (A1r/A2r references, score_v2 S);
  - an ENSEMBLE parent: iteration 0 is a family's training repeats (default tix2h s0-s2), scored as their mean
    ensemble (results/sim1/B/<label>/score_v2.json, no rerun);
  - each iteration trains one repeat per parent member (warm start member i -> repeat i, so the ensemble stays
    diverse), in parallel, and is scored with protocol v2 as the mean ensemble of its repeats;
  - acceptance on that single ensemble score: accepted if S < best S x (1 - accept_margin) (settings `rules`,
    frozen before the run). The elitism spread rule of rules.accept needs per-seed scores, which an ensemble
    score does not have; the margin plays its role;
  - two collection legs per iteration (hybrid, OOD / untrusted cells on GA18, states stored only as SEEDS of the
    next physics exploration): the ignition start (lean phi 0.5, 0-25 ms) and the flame state (A1r at 0.1 s,
    25 ms). The collection uses member 0 of the parent (the ISANN store does not take ensemble files).

CFD states are never training pairs: they seed Cantera reactors (stage 4 pasr.seeded), seed state excluded.

    iterml_v2.py --settings configs/iterml/iterml_v2_tix2h.yaml --root /opt/ofb/iterml_v2 auto
    iterml_v2.py ... run --iter 1          (one iteration by hand)
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import iterml as v1  # noqa: E402
from iterml import Loop, log, sh, spain_now, read_status, PY, REPO, OFENV  # noqa: E402


class LoopV2(Loop):
    # --- parent members -----------------------------------------------------------------------------
    def members(self, k):
        """[(model dir with chemmanifold_model.txt, model.pt)] of the parent ensemble of iteration k."""
        p = self.parent_of(k)
        if p == 0:
            i0 = self.s["iter0"]
            return [(Path(m), Path(t)) for m, t in zip(i0["members"], i0["members_pt"])]
        d = self.it(p) / "data"
        return [(d / "08_fluent" / self.mdir(t), d / "06_models" / self.mdir(t) / "model.pt") for t in self.tags()]

    def parent_model_dir(self, k):            # collection + seeds: member 0 of the parent
        return self.members(k)[0][0]

    def parent_model_pt(self, k):
        return self.members(k)[0][1]

    # --- [A] collection: ignition leg + flame leg ---------------------------------------------------
    def collect(self, k):
        c, st = self.s["collect"], self.s["collect"]["stop"]
        info_all = {}
        for leg, base in self.s["collect_bases"].items():
            run = self.it(k) / f"collect_{leg}"
            t0, t_end = float(base["t0"]), float(base["t_end"])
            if self.dry:
                t_end = t0 + 0.002
            if f"collect_{leg}" in self.state(k):
                continue
            if not run.exists():
                sen = " ".join(str(v) for v in c["sentinel"])
                sh(f"{HERE}/setup_collect.sh {base['case']} {run} {self.parent_model_dir(k)} {self.s['n_procs']} "
                   f"{c['shadow_every']} {c['shadow_per_bin']} {c['cap_per_box']} '{sen}' {c['sentinel_every']} "
                   f"{c['sentinel_per_step']}", env_of=True, logfile=self.it(k) / "setup.log")
            sh(f"foamDictionary -entry endTime -set {t_end} system/controlDict > /dev/null && "
               f"foamDictionary -entry startFrom -set latestTime system/controlDict > /dev/null && "
               f"foamDictionary -entry stopAt -set endTime system/controlDict > /dev/null && "
               f"foamDictionary -entry writeControl -set runTime system/controlDict > /dev/null && "
               f"foamDictionary -entry writeInterval -set 0.0025 system/controlDict > /dev/null && "
               f"foamDictionary -entry purgeWrite -set 2 system/controlDict > /dev/null", cwd=run, env_of=True)
            log(self.it(k), f"collection leg {leg}: {t0 * 1e3:.1f} -> {t_end * 1e3:.1f} ms ({self.s['n_procs']} ranks)")
            proc = subprocess.Popen(["bash", "-c", f". {OFENV} && mpirun -np {self.s['n_procs']} "
                                     "$(foamDictionary -entry application -value system/controlDict) -parallel "
                                     ">> log.run 2>&1"], cwd=run)
            reason, ood_run = None, 0
            while proc.poll() is None:
                time.sleep(10 if self.dry else st["check_s"])
                reason, ood_run = self.stop_reason(run, st, ood_run)
                if reason:
                    log(self.it(k), f"{leg}: inner stop: {reason}; writing and stopping")
                    sh("foamDictionary -entry stopAt -set writeNow system/controlDict > /dev/null", cwd=run, env_of=True)
                    proc.wait()
            if proc.returncode != 0 and not reason:
                reason = f"solver exited with {proc.returncode} (divergence?)"
                log(self.it(k), f"{leg}: {reason}")
            stt = read_status(run)
            info = dict(reason=reason or "t_end", steps=int(stt["step"].max()) if len(stt) else 0,
                        stored=int(stt["stored"].iloc[-1]) if len(stt) else 0)
            self.done(k, f"collect_{leg}", **info)
            info_all[leg] = info
            log(self.it(k), f"collection leg {leg} done: {info}")
        self.done(k, "collect", **{f"{a}_{b}": v for a, d in info_all.items() for b, v in d.items()})

    def seeds(self, k):
        cfg_p = self.config_path(k)
        self.write_config(k)
        self.link_data(k)
        runs = " ".join(str(self.it(k) / f"collect_{leg}") for leg in self.s["collect_bases"])
        md = self.parent_model_dir(k)
        sh(f"{PY} {REPO}/scripts/19_iterml_seeds.py --config {cfg_p} --runs {runs} "
           f"--model {md / 'chemmanifold_model.txt'} --scalers {self.parent_data(k) / '04_prep' / 'scalers.json'} "
           f"--out {self.it(k) / 'seeds'}" + self.previous_seeds(k), logfile=self.it(k) / "seeds.log")
        n = len(np.load(self.it(k) / "seeds" / "seeds.npz")["T"])
        self.done(k, "seeds", n_seeds=n)
        log(self.it(k), f"{n} seeds")

    # --- [D] training: one repeat per parent member, in parallel -------------------------------------
    def train(self, k):
        c, lg = self.config_path(k), self.it(k) / "train.log"
        log(self.it(k), "stage 05_preprocess.py")
        sh(f"{PY} {REPO}/scripts/05_preprocess.py --config {c}", logfile=lg)
        cfg = yaml.safe_load(open(c))
        seed0 = int(cfg.get("seed", 0))
        threads = list(self.s["train"].get("threads_per_repeat", [3, 3, 2]))
        procs = []
        for i, (tag, (md, pt)) in enumerate(zip(self.tags(), self.members(k))):
            ci = cfg.copy()
            ci["training"] = dict(cfg["training"], init_from=str(pt), threads=threads[i % len(threads)])
            cp = self.it(k) / f"iterml_iter{k}_{tag or 's0'}.yaml"
            with open(cp, "w") as f:
                f.write(f"# ITERML v2 iteration {k}, repeat {tag or 's0'}: warm start from parent member {i} ({pt})\n")
                yaml.safe_dump(ci, f, sort_keys=False)
            extra = f" --seed {seed0 + 100 * i}" + (f" --tag {tag}" if tag else "")
            cmd = (f"OMP_NUM_THREADS={ci['training']['threads']} {PY} {REPO}/scripts/07_train.py --config {cp}{extra} && "
                   f"{PY} {REPO}/scripts/12_export_fluent.py --config {cp}" + (f" --tag {tag}" if tag else ""))
            log(self.it(k), f"training repeat {tag or 's0'} (warm start from member {i}, {ci['training']['threads']} threads)")
            procs.append((tag, subprocess.Popen(["bash", "-c", cmd + f" >> {self.it(k)}/train_{tag or 's0'}.log 2>&1"])))
        info_all = {}
        for tag, p in procs:
            p.wait()
            if p.returncode != 0:
                raise RuntimeError(f"training repeat {tag or 's0'} failed ({p.returncode})")
            ti = json.load(open(self.it(k) / "data" / "06_models" / self.mdir(tag) / "train_info.json"))
            info_all[tag or "s0"] = dict(best_val_loss=ti.get("best_val_loss"), best_epoch=ti.get("best_epoch"),
                                         wall_time_s=ti.get("wall_time_s"))
        try:
            sh(f"{PY} {REPO}/scripts/15_register_model.py --config {c}", logfile=lg)
        except RuntimeError as e:
            log(self.it(k), f"registry: {e}")
        self.done(k, "train", **info_all)

    # --- [F] evaluation: protocol v2 on the mean ensemble of the repeats ----------------------------
    def label(self, k):
        return f"{self.s.get('label_prefix', 'C3')}_iter{k}"

    def eval(self, k, tag=""):
        e = self.it(k) / "ensemble"
        if not (e / "chemmanifold_ensemble.txt").exists():
            e.mkdir(exist_ok=True)
            spec = dict(blend="mean", note=f"{self.label(k)} = mean of the iteration-{k} repeats",
                        members=[dict(path=str(self.it(k) / "data" / "08_fluent" / self.mdir(t) / "chemmanifold_model.txt"))
                                 for t in self.tags()])
            yaml.safe_dump(spec, open(e / "spec.yaml", "w"), sort_keys=False)
            sh(f"{PY} {REPO}/scripts/make_ensemble.py --config {self.config_path(k)} --spec {e / 'spec.yaml'} --out {e}",
               logfile=self.it(k) / "eval.log")
            txt = (e / "chemmanifold_ensemble.txt").read_text().splitlines()
            out = []
            for line in txt:                       # absolute member paths (relative ones break when copied)
                if line.startswith("member "):
                    parts = line.split()
                    parts[1] = str((e / parts[1]).resolve())
                    line = " ".join(parts)
                out.append(line)
            (e / "chemmanifold_ensemble.txt").write_text("\n".join(out) + "\n")
        lst = self.it(k) / "eval_candidates.txt"
        lst.write_text(f"{self.label(k)} {e}\n")
        sh(f"PB_RUNS={self.root / 'protocol'} PB_OUT={self.s['results_dir']} SLOTS=1 {REPO}/server/sim1/phaseB.sh {lst}",
           env_of=True, logfile=self.it(k) / "eval.log")
        self.done(k, "eval", score=str(Path(self.s["results_dir"]) / self.label(k) / "score_v2.json"))

    def steps(self):
        return ["collect", "seeds", "explore", "train", "bench", "eval", "report"]

    def run(self, k, only=None):
        for step in ([only] if only else self.steps()):
            if not only and step in self.state(k):
                continue
            log(self.it(k), f"--- {step} (iteration {k}) ---")
            getattr(self, step)(k)

    # --- scores and the automatic loop --------------------------------------------------------------
    def score_of(self, k):
        p = Path(self.s["iter0"]["score"]) if k == 0 else Path(self.s["results_dir"]) / self.label(k) / "score_v2.json"
        if not p.exists():
            return dict(S=float("inf"), valid=False)
        d = json.load(open(p))
        return d if d.get("valid") else dict(d, S=float("inf"))

    def baseline(self):
        if self.best():
            return
        sc = self.score_of(0)
        json.dump(dict(iter=0, tag="", S=sc["S"], score=sc), open(self.root / "best.json", "w"), indent=1, default=float)
        self.decide(f"baseline: iteration 0 = {self.s['iter0']['label']} (ensemble) S = {sc['S']:.2f} "
                    f"(F {sc.get('F', float('nan')):.2f}, I {sc.get('I', float('nan')):.2f}, C {sc.get('C', float('nan')):.2f})")

    def auto(self, k_max):
        r = self.s["rules"]
        margin = float(r["accept_margin"])
        self.root.mkdir(parents=True, exist_ok=True)
        self.baseline()
        rej = 0
        for k in range(1, int(k_max) + 1):
            st = self.state(k)
            if "decision" in st:
                rej = 0 if st["decision"]["accepted"] else rej + 1
                continue
            best = self.best()
            why = v1.rules.stop(best["S"], rej, k - 1, r)
            if why:
                self.decide(f"STOP before iteration {k}: {why}; best = iteration {best['iter']} (S {best['S']:.2f})")
                return
            if "parent" not in st:
                st["parent"] = dict(iter=best["iter"], tag="")
                json.dump(st, open(self.it(k) / "state.json", "w"), indent=1)
                self.decide(f"iteration {k} starts from iteration {best['iter']} (the best, S {best['S']:.2f})")
            self.run(k)
            sc = self.score_of(k)
            ok = bool(np.isfinite(sc["S"]) and sc["S"] < best["S"] * (1 - margin))
            reason = (f"ensemble S {sc['S']:.2f} vs best {best['S']:.2f}: "
                      + (f"better by more than {margin:.0%}" if ok else f"not better by more than {margin:.0%}"))
            st = self.state(k)
            st["decision"] = dict(accepted=ok, reason=reason, score=sc)
            json.dump(st, open(self.it(k) / "state.json", "w"), indent=1, default=float)
            if ok:
                json.dump(dict(iter=k, tag="", S=sc["S"], score=sc), open(self.root / "best.json", "w"), indent=1, default=float)
                rej = 0
            else:
                rej += 1
            self.decide(f"iteration {k}: {'ACCEPTED' if ok else 'rejected'}: {reason}")
        best = self.best()
        self.decide(f"STOP after iteration {k_max} (maximum); best = iteration {best['iter']} (S {best['S']:.2f})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--settings", required=True)
    ap.add_argument("--root", default="/opt/ofb/iterml_v2")
    ap.add_argument("--dry", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--iter", type=int, required=True)
    s = sub.add_parser("step")
    s.add_argument("name")
    s.add_argument("--iter", type=int, required=True)
    au = sub.add_parser("auto")
    au.add_argument("--max", type=int, default=None)
    a = ap.parse_args()
    loop = LoopV2(a.settings, a.root if not a.dry else str(Path(a.root) / "dry"), a.dry)
    if a.cmd == "auto":
        loop.auto(a.max or loop.s["rules"]["max_iterations"])
    elif a.cmd == "run":
        loop.run(a.iter)
    else:
        loop.run(a.iter, a.name)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""ITERML loop driver (docs/ITERML-ROADMAP.md): collection run -> seeds -> seeded physics exploration
-> warm-start training -> gate -> pure CFD evaluation, one iteration at a time, resumable.

    iterml.py --settings configs/iterml/iterml.yaml --root /opt/ofb/iterml run --iter 1 [--dry]
    iterml.py ... step <collect|seeds|explore|train|bench|eval|report> --iter K [--dry]

Each step writes <root>/iterK/state.json when it finishes, so `run` skips what is done and a
restarted container continues where it stopped (the CFD legs resume from their latest write).
--dry is the short test of step S6: 5 ms collection, few seeds and picks, 10 epochs, 5 ms evaluation.

Rules kept by construction: the CFD states of the run are only SEEDS (stage 19 -> stage 4 seeded
reactors, the seeds themselves never paired); the shadow DI comparisons are saved and never trained on.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "openfoam" / "isann"))
from isann_lib import read_status  # noqa: E402

PY = sys.executable
OFENV = os.environ.get("OFENV", "/opt/ofb/ofenv.sh")
STEPS = ["collect", "seeds", "explore", "train", "bench", "eval", "report"]


def spain_now():
    t = datetime.now(timezone.utc)
    # Europe/Madrid: CET (UTC+1) from the last Sunday of October to the last Sunday of March
    return (t + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M CET")


def log(it_dir, msg):
    line = f"[{spain_now()}] {msg}"
    print(line, flush=True)
    with open(it_dir / "iterml.log", "a") as f:
        f.write(line + "\n")


def sh(cmd, cwd=None, logfile=None, env_of=False):
    """Run a command (in the OpenFOAM environment with env_of); raise on failure."""
    if env_of:
        cmd = f". {OFENV} && {cmd}"
    out = open(logfile, "a") if logfile else None
    r = subprocess.run(["bash", "-c", cmd], cwd=cwd, stdout=out or None, stderr=subprocess.STDOUT if out else None)
    if out:
        out.close()
    if r.returncode != 0:
        raise RuntimeError(f"failed ({r.returncode}): {cmd}")


class Loop:
    def __init__(self, settings, root, dry):
        self.sp = Path(settings).resolve()
        self.s = yaml.safe_load(open(self.sp))
        self.root = Path(root)
        self.dry = dry

    # --- paths ------------------------------------------------------------------------------------
    def it(self, k):
        d = self.root / f"iter{k}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def state(self, k):
        p = self.it(k) / "state.json"
        return json.load(open(p)) if p.exists() else {}

    def done(self, k, step, **info):
        st = self.state(k)
        st[step] = dict(done=spain_now(), **info)
        json.dump(st, open(self.it(k) / "state.json", "w"), indent=1)

    def parent_data(self, k):
        return Path(self.s["iter0"]["data"]) if k == 1 else self.it(k - 1) / "data"

    def parent_model_dir(self, k):
        """Directory with the parent's chemmanifold_model.txt (+ tests)."""
        if k == 1:
            return Path(self.s["iter0"]["model_dir"])
        return self.it(k - 1) / "data" / "08_fluent" / "resnet_film"

    def config_path(self, k):
        return self.it(k) / f"iterml_iter{k}.yaml"

    # --- [A] collection run -------------------------------------------------------------------------
    def collect(self, k):
        c = self.s["collect"]
        st = c["stop"]
        t_end = 0.005 if self.dry else c["t_end"]
        run = self.it(k) / "collect"
        if not run.exists():
            sen = " ".join(str(v) for v in c["sentinel"])
            sh(f"{HERE}/setup_collect.sh {self.s['base_case']} {run} {self.parent_model_dir(k)} {self.s['n_procs']} "
               f"{c['shadow_every']} {c['shadow_per_bin']} {c['cap_per_box']} '{sen}' {c['sentinel_every']} "
               f"{c['sentinel_per_step']}", env_of=True, logfile=self.it(k) / "setup.log")
        sh(f"foamDictionary -entry endTime -set {t_end} system/controlDict > /dev/null && "
           f"foamDictionary -entry startFrom -set latestTime system/controlDict > /dev/null && "
           f"foamDictionary -entry stopAt -set endTime system/controlDict > /dev/null", cwd=run, env_of=True)
        log(self.it(k), f"collection run to {t_end * 1e3:.1f} ms ({self.s['n_procs']} ranks)")
        proc = subprocess.Popen(["bash", "-c", f". {OFENV} && mpirun -np {self.s['n_procs']} "
                                 "rhoReactingBuoyantFoam -parallel >> log.run 2>&1"], cwd=run)
        reason, ood_run = None, 0
        while proc.poll() is None:
            time.sleep(10 if self.dry else st["check_s"])
            reason, ood_run = self.stop_reason(run, st, ood_run)
            if reason:
                log(self.it(k), f"inner stop: {reason}; writing and stopping")
                sh("foamDictionary -entry stopAt -set writeNow system/controlDict > /dev/null", cwd=run, env_of=True)
                proc.wait()
        if proc.returncode != 0 and not reason:
            reason = f"solver exited with {proc.returncode} (divergence?)"
            log(self.it(k), reason)
        stt = read_status(run)
        info = dict(reason=reason or "t_end", steps=int(stt["step"].max()) if len(stt) else 0,
                    stored=int(stt["stored"].iloc[-1]) if len(stt) else 0)
        self.done(k, "collect", **info)
        log(self.it(k), f"collection done: {info}")

    @staticmethod
    def stop_reason(run, st, ood_run):
        d = read_status(run)
        if len(d) < 2:
            return None, ood_run
        stored, boxes = d["stored"].to_numpy(), d["boxes"].to_numpy()
        if stored[-1] >= st["max_seeds"]:
            return f"{stored[-1]} states stored (max {st['max_seeds']})", ood_run
        w = int(st["saturation_window"])
        if len(d) > w and stored[-1] >= st["min_seeds"]:
            new = boxes[-1] - boxes[-1 - w]
            if new < st["saturation"] * boxes[-1]:
                return f"saturated: {new} new boxes in {w} steps of {boxes[-1]}", ood_run
        share = d["ood"].to_numpy() / np.maximum(d["hot"].to_numpy(), 1)
        tail = 0
        for x in share[::-1]:
            if x <= st["ood_share"]:
                break
            tail += 1
        if tail >= st["ood_steps"]:
            return f"model lost: OOD share > {st['ood_share']:.0%} for {tail} steps", tail
        return None, tail

    # --- [B] seeds ------------------------------------------------------------------------------------
    def write_config(self, k):
        base = (self.sp.parent / self.s["base_config"]).resolve()
        cfg = yaml.safe_load(open(base))
        cfg["data_dir"] = "data"
        cfg["chemistry"]["mechanism"] = str((base.parent.parent / cfg["chemistry"]["mechanism"]).resolve()) \
            if not Path(cfg["chemistry"]["mechanism"]).is_absolute() else cfg["chemistry"]["mechanism"]
        cfg["seed"] = int(cfg.get("seed", 0)) + k
        seeded = dict(self.s["seeded"])
        if self.dry:
            seeded.update(starts_per_seed=2, n_pick=6)
        seeded.update(files=[str(self.it(k) / "seeds" / "seeds.npz")], out=f"pairs_seeded_iter{k}.npz")
        cfg["pasr"]["seeded"] = seeded
        cfg["iterml"] = dict(iteration=k, seeds=self.s["seeds"], parent=str(self.parent_model_dir(k)))
        tr = self.s["train"]
        cfg["model"].update(tr["model"])
        iter0_scalers = Path(self.s["iter0"]["data"]) / "04_prep" / "scalers.json"
        cfg.setdefault("preprocess", {})["scalers_from"] = str(iter0_scalers)
        scratch = tr.get("scratch_every") and k % int(tr["scratch_every"]) == 0
        if not scratch:
            cfg["training"].update(tr["training"])
            cfg["training"]["init_from"] = str(self.parent_data(k) / "06_models" / "resnet_film" / "model.pt")
        if self.dry:
            cfg["training"]["epochs"] = 10
        hdr = (f"# ITERML iteration {k} ({spain_now()}): {base.name} + configs/iterml/iterml.yaml overrides.\n"
               f"# Training pairs: the a priori data of iteration 0, the seeded pairs of earlier iterations and\n"
               f"# pairs_seeded_iter{k}.npz (Cantera reactors started from the seeds of the iteration-{k} run).\n"
               f"# No CFD state is a training pair.\n")
        with open(self.config_path(k), "w") as f:
            f.write(hdr)
            yaml.safe_dump(cfg, f, sort_keys=False)
        return cfg

    def seeds(self, k):
        cfg_p = self.config_path(k)
        self.write_config(k)
        self.link_data(k)
        md = self.parent_model_dir(k)
        sh(f"{PY} {REPO}/scripts/19_iterml_seeds.py --config {cfg_p} --runs {self.it(k) / 'collect'} "
           f"--model {md / 'chemmanifold_model.txt'} --scalers {self.parent_data(k) / '04_prep' / 'scalers.json'} "
           f"--out {self.it(k) / 'seeds'}", logfile=self.it(k) / "seeds.log")
        n = len(np.load(self.it(k) / "seeds" / "seeds.npz")["T"])
        if self.dry and n > 500:
            d = dict(np.load(self.it(k) / "seeds" / "seeds.npz"))
            pick = np.random.default_rng(0).choice(n, 500, replace=False)
            np.savez(self.it(k) / "seeds" / "seeds.npz", **{key: (v[pick] if v.shape[:1] == (n,) else v) for key, v in d.items()})
            n = 500
        self.done(k, "seeds", n_seeds=n)
        log(self.it(k), f"{n} seeds")

    def link_data(self, k):
        """iterK/data: links to the parent's flame reference and every pairs file (a priori + seeded)."""
        d, p = self.it(k) / "data", self.parent_data(k)
        (d / "03_samples").mkdir(parents=True, exist_ok=True)
        for sub in ("00_flame",):
            if not (d / sub).exists():
                os.symlink((p / sub).resolve(), d / sub)
        for f in sorted((p / "03_samples").iterdir()):
            t = d / "03_samples" / f.name
            if not t.exists() and f.name != f"pairs_seeded_iter{k}.npz":
                os.symlink(f.resolve(), t)

    # --- [C] seeded exploration ---------------------------------------------------------------------
    def explore(self, k):
        sh(f"{PY} {REPO}/scripts/04_pasr_ensemble.py --config {self.config_path(k)} --only seeded",
           logfile=self.it(k) / "explore.log")
        n = len(np.load(self.it(k) / "data" / "03_samples" / f"pairs_seeded_iter{k}.npz")["dt"])
        self.done(k, "explore", seeded_pairs=n)
        log(self.it(k), f"{n} seeded pairs")

    # --- [D] training -------------------------------------------------------------------------------
    def train(self, k):
        c, lg = self.config_path(k), self.it(k) / "train.log"
        for script in ("05_preprocess.py", "07_train.py", "12_export_fluent.py"):
            log(self.it(k), f"stage {script}")
            sh(f"{PY} {REPO}/scripts/{script} --config {c}", logfile=lg)
        try:
            if self.dry:
                raise RuntimeError("dry run: not registered")
            sh(f"{PY} {REPO}/scripts/15_register_model.py --config {c}", logfile=lg)
        except RuntimeError as e:   # the registry is documentation; it must not stop the loop
            log(self.it(k), f"registry: {e}")
        info = json.load(open(self.it(k) / "data" / "06_models" / "resnet_film" / "train_info.json"))
        self.done(k, "train", best_val_loss=info.get("best_val_loss"), best_epoch=info.get("best_epoch"),
                  wall_time_s=info.get("wall_time_s"))

    # --- [E] gate: offline benchmark ---------------------------------------------------------------
    def bench(self, k):
        out = self.it(k) / "bench"
        n = 10 if self.dry else self.s["gate"]["n_states"]
        steps = 500 if self.dry else 2500
        sh(f"{PY} {REPO}/scripts/18_offline_benchmark.py --config {self.config_path(k)} "
           f"--models parent={self.parent_model_dir(k) / 'chemmanifold_model.txt'} "
           f"iter{k}={self.it(k) / 'data' / '08_fluent' / 'resnet_film' / 'chemmanifold_model.txt'} "
           f"--label iter{k} --out {out} --n-states {n} --steps {steps} --workers {self.s['n_procs']}",
           logfile=self.it(k) / "bench.log")
        m = json.load(open(out / "benchmark.json"))["models"]
        dt10 = {name: m[name]["alone"]["all"]["dT_10ms"]["mean"] for name in ("parent", f"iter{k}")}
        ok = dt10[f"iter{k}"] <= dt10["parent"] + float(self.s["gate"]["seed_spread_K"])
        log(self.it(k), f"gate: alone dT_10ms parent {dt10['parent']:.1f} K, iter{k} {dt10[f'iter{k}']:.1f} K -> "
                        f"{'pass' if ok else 'FAIL (evaluated anyway, flagged in the report)'}")
        self.done(k, "bench", report=str(out / "benchmark.md"), dT10_parent=round(dt10["parent"], 2),
                  dT10_new=round(dt10[f"iter{k}"], 2), gate="pass" if ok else "fail")

    # --- [F] evaluation: protocol v1, pure ---------------------------------------------------------
    def eval(self, k):
        t_end = 0.005 if self.dry else self.s["eval"]["t_end"]
        run = self.it(k) / "eval"
        md = self.it(k) / "data" / "08_fluent" / "resnet_film"
        sh(f"LABEL=iter{k}_pure T_END={t_end} {REPO}/openfoam/protocol/run_protocol.sh {self.s['base_case']} {run} "
           f"pure {md} {self.s['n_procs']}", env_of=True, logfile=self.it(k) / "eval.log")
        rep = self.it(k) / "eval_report"
        di = " ".join(self.s["di_snapshots"])
        try:
            sh(f"{PY} {REPO}/openfoam/protocol/score_protocol.py --di {di} --run {run / 'snap'} --label iter{k}_pure "
               f"--run-dir {run} --out {rep}", logfile=self.it(k) / "eval.log")
        except RuntimeError as e:
            log(self.it(k), f"protocol scoring: {e}")
        self.done(k, "eval", report=str(rep))

    def report(self, k):
        st = self.state(k)
        lines = [f"# ITERML iteration {k}", "", f"Updated {spain_now()}." + (" DRY RUN (short test)." if self.dry else ""), ""]
        for step in STEPS[:-1]:
            if step in st:
                lines.append(f"- **{step}**: " + ", ".join(f"{a}={b}" for a, b in st[step].items()))
        for extra in ("seeds/seeds_report.md",):
            p = self.it(k) / extra
            if p.exists():
                lines += ["", p.read_text()]
        (self.it(k) / "ITER-REPORT.md").write_text("\n".join(lines) + "\n")
        self.done(k, "report")

    def run(self, k, only=None):
        for step in ([only] if only else STEPS):
            if not only and step in self.state(k):
                continue
            log(self.it(k), f"--- {step} (iteration {k}) ---")
            getattr(self, step)(k)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--settings", default=str(REPO / "configs" / "iterml" / "iterml.yaml"))
    ap.add_argument("--root", default="/opt/ofb/iterml")
    ap.add_argument("--dry", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--iter", type=int, required=True)
    s = sub.add_parser("step")
    s.add_argument("name", choices=STEPS)
    s.add_argument("--iter", type=int, required=True)
    a = ap.parse_args()
    loop = Loop(a.settings, a.root if not a.dry else str(Path(a.root) / "dry"), a.dry)
    loop.run(a.iter, a.name if a.cmd == "step" else None)


if __name__ == "__main__":
    main()

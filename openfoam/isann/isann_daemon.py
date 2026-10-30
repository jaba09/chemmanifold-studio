#!/usr/bin/env python3
"""ISANN trainer: runs next to an OpenFOAM run with userChemStep's `isann` dictionary.

Every --poll seconds it reads the run's isannStatus.csv / isannPairs.csv (all ranks), merges the
new GA18 pairs into an archive, deduplicates them by a radius of novelty, and decides whether to
train (criteria in isann.yaml, explained in openfoam/isann/README.md):

  DI phase (no network yet): train the first model when
      step >= di.min_steps, deduplicated pairs >= di.min_pairs and the grid has saturated
      (new boxes over the last di.window steps < di.saturation of all boxes),
      or anyway at step di.max_steps;
  network phase: retrain when at least retrain.min_gap steps passed since the last model and
      - new deduplicated GA18 pairs (OOD, untrusted bins, shadow checks) >= retrain.new_pairs, or
      - GA18 share of the hot cells over the last retrain.window steps > retrain.ga18_share and
        there are >= retrain.min_new_pairs new pairs, or
      - some (T, Z) bin is untrusted (the shadow check failed there) and >= retrain.min_new_pairs.

A round fine-tunes the current network (warm start; the first round starts from the parent, an a
priori model) on the online pairs plus a replay share of the parent's a priori data, exports it
(stage 12, whose OOD tables then cover the online pairs too), and accepts it only if it beats the
current network on held-out online pairs (one step) and on short 0D rollouts against Cantera.
An accepted model is written to <run>/isann/model_v<k>.txt and named in <run>/isann/control from a
step a few steps ahead, when every rank loads it.

  python3 isann_daemon.py --run <run dir> --config isann.yaml
"""

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
from isann_lib import (Archive, enthalpy, features, landmark_threshold, one_step_errors, pairs_arrays,  # noqa: E402
                       radius_dedup, read_run_pairs, read_status, save_json)

ONLINE_REGIME = 20


def log(msg, f=None):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    if f:
        with open(f, "a") as fh:
            fh.write(line + "\n")


class Daemon:
    def __init__(self, run, cfg_path):
        self.run = Path(run).resolve()
        self.cfg = yaml.safe_load(open(cfg_path))
        self.dir = self.run / "isann"
        self.dir.mkdir(exist_ok=True)
        self.logf = self.dir / "daemon.log"
        self.state_path = self.dir / "state.json"
        self.state = json.load(open(self.state_path)) if self.state_path.exists() else dict(
            version=0, published_step=0, rounds=[])
        p = self.cfg["parent"]
        self.parent_dir = Path(p["data_dir"]).resolve()
        self.parent_cfg = yaml.safe_load(open(self.parent_dir / "06_models" / "resnet_film" / "config_used.yaml"))
        self.scalers = json.load(open(self.parent_dir / "04_prep" / "scalers.json"))
        self.species = list(self.scalers["species"])
        self.r = float(self.cfg["dedup"]["radius"]) * landmark_threshold(p["model_file"])
        self.archive = Archive(self.dir / "archive.npz")
        import cantera as ct
        self.gas = ct.Solution(str(REPO / self.parent_cfg["chemistry"]["mechanism"]))
        self.rng = np.random.default_rng(int(self.cfg.get("seed", 0)))
        dt = np.load(self.parent_dir / "04_prep" / "dataset.npz")["dt"]   # the trained dt range (stage 12)
        self.dt_range = (float(dt.min()), float(dt.max()))

    def save_state(self):
        save_json(self.state_path, self.state)

    # --- data -----------------------------------------------------------------------------------
    def update_archive(self):
        df = read_run_pairs(self.run, self.species)
        if df.empty:
            return 0
        n_new = self.archive.merge(pairs_arrays(df, self.species))
        if n_new:
            d = self.archive.d
            new = np.zeros(len(d["id"]), bool)
            new[-n_new:] = True
            X = features(d["Y_in"], d["T_in"], d["dt"], self.scalers)
            keep = radius_dedup(X[new], self.r, X_old=X[d["kept"]])
            idx = np.flatnonzero(new)[keep]
            d["kept"][idx] = True
            d["holdout"][idx] = self.rng.random(len(idx)) < float(self.cfg["gate"]["holdout_frac"])
            self.archive.save()
        return n_new

    def counts(self):
        d = self.archive.d
        if d is None:
            return 0, 0
        kept = d["kept"] & ~d["holdout"]
        return int(kept.sum()), int((kept & ~d["trained"]).sum())

    # --- decision -------------------------------------------------------------------------------
    def decide(self, st):
        step = int(st["step"].max())
        n_kept, n_new = self.counts()
        if step < self.state.get("retry_after", 0):   # after a failed or rejected round
            return None, {}
        if self.state["version"] == 0:
            c = self.cfg["di"]
            w = st[st["step"] > step - c["window"]]
            boxes = st["boxes"].to_numpy()
            sat = (boxes[-1] - boxes[max(0, len(boxes) - 1 - c["window"])]) / max(boxes[-1], 1)
            why = None
            if step >= c["max_steps"] and n_kept >= c["min_pairs_forced"]:
                why = f"step {step} >= max_steps"
            elif step >= c["min_steps"] and n_kept >= c["min_pairs"] and sat < c["saturation"]:
                why = f"saturated grid (new boxes {100 * sat:.2f}% over {c['window']} steps)"
            return why, dict(step=step, kept=n_kept, new=n_new, saturation=float(sat), hot=int(w["hot"].mean()))
        c = self.cfg["retrain"]
        if step - self.state["published_step"] < c["min_gap"] or self.state["rounds"] and \
                len(self.state["rounds"]) >= c.get("max_rounds", 99):
            return None, {}
        w = st[st["step"] > step - c["window"]]
        ga18 = float((w["ood"] + w["untrusted"]).sum() / max(w["hot"].sum(), 1))
        untrusted = int(w["untrusted_bins"].iloc[-1]) if len(w) else 0
        info = dict(step=step, kept=n_kept, new=n_new, ga18_share=ga18, untrusted_bins=untrusted)
        if n_new >= c["new_pairs"]:
            return f"{n_new} new pairs", info
        if ga18 > c["ga18_share"] and n_new >= c["min_new_pairs"]:
            return f"GA18 share {100 * ga18:.1f}%", info
        if untrusted > 0 and n_new >= c["min_new_pairs"]:
            return f"{untrusted} untrusted bins", info
        return None, info

    # --- one training round -----------------------------------------------------------------------
    def build_round(self, k):
        rd = self.dir / f"round{k}"
        if rd.exists():
            shutil.rmtree(rd)
        smp = rd / "03_samples"
        smp.mkdir(parents=True)
        d = self.archive.d
        tr = d["kept"] & ~d["holdout"]
        n_on = int(tr.sum())
        # The a priori data are all at 1 atm (the network's pressure input has zero spread), so the
        # online pairs are trained at that pressure too; the cells differ from it by < 0.2 %
        P = np.full(n_on, float(self.scalers["ctx_mu"][1]))
        online = dict(Y_in=d["Y_in"][tr], T_in=d["T_in"][tr], P_in=P,
                      h_in=enthalpy(self.gas, d["Y_in"][tr], d["T_in"][tr], P), dt=d["dt"][tr],
                      Y_out=d["Y_out"][tr], T_out=d["T_out"][tr],
                      regime=np.full(n_on, ONLINE_REGIME, dtype=np.int64), traj_id=-1 - np.arange(n_on))
        # Replay: a priori pairs of the parent, so the network does not forget what it knew
        c = self.cfg["training"]
        n_rep = int(np.clip(c["replay_factor"] * n_on, c["replay_min"], c["replay_max"]))
        prior = [np.load(p) for p in sorted((self.parent_dir / "03_samples").glob("pairs_*.npz"))]
        keys = list(online)
        allp = {key: np.concatenate([q[key] for q in prior]) for key in keys}
        sel = self.rng.choice(len(allp["dt"]), size=min(n_rep, len(allp["dt"])), replace=False)
        np.savez(smp / "pairs_0d.npz", **{key: v[sel] for key, v in allp.items()})
        np.savez(smp / "pairs_pasr.npz", **online)
        self.write_segments(smp, online, c)
        # Config: the parent's, warm-started from the current network, in the parent's units
        cfg = copy.deepcopy(self.parent_cfg)
        cfg["data_dir"] = "."
        cfg["chemistry"]["mechanism"] = str(REPO / self.parent_cfg["chemistry"]["mechanism"])
        cfg["model"]["latent_dim"] = int(c["latent_dim"])
        cfg["preprocess"]["scalers_from"] = str(self.parent_dir / "04_prep" / "scalers.json")
        cur = self.current_model_pt()
        t = cfg["training"]
        t.update(init_from=str(cur), epochs=int(c["epochs"]), lr_max=float(c["lr_max"]),
                 noise_amp=float(c["noise_amp"]), noise_end_frac=float(c["noise_end_frac"]),
                 patience=int(c["patience"]), pct_start=float(c.get("pct_start", 0.2)), threads=int(c["threads"]))
        if not c.get("rollout_loss", True):
            cfg.pop("rollout_loss", None)
        else:   # warm start: from the first epoch, weighted by training.rollout_weight
            cfg["rollout_loss"].update(start_frac=0.0, weight=float(c.get("rollout_weight", 0.5)))
        with open(rd / "config.yaml", "w") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
        return rd, n_on, len(sel)

    def write_segments(self, smp, online, c):
        """Rollout-loss segments: the parent's a priori ones plus GA18 (Cantera) continuations of
        up to training.online_segments online states, seg_steps steps at their own dt. A step of the
        CFD is one network call, so a cell's chemistry is a chain of calls: one-step pairs alone do
        not teach the network to stay stable along that chain (round 1 drifted -60 to -110 K in 2 ms
        in cooled lean gas while its one-step error was 18x lower than the parent's)."""
        import cantera as ct
        parent = np.load(self.parent_dir / "03_samples" / "segments.npz")
        K = parent["Y"].shape[1] - 1
        n = min(int(c.get("online_segments", 4000)), len(online["dt"]))
        sel = self.rng.choice(len(online["dt"]), size=n, replace=False)
        Ys, Ts = np.empty((n, K + 1, len(self.species))), np.empty((n, K + 1))
        ok = np.ones(n, bool)
        for j, i in enumerate(sel):
            try:
                self.gas.TPY = online["T_in"][i], online["P_in"][i], online["Y_in"][i]
                r = ct.IdealGasConstPressureReactor(self.gas, clone=True)
                net = ct.ReactorNet([r])
                net.rtol, net.atol = 1e-8, 1e-14
                Ys[j, 0], Ts[j, 0] = r.thermo.Y, r.T
                for k in range(1, K + 1):
                    net.advance(k * online["dt"][i])
                    Ys[j, k], Ts[j, k] = r.thermo.Y, r.T
            except ct.CanteraError:
                ok[j] = False
        seg = dict(Y=np.concatenate([parent["Y"], Ys[ok]]), T=np.concatenate([parent["T"], Ts[ok]]),
                   P=np.concatenate([parent["P"], online["P_in"][sel][ok]]),
                   h=np.concatenate([parent["h"], online["h_in"][sel][ok]]),
                   dt=np.concatenate([parent["dt"], online["dt"][sel][ok]]))
        np.savez(smp / "segments.npz", **seg)

    def current_model_pt(self):
        if self.state["version"] == 0:
            return self.parent_dir / "06_models" / "resnet_film" / "model.pt"
        return self.dir / f"round{self.state['rounds'][-1]['round']}" / "06_models" / "resnet_film" / "model.pt"

    def current_cfg_path(self):
        if self.state["version"] == 0:
            return None
        return self.dir / f"round{self.state['rounds'][-1]['round']}" / "config.yaml"

    def stage(self, script, cfg_path, *extra):
        py = sys.executable
        cmd = [py, str(REPO / "scripts" / script), "--config", str(cfg_path), *extra]
        with open(cfg_path.parent / "train.log", "a") as f:
            env = dict(os.environ, PYTHONPATH=str(REPO))
            r = subprocess.run(cmd, cwd=REPO, stdout=f, stderr=subprocess.STDOUT, env=env)
        if r.returncode:
            raise RuntimeError(f"{script} failed, see {cfg_path.parent / 'train.log'}")

    def load(self, cfg_path):
        from chemmanifold.io import load_config
        from chemmanifold.loading import load_surrogate
        if cfg_path is None:   # the parent, in its own data dir
            cfg = dict(self.parent_cfg, _config_path=str(self.parent_dir / "config.yaml"), data_dir=".")
            cfg["model"] = dict(cfg["model"], latent_dim=int(self.cfg["training"]["latent_dim"]))
        else:
            cfg = load_config(cfg_path)
        model, scalers, _ = load_surrogate(cfg, "resnet_film")
        return model

    def gate(self, cand_cfg):
        """Candidate vs current network on the held-out online pairs and on 0D rollouts."""
        import torch
        torch.set_num_threads(int(self.cfg["training"]["threads"]))
        d = self.archive.d
        ho = d["kept"] & d["holdout"]
        arrays = {k: d[k][ho] for k in ("Y_in", "T_in", "P_in", "dt", "Y_out", "T_out")}
        dt_range = self.dt_range
        res = {}
        for name, path in (("current", self.current_cfg_path()), ("candidate", cand_cfg)):
            m = self.load(path)
            res[name] = one_step_errors(m, self.scalers, arrays, dt_range)
            res[name].update(self.rollouts(m, arrays, dt_range))
        g = self.cfg["gate"]
        c, n = res["candidate"], res["current"]
        # strictly better one-step error on the held-out online pairs; on the rollouts, no more failed
        # states (|dT| > roll_fail_K after roll_steps) and a median not worse than max_ratio
        ok = c["T_mae"] < n["T_mae"] and c["roll_fail"] <= n["roll_fail"] and \
            c["roll_T_p50"] <= g["max_ratio"] * n["roll_T_p50"] + 0.1
        if self.state["version"] == 0:   # the first network must also be usable in absolute terms
            ok = ok and c["T_mae"] < g["first_T_mae"]
        res["n_holdout"] = int(ho.sum())
        res["accepted"] = bool(ok)
        return res

    def rollouts(self, model, arrays, dt_range):
        """n_roll held-out states advanced steps x dt by the model and by Cantera (GA18)."""
        from chemmanifold.fluent import advance
        g = self.cfg["gate"]
        n = min(int(g["n_roll"]), len(arrays["T_in"]))
        idx = np.random.default_rng(1).choice(len(arrays["T_in"]), size=n, replace=False)
        Y, T, P, dt = arrays["Y_in"][idx].copy(), arrays["T_in"][idx].copy(), arrays["P_in"][idx], arrays["dt"][idx]
        import cantera as ct
        ref_T = np.empty(n)
        for i in range(n):
            self.gas.TPY = T[i], P[i], Y[i]
            r = ct.IdealGasConstPressureReactor(self.gas, clone=True)
            net = ct.ReactorNet([r])
            net.rtol, net.atol = 1e-8, 1e-14
            net.advance(g["roll_steps"] * dt[i])
            ref_T[i] = r.T
        for _ in range(int(g["roll_steps"])):
            Y, T, *_ = advance(model, Y, T, P, dt, *dt_range)
        e = np.abs(T - ref_T)
        e[~np.isfinite(e)] = 1e4
        return dict(roll_T=float(e.mean()), roll_T_p50=float(np.median(e)), roll_T_p95=float(np.quantile(e, 0.95)),
                    roll_fail=int((e > float(g["roll_fail_K"])).sum()))

    def train_round(self, why, info):
        k = len(self.state["rounds"]) + 1
        t0 = time.time()
        rd, n_on, n_rep = self.build_round(k)
        log(f"round {k}: {why}; {n_on} online + {n_rep} replay pairs -> {rd}", self.logf)
        cfgp = rd / "config.yaml"
        self.stage("05_preprocess.py", cfgp)
        self.stage("07_train.py", cfgp)
        self.stage("12_export_fluent.py", cfgp)
        t_train = time.time() - t0
        res = self.gate(cfgp)
        rec = dict(round=k, why=why, **info, n_online=n_on, n_replay=n_rep, train_s=round(t_train, 1),
                   gate_s=round(time.time() - t0 - t_train, 1), gate=res)
        log(f"round {k}: gate {json.dumps(res, default=float)}", self.logf)
        d = self.archive.d
        d["trained"] |= d["kept"] & ~d["holdout"]
        self.archive.save()
        if res["accepted"]:
            v = self.state["version"] + 1
            src = rd / "08_fluent" / "resnet_film" / "chemmanifold_model.txt"
            dst = self.dir / f"model_v{v}.txt"
            shutil.copy(src, dst)
            st = read_status(self.run)
            from_step = int(st["step"].max()) + int(self.cfg["publish"]["steps_ahead"])
            tmp = self.dir / "control.tmp"
            tmp.write_text(f"version {v}\nmodel isann/model_v{v}.txt\nfromStep {from_step}\n")
            tmp.replace(self.dir / "control")
            self.state["version"] = v
            self.state["published_step"] = from_step
            rec.update(version=v, from_step=from_step)
            log(f"round {k}: accepted -> version {v} from step {from_step}", self.logf)
        else:
            log(f"round {k}: rejected, the run keeps version {self.state['version']}", self.logf)
            # back off after consecutive rejections: in the first run, rounds 9-12 (untrusted bins)
            # could not improve on the current network at all and were retrained every 3.5 ms
            n_rej = 1
            for r in reversed(self.state["rounds"]):
                if r["gate"]["accepted"]:
                    break
                n_rej += 1
            self.state["retry_after"] = int(info.get("step", 0)) + int(self.cfg["retrain"]["min_gap"]) * 2 ** min(n_rej - 1, 4)
        self.state["rounds"].append(rec)
        self.save_state()

    def loop(self, poll):
        log(f"ISANN daemon on {self.run}, radius {self.r:.4f}", self.logf)
        while True:
            st = read_status(self.run)
            n_new = self.update_archive()
            if not st.empty:
                why, info = self.decide(st)
                if n_new:
                    log(f"step {int(st['step'].max())}: +{n_new} pairs, kept {self.counts()} "
                        f"{json.dumps(info, default=float)}", self.logf)
                if why:
                    try:
                        self.train_round(why, info)
                    except Exception as e:   # keep the run going on the current network
                        log(f"round failed: {e}", self.logf)
                        self.state["retry_after"] = int(info.get("step", 0)) + int(self.cfg["retrain"]["min_gap"])
                        self.save_state()
            if (self.run / "isann" / "STOP").exists():
                break
            time.sleep(poll)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--config", default=str(HERE / "isann.yaml"))
    ap.add_argument("--poll", type=float, default=30.0)
    a = ap.parse_args()
    Daemon(a.run, a.config).loop(a.poll)


if __name__ == "__main__":
    main()

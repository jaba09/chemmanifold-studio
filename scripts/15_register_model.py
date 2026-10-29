"""Stage 15: model registry. Records one trained surrogate as a model card and rebuilds the catalogue.

Every trained model gets a card that says what it is, how it was trained and how well it did, so
that a model file found in a Fluent folder months later can be traced back to its data and settings:

  * identity: id = <config stem>-<arch>-<training date>-<first 8 hex of the model.pt sha256>,
    status (candidate | in-fluent | superseded | discarded) and free-text notes;
  * exploration: streams, the sampling options that define the explored space (heat loss, cooling
    reactors, radiating flamelets, recirculation, rollout loss) and the pair counts per regime;
  * manifold and training: latent dimension, network size, epochs, best epoch, wall time, machine,
    git commit, and the exact config used (06_models/<arch>/config_used.yaml when stage 7 wrote it);
  * certification: Tier 1/2/3, the cooled-gas and mixing tests, flame coverage and the Fluent export
    report, when those stages have run;
  * files: sha256 of model.pt and of the exported chemmanifold_model.txt (the file Fluent loads).

Writes models/cards/<id>.json (and a copy as 08_fluent/<arch>/model_card.json, next to the files that
go to Fluent), upserts models/registry.jsonl (one card per line, keyed by id) and
regenerates models/REGISTRY.md (summary table + one section per model), all under the repository.

    python scripts/15_register_model.py --config configs/burner_fluent_nonadiabatic.yaml --arch resnet_film
    python scripts/15_register_model.py --id <id> --status in-fluent --note "Fluent run 2026-10-28: ..."
    python scripts/15_register_model.py --rebuild          # only regenerate REGISTRY.md
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml

from chemmanifold.io import base_parser, load_config, stage_dir

ROOT = Path(__file__).resolve().parents[1]
REG_DIR = ROOT / "models"
REGIME_NAMES = {0: "reactor_0D", 1: "PaSR", 2: "flamelet_states", 3: "wall_cooled_0D", 4: "recirculation", 5: "unsteady_flamelets", 6: "equilibrium_tail_0D", 7: "vitiated_ignition"}
STATUSES = ("candidate", "in-fluent", "superseded", "discarded")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text()) if Path(path).exists() else None


def exploration(cfg):
    """The settings that define the explored thermochemical space, flattened to a few readable keys."""
    c, env, pasr = cfg["chemistry"], cfg["envelope"], cfg.get("pasr", {})
    out = dict(mechanism=c["mechanism"], fuel=c.get("fuel"), oxidizer=c.get("oxidizer"), P_atm=c.get("P_atm"),
               mode=env.get("mode", "premixed"), n_traj=env.get("n_traj"), f_pasr=env.get("f_pasr"))
    if out["mode"] == "flame":
        fl = cfg.get("flame", {})
        out.update(
            heat_loss=(f"fraction psi <= {env.get('psi_max', 1.0)} of the loss to T_wall = {env.get('T_wall', 300.0)} K"
                       if env.get("heat_loss") == "fraction" else f"fixed, |dh| <= {env.get('heat_loss_max')} J/kg"),
            cooling_reactors=(f"{env['f_cool']:.0%} of 0D seeds, tau_q {env.get('tau_q_range')} s"
                              if env.get("f_cool") else "none"),
            radiating_flamelets=bool(any(fl.get("radiation", [False]))),
            pasr_heat_loss=(f"psi in {pasr['loss_fraction_range']}" if "loss_fraction_range" in pasr
                            else f"dh in {pasr.get('dh_range')}"),
            recirculation=(f"{pasr['recirculation']['n_ensembles']} ensembles x {pasr['recirculation']['n_particles']}"
                           if pasr.get("recirculation") else "none"),
            strain_range=(f"flamelets {fl.get('mdot_fuel_min')} kg/m2/s x {fl.get('strain_factor')}^k, "
                          f"up to {fl.get('max_flamelets')}"),
            unsteady_flamelets=(", ".join(f"{k} {v['n']}" for k, v in cfg["unsteady_flamelets"].items()
                                          if isinstance(v, dict) and v.get("n"))
                                if cfg.get("unsteady_flamelets") else "none"),
        )
    rl = cfg.get("rollout_loss")
    out["rollout_loss"] = (f"{rl['steps']} x {rl['stride']} dt_base, weight {rl['weight']}" if rl and rl.get("weight")
                           else "none")
    return out


def build_card(cfg, arch):
    mdir = stage_dir(cfg, "models", arch, create=False)
    model_pt = mdir / "model.pt"
    ckpt = torch.load(model_pt, map_location="cpu", weights_only=False)
    info = read_json(mdir / "train_info.json") or {}
    used = mdir / "config_used.yaml"
    cfg_used = yaml.safe_load(used.read_text()) if used.exists() else {k: v for k, v in cfg.items()
                                                                        if not k.startswith("_")}
    trained = info.get("started_utc") or datetime.fromtimestamp(model_pt.stat().st_mtime, timezone.utc).isoformat(
        timespec="seconds")
    digest = sha256(model_pt)
    stem = Path(cfg["_config_path"]).stem
    card = dict(id=f"{stem}-{arch}-{trained[:10].replace('-', '')}-{digest[:8]}", config=f"{stem}.yaml", arch=arch,
                trained_utc=trained, status="candidate", notes=[], exploration=exploration(cfg_used))

    ds_path = stage_dir(cfg, "prep", create=False) / "dataset.npz"
    if ds_path.exists():
        with np.load(ds_path) as ds:
            reg, val = ds["regime"], ds["is_val"]
            card["data"] = dict(n_train=int((~val).sum()), n_val=int(val.sum()),
                                pairs_by_regime={REGIME_NAMES.get(int(g), str(g)): int((reg == g).sum())
                                                 for g in np.unique(reg)},
                                T_range_K=[float(ds["T_in"].min()), float(ds["T_in"].max())])
    fref = read_json(stage_dir(cfg, "flame", create=False) / "flame_reference.json")
    if fref:
        card["data"]["flamelets"] = dict(n=len(fref["T_max"]), n_radiating=int(sum(fref.get("radiation", []))),
                                         Z_st=fref["Z_st"], T_ad_max_K=fref["T_ad_max"],
                                         peak_T_K=[min(fref["T_max"]), max(fref["T_max"])])
    man = read_json(stage_dir(cfg, "manifold", create=False) / "manifold_report.json")
    m = cfg_used.get("model", {})
    hist = mdir / "history.csv"
    card["training"] = dict(
        latent_dim=int(ckpt.get("latent_dim", 0)), pca_d_995=man.get("d_global") if man else None,
        hidden=m.get("hidden"), n_blocks=m.get("n_blocks"), epochs=cfg_used.get("training", {}).get("epochs"),
        best_epoch=int(ckpt.get("epoch", 0)), loss_weights=cfg_used.get("training", {}).get("loss_weights"),
        n_epochs_run=int(len(pd.read_csv(hist))) if hist.exists() else None,
        **{k: info[k] for k in ("wall_time_s", "n_parameters", "device", "threads", "torch", "machine", "git_commit")
           if k in info})

    ev = stage_dir(cfg, "eval", arch, create=False)
    t1, t2, t3 = (read_json(ev / f) for f in ("tier1.json", "tier2.json", "tier3_summary.json"))
    cov = read_json(stage_dir(cfg, "eval", create=False) / "flame_coverage.json")
    cert = {}
    if t1:
        cert["tier1"] = dict(r2_dy=t1["r2_dy_projected"], T_mae_K=t1["T_mae_K"], T_max_err_K=t1["T_max_err_K"],
                             elemental_residual_max=t1["elemental_residual_max"])
    if t2:
        cert["tier2"] = dict(tau_ign_err_pct=t2["tau_ign_rel_err_pct"], T_final_ml_K=t2["T_final_ml"],
                             T_final_cantera_K=t2["T_final_cantera"])
    if t3:
        cert["tier3"] = t3
    if cov:
        cert["coverage_heldout_flamelets"] = cov.get("heldout_states_covered")
    exp_dir = stage_dir(cfg, "fluent", arch, create=False)
    rep = read_json(exp_dir / "export_report.json")
    if rep:
        cert["export"] = dict(ood_flagged_validation=rep["validation_flagged_fraction"]["any"],
                              T_range_K=rep["T_range"], dt_range_s=rep["dt_range"])
    card["certification"] = cert
    card["files"] = dict(model_pt_sha256=digest, data_dir=str(Path(cfg["data_dir"])))
    if (exp_dir / "chemmanifold_model.txt").exists():
        card["files"]["fluent_model_sha256"] = sha256(exp_dir / "chemmanifold_model.txt")
    return card


def load_registry():
    path = REG_DIR / "registry.jsonl"
    if not path.exists():
        return {}
    cards = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return {c["id"]: c for c in cards}


def clean(o):
    """NaN -> None, so the files stay strict JSON."""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    return None if isinstance(o, float) and not np.isfinite(o) else o


def save_registry(reg):
    reg = {k: clean(v) for k, v in reg.items()}
    REG_DIR.mkdir(exist_ok=True)
    (REG_DIR / "cards").mkdir(exist_ok=True)
    cards = sorted(reg.values(), key=lambda c: c["trained_utc"])
    (REG_DIR / "registry.jsonl").write_text("".join(json.dumps(c, sort_keys=False) + "\n" for c in cards))
    for c in cards:
        (REG_DIR / "cards" / f"{c['id']}.json").write_text(json.dumps(c, indent=2) + "\n")
    (REG_DIR / "REGISTRY.md").write_text(render(cards))


def fmt(v, spec="{:.3g}"):
    return "–" if v is None or (isinstance(v, float) and not np.isfinite(v)) else spec.format(v)


def render(cards):
    lines = ["# Surrogate model registry", "",
             "One row per trained surrogate, oldest first. Generated by `scripts/15_register_model.py` from "
             "`models/registry.jsonl`; edit status and notes with that script, not by hand. The full card of each "
             "model (exploration settings, data, training, certification, file hashes) is in `models/cards/`.", "",
             "To identify the model a Fluent run used, compare the sha256 of its `chemmanifold_model.txt` "
             "with `fluent_model_sha256`.", "",
             "| Model | Status | Trained | Pairs (train) | Latent d | T1 T MAE [K] | T3 T MAE [K] | Cooled T MAE [K] | "
             "Mixing T MAE [K] | Coverage |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for c in cards:
        t3 = c.get("certification", {}).get("tier3", {})
        lines.append(
            f"| [`{c['id']}`](#{c['id'].lower()}) | {c['status']} | {c['trained_utc'][:10]} | "
            f"{fmt(c.get('data', {}).get('n_train'), '{:,}')} | {fmt(c.get('training', {}).get('latent_dim'), '{}')} | "
            f"{fmt(c.get('certification', {}).get('tier1', {}).get('T_mae_K'), '{:.2f}')} | "
            f"{fmt(t3.get('mean_T_mae_manifold_K'), '{:.1f}')} | {fmt(t3.get('cooled_mean_T_mae_K'), '{:.1f}')} | "
            f"{fmt(t3.get('mixing_mean_T_mae_K'), '{:.1f}')} | "
            f"{fmt(c.get('certification', {}).get('coverage_heldout_flamelets'), '{:.1%}')} |")
    for c in cards:
        lines += ["", f"## {c['id']}", "",
                  f"Config `{c['config']}`, {c['arch']}, trained {c['trained_utc']}, status **{c['status']}**."]
        if c.get("notes"):
            lines += [""] + [f"- {n}" for n in c["notes"]]
        lines += ["", "| Exploration | |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in c.get("exploration", {}).items()]
        d, t = c.get("data", {}), c.get("training", {})
        if d:
            regimes = ", ".join(f"{k} {v:,}" for k, v in d.get("pairs_by_regime", {}).items())
            lines += ["", f"Data: {d.get('n_train', 0):,} train / {d.get('n_val', 0):,} validation pairs ({regimes})."]
            if d.get("flamelets"):
                f = d["flamelets"]
                lines.append(f"Flamelets: {f['n']} ({f['n_radiating']} radiating), Z_st {f['Z_st']:.4f}, "
                             f"peak T {f['peak_T_K'][0]:.0f}–{f['peak_T_K'][1]:.0f} K.")
        if t:
            wall = f", {t['wall_time_s'] / 60:.0f} min on {t.get('threads')} threads ({t.get('machine')})" \
                if t.get("wall_time_s") else ""
            lines.append(f"Training: latent d {t.get('latent_dim')}, hidden {t.get('hidden')} x {t.get('n_blocks')} "
                         f"blocks, best epoch {t.get('best_epoch')} of {t.get('epochs')}{wall}"
                         + (f", git {t['git_commit']}" if t.get("git_commit") else "") + ".")
        cert = c.get("certification", {})
        if cert:
            t1, t2, t3 = cert.get("tier1", {}), cert.get("tier2", {}), cert.get("tier3", {})
            parts = []
            if t1:
                parts.append(f"Tier 1 R2 {t1['r2_dy']:.4f}, T MAE {t1['T_mae_K']:.2f} K")
            if cert.get("coverage_heldout_flamelets") is not None:
                parts.append(f"held-out flamelet coverage {cert['coverage_heldout_flamelets']:.1%}")
            if t2:
                parts.append(f"Tier 2 tau error {t2['tau_ign_err_pct']:+.0f}%" + (
                    f", final T {t2['T_final_ml_K']:.0f} K (Cantera {t2['T_final_cantera_K']:.0f} K)"
                    if t2.get("T_final_ml_K") is not None else ""))
            if t3:
                parts.append(f"Tier 3 mean |tau error| {fmt(t3.get('mean_abs_tau_err_pct'), '{:.0f}')}%, "
                             f"T MAE {fmt(t3.get('mean_T_mae_manifold_K'), '{:.1f}')} K")
            if "cooled_mean_T_mae_K" in t3:
                parts.append(f"cooled gas T MAE {t3['cooled_mean_T_mae_K']:.1f} K (max {t3['cooled_max_T_mae_K']:.0f} K)")
            if "mixing_mean_T_mae_K" in t3:
                parts.append(f"mixing T MAE {t3['mixing_mean_T_mae_K']:.1f} K (max {t3['mixing_max_T_mae_K']:.0f} K)")
            lines.append("Certification: " + "; ".join(parts) + ".")
        files = c.get("files", {})
        if files.get("fluent_model_sha256"):
            lines.append(f"Fluent file sha256: `{files['fluent_model_sha256']}`.")
    return "\n".join(lines) + "\n"


def main(a):
    reg = load_registry()
    if a.config:
        card = build_card(load_config(a.config), a.arch)
        old = reg.get(card["id"])
        if old:                                   # keep the human-curated fields of a re-registered model
            card["status"], card["notes"] = old["status"], old["notes"]
        reg[card["id"]] = card
        a.id = a.id or card["id"]
        cfg = load_config(a.config)
        exp_dir = stage_dir(cfg, "fluent", a.arch, create=False)
        if exp_dir.exists():                      # the card travels with the files copied to Fluent
            (exp_dir / "model_card.json").write_text(json.dumps(clean(card), indent=2) + "\n")
        print(f"  registered {card['id']}")
    if a.status or a.note:
        if a.id not in reg:
            raise SystemExit(f"unknown model id {a.id!r}; known: {', '.join(reg)}")
        if a.status:
            reg[a.id]["status"] = a.status
        if a.note:
            reg[a.id]["notes"].append(f"{datetime.now(timezone.utc):%Y-%m-%d}: {a.note}")
    save_registry(reg)
    print(f"  wrote {REG_DIR / 'REGISTRY.md'} ({len(reg)} models)")


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.set_defaults(config=None)
    p.add_argument("--arch", choices=["resnet_film", "chemnode"], default="resnet_film")
    p.add_argument("--id", help="model id, for --status / --note on an already registered model")
    p.add_argument("--status", choices=STATUSES)
    p.add_argument("--note", help="append a dated note to the model's card")
    p.add_argument("--rebuild", action="store_true", help="only regenerate REGISTRY.md")
    main(p.parse_args())

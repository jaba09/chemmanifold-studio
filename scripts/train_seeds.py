"""Train the same configuration with several training seeds, to put error bars on any comparison.

Only the network's random start and batch order change (`training.seed`); the exploration data
(stages 0-6) is the base run's and is linked, not regenerated. Seed k gets its own data directory
`<data_dir>_seeds/s<k>/` and config `<data_dir>_seeds/<stem>_s<k>.yaml`, so stage 15 registers it as
its own model (`<stem>_s<k>-<arch>-...`). The base run counts as the seed of its config (cfg seed,
0 by default) and is not retrained.

For each seed this runs stages 7 (train), 8-10 (certification), 12 (Fluent/OpenFOAM export) and 15
(registry). With `--dest`, the exported model files are copied to `<dest>/<name>/seed<k>/` (the base
run's too), the layout stage 18 (offline benchmark) reads with `--models-dir`.

    python scripts/train_seeds.py --config configs/burner_openfoam_ood1.yaml --seeds 1 2 \\
        --parallel 2 --threads 2 --dest /mnt/project-files/chemmanifold/benchmark/semillas --name ood1

Seeds run `--parallel` at a time with `--threads` torch threads each; a seed whose exported model
already exists is skipped (re-running resumes).
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SHARED = ["00_flame", "01_envelope", "02_autoignition", "03_samples", "04_prep", "05_manifold"]
STAGES = ["07_train.py", "08_tier1_validation.py", "09_tier2_rollout.py", "10_tier3_envelope.py",
          "12_export_fluent.py", "15_register_model.py"]
EXPORTS = ["chemmanifold_model.txt", "chemmanifold_tests.txt", "export_report.json", "model_card.json"]


def seed_config(base_cfg_path, seed, threads):
    """Write the seed's config and link the base run's data stages into its data directory."""
    base_cfg_path = Path(base_cfg_path).resolve()
    with open(base_cfg_path) as f:
        cfg = yaml.safe_load(f)
    base_root = (base_cfg_path.parent / cfg["data_dir"]).resolve()
    seeds_root = base_root.parent / f"{base_root.name}_seeds"
    data = seeds_root / f"s{seed}"
    data.mkdir(parents=True, exist_ok=True)
    for d in SHARED:
        src, dst = base_root / d, data / d
        if src.exists() and not dst.exists():
            dst.symlink_to(src, target_is_directory=True)
    cov = base_root / "07_eval" / "flame_coverage.json"           # data coverage: same data, same result
    if cov.exists():
        (data / "07_eval").mkdir(exist_ok=True)
        shutil.copy2(cov, data / "07_eval" / cov.name)
    cfg["data_dir"] = data.name
    cfg.setdefault("training", {})["seed"] = int(seed)
    if threads:
        cfg["training"]["threads"] = int(threads)
    path = seeds_root / f"{base_cfg_path.stem}_s{seed}.yaml"
    with open(path, "w") as f:
        f.write(f"# Seed {seed} of {base_cfg_path.name}, written by scripts/train_seeds.py: same data (linked from\n"
                f"# {base_root}), only training.seed changes.\n")
        yaml.safe_dump(cfg, f, sort_keys=False)
    return path, data


def copy_exports(data_root, arch, dest):
    src = data_root / "08_fluent" / arch
    if not (src / "chemmanifold_model.txt").exists():
        return False
    dest.mkdir(parents=True, exist_ok=True)
    for f in EXPORTS:
        if (src / f).exists():
            shutil.copy2(src / f, dest / f)
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--seeds", nargs="+", type=int, default=[1, 2])
    p.add_argument("--arch", choices=["resnet_film", "chemnode"], default="resnet_film")
    p.add_argument("--parallel", type=int, default=1, help="seeds trained at the same time")
    p.add_argument("--threads", type=int, default=None, help="torch threads per seed (training.threads)")
    p.add_argument("--dest", help="copy the exported models to <dest>/<name>/seed<k>/")
    p.add_argument("--name", help="model name under --dest (default: the config stem)")
    a = p.parse_args()

    with open(a.config) as f:
        base = yaml.safe_load(f)
    base_root = (Path(a.config).resolve().parent / base["data_dir"]).resolve()
    name = a.name or Path(a.config).stem
    base_seed = int(base.get("training", {}).get("seed", base.get("seed", 0)))
    if a.dest and copy_exports(base_root, a.arch, Path(a.dest) / name / f"seed{base_seed}"):
        print(f"  base run = seed {base_seed}: copied to {Path(a.dest) / name / f'seed{base_seed}'}")

    todo = []
    for s in a.seeds:
        if s == base_seed:
            continue
        cfg_path, data = seed_config(a.config, s, a.threads)
        if (data / "08_fluent" / a.arch / "chemmanifold_model.txt").exists():
            print(f"  seed {s}: already exported, skipped")
        else:
            todo.append((s, cfg_path, data))

    def chain(cfg_path, data):
        cmds = " && ".join(f"{sys.executable} {ROOT / 'scripts' / sc} --config {cfg_path} --arch {a.arch}"
                           for sc in STAGES)
        log = open(data / f"train_seeds_{a.arch}.log", "a")
        return subprocess.Popen(["bash", "-c", cmds], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)

    running, t0, failed = [], time.time(), []
    while todo or running:
        while todo and len(running) < a.parallel:
            s, cfg_path, data = todo.pop(0)
            print(f"  seed {s}: started ({cfg_path}), log {data / f'train_seeds_{a.arch}.log'}", flush=True)
            running.append((s, data, chain(cfg_path, data)))
        time.sleep(10)
        for item in list(running):
            s, data, proc = item
            if proc.poll() is None:
                continue
            running.remove(item)
            if proc.returncode:
                failed.append(s)
                print(f"  seed {s}: FAILED (exit {proc.returncode}), see its log", flush=True)
                continue
            print(f"  seed {s}: done after {(time.time() - t0) / 60:.0f} min", flush=True)
            if a.dest:
                copy_exports(data, a.arch, Path(a.dest) / name / f"seed{s}")
    if failed:
        sys.exit(f"seeds failed: {failed}")


if __name__ == "__main__":
    main()

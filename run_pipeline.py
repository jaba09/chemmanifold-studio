"""Run the full ChemManifold pipeline. Each stage is a separate process that reads its inputs from
and writes its outputs to `data_dir`, so any stage can be re-run on its own. Stages 0 (flame
reference) and 11 (flame coverage) run only for `envelope.mode: flame`. Stage 12 exports the
models for the Fluent UDF; stages 13-14 (Fluent comparisons) and 16 (coverage gaps of a Fluent
solution) need Fluent exports and run by hand;
stage 15 records each trained model in the registry (models/REGISTRY.md).

    python run_pipeline.py                       # everything, both architectures
    python run_pipeline.py --from 7 --arch chemnode
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
STAGES = [
    (0, "00_flame_reference.py", False),
    (1, "01_sample_envelope.py", False),
    (2, "02_autoignition_0d.py", False),
    (3, "03_arclength_sampling.py", False),
    (4, "04_pasr_ensemble.py", False),
    (5, "05_preprocess.py", False),
    (6, "06_manifold_analysis.py", False),
    (7, "07_train.py", True),
    (8, "08_tier1_validation.py", True),
    (9, "09_tier2_rollout.py", True),
    (10, "10_tier3_envelope.py", True),
    (11, "11_flame_coverage.py", False),
    (12, "12_export_fluent.py", True),
    (15, "15_register_model.py", True),
]
FLAME_ONLY = {0, 11}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default=str(ROOT / "config.yaml"))
    p.add_argument("--from", dest="start", type=int, default=0)
    p.add_argument("--to", dest="stop", type=int, default=15)
    p.add_argument("--arch", nargs="+", default=["resnet_film", "chemnode"], choices=["resnet_film", "chemnode"])
    a = p.parse_args()
    with open(a.config) as f:
        flame = yaml.safe_load(f)["envelope"].get("mode", "premixed") == "flame"

    for num, script, per_arch in STAGES:
        if not a.start <= num <= a.stop or (num in FLAME_ONLY and not flame):
            continue
        for arch in (a.arch if per_arch else [None]):
            cmd = [sys.executable, str(ROOT / "scripts" / script), "--config", a.config]
            if arch:
                cmd += ["--arch", arch]
            print(f"\n=== stage {num}: {script}{' [' + arch + ']' if arch else ''} ===", flush=True)
            t0 = time.time()
            subprocess.run(cmd, check=True, cwd=ROOT)
            print(f"=== stage {num} done in {time.time() - t0:.1f}s ===", flush=True)


if __name__ == "__main__":
    main()

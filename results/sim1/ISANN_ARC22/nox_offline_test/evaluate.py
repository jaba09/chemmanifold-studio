"""Offline NOx test: v6 of run isann_arc22 vs two retrains of its round 7 from v6 (A: same loss, B: + NOx
relative term), on the run's held-out online pairs (never trained on) and 0D rollouts vs the ARC kernel."""
import json, sys, importlib.util as u
from pathlib import Path
import numpy as np
S = Path(sys.argv[1]); RUN = "/opt/ofb/run/isann_arc22"
sys.path.insert(0, "/opt/ofb/isann-gri-src/openfoam/isann"); sys.path.insert(0, "/opt/ofb/isann-gri-src")
spec = u.spec_from_file_location("d", "/opt/ofb/isann-gri-src/openfoam/isann/isann_daemon.py"); m = u.module_from_spec(spec); spec.loader.exec_module(m)
from isann_lib import one_step_errors
d = m.Daemon(RUN, f"{RUN}/isann/isann.yaml")          # read-only use: no save, no train
d.smap.reference = "arc"                               # ARC kernel = the run's DI chemistry
d.cfg["gate"]["roll_species"] = {"OH": 5e-5, "NO": 3e-6, "NO2": 2e-7, "N2O": 5e-8, "HCN": 2e-6}
a = d.archive.d; ho = a["kept"] & a["holdout"]
arrays = {k: a[k][ho] for k in ("Y_in", "T_in", "P_in", "dt", "Y_out", "T_out")}
res = {}
for name, cfg in (("v6", f"{RUN}/isann/round7/config.yaml"), ("A_same_loss", S / "A/config.yaml"), ("B_nox_loss", S / "B/config.yaml")):
    model = d.load(cfg)
    r = one_step_errors(model, d.scalers, arrays, d.dt_range)
    r.update(d.rollouts(model, arrays, d.dt_range))
    res[name] = r
    print(name, json.dumps({k: round(v, 4) for k, v in r.items()}), flush=True)
res["n_holdout"] = int(ho.sum())
json.dump(res, open(S / "results.json", "w"), indent=1)

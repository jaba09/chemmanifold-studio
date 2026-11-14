"""Write a ChemManifold ensemble file and check the C ensemble code against a Python reference.

An ensemble file (chemmanifold_ensemble.txt) lists member model files (stage 12 exports) and how to
combine them (fluent/udf/chemmanifold_ensemble.h): `mean` (deep ensemble) or `gate` (each member owns a
soft box in temperature T and normalised progress variable c, chemmanifold/ensemble.py). The gate
tables (Bilger Z, Yc_eq(Z)) come from the config's streams and mechanism: physics only.

Spec (YAML):

    blend: gate                       # or mean
    note: "P1, three T bands"
    members:
      - path: /path/to/cold/chemmanifold_model.txt
        T: [0, 1200, 100]             # lo, hi, blending width [K]; omitted = no cut
      - path: /path/to/hot/chemmanifold_model.txt
        T: [1200, 5000, 100]
        c: [0.0, 1.0e9, 0.0]          # lo, hi, width in c

Self-test: on validation states of the config's dataset, every ensemble step through the C code
(cme_advance) is compared with the same blend done here from the members' own C steps and the
Python gate weights. Writes <out>/chemmanifold_ensemble.txt and <out>/ensemble_selftest.json.

    python scripts/make_ensemble.py --config configs/burner_openfoam_ood8.yaml --spec spec.yaml --out dir
"""

import ctypes
import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import yaml

from chemmanifold.ensemble import gate_tables, gate_vars, gate_weights, write_ensemble_file
from chemmanifold.io import base_parser, load_config, load_npz, stage_dir

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("stage17", ROOT / "scripts" / "17_di_local_stability.py")
stage17 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage17)


def selftest(lib, ens_path, members, blend, tab, ds, n, dt, seed=0):
    dp = ctypes.POINTER(ctypes.c_double)
    err = ctypes.create_string_buffer(512)
    ens = lib.cme_load(str(ens_path).encode(), err, 512)
    if not ens:
        raise RuntimeError(err.value.decode())
    ms = []
    for m in members:
        h = lib.cm_load(str(m["abspath"]).encode(), err, 512)
        if not h:
            raise RuntimeError(err.value.decode())
        ms.append(h)
    lib.cm_enthalpy.restype = ctypes.c_double
    lib.cm_enthalpy.argtypes = [ctypes.c_void_p, dp, ctypes.c_double]
    lib.cm_temperature.restype = ctypes.c_double
    lib.cm_temperature.argtypes = [ctypes.c_void_p, dp, ctypes.c_double, ctypes.c_double]
    opt = stage17.CmOptions()
    lib.cm_default_options(ctypes.byref(opt))
    opt.T_freeze = 0.0
    rng = np.random.default_rng(seed)
    pick = rng.choice(len(ds["T_in"]), size=min(n, len(ds["T_in"])), replace=False)
    Y0, T0, P0 = ds["Y_in"][pick], ds["T_in"][pick], ds["P_in"][pick]
    _, c0 = gate_vars(tab, Y0)
    w_py = gate_weights(T0, c0, members, blend)
    info, sp = stage17.CmInfo(), ctypes.c_double()
    w_c, Zc, cc = (ctypes.c_double * len(members))(), ctypes.c_double(), ctypes.c_double()
    max_w = max_dY = max_dT = 0.0
    n_used = np.zeros(len(members) + 1, int)
    for i in range(len(pick)):
        y = np.ascontiguousarray(Y0[i], float).copy()
        lib.cme_weights(ens, y.ctypes.data_as(dp), T0[i], w_c, ctypes.byref(Zc), ctypes.byref(cc))
        max_w = max(max_w, float(np.max(np.abs(np.array(w_c[:]) - w_py[i]))))
        yc = y.copy()
        if lib.cme_advance(ens, ctypes.byref(opt), yc.ctypes.data_as(dp), T0[i], P0[i], dt, ctypes.byref(info),
                           ctypes.byref(sp)) != 0:
            continue
        Tc = info.T_out
        yb, ws, Tg, used = np.zeros_like(y), 0.0, 0.0, 0
        for k, h in enumerate(ms):
            if w_py[i, k] <= 0:
                continue
            ym = y.copy()
            if lib.cm_advance(h, ctypes.byref(opt), ym.ctypes.data_as(dp), T0[i], P0[i], dt, ctypes.byref(info)) != 0:
                continue
            yb += w_py[i, k] * ym
            ws += w_py[i, k]
            Tg += w_py[i, k] * info.T_out
            used += 1
        n_used[used] += 1
        yb /= ws
        hh = lib.cm_enthalpy(ms[0], y.ctypes.data_as(dp), T0[i])
        Tp = lib.cm_temperature(ms[0], yb.ctypes.data_as(dp), hh, Tg / ws)
        max_dY = max(max_dY, float(np.max(np.abs(yb - yc))))
        max_dT = max(max_dT, abs(Tp - Tc))
    for h in ms:
        lib.cm_free(h)
    lib.cme_free(ens)
    ok = max_w < 1e-9 and max_dY < 1e-12 and max_dT < 1e-6
    return dict(states=len(pick), dt=dt, max_weight_diff=max_w, max_dY=max_dY, max_dT_K=max_dT, passed=bool(ok),
                members_used_histogram={str(k): int(v) for k, v in enumerate(n_used)})


def main(cfg, args):
    spec = yaml.safe_load(Path(args.spec).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    blend = spec.get("blend", "gate")
    members = []
    for m in spec["members"]:
        ap = Path(m["path"]).resolve()
        mm = dict(m)
        for key in ("T", "c"):             # YAML 1.1 reads 1.0e9 (no exponent sign) as a string
            if key in mm:
                mm[key] = [float(v) for v in mm[key]]
        mm["abspath"] = ap
        mm["path"] = os.path.relpath(ap, out.resolve())
        if " " in mm["path"]:
            raise SystemExit(f"member path must not contain spaces: {mm['path']}")
        members.append(mm)
    lib = stage17.core_library(out)
    err = ctypes.create_string_buffer(512)
    h = lib.cm_load(str(members[0]["abspath"]).encode(), err, 512)
    if not h:
        raise SystemExit(err.value.decode())
    species = [lib.cm_species_name(h, k).decode() for k in range(lib.cm_n_species(h))]
    lib.cm_free(h)
    tab = gate_tables(cfg, species=species)
    path = write_ensemble_file(out / "chemmanifold_ensemble.txt", tab, members, blend, spec.get("note", ""))
    print(f"  wrote {path} ({blend}, {len(members)} members, Z_st {tab['Z_st']:.4f})")
    ds = load_npz(stage_dir(cfg, "prep") / "dataset.npz")
    m = ds["is_val"]
    rep = selftest(lib, path, members, blend, tab, {k: ds[k][m] for k in ("Y_in", "T_in", "P_in")}, args.n, args.dt)
    (out / "ensemble_selftest.json").write_text(json.dumps(rep, indent=1))
    print("  selftest " + ("PASSED" if rep["passed"] else "FAILED") + f": {json.dumps(rep)}")
    if not rep["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--spec", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--n", type=int, default=500, help="self-test states")
    p.add_argument("--dt", type=float, default=2e-5)
    a = p.parse_args()
    main(load_config(a.config), a)

"""Stage 17: local closed-loop stability of exported surrogates on the states of a CFD solution.

Evaluation only: the CFD states are starting points of a test, never training data.

Takes the cells of a solution computed with direct GA18 chemistry (an OpenFOAM time directory or a
Fluent ASCII export), samples hot cells stratified by mixture fraction, and advances each one as a
homogeneous constant-(p, h) reactor for `--steps` steps of `--dt` (the CFD time step):

  * reference: Cantera with the mechanism of the config;
  * surrogate: the exported model file (chemmanifold_model.txt) through the UDF's own C core
    (fluent/udf/chemmanifold_core.c, compiled here and called with ctypes), chaining its outputs
    exactly as Fluent or OpenFOAM do, with the UDF's default options.

Without transport this is the harshest local test: in the CFD, diffusion pulls a drifting cell back
towards its neighbours, here nothing does. It reports, per model and per Z band, the OOD share of the
starting states and the T error after 1 step, 1 ms and the full horizon, and the share of cells that
drift by more than 100 K. Several models can be compared on the same cells.

    python scripts/17_di_local_stability.py --config configs/burner_fluent_strain.yaml \\
        --states /path/to/openfoam/4000 --models new=data/.../chemmanifold_model.txt old=/path/model.txt

Writes 08_fluent/stability_<label>/stability.json, stability.md, stability_cells.csv
"""

import ctypes
import json
import subprocess
from pathlib import Path

import cantera as ct
import numpy as np
import pandas as pd

from chemmanifold.chemistry import make_gas
from chemmanifold.flame import BilgerZ, flame_pressure, stream_states
from chemmanifold.fluent import fluent_state, read_fluent_ascii
from chemmanifold.io import base_parser, load_config, stage_dir

ROOT = Path(__file__).resolve().parents[1]
Z_BANDS = [0.0, 0.03, 0.055, 0.11, 0.22, 1.0]


class CmOptions(ctypes.Structure):
    _fields_ = [("T_freeze", ctypes.c_double), ("max_substeps", ctypes.c_int), ("ood_action", ctypes.c_int),
                ("T_margin", ctypes.c_double), ("y_margin", ctypes.c_double), ("p_tol", ctypes.c_double),
                ("check_ood", ctypes.c_int)]


class CmInfo(ctypes.Structure):
    _fields_ = [("flags", ctypes.c_uint), ("n_sub", ctypes.c_int), ("dt_sub", ctypes.c_double),
                ("Z", ctypes.c_double), ("manifold_ratio", ctypes.c_double), ("data_ratio", ctypes.c_double),
                ("hrr", ctypes.c_double), ("T_out", ctypes.c_double)]


def core_library(build_dir):
    """Compile the UDF's C core to a shared library (once) and declare its functions."""
    src = ROOT / "fluent" / "udf" / "chemmanifold_core.c"
    so = Path(build_dir) / "libchemmanifold_core.so"
    if not so.exists() or so.stat().st_mtime < src.stat().st_mtime:
        subprocess.run(["cc", "-O2", "-shared", "-fPIC", "-o", str(so), str(src), "-lm"], check=True)
    lib = ctypes.CDLL(str(so))
    lib.cm_load.restype = ctypes.c_void_p
    lib.cm_load.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    lib.cm_n_species.argtypes = [ctypes.c_void_p]
    lib.cm_species_name.restype = ctypes.c_char_p
    lib.cm_species_name.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.cm_default_options.argtypes = [ctypes.POINTER(CmOptions)]
    dp = ctypes.POINTER(ctypes.c_double)
    lib.cm_advance.argtypes = [ctypes.c_void_p, ctypes.POINTER(CmOptions), dp, ctypes.c_double, ctypes.c_double,
                               ctypes.c_double, ctypes.POINTER(CmInfo)]
    lib.cm_ood.argtypes = [ctypes.c_void_p, ctypes.POINTER(CmOptions), dp, ctypes.c_double, ctypes.c_double,
                           ctypes.POINTER(CmInfo)]
    return lib


def read_openfoam_field(path):
    """internalField of an ASCII OpenFOAM volScalarField (uniform or nonuniform List)."""
    text = Path(path).read_text()
    i = text.index("internalField")
    head = text[i:i + 200]
    if "nonuniform" not in head:
        return float(head.split("uniform")[1].split(";")[0])
    j = text.index("(", i)
    n = int(text[text.index(">", i) + 1:j].split()[-1])
    return np.array(text[j + 1:text.index(")", j)].split(), dtype=float)[:n]


def openfoam_state(time_dir, species):
    d = Path(time_dir)
    T = read_openfoam_field(d / "T")
    n = len(T)
    Y = np.zeros((n, len(species)))
    for k, s in enumerate(species):
        if (d / s).exists():
            Y[:, k] = read_openfoam_field(d / s)
    p = read_openfoam_field(d / "p")
    P = np.full(n, p) if np.isscalar(p) else p
    return Y, T, P


def load_states(path, species):
    path = Path(path)
    if path.is_dir():
        return openfoam_state(path, species)
    Y, T, P, _ = fluent_state(read_fluent_ascii(path), species)
    return Y, T, P


def sample_cells(Z, T, n, T_min, rng):
    """Up to n hot cells, the same number per Z band where available."""
    hot = np.flatnonzero(T > T_min)
    per = max(1, n // (len(Z_BANDS) - 1))
    picks = []
    for lo, hi in zip(Z_BANDS[:-1], Z_BANDS[1:]):
        band = hot[(Z[hot] >= lo) & (Z[hot] < hi)]
        picks.append(rng.choice(band, size=min(per, len(band)), replace=False) if len(band) else band)
    return np.concatenate(picks)


def reference(gas, Y, T, P, dt, steps, keep):
    """T after every step and Y after the steps in `keep` (indices from 0)."""
    gas.TPY = T, P, Y
    r = ct.IdealGasConstPressureReactor(gas, clone=False)
    net = ct.ReactorNet([r])
    out, Ys = np.empty(steps), {}
    for k in range(steps):
        net.advance((k + 1) * dt)
        out[k] = r.T
        if k in keep:
            Ys[k] = r.phase.Y.copy()
    return out, Ys


def surrogate(lib, model, opt, Y, T, P, dt, steps, keep):
    y = np.ascontiguousarray(Y, dtype=float).copy()
    ptr = y.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    info = CmInfo()
    lib.cm_ood(model, ctypes.byref(opt), ptr, T, P, ctypes.byref(info))
    flags0 = info.flags & 0x3F
    out, Ys = np.full(steps, np.nan), {}
    for k in range(steps):
        if lib.cm_advance(model, ctypes.byref(opt), ptr, T, P, dt, ctypes.byref(info)) != 0:
            break
        T = info.T_out
        out[k] = T
        if k in keep:
            Ys[k] = y.copy()
    return out, Ys, flags0


def main(cfg, args):
    gas = make_gas(cfg)
    species = list(gas.species_names)
    (Yf, _), (Yo, _) = stream_states(gas, cfg)
    Y, T, P = load_states(args.states, species)
    Y = np.clip(Y, 0.0, None)
    Y /= Y.sum(1, keepdims=True)
    Z = np.clip(BilgerZ(gas, Yf, Yo)(Y), 0.0, 1.0)
    rng = np.random.default_rng(cfg["seed"])
    cells = sample_cells(Z, T, args.n_cells, args.T_min, rng)
    print(f"  {len(T)} cells read, {int((T > args.T_min).sum())} above {args.T_min:.0f} K, {len(cells)} sampled")

    out_dir = stage_dir(cfg, "fluent", f"stability_{args.label}")
    lib = core_library(out_dir)
    k_1ms = min(args.steps, max(1, int(round(1e-3 / args.dt)))) - 1
    rows = []
    keep = {0, k_1ms}
    ref = [reference(gas, Y[c], T[c], P[c], args.dt, args.steps, keep) for c in cells]
    T_ref = np.array([r[0] for r in ref])
    track = [s for s in ("CO", "OH") if s in species]
    for spec in args.models:
        name, path = spec.split("=", 1)
        err = ctypes.create_string_buffer(512)
        model = lib.cm_load(str(path).encode(), err, 512)
        if not model:
            raise RuntimeError(f"{path}: {err.value.decode()}")
        names = [lib.cm_species_name(model, k).decode() for k in range(lib.cm_n_species(model))]
        idx = [species.index(s) for s in names]
        opt = CmOptions()
        lib.cm_default_options(ctypes.byref(opt))
        for i, c in enumerate(cells):
            T_s, Y_s, flags = surrogate(lib, model, opt, Y[c, idx], T[c], P[c], args.dt, args.steps, keep)
            d = T_s - T_ref[i]
            row = dict(model=name, cell=int(c), Z=Z[c], T0=T[c], ood=int(flags != 0), flags=int(flags),
                       dT_1=d[0], dT_1ms=d[k_1ms], dT_end=d[-1], dT_max=np.nanmax(np.abs(d)),
                       failed=int(not np.isfinite(d[-1])),
                       incT_ref_1=T_ref[i, 0] - T[c], incT_ref_1ms=T_ref[i, k_1ms] - T[c])
            for sp in track:                     # species increments over 1 step and 1 ms
                ks, km = species.index(sp), names.index(sp)
                for k, tag in ((0, "1"), (k_1ms, "1ms")):
                    y_ref = ref[i][1].get(k, np.full(len(species), np.nan))[ks]
                    y_sur = Y_s.get(k, np.full(len(names), np.nan))[km]
                    row[f"inc{sp}_ref_{tag}"] = y_ref - Y[c, ks]
                    row[f"inc{sp}_err_{tag}"] = y_sur - y_ref
            rows.append(row)
        print(f"  {name}: done")
    df = pd.DataFrame(rows)
    df["band"] = pd.cut(df.Z, Z_BANDS, right=False, labels=[f"{a}-{b}" for a, b in zip(Z_BANDS[:-1], Z_BANDS[1:])])

    def rel(err, inc):
        """Relative error of the chemical increment: sum |error| / sum |true increment|."""
        return float(np.nansum(np.abs(err)) / max(np.nansum(np.abs(inc)), 1e-30))

    def summary(g):
        out = dict(cells=len(g), ood=float(g.ood.mean()), dT_1=float(g.dT_1.abs().mean()),
                   dT_1ms=float(g.dT_1ms.abs().mean()), dT_end=float(g.dT_end.abs().mean()),
                   drift100=float((g.dT_max > 100).mean()), failed=int(g.failed.sum()),
                   rel_T_1=rel(g.dT_1, g.incT_ref_1), rel_T_1ms=rel(g.dT_1ms, g.incT_ref_1ms))
        for sp in track:
            out[f"rel_{sp}_1"] = rel(g[f"inc{sp}_err_1"], g[f"inc{sp}_ref_1"])
            out[f"rel_{sp}_1ms"] = rel(g[f"inc{sp}_err_1ms"], g[f"inc{sp}_ref_1ms"])
        return out

    report = dict(states=str(args.states), dt=args.dt, steps=args.steps, T_min=args.T_min,
                  models={m: dict(all=summary(g), **{str(b): summary(gb) for b, gb in g.groupby("band", observed=True)})
                          for m, g in df.groupby("model", sort=False)})
    df.to_csv(out_dir / "stability_cells.csv", index=False)
    (out_dir / "stability.json").write_text(json.dumps(report, indent=2))
    hzn = args.steps * args.dt * 1e3
    lines = [f"Cells above {args.T_min:.0f} K from `{args.states}`, homogeneous reactors, {args.steps} steps of "
             f"{args.dt:g} s ({hzn:g} ms). Mean |dT| against Cantera; drift = share with |dT| > 100 K at any step. "
             "Increment error = sum |error| / sum |Cantera increment| of T, CO and OH over one step (the "
             "chemical source the CFD balances against transport) and over 1 ms.", "",
             f"| model | Z band | cells | OOD at start | 1 step [K] | 1 ms [K] | {hzn:g} ms [K] | drift > 100 K "
             "| incr. T 1 step | incr. CO 1 step | incr. OH 1 step | incr. T 1 ms | incr. OH 1 ms |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m, r in report["models"].items():
        for b, s in r.items():
            lines.append(f"| {m} | {b} | {s['cells']} | {s['ood']:.0%} | {s['dT_1']:.1f} | {s['dT_1ms']:.1f} | "
                         f"{s['dT_end']:.1f} | {s['drift100']:.0%} | {s['rel_T_1']:.0%} | {s.get('rel_CO_1', np.nan):.0%} "
                         f"| {s.get('rel_OH_1', np.nan):.0%} | {s['rel_T_1ms']:.0%} | {s.get('rel_OH_1ms', np.nan):.0%} |")
    (out_dir / "stability.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--states", required=True, help="OpenFOAM time directory or Fluent ASCII export")
    p.add_argument("--models", nargs="+", required=True, help="label=path/to/chemmanifold_model.txt")
    p.add_argument("--label", default="di")
    p.add_argument("--n-cells", type=int, default=1500)
    p.add_argument("--T-min", dest="T_min", type=float, default=600.0)
    p.add_argument("--dt", type=float, default=4e-5)
    p.add_argument("--steps", type=int, default=250)
    a = p.parse_args()
    main(load_config(a.config), a)

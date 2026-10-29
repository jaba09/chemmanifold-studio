#!/usr/bin/env python3
"""Export OpenFOAM snapshots of the burner as Fluent-style ASCII tables, for the OOD diagnostics.

For each time of a run (decomposed or not), writes <out>/<label>_t<time>.csv with one row per cell:

  cellnumber, x-coordinate (axial), y-coordinate (radius), cell-volume,
  temperature, absolute-pressure, density-free mass fractions (Fluent species names: h2, ch2<s>, ...),
  x-velocity, radial-velocity, velocity-magnitude,
  strain-rate-mag   sqrt(2 S:S), S = sym(grad U)  (Fluent's "Strain Rate")
  mixture-fraction  Bilger Z (GA18 elements, CH4 and air streams of the case)
  scalar-dissipation  chi = 2 D |grad Z|^2, D = 2.2e-5 (T/300)^1.7 m2/s (unity Lewis, as in the case)

so scripts/16_coverage_gaps.py and 17_di_local_stability.py read it like a Fluent export. The tables
are a diagnostic of WHERE the run leaves the sampled space; they are never used as training data.

Needs the OpenFOAM environment (reconstructPar, foamFormatConvert, postProcess) and numpy.

  python3 foam_snapshot.py <run dir> <out dir> --label hyb1 [--times 0.005 0.01 ...]
"""

import argparse
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np

# GA18 species of the case and their elements (C, H, O)
ELEMENTS = {
    "H2": (0, 2, 0), "H": (0, 1, 0), "O": (0, 0, 1), "O2": (0, 0, 2), "OH": (0, 1, 1), "H2O": (0, 2, 1),
    "HO2": (0, 1, 2), "H2O2": (0, 2, 2), "CH2": (1, 2, 0), "CH2(S)": (1, 2, 0), "CH3": (1, 3, 0),
    "CH4": (1, 4, 0), "CO": (1, 0, 1), "CO2": (1, 0, 2), "HCO": (1, 1, 1), "CH2O": (1, 2, 1),
    "CH3O": (1, 3, 1), "N2": (0, 0, 0),
}
W_EL = np.array([12.011, 1.008, 15.999])
W_SP = {s: float(np.dot(e, W_EL)) + (28.014 if s == "N2" else 0.0) for s, e in ELEMENTS.items()}
FUEL = {"CH4": 1.0}
AIR = {"O2": 0.233, "N2": 0.767}


def run(cmd, cwd, log):
    with open(Path(cwd) / log, "w") as f:
        subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, check=True)


def read_field(path, n):
    """internalField of an ASCII OpenFOAM field: (n,) or (n, k)."""
    txt = Path(path).read_text()
    m = re.search(r"internalField\s+uniform\s+(\([^)]*\)|[^;]+);", txt)
    if m:
        v = np.array(m.group(1).strip("()").split(), float)
        return np.tile(v, (n, 1)).squeeze()
    m = re.search(r"internalField\s+nonuniform\s+List<(\w+)>\s*(\d+)\s*\(", txt)
    if not m:
        raise ValueError(f"cannot read {path}")
    kind, cnt = m.group(1), int(m.group(2))
    body = txt[m.end():]
    if kind == "scalar":
        return np.array(body.split(")", 1)[0].split(), float)[:cnt]
    k = {"vector": 3, "tensor": 9, "symmTensor": 6}[kind]
    vals = np.array(body[: body.find(";")].replace("(", " ").replace(")", " ").split()[: cnt * k], float)
    return vals.reshape(cnt, k)


def bilger(Y):
    """Bilger Z from a dict of mass-fraction arrays."""
    def beta(comp):
        zc = sum(comp.get(s, 0) * ELEMENTS[s][0] * W_EL[0] / W_SP[s] for s in ELEMENTS)
        zh = sum(comp.get(s, 0) * ELEMENTS[s][1] * W_EL[1] / W_SP[s] for s in ELEMENTS)
        zo = sum(comp.get(s, 0) * ELEMENTS[s][2] * W_EL[2] / W_SP[s] for s in ELEMENTS)
        return 2 * zc / W_EL[0] + 0.5 * zh / W_EL[1] - zo / W_EL[2]
    bf, bo = beta(FUEL), beta(AIR)
    return (beta(Y) - bo) / (bf - bo)


def write_scalar(path, name, values):
    n = len(values)
    with open(path, "w") as f:
        f.write("FoamFile { version 2.0; format ascii; class volScalarField; object %s; }\n" % name)
        f.write("dimensions [0 0 0 0 0 0 0];\ninternalField nonuniform List<scalar>\n%d\n(\n" % n)
        f.write("\n".join(f"{v:.8g}" for v in values))
        f.write("\n);\nboundaryField { \".*\" { type zeroGradient; } front { type wedge; } back { type wedge; } }\n")


def prepare_pp(case, pp):
    """A light copy of the case for post-processing in ASCII (mesh linked, not copied)."""
    pp.mkdir(parents=True, exist_ok=True)
    (pp / "constant").mkdir(exist_ok=True)
    for f in (case / "constant").iterdir():
        dst = pp / "constant" / f.name
        if not dst.exists():
            dst.symlink_to(f.resolve())
    if (pp / "system").exists():
        shutil.rmtree(pp / "system")
    shutil.copytree(case / "system", pp / "system")
    cd = (pp / "system" / "controlDict").read_text()
    cd = re.sub(r"writeFormat\s+\w+;", "writeFormat ascii;", cd)
    cd = re.sub(r"functions\s*\{.*\}\s*(//[^\n]*\s*)*$", "functions {}\n", cd, flags=re.S)
    (pp / "system" / "controlDict").write_text(cd)
    if not (pp / "0" / "C").exists():
        (pp / "0").mkdir(exist_ok=True)
        run(["postProcess", "-func", "writeCellCentres", "-time", "0"], pp, "log.C")
        run(["postProcess", "-func", "writeCellVolumes", "-time", "0"], pp, "log.V")


def times_of(case):
    d = case / "processor0" if (case / "processor0").exists() else case
    ts = []
    for p in d.iterdir():
        try:
            t = float(p.name)
        except ValueError:
            continue
        if t > 0 and (p / "T").exists():
            ts.append(p.name)
    return sorted(ts, key=float)


def export(case, pp, tname, out_csv):
    if (case / "processor0").exists() and not (case / tname / "T").exists():
        run(["reconstructPar", "-time", tname], case, "log.reconstruct_pp")
    dst = pp / tname
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(case / tname, dst)
    run(["foamFormatConvert", "-time", tname], pp, "log.convert")
    C = read_field(pp / "0" / "C", 0)
    n = len(C)
    V = read_field(pp / "0" / "V", n)
    T = read_field(dst / "T", n)
    p = read_field(dst / "p", n)
    U = read_field(dst / "U", n)
    Y = {s: read_field(dst / s, n) if (dst / s).exists() else np.zeros(n) for s in ELEMENTS}
    G = read_field(dst / "grad(U)", n) if (dst / "grad(U)").exists() else None
    Z = bilger(Y)
    write_scalar(dst / "Zmix", "Zmix", Z)
    run(["postProcess", "-func", "grad(Zmix)", "-time", tname], pp, "log.gradZ")
    gZ = read_field(dst / "grad(Zmix)", n)
    r = np.hypot(C[:, 1], C[:, 2])
    er = np.where(r[:, None] > 0, np.c_[np.zeros(n), C[:, 1], C[:, 2]] / np.maximum(r, 1e-30)[:, None], 0)
    cols = {
        "cellnumber": np.arange(n), "x-coordinate": C[:, 0], "y-coordinate": r, "cell-volume": V,
        "temperature": T, "absolute-pressure": p,
    }
    for s in ELEMENTS:
        cols[s.lower().replace("(", "<").replace(")", ">")] = Y[s]
    cols["x-velocity"] = U[:, 0]
    cols["radial-velocity"] = (U * er).sum(1)
    cols["velocity-magnitude"] = np.linalg.norm(U, axis=1)
    if G is not None:
        g = G.reshape(n, 3, 3)
        S = 0.5 * (g + g.transpose(0, 2, 1))
        cols["strain-rate-mag"] = np.sqrt(2 * (S * S).sum((1, 2)))
    cols["mixture-fraction"] = Z
    D = 2.2e-5 * (np.maximum(T, 200) / 300.0) ** 1.7
    cols["scalar-dissipation"] = 2 * D * (gZ ** 2).sum(1)
    names = list(cols)
    np.savetxt(out_csv, np.column_stack([cols[k] for k in names]), delimiter=",", header=",".join(names),
               comments="", fmt="%.8g")
    shutil.rmtree(dst)
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case")
    ap.add_argument("out")
    ap.add_argument("--label", default="run")
    ap.add_argument("--times", nargs="*", default=None, help="default: every written time")
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args()
    case, out = Path(a.case).resolve(), Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    pp = out / f".pp_{a.label}"
    prepare_pp(case, pp)
    for t in a.times or times_of(case):
        csv = out / f"{a.label}_t{float(t) * 1e3:07.2f}ms.csv"
        if a.skip_existing and csv.exists():
            continue
        n = export(case, pp, t, csv)
        print(f"{csv}: {n} cells")


if __name__ == "__main__":
    main()

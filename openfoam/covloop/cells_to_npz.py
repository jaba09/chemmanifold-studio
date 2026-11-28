#!/usr/bin/env python3
"""COVLOOP step 3 input: cell states of one leg (ARC22 species) -> cells.npz for scripts/25_coverage.py.

Reads reconstructed ASCII time directories of an OpenFOAM run (T, p, the 22 ARC species, cell volumes V) and
writes, for all requested snapshots together,
  T (N,), Y (N, 22), species (22,), mass (N,) = rho V, dt (N,) chemistry step of the snapshot, time (N,),
  ood (N, bool)  = the model's own trust gate at that state and dt (CPUFastMoE.step: local PCA, inter-expert
                   discrepancy, positivity, dt range, i.e. the flags the C core raises in the run),
  excluded (N,)  = True: these are CFD states, starting states for step 4 at most, never training pairs.
rho comes from the ideal gas law with the ARC22 molecular weights (the run's own rho is used when written).
The OOD flag is recomputed offline with the same exported model instead of being written by the plug-in, so the
run needs no extra field; pass the model the leg ran with. The chemistry dt is the flow deltaT of the snapshot
(uniform/time), which is what userChemStep passes to the surrogate without LTS.

  python3 cells_to_npz.py RUN_DIR OUT.npz --model iterK/moe.npz [--times 0.01 0.02 ...] [--every 1] [--volumes]
--volumes runs `postProcess -func writeCellVolumes` for times that miss V (needs the OpenFOAM environment);
times written in binary must first go through `foamFormatConvert` (see openfoam/tools/foam_snapshot.py).
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import numpy as np
from foam_snapshot import read_field  # noqa: E402

RU = 8314.462618
SKEL = os.path.join(HERE, "..", "..", "mechanisms", "arc_gri30_nox22", "gri30_skel43.yaml")


def time_dirs(run):
    out = []
    for p in Path(run).iterdir():
        try:
            t = float(p.name)
        except ValueError:
            continue
        if t > 0 and (p / "T").exists():
            out.append((t, p))
    return [p for _, p in sorted(out)]


def delta_t(tdir):
    f = tdir / "uniform" / "time"
    if f.exists():
        m = re.search(r"\bdeltaT\s+([0-9eE+.\-]+);", f.read_text())
        if m:
            return float(m.group(1))
    return None


def element_matrix(species, mech=SKEL):
    import cantera as ct
    gas = ct.Solution(mech)
    idx = [gas.species_index(s) for s in species]
    W = gas.molecular_weights[idx]
    A = np.array([[gas.n_atoms(k, e) * gas.atomic_weight(e) / gas.molecular_weights[k] for k in idx]
                  for e in range(gas.n_elements)])
    return W, A[np.abs(A).sum(1) > 0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("out")
    ap.add_argument("--model", required=True, help="moe.npz the leg ran with (its .json gives the species)")
    ap.add_argument("--times", nargs="*", type=float)
    ap.add_argument("--every", type=int, default=1, help="use every n-th written time")
    ap.add_argument("--dt", type=float, help="chemistry dt when uniform/time has none (LTS: use the dt histogram)")
    ap.add_argument("--volumes", action="store_true")
    ap.add_argument("--mech", default=SKEL)
    a = ap.parse_args()
    from chemmanifold.moe import CPUFastMoE
    species = json.load(open(a.model.replace(".npz", ".json")))["species"]
    fast = CPUFastMoE.load(a.model)
    W, A = element_matrix(species, a.mech)
    dirs = time_dirs(a.run)
    if a.times:
        dirs = [d for d in dirs if any(abs(float(d.name) - t) <= 1e-9 * max(1.0, t) for t in a.times)]
    dirs = dirs[:: max(1, a.every)]
    if not dirs:
        sys.exit("no time directories with T found (reconstructPar first?)")
    out = {k: [] for k in ("T", "Y", "mass", "dt", "time", "ood")}
    for d in dirs:
        if not (d / "V").exists():
            if not a.volumes:
                sys.exit(f"{d}/V missing: rerun with --volumes or postProcess -func writeCellVolumes")
            subprocess.run(["postProcess", "-func", "writeCellVolumes", "-time", d.name], cwd=a.run, check=True,
                           stdout=subprocess.DEVNULL)
        T = read_field(d / "T", 0)
        n = len(T)
        Y = np.zeros((n, len(species)))
        for k, s in enumerate(species):
            if (d / s).exists():
                Y[:, k] = read_field(d / s, n)
            elif s != "N2":
                print(f"[cells] {d.name}: field {s} missing, taken as 0")
        if not (d / "N2").exists():                       # inert species written implicitly
            Y[:, species.index("N2")] = 1.0 - np.delete(Y, species.index("N2"), 1).sum(1)
        Y = np.maximum(Y, 0.0)
        p = read_field(d / "p", n) if (d / "p").exists() else np.full(n, 101325.0)
        rho = read_field(d / "rho", n) if (d / "rho").exists() else p / (RU * T * (Y / W).sum(1))
        V = read_field(d / "V", n)
        dt = delta_t(d) or a.dt
        if dt is None:
            sys.exit(f"{d}: no deltaT in uniform/time; pass --dt")
        dts = np.full(n, dt)
        _, fb = fast.step(T, Y, dts, A=A)
        hot = T >= fast.T_frozen
        print(f"[cells] t={d.name}: {n} cells, dt {dt:.3g} s, OOD {100 * fb[hot].mean() if hot.any() else 0:.1f} % "
              f"of {hot.sum()} active cells")
        for k, v in zip(out, (T, Y, rho * V, dts, np.full(n, float(d.name)), fb)):
            out[k].append(v)
    out = {k: np.concatenate(v) for k, v in out.items()}
    np.savez(a.out, species=np.array(species), excluded=np.ones(len(out["T"]), bool), **out)
    print(f"{len(out['T'])} cell states from {len(dirs)} snapshots -> {a.out}")


if __name__ == "__main__":
    main()

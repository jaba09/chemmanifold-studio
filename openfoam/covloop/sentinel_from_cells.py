#!/usr/bin/env python3
"""COVLOOP sentinels: 25- and 200-step closed-loop checks of the surrogate from cell states of a leg -> sentinel.npz.

Start states are drawn from cells.npz (cells_to_npz.py), up to --per-bin of them in every reacting coverage bin,
so that every bin that carries mass gets multi-step checks, not only the bins the run happens to flag. From each
start the exported model is stepped on its own output at the leg's dt (element projection, constant (h, p)
T inversion with the skel43 NASA-7 data, as in the C core) and compared with the ARC22 kernel integrated over
the same times (general_sampling.label_segment). The check fails when, at step 25 or 200,
  |T_s - T_DI| > max(1 K, 0.3 |T_DI - T0|), or for OH, CO, H, O, NO, NO2, N2O, HCN
  |Ys - Yd| > max(floor, 0.3 |Yd - Y0|)  (floors as in shadow_to_npz.py).
Comparison data only: neither the starts nor the DI trajectories are ever training data.

  python3 sentinel_from_cells.py cells.npz OUT.npz --model iterK/moe.npz [--per-bin 3] [--steps 25 200] [--np 8]
"""
import argparse, json, os, sys
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import numpy as np
from shadow_to_npz import FLOORS  # noqa: E402
from cells_to_npz import SKEL, element_matrix  # noqa: E402

_W = {}


def _di(args):
    if "arc" not in _W:
        import cantera as ct
        from chemmanifold import general_sampling as gs
        _W["arc"], _W["gas"], _W["gs"] = gs.ARC(), ct.Solution(gs.SKEL), gs
    T, Y, dt, n = args
    try:
        return _W["gs"].label_segment(_W["arc"], T, Y, dt, n, _W["gas"])
    except Exception:
        return None, None


def rollout(fast, thermo, T0, Y0, dt, n, A):
    """Pure surrogate rollout (no fallback); returns T (B, n), Y (B, n, S) and the share of steps flagged OOD."""
    import torch
    h0 = thermo.nasa.enthalpy(torch.as_tensor(Y0), torch.as_tensor(T0)).numpy()
    T, Y = T0.copy(), Y0.copy()
    Ts, Ys, fbs = [], [], []
    for _ in range(n):
        Y, fb = fast.step(T, Y, dt, A=A)
        T = thermo.nasa(torch.as_tensor(Y), torch.as_tensor(h0), torch.as_tensor(T)).numpy()
        Ts.append(T.copy()), Ys.append(Y.copy()), fbs.append(fb)
    return np.stack(Ts, 1), np.stack(Ys, 1), np.mean(fbs, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cells")
    ap.add_argument("out")
    ap.add_argument("--model", required=True)
    ap.add_argument("--per-bin", type=int, default=3)
    ap.add_argument("--steps", nargs="+", type=int, default=[25, 200])
    ap.add_argument("--max-starts", type=int, default=3000)
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mech", default=SKEL)
    a = ap.parse_args()
    from chemmanifold.coverage import CoverageGrid, reacting_mask
    from chemmanifold.moe import CPUFastMoE, RolloutThermo
    rng = np.random.default_rng(a.seed)
    c = dict(np.load(a.cells, allow_pickle=True))
    species = [str(s) for s in c["species"]]
    if species != json.load(open(a.model.replace(".npz", ".json")))["species"]:
        sys.exit("species of cells.npz and model differ")
    grid = CoverageGrid(a.mech)
    Z, Tc, cc, dh = grid.coordinates(c["T"], c["Y"], species=species)
    b, _ = grid.bin_index(Z, Tc, cc, dh)
    fast = CPUFastMoE.load(a.model)
    act = reacting_mask(Tc, cc) & (c["T"] >= fast.T_frozen)
    pick = []
    for bb in np.unique(b[act]):
        i = np.where(act & (b == bb))[0]
        pick.append(rng.choice(i, min(a.per_bin, len(i)), replace=False))
    pick = np.concatenate(pick) if pick else np.zeros(0, int)
    if len(pick) > a.max_starts:
        pick = rng.choice(pick, a.max_starts, replace=False)
    n = max(a.steps)
    T0, Y0, dt = c["T"][pick], c["Y"][pick], c["dt"][pick]
    print(f"[sentinel] {len(pick)} starts in {len(np.unique(b[pick]))} bins, {n} steps each")
    with Pool(a.np) as pool:
        ref = pool.map(_di, [(T0[i], Y0[i], dt[i], n) for i in range(len(pick))], chunksize=4)
    ok = np.array([r[0] is not None for r in ref])
    W, A = element_matrix(species, a.mech)
    th = RolloutThermo(species, a.mech)
    Ts, Ys, fb = rollout(fast, th, T0[ok], Y0[ok], dt[ok], n, A)
    Td = np.array([r[0] for r, k in zip(ref, ok) if k])
    Yd = np.array([r[1] for r, k in zip(ref, ok) if k])
    passed = np.ones(ok.sum(), bool)
    detail = {}
    for s in a.steps:
        j = s - 1
        bad = np.abs(Ts[:, j] - Td[:, j]) > np.maximum(1.0, 0.3 * np.abs(Td[:, j] - T0[ok]))
        for sp, fl in FLOORS.items():
            if sp in species:
                k = species.index(sp)
                bad |= np.abs(Ys[:, j, k] - Yd[:, j, k]) > np.maximum(fl, 0.3 * np.abs(Yd[:, j, k] - Y0[ok, k]))
        detail[f"pass_{s}"] = ~bad
        passed &= ~bad
        print(f"[sentinel] step {s}: {100 * bad.mean():.1f} % fail")
    np.savez(a.out, T=T0[ok], Y=Y0[ok], dt=dt[ok], species=np.array(species), ood_share=fb,
             excluded=np.ones(ok.sum(), bool), **{"pass": passed}, **detail)
    print(f"{ok.sum()} sentinel checks ({(~ok).sum()} DI failures dropped), {100 * (1 - passed.mean()):.1f} % fail "
          f"-> {a.out}")


if __name__ == "__main__":
    main()

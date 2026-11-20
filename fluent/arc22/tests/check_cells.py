"""A priori check on real burner states: for hot cells of the Fluent GRI-Mech 3.0 DI solution, advance
each cell over one chemistry dt with (a) the UDF's ARC22 step (22 species, the 31 others dropped) and
(b) a Cantera GRI-Mech 3.0 constant-pressure reactor from the full 53-species state; compare T and
species after dt, and time the UDF step (the cost per cell Fluent will see).

    python fluent/arc22/tests/check_cells.py quemadorUnicoTesis_60KCells-GRI--ID.dat.h5   (needs h5py, Cantera)
"""
import sys, time, pathlib
import numpy as np, h5py, cantera as ct
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from arc22py import ARC22

FLUENT53 = ("h2 h o o2 oh h2o ho2 h2o2 c ch ch2 ch2<s> ch3 ch4 co co2 hco ch2o ch2oh ch3o ch3oh c2h c2h2 c2h3 "
            "c2h4 c2h5 c2h6 hcco ch2co hccoh n nh nh2 nh3 nnh no no2 n2o hno cn hcn h2cn hcnn hcno hocn hnco "
            "nco ar c3h7 c3h8 ch2cho ch3cho n2").split()


def main(dat, n=300, seed=1):
    c = h5py.File(dat, "r")["results/1/phase-1/cells"]
    T, Y53 = c["SV_T/1"][:], c["SV_Y/1"][:]
    arc, gri = ARC22(), ct.Solution("gri30.yaml")
    i22 = [FLUENT53.index(s.lower()) for s in arc.names]
    to_gri = [gri.species_index(s.upper().replace("<S>", "(S)")) for s in FLUENT53]
    hot = np.random.default_rng(seed).choice(np.where(T > 1000)[0], n, replace=False)
    lines = ["# A priori check on the Fluent GRI-Mech 3.0 burner solution", "",
             f"{n} random cells with T > 1000 K (of {(T > 1000).sum()}); after one chemistry dt, ARC22 UDF step vs "
             "Cantera GRI-Mech 3.0 from the full 53-species state.", "",
             "| dt [s] | mean abs dT err [K] | max [K] | mean abs dT [K] (GRI) | OH rel err | CO rel err | NO rel err | UDF ms/cell |",
             "|---|---|---|---|---|---|---|---|"]
    for dt in (1e-5, 1e-4, 1e-3):
        e, d, rel, cpu = [], [], {k: [] for k in ("OH", "CO", "NO")}, 0.0
        for i in hot:
            Y = Y53[i, i22] / Y53[i, i22].sum()
            c0 = time.perf_counter(); Ya, info = arc.advance(Y, T[i], ct.one_atm, dt); cpu += time.perf_counter() - c0
            yg = np.zeros(gri.n_species); yg[to_gri] = Y53[i]
            gri.TPY = T[i], ct.one_atm, yg
            r = ct.IdealGasConstPressureReactor(gri, clone=False); net = ct.ReactorNet([r]); net.rtol, net.atol = 1e-8, 1e-14
            net.advance(dt)
            e.append(info.T_out - r.T); d.append(r.T - T[i])
            for k in rel:
                yg_k = r.phase.Y[gri.species_index(k)]
                rel[k].append(abs(Ya[arc.names.index(k)] - yg_k) / max(yg_k, 1e-6))
        e = np.abs(e)
        lines.append(f"| {dt:g} | {e.mean():.2f} | {e.max():.1f} | {np.abs(d).mean():.1f} | {np.mean(rel['OH']):.3f} | "
                     f"{np.mean(rel['CO']):.3f} | {np.mean(rel['NO']):.3f} | {1e3*cpu/n:.2f} |")
    text = "\n".join(lines) + "\n"
    print(text)
    (pathlib.Path(__file__).resolve().parent / "CHECK_CELLS.md").write_text(text)


if __name__ == "__main__":
    main(sys.argv[1])

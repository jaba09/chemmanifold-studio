"""COVLOOP stage 0: C-core MoE (chemmanifold_core.c, arch moe_top2) vs numpy CPUFastMoE on ARC22 pairs.
Needs the smoke pairs from scripts/26_general_sampling.py (configs/covloop_smoke.yaml) and gcc."""
import sys, os, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
import cantera as ct
from chemmanifold.moe import MoEConfig, MoESurrogate, CPUFastMoE, project_elements, write_core_model
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
tmp = "/tmp/claude-0/moe_core"; os.makedirs(tmp, exist_ok=True)
d = np.load(sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-0/gs_smoke/pairs.npz", allow_pickle=True)
sp = [str(s) for s in d["species"]]
cfg = MoEConfig(n_experts=4, expert_hidden=32, router_hidden=16, epochs_router=3, epochs_expert=5,
                epochs_joint=5, threads=4, species=sp)
m = MoESurrogate(cfg).fit(d["T"], d["Y"], d["dt"], d["dY"], log=lambda s: None)
A = write_core_model(f"{tmp}/model.txt", m.arrays, sp)
subprocess.check_call(["gcc", "-O2", "-I", f"{root}/fluent/udf", "-o", f"{tmp}/t", f"{root}/tests/moe_core_test.c",
                       f"{root}/fluent/udf/chemmanifold_core.c", "-lm"])
n = min(300, len(d["T"]))
with open(f"{tmp}/states.txt", "w") as f:
    f.write(f"{n}\n")
    for i in range(n):
        f.write("%.17g %.17g " % (d["T"][i], d["dt"][i]) + " ".join("%.17g" % y for y in d["Y"][i]) + "\n")
subprocess.check_call([f"{tmp}/t", f"{tmp}/model.txt", f"{tmp}/states.txt", f"{tmp}/out.txt"])
o = np.loadtxt(f"{tmp}/out.txt")
Yc, Tc = o[:, 2:2 + len(sp)], o[:, 1]
fast = CPUFastMoE(m.arrays)
R, info = fast.rate(d["T"][:n], d["Y"][:n], d["dt"][:n])
Yn = project_elements(d["Y"][:n], d["Y"][:n] + d["dt"][:n, None] * R, A)
gri = ct.Solution("gri30.yaml"); g = ct.Solution(thermo="ideal-gas", species=[gri.species(s) for s in sp])
Tn = []
for i in range(n):
    g.TPY = d["T"][i], 101325.0, d["Y"][i]; h = g.enthalpy_mass
    g.HPY = h, 101325.0, Yn[i]; Tn.append(g.T)
dY = np.abs(Yc - Yn).max(); dT = np.abs(Tc - np.array(Tn)).max()
dr = np.abs(o[:, -2] - info["gate_ratio"]).max()
print("median |dT| %.1e K" % np.median(np.abs(Tc - np.array(Tn))))
print("C vs numpy: max |dY| %.2e, max |dT| %.2e K, max |pca ratio diff| %.2e" % (dY, dT, dr))
assert dY < 1e-10 and dT < 0.5 and dr < 1e-8
print("SMOKE OK")

"""End-to-end smoke: general-sampling pairs (scripts/26 output) -> MoE fit -> numpy step with ARC22 element matrix."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from chemmanifold.moe import MoEConfig, MoESurrogate, CPUFastMoE
from chemmanifold import general_sampling as gs
d = np.load(sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-0/gs_smoke/pairs.npz", allow_pickle=True)
arc = gs.ARC()
A = np.zeros((4, 22))
for k in range(22):
    e = np.zeros(4); arc.lib.arc_species_elements(k, arc._p(e)); A[:, k] = e / arc.W[k]
cfg = MoEConfig(n_experts=4, expert_hidden=32, router_hidden=16, epochs_router=5, epochs_expert=10,
                epochs_joint=10, threads=4, species=[str(s) for s in d["species"]])
m = MoESurrogate(cfg).fit(d["T"], d["Y"], d["dt"], d["dY"], log=lambda s: None)
f = CPUFastMoE(m.arrays)
Yn, fb = f.step(d["T"], d["Y"], d["dt"], A=A)
drift = np.abs((Yn - d["Y"]) @ A.T).max()
print("pairs %d, router acc %.3f, fallback %.3f, element drift %.1e, L1 err %.2e vs |dY| %.2e" % (
    len(d["T"]), m.history["router_acc"], fb.mean(), drift, np.abs(Yn - d["Y"] - d["dY"]).sum(1).mean(),
    np.abs(d["dY"]).sum(1).mean()))
assert drift < 1e-14
print("SMOKE OK")

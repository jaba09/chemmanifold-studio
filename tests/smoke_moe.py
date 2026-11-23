"""Smoke test of chemmanifold/moe.py (COVLOOP stage 0): tiny 0D CH4/air dataset, short training,
torch-vs-numpy parity, element conservation, trust-gate behaviour on an off-manifold state.
Run: python -I tests/smoke_moe.py  (needs torch, cantera, scikit-learn; ~1-2 min on 4 cores)."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
import cantera as ct
from chemmanifold.moe import MoEConfig, MoESurrogate, CPUFastMoE

rng = np.random.default_rng(0)
mech = os.path.join(os.path.dirname(__file__), "..", "mechanisms", "arc_gri30_nox22", "gri30_skel43.yaml")
gas = ct.Solution(mech)
S = gas.n_species
A = np.array([[gas.n_atoms(k, e) * gas.atomic_weight(e) / gas.molecular_weights[k]
               for k in range(S)] for e in range(gas.n_elements)])
states = []
for phi in (0.7, 1.0, 1.3):
    for T0 in (1150.0, 1300.0):
        gas.set_equivalence_ratio(phi, "CH4", "O2:1, N2:3.76"); gas.TP = T0, ct.one_atm
        r = ct.IdealGasConstPressureReactor(gas, clone=True); net = ct.ReactorNet([r])
        for t in np.geomspace(1e-5, 0.2, 60):
            net.advance(t); states.append((r.thermo.T, r.thermo.Y.copy()))
T, Y, dt, dY = [], [], [], []
for Ts, Ys in states:
    for _ in range(2):
        d = 10 ** rng.uniform(-6, -4)
        gas.TPY = Ts, ct.one_atm, Ys
        r = ct.IdealGasConstPressureReactor(gas, clone=True); net = ct.ReactorNet([r])
        net.rtol, net.atol = 1e-9, 1e-15
        net.advance(d)
        T.append(Ts); Y.append(Ys); dt.append(d); dY.append(r.thermo.Y - Ys)
T, Y, dt, dY = map(np.array, (T, Y, dt, dY))
print("pairs", len(T), "species", S)
cfg = MoEConfig(n_experts=3, expert_hidden=32, router_hidden=16, epochs_router=5, epochs_expert=10,
                epochs_joint=10, threads=4, species=list(gas.species_names), dt_min=1e-6, dt_max=1e-4)
t0 = time.time()
m = MoESurrogate(cfg).fit(T, Y, dt, dY, log=lambda s: None)
print("train s %.1f router acc %.3f" % (time.time() - t0, m.history["router_acc"]))
fast = CPUFastMoE(m.arrays)
Rt = m.torch_rate(T, Y, dt)
Rn, info = fast.rate(T, Y, dt)
par = np.max(np.abs((Rt - Rn) * dt[:, None]))
print("parity max |dY torch - dY numpy| %.2e" % par)
Yn, fb = fast.step(T, Y, dt, A=A)
cons = np.max(np.abs((Yn - Y) @ A.T))
print("element drift max %.2e, min Y %.2e, fallback share %.3f" % (cons, Yn.min(), fb.mean()))
err = np.abs(Yn - (Y + dY)).sum(1)
print("mean L1 dY error %.2e (mean |dY| %.2e)" % (err.mean(), np.abs(dY).sum(1).mean()))
Yo = Y[:5].copy(); Yo[:, gas.species_index("OH")] += 0.05; Yo /= Yo.sum(1, keepdims=True)
_, fbo = fast.step(T[:5], Yo, dt[:5])
print("off-manifold states flagged:", int(fbo.sum()), "/ 5")
m.save("/tmp/claude-0/smoke_moe.npz")
assert par < 1e-8 and cons < 1e-12 and Yn.min() >= 0 and fbo.sum() >= 4
print("SMOKE OK")

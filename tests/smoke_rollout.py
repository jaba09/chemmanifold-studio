"""Smoke test of the MoE rollout loss pieces (COVLOOP stage 0).

Checks that the reference segments (scripts/26 `rollout:`) are constant-(h, p) ARC22 trajectories that the torch
NASA-7 inversion of RolloutThermo reproduces, that the element projection keeps the segment elements, and that the
rollout loss is finite and differentiable.
Run: python -I tests/smoke_rollout.py SEGMENTS.npz   (segments from configs/covloop_smoke.yaml, ~10 s)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
import torch
from chemmanifold.moe import MoEConfig, MoESurrogate, RolloutThermo, build_torch_model, _RolloutLoss

seg = np.load(sys.argv[1], allow_pickle=True)
sp = [str(s) for s in seg["species"]]
mech = os.path.join(os.path.dirname(__file__), "..", "mechanisms", "arc_gri30_nox22", "gri30_skel43.yaml")
th = RolloutThermo(sp, mech)
f = lambda a: torch.as_tensor(np.asarray(a, float))
T0, Y0, Tr, Yr = f(seg["T0"]), f(seg["Y0"]), f(seg["Tref"]), f(seg["Yref"])
M, n, S = Yr.shape
h0 = th.nasa.enthalpy(Y0, T0)
Tinv = th.nasa(Yr.reshape(-1, S), h0.repeat_interleave(n), T0.repeat_interleave(n)).reshape(M, n)
dT = (Tinv - Tr).abs().max().item()
A = th.proj.A
del_el = ((Yr - Y0[:, None]) @ A.T).abs().max().item()
Yp = th.proj(Y0, Yr[:, -1] * 1.01)
del_proj = ((Yp - Y0) @ A.T).abs().max().item()
print(f"{M} segments x {n} steps; max |T_inv - T_ref| {dT:.3f} K; element drift ref {del_el:.2e}, projection {del_proj:.2e}")

# rollout loss on an untrained model: finite and gives gradients
cfg = MoEConfig(n_experts=2, expert_hidden=16, router_hidden=8, species=sp)
sur = MoESurrogate(cfg)
x = np.column_stack([seg["T0"], ((np.maximum(seg["Y0"], 0) + 1e-10) ** 0.1 - 1) / 0.1])
sur.x_mu, sur.x_sd = x.mean(0), np.where(x.std(0) > 0, x.std(0), 1.0)
sur.ldt_mu, sur.ldt_sd = np.log10(seg["dt"]).mean(), max(np.log10(seg["dt"]).std(), 1e-6)
R = (Yr[:, 0] - Y0).numpy() / seg["dt"][:, None]
sur.R_mu, sur.R_sd = R.mean(0), np.where(R.std(0) > 0, R.std(0), 1.0)
model = build_torch_model(S + 1, S, cfg).double()
loss = _RolloutLoss(model, dict(seg), th, sur, cfg)()
loss.backward()
g = sum(p.grad.abs().sum().item() for p in model.parameters() if p.grad is not None)
print(f"rollout loss {loss.item():.4g}, grad L1 {g:.3g}")
assert dT < 1.0 and del_el < 1e-12 and del_proj < 1e-12 and np.isfinite(loss.item()) and g > 0
print("SMOKE OK")

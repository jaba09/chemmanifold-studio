# Reference runs

## H2/air (default `config.yaml`)

H2/air, Cantera `h2o2.yaml` (10 species), envelope phi 0.5–2.0, T0 1050–1300 K, P0 1–5 atm,
64 Sobol trajectories (42 autoignition, 22 PaSR), dt_base = 2 us. Run on 4 CPU cores. The full
pipeline takes about 11 minutes, almost all of it training (300 epochs per model, about 1 s per epoch).

### Data and manifold (stages 1–6)

* 17,514 autoignition pairs (arc-length sampled, strides 1/2/4) + 8,800 PaSR micromixing pairs.
* 23,156 train / 3,158 validation pairs.
* Global PCA: d_99.5% = 6 components.
* VQ-PCA (K = 4): R2(2) = 0.952, R2(3) = 0.992, R2(4) = 0.997, R2(6) = 0.9997, R2(8) = 0.99998,
  so the recommended latent dimension is d = 4 (used by Phy-ChemNODE).

### Certification

| Metric | ResNet-FiLM | Phy-ChemNODE |
|---|---|---|
| Parameters | 234k | 55k |
| **Tier 1** R2 of Box-Cox increments (validation) | 0.9998 | 0.9973 |
| Tier 1 max elemental residual max\|AY_hat − AY_t\| | 8.3e-17 | 8.3e-17 |
| Tier 1 max \|sum Y − 1\| change | 2.2e-16 | 2.2e-16 |
| Tier 1 temperature MAE / max error | 0.60 K / 38.6 K | 2.11 K / 67.1 K |
| **Tier 2** (phi=1, 1150 K, 1 atm, 250 × 2 us) tau_ign error | −6.5% (58 vs 62 us) | −6.5% (58 vs 62 us) |
| Tier 2 progress-aligned T MAE | 26.4 K | 21.0 K |
| Tier 2 phase-aligned species NRMSE | 0.76% | 0.82% |
| **Tier 3** (18-point phi × T0 × P0 grid) mean / max \|tau_ign error\| | 3.8% / 21.8% | 4.6% / 11.1% |
| Tier 3 mean / max progress-aligned T MAE | 61.1 K / 179 K | 31.7 K / 85.3 K |
| Tier 3 mean / max species NRMSE | 0.55% / 1.69% | 0.74% / 1.57% |

The tau_ign resolution is one rollout step (2 us), so at short delays one step is already ±3–10%.

### Known weakness

ResNet-FiLM drifts during long post-ignition stretches at 1 atm (for example, phi = 0.6 at 1100 K
ends at 2152 K instead of 2430 K after 500 us). Because h is conserved, this drift is a slow
composition creep along the equilibrium tail. The 0D trajectories stop 25 steps after reaching
equilibrium (§2.3), so these states are barely in the training data. Possible fixes are a longer
equilibrium tail (`autoignition.n_consecutive`), a larger `loss_weights.equil`, or a few multi-step
rollout losses during training. Phy-ChemNODE, whose dynamics are confined to the 4-D latent manifold,
is noticeably more stable here.

## CH4/air, GRI-Mech 3.0 (`configs/ch4_gri30.yaml`, experimental)

53 species, phi 0.6–1.6, T0 1400–1700 K, P0 1–5 atm, dt_base = 10 us. 23,733 autoignition +
8,800 PaSR pairs. Global PCA d_99.5% = 9 (the spec quotes d = 9 for GRI-Mech 3.0). VQ-PCA gives
R2(6) = 0.998, so latent d = 6. Wall time on 4 CPU threads is about 23 min: PaSR takes 3.7 min and
each model trains in about 9.5 min.

| Metric | ResNet-FiLM | Phy-ChemNODE |
|---|---|---|
| Tier 1 R2 of Box-Cox increments | 0.9970 | 0.9926 |
| Tier 1 max elemental residual | 1.9e-16 | 1.9e-16 |
| Tier 1 temperature MAE | 0.53 K | 1.37 K |
| Tier 2 tau_ign error (phi=1, 1550 K, 1 atm) | −36% | −8.3% |
| Tier 3 mean \|tau_ign error\| | 34% | 24% |
| Tier 3 mean progress-aligned T MAE | 1128 K | 126 K |
| Tier 3 mean species NRMSE | 45% | 4.9% |

Single-step accuracy and conservation are as good as for H2, but closed-loop rollouts are not
stable yet. After ignition, ResNet-FiLM collapses to the 280 K lower bound of the temperature
solver in most cases. Phy-ChemNODE stays physical, but it fires too early at 1 atm with long
delays (about 1.7–2.4 ms). The likely causes are the same as for the H2 equilibrium drift, made
worse by the 53-species state: thin data on the long induction and equilibrium segments, and no
multi-step rollout term in the loss. More trajectories (`envelope.n_traj`), a larger `n_pick`, and
a rollout loss are the next things to try.

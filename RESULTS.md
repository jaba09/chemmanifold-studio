# Reference run (default `config.yaml`)

H2/air, Cantera `h2o2.yaml` (10 species), envelope phi 0.5–2.0, T0 1050–1300 K, P0 1–5 atm,
64 Sobol trajectories (42 autoignition, 22 PaSR), dt_base = 2 us. Run on 4 CPU cores. The full
pipeline takes about 11 minutes, almost all of it training (300 epochs per model, about 1 s per epoch).

## Data and manifold (stages 1–6)

* 17,514 autoignition pairs (arc-length sampled, strides 1/2/4) + 8,800 PaSR micromixing pairs.
* 23,156 train / 3,158 validation pairs.
* Global PCA: d_99.5% = 6 components.
* VQ-PCA (K = 4): R2(2) = 0.952, R2(3) = 0.992, R2(4) = 0.997, R2(6) = 0.9997, R2(8) = 0.99998,
  so the recommended latent dimension is d = 4 (used by Phy-ChemNODE).

## Certification

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

## Known weakness

ResNet-FiLM drifts during long post-ignition stretches at 1 atm (for example, phi = 0.6 at 1100 K
ends at 2152 K instead of 2430 K after 500 us). Because h is conserved, this drift is a slow
composition creep along the equilibrium tail. The 0D trajectories stop 25 steps after reaching
equilibrium (§2.3), so these states are barely in the training data. Possible fixes are a longer
equilibrium tail (`autoignition.n_consecutive`), a larger `loss_weights.equil`, or a few multi-step
rollout losses during training. Phy-ChemNODE, whose dynamics are confined to the 4-D latent manifold,
is noticeably more stable here.

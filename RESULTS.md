# Reference runs

## Burner flame, CH4/air with GA18 (default `config.yaml`)

The streams are those of the Fluent burner: CH4 at 300 K and air at 300 K with Y_O2 = 0.21 by
mass, at 1 atm. Z_st = 0.050 and the adiabatic peak is 2126 K. Run on 4 CPU threads, the full
pipeline takes about 55 min: about 2.5 min for flamelets, 1.5 min for sampling, and 23–26 min to
train each model (300 epochs on 49k pairs).

### Flame reference and sampled space

* 14 counterflow flamelets (mixture-averaged transport), strain 7–881 1/s, peak T 1771–2070 K.
  Five of them (1, 4, 7, 10, 13) are held out of training to test coverage.
* 39,480 0D reactor pairs from 62 seeds, 13,600 PaSR pairs from 34 ensembles, and 3,057
  flamelet-state pairs, for 56,137 pairs in total (49,401 train / 6,736 validation).
* Global PCA: d_99.5% = 11 (out of 18 species). VQ-PCA R2(8) = 0.9965, so latent d = 8.

| Bound | Sampled data | Flamelets |
|---|---|---|
| Pressure | 1 atm | 1 atm |
| Mixture fraction Z | 0–1 | 0–1 |
| Temperature | 300–2076 K | 300–2070 K (adiabatic max 2126 K) |

Held-out flamelet states with a sampled state within 0.5 standard deviations (all species + T):
**93.4%**. By Z band: 90% for Z < 0.025, 99% for 0.025–0.05, 96% for 0.05–0.10, 100% for
0.10–0.20, and 94% for Z > 0.2. The median distance is 0.19 and the maximum 1.05.

What goes beyond the steady flame: 86% of the sampled states are more than 0.5 sigma from every
steady flamelet state. These are the ignition, partially burnt and heat-loss states that the 0D
and PaSR seeds produce. They stay inside the flame's T, Z and P bounds, but some intermediates peak
higher than in the steady flame: CH2O 3.1e-3 vs 4.9e-4, H 3.9e-4 vs 8.2e-5, H2O2 1.1e-4 vs 1.9e-5,
and CH3O 1.2e-4 vs 1.0e-6. These peaks come from slow-ignition transients. A Fluent run passes
through such states while it converges, so they are kept. Narrowing `envelope.alpha` (for example
to [0.5, 1.0]) or lowering `autoignition.t_max` trims them.

### Certification

| Metric | ResNet-FiLM | Phy-ChemNODE |
|---|---|---|
| Tier 1 R2 of Box-Cox increments (all / flamelet states) | 0.9977 / 0.928 | 0.9965 / 0.925 |
| Tier 1 max elemental residual | 4.6e-16 | 4.7e-16 |
| Tier 1 temperature MAE / max error | 0.02 K / 4.2 K | 0.05 K / 3.0 K |
| Tier 2 (Z = 0.05, alpha = 0.6, 500 × 10 us) ignition time error | 0% (470 us) | +260% |
| Tier 2 final T (Cantera 2113 K) | 2077 K | 1775 K |
| Tier 3 (Z 0.03/0.05/0.08 × alpha 0.6/0.7/0.8) mean \|tau error\| | 9.3% | 232% |
| Tier 3 mean progress-aligned T MAE / species NRMSE | 34.8 K / 2.1% | 85.1 K / 5.2% |

ResNet-FiLM is the usable model for this flame. It ignites at the right time, but it settles
30–45 K below the burnt temperature at Z = 0.03 and 0.05. The rich case Z = 0.08, alpha = 0.8
settles 155 K low, with a 9.8% species error. Phy-ChemNODE ignites late at stoichiometric
conditions, and in one rich case it collapses to the 280 K solver bound, so it is not stable here
yet. The 18-species state with an intrinsic dimension of about 11 is harder for an 8-D latent ODE.

## Recirculation exploration (`configs/burner_fluent_recirc.yaml`): alternative model for Fluent

Why: in the burner, hot products recirculate and mix with the fresh CH4 and air jets before they
burn. The non-adiabatic exploration only reached those states indirectly, and its worst case
(stoichiometric products mixed 50/50 into the fuel jet) collapsed to 450 K instead of 894 K. This
exploration keeps everything of `burner_fluent_nonadiabatic` and adds a three-stream PaSR (regime 4),
again derived a priori, with no CFD state:

* 40 ensembles × 400 particles, each a mixture beta·products(Z_p, psi_p) + (1 − beta)·pure fuel or
  air, beta ~ Beta(0.7, 0.7), psi_p in [0, 0.85];
* half of the particles are aged 10 us–5 ms before the pair is taken, so partly reacted mixtures
  are sampled too; then one 40 us stride (adiabatic Cantera target).

Data: 96,129 train pairs (82,049 + recirculation). Latent d = 12. Training was stopped by the 2 h
job limit at epoch ~289 of 300; the best checkpoint (epoch 285) was kept.

| Metric | non-adiabatic | recirculation |
|---|---|---|
| Tier 1 T MAE | 0.03 K | 0.03 K |
| **Products mixed into fuel/air**, 6 cases, 250 × 40 us: mean / max T MAE | 50.1 K / 121 K (fuel, beta 0.5: 451 vs 894 K) | **15.1 K / 27 K** |
| Same, mean species NRMSE | 3.1% | 1.3% |
| Cooled burnt gas (9 cases): mean / max T MAE | **5.9 K / 17 K** | 13.5 K / 71 K (Z 0.033, psi 0.6: 756 vs 935 K) |
| Tier 3 (10 us) mean T MAE / tau error | **21.3 K** / – | 47.2 K / 50% |
| Tier 3 at 40 us: rich Z 0.088 final T | **within 5 K** | 60–140 K low (1753–1822 vs 1879–1892 K) |
| Tier 3 at 40 us: ignition | stoichiometric exact; slow seeds 1.4–2.4× late | stoichiometric exact (+14 K); lean alpha 0.6 3.7× late, rich alpha 0.6 18% early |
| Coverage of held-out flamelets / stage 14 one-step error | 97.5% / 0.09 K | 97.6% / 0.12 K, 0% OOD |
| UDF self-test / cost per cell call | 60/60, 92 us | 60/60, 145 us |

Neither model wins everywhere: recirculation is much better on products mixed into the jets, the
non-adiabatic model is better on cooled gas and on rich closed-loop temperatures. Which one the
burner needs is decided by the Fluent run (see `models/REGISTRY.md`).

## Non-adiabatic exploration (`configs/burner_fluent_nonadiabatic.yaml`): the model for Fluent

Why: in the first Fluent run with the `burner_fluent_air` model, 27% of the hot cells of the DI flame
were outside the sampled space, and the share rose to 50% in 19 steps of 40 us. The burner gas loses
heat to 300–323 K walls and by radiation, which the adiabatic exploration (a fixed loss of at most
1.2e5 J/kg, applied once to the seed) did not reach. The new exploration is derived a priori from the
mechanism and the burner's boundary physics only; no CFD state is used:

* losses as a fraction psi of the largest physical loss (the composition cooled to T_wall = 300 K),
  psi up to 0.85 for seeds and PaSR particles;
* 36 of 104 0D reactors lose heat to T_wall with tau_q = 1 ms–1 s while reacting; their states are
  paired with adiabatic constant-(p, h) Cantera steps (19,851 pairs);
* a second sweep of 15 radiating (optically thin CO2/H2O) counterflow flamelets, peak T 1652–1902 K
  at low strain;
* a multi-step rollout loss: 8 chained 40 us steps, weight 0.2, from epoch 91 (14,673 segments).

Data: 30 flamelets (10 held out), 64,035 0D + 22,400 PaSR + 6,803 flamelet pairs, so 82,049 train /
11,189 validation. Global PCA d_99.5% = 12 (8 for the adiabatic space), so latent d = 12. On 4 CPU
threads: flamelets 4 min, sampling 3 min, training 98 min.

| Metric | adiabatic (`burner_fluent_air`) | non-adiabatic |
|---|---|---|
| Tier 1 R2 of Box-Cox increments / T MAE | 0.9967 / 0.03 K | 0.9961 / 0.03 K |
| **Cooled burnt gas**, Z 0.033/0.055/0.088 × psi 0.2/0.4/0.6, 250 × 40 us: mean / max T MAE | **277 K / 613 K** (5 of 9 collapse towards 280 K) | **5.9 K / 17 K** |
| Same, mean species NRMSE | 9.9% | 0.2% |
| Tier 3 at 40 us (6 seeds): final T error | 0–123 K (rich Z 0.088, alpha 0.8: 1756 vs 1879 K) | 0–5 K |
| Tier 3 at 40 us: ignition time | within 0–20% | stoichiometric exact; slow lean/rich seeds 1.4–2.4× late |
| Tier 3 (10 us) mean T MAE / species NRMSE | 23.2 K / 4.9% | 21.3 K / 1.1% |
| Coverage of held-out flamelets (0.5 sigma) | 98.5% (adiabatic only) | 97.5% (adiabatic + radiating) |
| Stage 14, one 40 us step on held-out adiabatic / radiating flamelets | 0.09 K / – | 0.09 K / 0.07 K, 0.1% / 0.4% flagged OOD |
| UDF self-test / cost per cell call | 60/60, 122 us | 60/60, 92 us |

The ignition-time column of `tier3.csv` (10 us steps) reads -100% for the stoichiometric seeds:
the new model's rise is smoother, so the steepest dT/dt is at the first step. At 40 us the same
seeds ignite on time (200 us vs 200 us). The remaining weakness is the delay of slowly igniting
seeds, which matters for lighting a cold field but not for continuing a burning solution.

## Burner flame with the Fluent case's air (`configs/burner_fluent_air.yaml`): the model for Fluent

Same as above, but the air is the one the Fluent case really solves: O2 = 0.21 by **mole**
(Y_O2 = 0.233), so Z_st = 0.055 and the adiabatic peak is 2239 K. Run on 4 CPU threads, ResNet-FiLM
only: flamelets 2 min, sampling ~1.5 min, training 18 min.

* 15 flamelets, strain 7–1316 1/s, peak T 1907–2200 K. 56,796 pairs (49,980 train / 6,816 validation).
  Global PCA d_99.5% = 11, VQ-PCA R2(8) = 0.9975, latent d = 8.
* Coverage of the held-out flamelets: **98.5%** within 0.5 sigma. Sampled T 300–2202 K.

| Metric | ResNet-FiLM |
|---|---|
| Tier 1 R2 of Box-Cox increments / max elemental residual | 0.9967 / 4.8e-16 |
| Tier 1 temperature MAE / max error | 0.03 K / 3.9 K |
| Tier 2 (Z = 0.055, alpha = 0.6, 500 × 10 us) ignition time | 190 us vs 190 us (0%) |
| Tier 2 final T (Cantera 2242 K) | 2256 K (+14 K) |
| Tier 3 (Z 0.033/0.055/0.088 × alpha 0.6/0.7/0.8) mean \|tau error\| | 35.7% (stoichiometric 0–14%) |
| Tier 3 mean T MAE / species NRMSE | 23.2 K / 4.9% |
| Stage 14 on held-out flamelet states, one 40 us step (837 cells ≥ 600 K) | T MAE 0.09 K (max 2.7 K), 1.3% flagged OOD |
| UDF self-test (C core vs PyTorch) / cost | 60/60 cases, 122 us per cell call (1 core) |

Near stoichiometric this model is better than the default-config one (final T within 15 K). The
weak spot is the rich side, Z = 0.088: alpha = 0.6 ignites 2× late and ends 350 K low, alpha = 0.8
ends 200 K low (same weakness as the 155 K of the default config). The lean slow case (Z = 0.033,
alpha = 0.6) ignites 59% late but reaches the right temperature.

A second run with 50% more seeds weighted to the rich side and `equil` loss weight 0.3 matched single
steps as well (stage 14 T MAE 0.08 K) but was much worse in closed loop (mean |tau error| 970%,
stoichiometric ignition 10× late), so it was discarded. Closed-loop behaviour varies a lot between
trainings with similar single-step accuracy; a multi-step rollout loss is the fix to try next.

## H2/air premixed autoignition (`configs/h2_air_premixed.yaml`)

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

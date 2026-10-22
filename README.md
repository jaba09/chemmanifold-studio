# ChemManifold Studio

Python implementation of the *ChemManifold Studio* technical specification: physics-constrained
machine-learning surrogates for stiff combustion chemical kinetics. The pipeline

1. explores the physically feasible thermochemical space of a kinetic mechanism (Sobol envelope
   sampling, 0D autoignition, arc-length importance sampling, PaSR micromixing ensemble),
2. analyses the slow manifold (Box-Cox + z-score preprocessing, global PCA, VQ-PCA),
3. trains hard-constrained neural flow-map surrogates (ResNet-FiLM and Phy-ChemNODE) whose outputs
   pass through an abundance-weighted null-space projection and a NASA-7 Newton temperature solver,
4. certifies them with single-step, closed-loop rollout and operating-envelope tests.

Every stage is a standalone script. It reads its inputs from `data/` and writes its outputs back to
`data/`, so a stage can be re-run, inspected or replaced without touching the others.

## Setup

```bash
python3 -m venv .venv            # or: uv venv .venv --python 3.12
source .venv/bin/activate
pip install -r requirements.txt  # exact tested versions: requirements-lock.txt
pip install -e .
```

### Apple Silicon (M1/M2/M3 Macs)

Cantera and PyTorch both ship native arm64 wheels, so the steps above work unchanged with a native
Python 3.10–3.13 (for example from Homebrew: `brew install python@3.12`, then
`python3.12 -m venv .venv`). Do not use an x86 Python under Rosetta.

The defaults are tuned for a MacBook Air (16 GB RAM, 8 cores):

* `training.threads: 4` keeps PyTorch on the four performance cores.
* `training.device: auto` keeps the network on the CPU. The hard-physics layers need float64,
  and Apple's MPS GPU backend has no float64, so on MPS only the network can move to the
  GPU and every batch has to be copied back and forth. For networks this small (about 0.2M
  parameters) that is usually slower than the CPU. You can try `device: mps` to compare.
* Peak memory measured for the H2 case is under 1 GB for every stage. The CH4 case is larger
  but still far below 16 GB.

## Running

```bash
python run_pipeline.py                          # all stages, both architectures
python run_pipeline.py --from 7 --arch chemnode # retrain + certify one model only
python scripts/02_autoignition_0d.py --config config.yaml   # any single stage
```

All settings (mechanism, envelope bounds, sample counts, network sizes, training schedule,
certification grid) live in one YAML file. Two chemical systems are included:

| Config | Mechanism | Species | phi | T0 | P0 | dt_base |
|---|---|---|---|---|---|---|
| [`config.yaml`](config.yaml) (default) | H2/air, Cantera `h2o2.yaml` | 10 | 0.5–2.0 | 1050–1300 K | 1–5 atm | 2 us |
| [`configs/ch4_gri30.yaml`](configs/ch4_gri30.yaml) (experimental) | CH4/air, GRI-Mech 3.0 (`gri30.yaml`) | 53 | 0.6–1.6 | 1400–1700 K | 1–5 atm | 10 us |

```bash
python run_pipeline.py --config configs/ch4_gri30.yaml   # writes to data/ch4_gri30/
```

The CH4 case runs end to end and is accurate for single steps, but its closed-loop rollouts are
not yet stable (see `RESULTS.md`), so treat it as a starting point rather than a validated model.

Any other mechanism that uses NASA-7 thermodynamics works as well. Copy a config, then set
`chemistry.mechanism` (a Cantera YAML file), `fuel`/`oxidizer`, the envelope, and `dt_base`/`t_max`.

## Stages and on-disk handoff

| # | Script | Spec | Reads | Writes (`data/…`) |
|---|--------|------|-------|-------------------|
| 1 | `01_sample_envelope.py` | §2.2 | config | `01_envelope/initial_conditions.csv` |
| 2 | `02_autoignition_0d.py` | §2.3 | 1 | `02_autoignition/traj_XXXX.npz` (t, Y, T, P, h, q̇) |
| 3 | `03_arclength_sampling.py` | §2.4 | 2 | `03_samples/pairs_0d.npz` |
| 4 | `04_pasr_ensemble.py` | §2.5 | 1 | `03_samples/pairs_pasr.npz` |
| 5 | `05_preprocess.py` | §3.1–3.2, §5.1 | 3, 4 | `04_prep/dataset.npz`, `scalers.json`, `thermo.npz` |
| 6 | `06_manifold_analysis.py` | §3.3 | 5 | `05_manifold/manifold_report.json`, plots |
| 7 | `07_train.py --arch …` | §4, §5 | 5, 6 | `06_models/<arch>/model.pt`, `history.csv`, `loss.png` |
| 8 | `08_tier1_validation.py` | §6.1 | 5, 7 | `07_eval/<arch>/tier1.json`, parity plot |
| 9 | `09_tier2_rollout.py` | §6.2 | 5, 7 | `07_eval/<arch>/tier2*.{json,npz,png}` |
| 10 | `10_tier3_envelope.py` | §6.3 | 5, 7 | `07_eval/<arch>/tier3.csv`, summary, heatmap |

Transition-pair files share one layout: `Y_in, T_in, P_in, h_in, dt, Y_out, T_out, regime, traj_id`
(regime 0 = 0D autoignition, 1 = PaSR micromixing).

## Package layout

```
chemmanifold/
  io.py         config loading, stage directories, npz/json helpers
  chemistry.py  Cantera setup, elemental mass matrix A (Eq. 5), NASA-7 tables
  boxcox.py     invertible Box-Cox transform (Eqs. 17-18), NumPy + torch
  physics.py    NullSpaceProjection (Eqs. 23-27), NasaTemperatureSolver (Eqs. 28-31), float64
  models.py     ResNetFiLM (Eqs. 32-37), PhyChemNODE (Eqs. 38-41), Surrogate wrapper
  loading.py    load scalers / thermo tables / trained checkpoints
  rollout.py    Cantera reference, batched autoregressive rollout, Tier 2/3 metrics
scripts/        the ten pipeline stages
run_pipeline.py runs the stages as separate processes
```

## Implementation notes (where the spec leaves choices open)

* **Equilibrium for PaSR (§2.5 step 2)** uses `gas.equilibrate("HP")`, which gives the same burnt
  state as integrating the reactor to equilibrium, at a fraction of the cost.
* **Arc-length coordinates (Eq. 12)** normalize T with each trajectory's own min/max temperature.
* **Composite loss (Eq. 44)**: the spec names the terms but not their form. `07_train.py` uses
  - `L_inc`: MSE of normalized step velocities (Eq. 43); `v_pred` uses the raw network candidate,
    measured from the *clean* input, so a perturbed input is trained to return to the true target;
  - `L_mass`: squared elemental residual of the unprojected candidate, so the network learns to be
    near-conservative and the projection only makes small corrections;
  - `L_T`: MSE of the Newton-recovered temperature, normalized by the std of training ΔT;
  - `L_equil`: penalizes predicted increments on pairs that are already at equilibrium;
  - `L_AE`: autoencoder reconstruction for Phy-ChemNODE (zero for ResNet-FiLM).
  Weights are in `config.yaml → training.loss_weights`.
* **Phy-ChemNODE time** is non-dimensionalized as `t* = t / dt_base`; the latent dimension is taken
  from the VQ-PCA report (`model.latent_dim: auto`).
* **Precision**: the networks run in float32; decoding, projection and temperature recovery run in
  float64, which is what gives elemental conservation to ~1e-16.
* **Tier 3 NRMSE (Eq. 49)** is phase-aligned by shifting the surrogate trajectory so both ignition
  indices coincide, then comparing over the overlapping window.

## Results

See `RESULTS.md` for the metrics from the reference run of the default configuration.

# ISANN: the surrogate learns while the flame runs

ISANN (an ISAT-like online ANN) is the run mode in which the CFD itself produces the network's
training data:

1. The run starts with direct integration (GA18, OpenFOAM's ODE solver) in every cell.
2. Each hot cell's (state, dt, GA18 result) pair is offered to a deduplicating store; the kept
   pairs are written per rank to `processor*/isannPairs.csv`.
3. `isann_daemon.py`, next to the run, merges them and, once there are enough, fine-tunes a
   network (warm start from an a priori model, plus a replay share of its a priori data).
4. If the new network beats the current one on held-out pairs, the daemon names it in
   `isann/control`; every rank loads it at the same step and from then on uses it in the cells it
   does not flag as out of distribution (OOD). OOD cells, and cells of (T, Z) bins where the
   shadow check found the network wrong, stay on GA18.
5. Those GA18 cells keep producing pairs, which trigger the next training. Repeat.

This breaks the earlier rule that the network is trained only on the a priori exploration: here
training on pairs from the run is the method (decided on 2026-10-30). ISANN models are CFD-adapted
and are registered apart from the a priori ones.

## Files

| File | What it does |
|---|---|
| `../userChemStep/isannStore.H` | first deduplication level (grid with a cap per box, reservoir replacement) |
| `../userChemStep/userChemStep.C` | the `isann` mode: DI phase, pair logging, hot model switch, trust bins |
| `isann_lib.py` | second deduplication level (radius of novelty), archive, data of a round, gate metrics |
| `isann_daemon.py` | watches the run, decides when to train, trains, gates and publishes |
| `isann.yaml` | all the criteria below |
| `setup_isann.sh` | makes a run directory from a base case and a parent model |
| `dedup_eval.py` | measures the deduplication on DI snapshots |

## Criteria

**Enough data for the first network** (end of the DI phase): at least `di.min_steps` steps on GA18
(2 ms), at least `di.min_pairs` deduplicated pairs (3000), and the grid has saturated (the boxes
created over the last 25 steps are under 2 % of all boxes: the run is no longer visiting new
states). If that never happens, train anyway at `di.max_steps` (8 ms).

**OOD detector**: the exported model's own checks (T range, T per Z band, pressure, species range,
VQ-PCA manifold residual, distance to training landmarks). The tables are rebuilt at every export
from that round's training data, so states the run has already labelled stop being OOD.

**Error check (ISAT-like)**: every 10 steps up to 2 cells per (T, Z, inside/OOD) bin and rank are
also run on GA18 from the same state (the shadow check). A check fails when
|T_ann - T_GA18| > max(1 K, 0.3 |dT_GA18|) or the same for OH with 5e-5. A bin with at least 2
failed checks and more failures than successes (both decayed by 0.9 per check) is *untrusted*: its
cells go to GA18 until the next model. This catches errors the OOD checks do not see.

**Retraining triggers**: at least 100 steps after the last model, and one of: 1500 new
deduplicated GA18 pairs; GA18 share of the hot cells above 5 % over 25 steps (with at least 300
new pairs); an untrusted bin (with at least 300 new pairs).

**Acceptance gate**: 15 % of the deduplicated pairs are held out and never trained on. A candidate
is accepted only if its one-step |dT| on them is lower than the current network's, and its error
after 100-step 0D rollouts from 40 held-out states (against Cantera) is at most 1.1 times the
current one's. The first network must also have a one-step |dT| under 2 K.

## Deduplication

Thousands of cells of the same burnt gas give the same pair. Two levels:

1. In the run (C++, `isannStore.H`): a grid on T (25 K), sqrt(Z) (0.02), log10 Y of CO2, CO, OH, H,
   CH4, O2, CH2O, HO2 (quarter decades, floor 1e-8) and log10 dt (0.1). Each box keeps at most
   `capPerBox` pairs; when full, a new candidate replaces a random kept one with probability
   cap / n, so the box keeps a uniform sample over the run and not only the start-up.
2. In the daemon (Python): a pair is kept only if no kept pair lies within r in the network's OOD
   coordinates (Box-Cox z-scored species, z-scored T and log10 dt); r = 0.05 times the landmark
   threshold of the data check.

`dedup_eval.py` measured it on the 902 029 hot-cell states of the 20 DI snapshots (0-50 ms): the
grid with cap 1 keeps 14 844 (61x less), grid + radius 0.05 keeps 9 686 (93x less). Every
candidate stays within 0.27 landmark thresholds of a kept pair (99.6 % within 0.1). A random subset
of the same size leaves states up to 1.3 thresholds away, beyond what the data check calls OOD.

## Running it

```
./setup_isann.sh <base case> <run dir> <parent model dir> 2
cd <run dir> && mpirun -np 2 rhoReactingBuoyantFoam -parallel > log.run 2>&1 &
python3 isann_daemon.py --run <run dir> --config isann.yaml &
```

The parent model directory needs `chemmanifold_model.txt`; `isann.yaml` points to the parent's
data directory (03_samples for the replay, 04_prep for the scalers, 06_models for the warm start).
The daemon trains on 2 threads, so a 4-core machine runs 2 CFD ranks next to it. Touch
`<run dir>/isann/STOP` to stop the daemon. After a restart of the run, each rank loads the model
named in the control file again at its first step.

## First run (2026-10-30)

Burner, lit start, 0-50 ms, parent ood7. DI phase to 11.2 ms (the grid had not saturated, so
the first training was forced at 8 ms; that round was rejected by the rollout gate and the next one
accepted), then six accepted networks (v1 at 11.2 ms ... v6 at 36.2 ms) out of 12 rounds. Flame
(T > 1600 K) mean |T - T_DI| 2.0-3.4 K from 25 to 50 ms, against 3.5-5.7 K for the ood1 hybrid and
~10 K for the ood7 hybrid; OH error 33-90 % against ~300 % for ood1. GA18 share 0.14-0.5 % of the
hot cells with the network. 7.9 s/step in the DI phase, 4.2 s/step with the network (2 ranks).
The network is adapted to this flame: it is not an a priori model. Full report (Spanish):
`/mnt/project-files/chemmanifold/isann/INFORME-ISANN.md`.

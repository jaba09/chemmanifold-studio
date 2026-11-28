# COVLOOP code (stage 0)

Roadmap: `docs/COVERAGE-LOOP-ROADMAP.md`. Status 2026-11-27 (Spain time): stage 0 written and smoke-tested in the
cloud only, including the rollout loss and the leg export. Nothing has run on sim1 yet.

| Piece | File | Tested |
|---|---|---|
| Top-2 MoE, dt in, dY out, CPU (train, export, numpy inference, trust gate, element projection) | `chemmanifold/moe.py`, `scripts/27_train_moe.py` | `tests/smoke_moe.py`, `tests/smoke_pipeline.py` |
| MoE in the plain-C core (arch `moe_top2`), used unchanged by `userChemStep` and the Fluent UDF | `fluent/udf/chemmanifold_core.c` | `tests/smoke_moe_core.py`: C vs numpy max dY 6e-17, T 0.08 K worst (Newton, 4 iterations) |
| General sampling, 15 families, ARC22 labels | `chemmanifold/general_sampling.py`, `scripts/26_general_sampling.py`, `configs/covloop_{smoke,general}.yaml` | smoke size: 15 families, 2.3k pairs in ~7 min on 4 cores |
| Coverage grid, holes, C, C_data | `chemmanifold/coverage.py`, `scripts/25_coverage.py` | `tests/smoke_coverage.py` |
| Hole-seeded sampling S1-S4 (starts excluded, deduplicated across iterations) | `scripts/28_hole_sampling.py` | via `tests/smoke_covloop.py` |
| Shadow checks -> trust (incl. NOx floors) | `openfoam/covloop/shadow_to_npz.py` | not yet (needs a real shadowDI.csv) |
| Driver with frozen rules (train / coverage / seed / decide) | `openfoam/covloop/covloop.py`, `configs/covloop/rules.yaml` | `tests/smoke_covloop.py` (fake leg, no OpenFOAM) |
| Rollout loss (24-step reference segments, closed loop with projection + T inversion) | `chemmanifold/moe.py` (`RolloutThermo`), `scripts/26` (`segments.npz`), `scripts/27 --segments` | `tests/smoke_rollout.py` |
| Leg export: cells (T, Y22, rho V, dt, OOD by the leg's model) and 25/200-step sentinels from per-bin cell starts | `openfoam/covloop/cells_to_npz.py`, `openfoam/covloop/sentinel_from_cells.py` | `tests/smoke_cell_export.py` (fake OpenFOAM run) |
| Selftest vectors for moe_top2 (chemmanifold_tests.txt for the plug-in's on-load selftest; checked vs numpy) | `scripts/29_export_moe_tests.py`, `fluent/udf/cm_make_tests.c` (run by `scripts/27` at the end) | smoke model: 306/306 cases pass `cm_selftest` |
| Case B slit burner | `openfoam/slitBurner/make_case.py` | files generated; blockMesh/solver not yet |

Still to do on sim1 (gate G0/G1):
1. DONE 2026-11-28: userChemStep built (/home/ubuntu/runs/covloop/lib, put it first on LD_LIBRARY_PATH; MPICH mpirun),
   C core = numpy to 7e-15 on 2308 pairs; Case B 50 um 1 ms clean on 4 ranks (36 min), not anchored yet.
2. Case B 20 ms coarse run (anchoring), then the G1 reference runs.
3. Check `cells_to_npz.py` on a real ARC22 leg (field names, binary vs ASCII, deltaT under LTS).
4. Production step 1 (`configs/covloop_general.yaml`, ~10-16 h on 8 cores) and G0 offline tests.

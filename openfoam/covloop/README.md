# COVLOOP code (stage 0)

Roadmap: `docs/COVERAGE-LOOP-ROADMAP.md`. Status 2026-11-23 (Spain time): stage 0 written and smoke-tested in the
cloud only. Nothing has run on sim1.

| Piece | File | Tested |
|---|---|---|
| Top-2 MoE, dt in, dY out, CPU (train, export, numpy inference, trust gate, element projection) | `chemmanifold/moe.py`, `scripts/27_train_moe.py` | `tests/smoke_moe.py`, `tests/smoke_pipeline.py` |
| MoE in the plain-C core (arch `moe_top2`), used unchanged by `userChemStep` and the Fluent UDF | `fluent/udf/chemmanifold_core.c` | `tests/smoke_moe_core.py`: C vs numpy max dY 6e-17, T 0.08 K worst (Newton, 4 iterations) |
| General sampling, 15 families, ARC22 labels | `chemmanifold/general_sampling.py`, `scripts/26_general_sampling.py`, `configs/covloop_{smoke,general}.yaml` | smoke size: 15 families, 2.3k pairs in ~7 min on 4 cores |
| Coverage grid, holes, C, C_data | `chemmanifold/coverage.py`, `scripts/25_coverage.py` | `tests/smoke_coverage.py` |
| Hole-seeded sampling S1-S4 (starts excluded, deduplicated across iterations) | `scripts/28_hole_sampling.py` | via `tests/smoke_covloop.py` |
| Shadow checks -> trust (incl. NOx floors) | `openfoam/covloop/shadow_to_npz.py` | not yet (needs a real shadowDI.csv) |
| Driver with frozen rules (train / coverage / seed / decide) | `openfoam/covloop/covloop.py`, `configs/covloop/rules.yaml` | `tests/smoke_covloop.py` (fake leg, no OpenFOAM) |
| Case B slit burner | `openfoam/slitBurner/make_case.py` | files generated; blockMesh/solver not yet |

Still to do on sim1 (gate G0/G1), each needs Javier's typed OK in the thread:
1. Build `userChemStep` with `-DUSERCHEMSTEP_ARC` against the new core; load a `moe_top2` model; selftest.
2. Cell export of a leg for ARC22 species (`cells.npz`: T, Y, mass = rho V, OOD flag): extend `foam_snapshot.py`
   (today GA18 names) or write the OOD flags as a field.
3. Sentinel export (`sentinel.npz`) from the userChemStep sentinel store (reason 4) rolled out 25/200 steps.
4. Case B: blockMesh + checkMesh + 1 ms coarse (50 um) smoke, then the G1 reference runs.
5. Rollout loss in `MoESurrogate.fit` (24-step segments, weight 0.5), not yet implemented.
6. Production step 1 (`configs/covloop_general.yaml`, ~10-16 h on 8 cores) and G0 offline tests.

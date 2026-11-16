# ITERML loop

Plan and rules: [docs/ITERML-ROADMAP.md](../../docs/ITERML-ROADMAP.md). One iteration:

```
. /opt/ofb/ofenv.sh                      # OpenFOAM v2412 + libuserChemStep
/opt/ofb/ml/bin/python openfoam/iterml/iterml.py run --iter 1          # full iteration
/opt/ofb/ml/bin/python openfoam/iterml/iterml.py --dry run --iter 1    # short test (S6)
/opt/ofb/ml/bin/python openfoam/iterml/iterml.py step seeds --iter 1   # one step again
```

Everything goes to `<root>/iterK/` (default root `/opt/ofb/iterml`, `--dry` uses `<root>/dry`):
`collect/` (OpenFOAM case, `processor*/isannPairs.csv`, `shadowDI.csv`), `seeds/` (stage 19),
`data/` (links to the parent's data + `pairs_seeded_iterK.npz`, new `04_prep`, `06_models`, `08_fluent`),
`bench/`, `eval/`, `eval_report/`, `ITER-REPORT.md`, `iterml.log` (Spain time), `state.json`.

Run the driver as a harness background task and relaunch it if it is killed: each finished step is
recorded in `state.json` and skipped, and the CFD legs resume from their latest write.

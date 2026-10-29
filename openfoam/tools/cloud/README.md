# Scripts of the cloud OpenFOAM runs (2026-10-28/29)

The scripts used for the GA18 DI and surrogate runs of the burner in a cloud container.
Their paths are hard-coded to that container's layout (`/opt/ofb`), so read them as a record
of what was run.

| File | What it does |
|---|---|
| `env.sh` | environment of OpenFOAM v2412, installed with micromamba from conda-forge into `/opt/ofb/env` |
| `setup.sh <name> <di\|noadiabatico\|recirculacion>` | transient case (dt 2e-5 s, 50 ms) from the LTS state 4227, with a chemistry-weighted decomposition |
| `runall.sh`, `runhyb.sh` | the DI / surrogate / hybrid runs one after the other; they resume after a restart |
| `compare.py <time> <png> ref run...` | T contours and metrics (mean \|dT\| where T_ref > 1000 K, Tmax, CO, OH) against the first run |
| `plotT.py <case> <time> <png> [field] [Tmax]` | one contour of the 2D wedge |
| `foamread.py` | reads ASCII OpenFOAM internal fields |
| `oodmap.c` | OOD checks of a list of states with a model file (build: `gcc -O2 oodmap.c ../../../fluent/udf/chemmanifold_core.c -I../../../fluent/udf -lm`) |

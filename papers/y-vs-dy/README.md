# Paper draft: state output Y(t+dt) vs increment output dY (Combustion and Flame)

- `y_vs_dy.tex`, `refs.bib`, `y_vs_dy.pdf`: draft v0 (elsarticle). `\todo{}` in red = to resolve before submission.
- `scripts/analyse.py data`: error by temperature band (`data/bands.csv`) from the 2.5 ms snapshots of both
  ISANN runs and DI, and increment sizes in the units of each loss (`data/scales.csv`).
- `scripts/make_figs.py data figs`: all figures.

Runs (same container, 2 CFD ranks + 2 trainer threads, `openfoam/isann/isann.yaml` criteria):
- state output, parent ood7: `/mnt/project-files/chemmanifold/isann/delta-output/carrera_y/`
- increment output, parent ood7dy (`model.output: dY`): `.../delta-output/carrera_dy/`
- offline benchmark (stage 18, 218 Cantera states): `.../delta-output/benchmark/`
Build: `pdflatex y_vs_dy && bibtex y_vs_dy && pdflatex y_vs_dy && pdflatex y_vs_dy`.

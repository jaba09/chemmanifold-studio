# One network or several? (draft v0, 2026-11-03)

Paper draft comparing a single neural chemistry surrogate with a deep ensemble (P0) and region experts (P1),
from the ensemble roadmap (docs/ENSEMBLE-ROADMAP.md, section 11). Target: Combustion and Flame (elsarticle).

- `single_vs_multiple_ann.tex`, `refs.bib`, compiled `single_vs_multiple_ann.pdf`
- `figs/` from `scripts/make_figs.py --e4 /mnt/project-files/chemmanifold/ensemble/e4`
- Red `[TODO: ...]` marks items to resolve before submission (author data, GA18 reference, exploration table,
  error-map figure, Fluent timing, 3x-parameter control, spread map in the burner).

Build: `pdflatex single_vs_multiple_ann && bibtex single_vs_multiple_ann && pdflatex single_vs_multiple_ann && pdflatex single_vs_multiple_ann`

# ARC_GRI30_NOx22 (preprint v1, 2026-11-17)

Analytically reduced GRI-Mech 3.0 with NOx (22 transported + 21 QSS species): reduction procedure, two independent
0D/1D validations, and OpenFOAM direct integration of the radiating burner flame against full GRI-Mech 3.0 (same
code) and Fluent GRI-Mech 3.0. Target: Combustion and Flame (elsarticle). Source text: the merged draft
https://claude.ai/artifact/M5mtw4X5dG4RM9AiemtYWX; numbers from results/sim1/ARC22.

- `arc22_cnf.tex`, `refs.bib`, compiled `arc22_cnf.pdf`
- `figs/` from `scripts/make_figs.py` (needs results/sim1/ARC22/fields and the sim1 run dirs for the ignition traces)
- `elsarticle.cls` generated from CTAN elsarticle.ins (not installed on sim1), `elsarticle-num.bst` from CTAN
- Red `[TODO: ...]` marks items to resolve before submission (authors, affiliation, data archive, funding, whether
  to fix the near-axis radiation divergence). Every refs.bib entry was written from memory and must be checked.

Build: `pdflatex arc22_cnf && bibtex arc22_cnf && pdflatex arc22_cnf && pdflatex arc22_cnf`

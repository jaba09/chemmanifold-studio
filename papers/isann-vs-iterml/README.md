# ISANN vs ITERML comparison paper (draft v2, 21 Nov 2026)

- `isann_vs_iterml.tex` + `refs.bib` (elsarticle, target Combustion and Flame), compiled `isann_vs_iterml.pdf`.
- v2: all headline results on the corrected burner (top + chimney open, wall radiation, constant Lewis) under
  protocol v2, both schemes from the same physics-only parent family (tix2c). Sources: `results/sim1/{C2,C3,C3b,D,E2}`
  on branch `claude/project-thread-mq77al`. The v1 study (earlier configuration, protocol v1) is Appendix A.
- Red `[TODO]` = before submission.
- Figures: `python ../common/make_v2_figs.py <path to results/sim1> . p2` draws `figs/fig_v2_runs.pdf`.
  `figs/v1_*.pdf` are the v1 figures (old `scripts/make_figs.py`, reads the protocol v1 reports in the project files).
- Build: `pdflatex; bibtex; pdflatex; pdflatex` (needs texlive-science for siunitx).

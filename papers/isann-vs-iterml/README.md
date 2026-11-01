# ISANN vs ITERML comparison paper (draft)

- `isann_vs_iterml.tex` + `refs.bib` (elsarticle, target Combustion and Flame), compiled `isann_vs_iterml.pdf`.
- Includes ITERML iterations 1 and 2 (iteration 2 is a negative result). Red `[TODO]` = before submission.
- Figures: `python scripts/make_figs.py` reads the protocol v1 reports in the project files
  (`chemmanifold/...`) and draws ITERML iteration 2 automatically once `iterml/iter2/eval_protocol_report.md` exists.
- Build: `pdflatex; bibtex; pdflatex; pdflatex`.

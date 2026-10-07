# Smithsonian initial report

Complete local report based on the supplied `Smithsonian.pdf`, with the two proposed architectures retained. The earlier partial-section files in `../initial_report/` are unchanged.

## Deliverables

- [Compiled report](Smithsonian_initial_report.pdf)
- [Editable LaTeX](report.tex) and [BibTeX bibliography](references.bib)
- [Items to confirm before submission](HANDOFF.md)
- [Inventory and pilot validation](asset_validation.json)
- [Input provenance](../../source_manifest.json)

The report is an initial project report. It distinguishes the completed source audit and historical detector diagnostic from planned classification experiments. No models were trained to produce it.

## Build

From this directory, with a TeX Live installation containing the packages named in `report.tex`:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build report.tex
cp build/report.pdf Smithsonian_initial_report.pdf
```

The supplied `generated_counts.tex` and vector figure make PDF compilation independent of Python and the full project dataset. Import `report.tex`, `references.bib`, `generated_counts.tex`, and `figures/category_distribution.pdf` into Overleaf and select `report.tex` as the main document to edit there.

To regenerate and verify the figure and counts inside the project repository:

```bash
python build_assets.py
```

This requires Matplotlib (built with 3.10.8), the existing `data/current/` inventories, and the September 24 pilot results. It reads those inputs without changing them. The local build used `/home/pb52/miniconda3/envs/research-agent/bin/python`; no shared environment packages were changed.

The source bundle includes a portable copy of the verified figure/count inputs for document compilation. Recreating the underlying inventory audit still requires the repository data recorded by hash in `asset_validation.json`.

## Rubric coverage

| Initial-report requirement | Location |
| --- | --- |
| General-audience problem and significance | Section 1.1 |
| Clear objectives | Section 1.2 |
| Domain and technical prior work | Section 2 |
| Data sources, labels, initial exploration and limitations | Section 3, Table 1, Figure 1 |
| Data science pipeline and justified choices | Sections 4–5 |
| Validation and reproducibility plan | Section 5.4 |
| Completed work distinguished from proposed work | Sections 3 and 6 |
| Impact, limitations and next steps | Sections 1 and 7 |
| Contents, page numbers, captions and references | Throughout |

The examples informed organization and level of detail; their results and wording were not imported. The reference section distinguishes scholarly publications from internal project records.

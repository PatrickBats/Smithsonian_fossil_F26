# Smithsonian initial report

Complete local report based on the supplied `Smithsonian.pdf`, with the two proposed architectures retained. The earlier partial-section files in `../initial_report/` are unchanged.

The current version uses the official **IEEEtran conference class**, with its two-column body, typography, captions, headings, and IEEE bibliography style. Course-specific adaptations are a single-column title/contents page, visible page numbers, mentor/sponsor credits, and omission of the optional abstract. It is an IEEE-style course report, not a camera-ready submission to a named conference. The preceding 15-page version is preserved under `revisions/03-before-ieee-format/`.

## Deliverables

- [Compiled report](Smithsonian_initial_report.pdf)
- [Editable LaTeX](report.tex) and [BibTeX bibliography](references.bib)
- [Items to confirm before submission](HANDOFF.md)
- [Inventory and pilot validation](asset_validation.json)
- [Input provenance](source_manifest.json)

The report is an initial project report. It distinguishes the completed source audit and historical detector diagnostic from planned classification experiments. No models were trained to produce it.

## Build

From this directory, with a TeX Live installation containing the packages named in `report.tex`:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build report.tex
cp build/report.pdf Smithsonian_initial_report.pdf
```

The supplied `generated_counts.tex` and vector figure make PDF compilation independent of Python and the full project dataset. Upload the source ZIP to Overleaf and select `report.tex` as the main document. The bundle includes unchanged `IEEEtran.cls` (v1.8b) and `IEEEtran.bst`; their upstream notices and provenance are retained in `template/`. No system-wide template installation is required.

To regenerate and verify the figure and counts inside the project repository:

```bash
python build_assets.py
```

This requires Matplotlib (built with 3.10.8), the existing `data/current/` inventories, and the September 24 pilot results. It reads those inputs without changing them. The local build used `/home/pb52/miniconda3/envs/research-agent/bin/python`; no shared environment packages were changed.

The source bundle includes a portable copy of the verified figure/count inputs for document compilation. Recreating the underlying inventory audit still requires the repository data recorded by hash in `asset_validation.json`.

## Rubric coverage

| Initial-report requirement | Location |
| --- | --- |
| General-audience problem and significance | Section I-A |
| Clear objectives | Section I-B |
| Domain and technical prior work | Section II |
| Data sources, labels, initial exploration and limitations | Section III, Table I, Figure 1 |
| Data science pipeline and justified choices | Sections IV–V |
| Validation and reproducibility plan | Section V-D |
| Completed work distinguished from proposed work | Sections III and VI |
| Impact, limitations and next steps | Sections I and VII |
| Contents, page numbers, captions and references | Throughout |

The examples informed organization and level of detail; their results and wording were not imported. The reference section distinguishes scholarly publications from internal project records.

## Visual update — September 27

The current report includes two full-width vector architecture diagrams and a six-panel figure of authentic, expert-labeled specimens. Regenerate the specimen panel with `python build_visuals.py`, then the final architecture figures with `python build_architecture_figures.py`. The source tile pixels, annotation metadata and crop provenance are in `figures/specimen_sources/` and `figures/specimen_manifest.json`. The images are focus-stacked crops, without color correction or retouching; fields of view differ. Architecture internals and output graphics are conceptual. The report before these edits is preserved in `revisions/04-before-visual-refresh/`.

## Academic prose revision

The report now describes data composition and methods without the annotation-correction history, file-transfer details, or dated progress narrative. The inventory subsection is merged into the data description. Class-imbalance strategies are presented as options for validation. Dates remain where relevant to the prospective course schedule and bibliographic publication years. Original source records and prior versions remain unchanged. The previous PDF and source bundle are in `revisions/05-before-academic-prose/`.

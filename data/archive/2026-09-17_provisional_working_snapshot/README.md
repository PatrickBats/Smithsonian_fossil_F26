# Superseded September 17 working snapshot

Historical only. Use [the verified Fall 2026 inventory](../../current/README.md). The remainder records the pre-update state.

# Existing annotation inventory — updated dataset audit pending

**September 21 status:** the full dataset installation is underway according to Patrick. Sponsors identified missing/possibly outdated annotations in this inventory. See [current context](../../../docs/CURRENT_CONTEXT.md). Reconcile the new files before treating these counts as complete or using them to finalize training.

**classification_annotations.csv** preserves the September 17 working selection: **933 YES annotation records across 27 categories**, from the September 17, 2026 audit. This is the user-approved working mapping, including 112 provisional YES matches. Original identifications and match methods are retained; provisional matches are working assumptions, not sponsor-verified corrections.

- classification_annotations.csv: current YES selection, with slide paths and annotation identifiers.
- slide_annotation_records.json: source geometry and annotation-file checksums; join by annotation_file and record_index.
- category_summary.csv and category_by_slide.csv: counts across all mapped priorities.
- annotation_records.csv: complete audit, including 63 MAYBE, 9,623 NO, 212 unmatched and 344 untitled records. Those are not part of the initial YES selection.
- provisional_aliases.json and provisional_matches.csv: approved provisional mappings and affected annotations.

Original images and annotations remain on NOTS. No crops, splits or training have been produced. These are annotation counts, not a completed specimen-quality or duplicate audit. Use slide grouping when designing evaluation; final split and label-quality checks remain to be established.

Older mappings are in [the archive](../README.md). Sponsor source tables remain unchanged under [original data documents](../../../docs/sources/data/). Their totals describe the supplied source inventory, not this working selection.

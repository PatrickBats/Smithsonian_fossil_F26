# Correct working dataset: Fall_2026

**Use this version for all new data preparation.** The user supplied Fall_2026.zip on September 21, 2026 and identified it as the correct dataset. Its 83 NDPA files reconcile exactly with Ingrid’s supplied tables after trimming three trailing spaces. It supersedes the September 17 933-record snapshot.

## Draft broad grouping

The [broad v1 map](broad_v1/README.md) groups the current 32 YES categories into 28 draft operational groups, preserving fine labels and all 2,283 eligible specimens. It is a separate proposal, not a replacement for the original map or historical results.

## Verified inventory

- 83 annotation files and one 15,965,474,680-byte NDPI image in the archive.
- 11,275 named annotation records across all 185 supplied title rows and 65 categories; every title and category count agrees with the tables.
- 2,290 YES records across all 32 YES categories, 114 MAYBE records, and 8,871 NO records under the supplied mapping.
- 227 untitled records: 133 rectangles and 94 circles. They are not assigned training labels.
- No old provisional aliases are used. Three label records require trailing-space trimming only.
- All 83 annotation files on NOTS match the archive SHA-256 hashes: 48 are in annotations_F26 and 35 unchanged files remain under raw. All 83 matching image headers and small center regions read successfully. Use cluster_source_paths.csv to select the exact verified source paths.

## Files

- classification_annotations.csv: the 2,290 YES records under the original supplied categories; **not yet a sampled, broad-category or training-ready dataset**.
- annotation_records.csv: all 11,502 annotation records with original labels, source filenames, hashes, and resolved NOTS image paths.
- annotation_geometry.json: geometry keyed by record_id.
- title_reconciliation.csv and category_summary.csv: complete count comparisons against the sponsor tables.
- category_by_slide.csv and labels_by_slide.csv: distribution by slide.
- audit_manifest.json: ZIP/member checksums, counts, and pairing evidence; every ZIP member passed CRC verification.
- [Original updated NDPA files](../../docs/sources/data/Fall_2026/): immutable source annotations extracted from the archive.

The ZIP and NDPI image are not committed to Git. Original images stay on NOTS. Use cluster_source_paths.csv for extraction: annotations_F26 alone contains only 48 of the 83 required files. Unchanged matching annotations are explicitly resolved in raw; do not choose neighboring files blindly. See cluster_verification.json for the verification scope.

Next: define the broad-first mapping agreed September 18, retaining fine labels; inspect specimen extraction, including labels outside old rectangles; establish grouped evaluation and the initial 50-grain balancing policy before training. Keep MAYBE and NO separate from the initial YES selection. No training or sampling has been run.

Earlier mappings are preserved in [the archive](../archive/README.md). See [current context](../../docs/CURRENT_CONTEXT.md).

Latest NOTS check: [verified source paths](cluster_source_paths.csv) and [verification report](cluster_verification.json). No shared cluster files were changed.

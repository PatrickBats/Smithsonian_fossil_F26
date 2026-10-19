# Method A: comparison of three training-data variants

**All three experiments use Method A: one RF-DETR 2XL model for localization and
28-class identification.** A1/A2/A3 change training-data construction. They are
not three architectures and should not be confused with Method B's separate
detector-plus-classifier pipeline.

On the same 274 known validation targets, A3 has the highest observed primary
end-to-end success: **55/274 (20.07%)**, compared with 46/274 for A1 and A2.
A2 has the highest known-reference detection recall. These results support
further study of the training data; they do not prove that annotation-empty
tiles caused the historical baseline's missed detections.

## Data treatments

| Method A variant | Training-data treatment | Train tiles | Known train targets | Box instances |
| --- | --- | ---: | ---: | ---: |
| A1 — positive ROI grid | Keep original tiles containing a retained YES box | 884 | 1,061 | 1,586 |
| A2 — context crops, original coverage | Recrop around the original 1,061 covered targets | 918 | 1,063 | 1,189 |
| A3 — context crops, full train coverage | Extend the crop pool to all targets assigned to train | 1,423 | 1,605 | 1,768 |

A2 incidentally contains two additional already labeled train targets, whose
labels are retained. It therefore approximates, but does not exactly preserve,
A1's supervised target set. A3 adds anchors for the 544 assigned train targets
that did not enter the original grid/label-retention pipeline. No targets move
between train, validation and test.

The adopted assignment contains 2,283 records across 75 exact source-image files:
1,605 train, 347 validation and 331 reserved test. This is the assignment used for
this comparison, not a replacement for the full 2,290-YES-record source inventory.
The 28-class map is also unchanged and retains draft groupings pending sponsor
review. We report identification classes, not 28 biological species.

### Why targets were missing from the original grid

The original 5,152 training tiles come from fixed rectangular ROIs, not a
whole-slide grid or a window around every annotated target. Of these, 4,268
have no retained YES box. The grid and retention policy cover 1,061 train and
274 validation targets, leaving 544 train and 73 validation records uncovered.

An uncovered record may be outside a retained ROI, intersect tiles too little to
pass the box rule (visible area >=16 pixels squared and >25% of the original
box), or lie in a source ROI too small to generate a 1024-pixel tile. The total
617 is a coverage failure count; it has **not** been broken down into these
causes. It is not evidence that all 617 centers lie outside ROI rectangles.
A1 removes annotation-empty train tiles; A2/A3 additionally change the training
windows. Missing annotations can still occur inside every retained real window.

### Context crop construction

The shared A2/A3 pool has 1,423 unique windows: 1,392 at 512 pixels, 23 at 640
and 8 at 768. Target-size inspection and a 32-pixel context margin determine the
window size. A deterministic search changes anchor position and prefers not to
cut known boxes. Existing windows can be reused with at least 16 pixels of
margin, eliminating 182 additional windows. Every intersecting known YES label
is retained; 40 unavoidable partial box instances remain clipped and flagged.

The full focal series is fused using absolute LoG k=5, with plane zero checked
against OpenSlide. A crop is placed without resizing at a random offset in a
1024-pixel canvas, with uniform median edge-color padding. The model then applies
the common 1000-pixel resize. This preserves object scale relative to the original
validation tiles. Padding introduces synthetic boundaries and changes context;
its benefit is empirical and it does not resolve incomplete interior annotations.

## Shared new-run protocol

- RF-DETR 2XL, 28 target classes, generic pretrained initialization; no fossil-trained initialization.
- Seed 20261013; batch 1 and gradient accumulation 16; AdamW LR 1e-4 and encoder LR 1e-5; cosine scheduling.
- Exactly 2,400 optimizer steps per new variant, with final EMA weights selected in advance. No AP-based checkpoint selection or early stopping.
- Direct resize and horizontal flip only; the library's secondary random crop is disabled in the experiment process.
- Full original validation grid: 1,432 tiles and 274 unique known references. The 261-positive-tile subset is a diagnostic.
- Primary confidence >=0.50 and IoU >=0.50, using the same boundary-aware tile deduplication and one-to-one matching for all variants.
- Fixed confidence sweeps at 0.25/0.50/0.75. Test pixels remain unused.

Equal optimizer-step budgets imply different epoch counts and different
repetition per image. The completed models reached approximately 43, 42 and 27
started epochs respectively. This report compares the recorded single-seed runs;
there are no repeat-seed uncertainty estimates.

## Primary validation results

| Model / data treatment | Detected / 274 | Known detection recall | Correct location and class / 274 | End-to-end success |
| --- | ---: | ---: | ---: | ---: |
| Historical Method A full-grid baseline | 24 | 8.76% | 20 | 7.30% |
| Method A–A1: positive ROI grid | 84 | 30.66% | 46 | 16.79% |
| Method A–A2: original-coverage context crops | 101 | 36.86% | 46 | 16.79% |
| Method A–A3: all-train context crops | 99 | 36.13% | 55 | 20.07% |

The historical baseline used 5,152 training tiles, a different augmentation and
LR schedule, AP-based model selection and an early-stopped duration of 16 epochs.
Its comparison is a contextual reference, not a controlled data-only ablation.
Among the three new runs, A2 recovers more known locations than A1 but has the
same end-to-end correct count; A3 has the highest end-to-end correct count.

Unmatched predictions are **unreviewed**, not established false positives. The
primary unmatched counts are 309/347/337 for A1/A2/A3. These counts do not provide
precision without complete scene ground truth. Recall here is only over known
annotated targets in the retained validation grid, not over all pollen or the
73 other assigned validation records. Conditional classification and per-class
support are included in the aggregate JSON files and use their stated denominators.

### Fixed confidence sweep

Entries are detected known targets / correctly localized and classified targets;
the denominator for each is the same 274 known references.

| Method A variant | Confidence 0.25 | Confidence 0.50 (primary) | Confidence 0.75 |
| --- | --- | --- | --- |
| A1 | 136 / 60 | 84 / 46 | 47 / 31 |
| A2 | 150 / 56 | 101 / 46 | 53 / 28 |
| A3 | 158 / 73 | 99 / 55 | 40 / 27 |

These thresholds were specified before evaluation. Lower-threshold results do
not establish better full-scene precision or justify selecting a threshold on
the untouched test set.

## Completed execution and evaluation recovery

Training jobs 2255055/2255093/2255094 completed all 2,400 optimization steps on
October 18, 2026, starting around 03:19 CDT. The latter two job processes later
exited during validation, after their training checkpoints had been saved.

In the observed runtime, the model builder creates 29 sigmoid output slots for
`num_classes=28`. The custom COCO loader remaps the supplied category IDs to
training target indices 0–27; slot 28 is unassigned. The original evaluator
asserted every returned prediction was within 0–27, stopping the A2/A3 runs
when that unused slot appeared during the confidence-0.25 pass.

The included evaluator excludes and audits slot 28, without remapping it to a
pollen class, and rejects any other unexpected ID. Recovery jobs 2269057/2269058
completed full validation and guarded checkpoint pruning; comparison/audit job
2269059 also completed with exit 0. **Weights were not retrained or changed.**
Only 2 A2 predictions and 1 A3 prediction were excluded at confidence >=0.25;
maximum scores were 0.422812 and 0.353473. None reached the primary threshold
0.50. The original A1 full validation contained no out-of-range predictions.

Final checks verified the three retained checkpoint hashes, source-image and
consumed-PNG metadata, authoritative annotation CRC-32 values, and external
label/map/pretrained hashes. This is not full-byte NDPI hashing. Cleanup removed
only redundant owned, singly linked checkpoints in the three new run directories
(7,590,975,237 bytes), preserving final EMA models, the old baseline and all
source/teammate files.

## Code, evidence and locations

- [Implementation and reproduction stages](../../scripts/method_a/data_variants/README.md)
- [Dataset counts and frozen input hashes](dataset_counts.json)
- [A1 primary per-class results and fixed sweeps](a1_validation.json)
- [A2 primary per-class results and fixed sweeps](a2_validation.json)
- [A3 primary per-class results and fixed sweeps](a3_validation.json)
- [Recorded cross-variant aggregate, unchanged](recorded_comparison.json)
- [Run, checkpoint and algorithm provenance](provenance.json)
- [Historical Method A baseline PR #5](https://github.com/PatrickBats/Smithsonian_fossil_F26/pull/5)

The reports contain curated aggregate metrics only. Images, row-level annotation
and split manifests, predictions and weight payloads stay on NOTS:

| Purpose | NOTS location |
| --- | --- |
| Executed source | `/projects/dsci435/Smithsonian_F26/method_a/experiments/sparse_labels_20261017/` |
| Logs | `/projects/dsci435/Smithsonian_F26/runs/method_a_sparse_labels_20261017/` |
| Metrics and predictions | `/projects/dsci435/Smithsonian_F26/results/method_a_sparse_labels_20261017/` |
| Data, row-level provenance and large model artifacts | `/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_sparse_labels_20261017/` |

Each final model is `run_artifacts/<recorded directory ID>/training/checkpoint_final_ema.pth`
under the RHF root. The package preserves numerical crop, fusion and scoring
functions while adding public variant aliases, configurable paths, safer metadata
writes and readable formatting. The recorded training and GPU inference checks
used the executed NOTS source; the reorganized package has not been retrained.
Dependency-free tests verify naming, output boundaries, aggregate consistency
and selected algorithm AST identity, alongside the repository's source/link checks.

# Method A with ignore regions (A4) — October 22, 2026

Method A (one RF-DETR-2XL that detects and classifies 28 categories jointly) recovered only
~36% of the 274 known validation specimens in the A1–A3 data variants (confidence 0.5, IoU 0.5),
while Method B's one-class detector recovers 94%. This experiment tests one explanation for that
gap and reports a fix for the detection half of the problem. Classification remains the gap to
Method B.

Headline, full 1,432-tile grid, 274 known targets, detected / correctly classified:

| Threshold | A3 (Yunfan, recorded) | A4 initonly | A4 noaug | **A4** |
| --- | --- | --- | --- | --- |
| 0.25 | 158 / 73 | 188 / 64 | 250 / 60 | **252 / 70** |
| 0.30 | — | 162 / 64 | 237 / 67 | **243 / 85** |
| 0.50 | 99 / 55 | 64 / 44 | 144 / 64 | **117 / 61** |
| 0.75 | 40 / 27 | 17 / 17 | 62 / 41 | **37 / 33** |
| best end-to-end correct | 73 | 64 | 69 | **85** |

Reference: Method B detector 258/274 detected; B + DINO 125 correct (`results/rgb_comparison.json`
in the software review repository). A3 numbers are from
`reports/method_a_data_variants_2026-10-18/a3_validation.json` there.

## The hypothesis

The sponsor labeled only priority specimens, so most grains in a training tile have no box.
DETR training matches each labeled box to one query and trains every unmatched query toward
"no object." On these tiles that trains the model to suppress unlabeled pollen. Method B's
detector never received that signal because its single-class training data labeled every grain.

## What changed relative to A3

Everything in Yunfan's A3 recipe is held fixed: the same 1,423 context-crop training tiles and
annotation file, 28 categories, 1000 px, batch 1 × 16 gradient accumulation, lr 1e-4 with the
DINOv2 encoder at 1e-5, cosine schedule, 2,400 optimizer steps, final EMA weights, no
validation-based checkpoint selection, seed 20261013, default random crop disabled, rfdetr 1.6.4
/ rfdetr-plus 1.0.2, and the unchanged 1,432-tile fixed-grid evaluation (`evaluate.py` matching
code, copied as `evaluate_run.py`). Three things change:

1. **Initialization from the Spring one-class detector** (`weights/rfdetr(2xl)_best_plane.pth`)
   instead of generic COCO weights. rfdetr resizes the 2-row one-class head to 29 rows by tiling,
   which alternates the pollen row with the unused always-negative row across the 28 classes;
   `seed_class_head_from_one_class` overwrites all 28 class rows (decoder head and the 13
   encoder proposal heads) with the trained pollen row. The pollen row is identified empirically
   from the `class_id` the one-class model emits (`pred_class_id_hist`, all 4,741 detections on
   row 0); the bias / weight-norm heuristics pointed at the wrong row and are only recorded.
2. **Ignore regions.** `make_ignore_labels.py` runs the one-class detector over every training
   tile (confidence ≥ 0.3). Detections not overlapping a labeled box (IoU < 0.5) are written as a
   29th category `__ignore__`. `train_ignore.py` patches the criterion so those boxes are removed
   before Hungarian matching and unmatched queries whose predicted box overlaps an ignore box
   (IoU ≥ 0.5) receive zero classification loss at every decoder layer and the encoder proposals.
   Box losses touch only matched queries and are unchanged. (rfdetr's native `iscrowd=1` drops
   boxes entirely, which returns them to background, so the loss is patched instead.)
   Measured on the training tiles: 1,768 labeled boxes, 3,102 ignore boxes — **1.75 unlabeled
   grains per labeled grain**; the detector recovered 1,624/1,768 (92%) of labeled boxes.
3. **Augmentation:** VerticalFlip p=0.5 and RandomRotate90 p=0.5 added to the team's
   HorizontalFlip. Pollen has no canonical orientation.

Two ablations isolate the changes with the same seed and budget:

- **initonly** — change 1 and 3 only (plain A3 annotation file, no ignore boxes).
- **noaug** — change 1 and 2 only (HorizontalFlip only).

## Results

Full grid; cls-on-matched is classification accuracy among the targets each model detected.

| Threshold | A4 det / correct / cls-on-matched / unmatched | initonly | noaug |
| --- | --- | --- | --- |
| 0.25 | 252 / 70 / 28% / 3,435 | 188 / 64 / 34% / 1,461 | 250 / 60 / 24% / 3,581 |
| 0.30 | 243 / 85 / 35% / 2,337 | 162 / 64 / 40% / 877 | 237 / 67 / 28% / 2,517 |
| 0.40 | 185 / 77 / 42% / 1,024 | 104 / 59 / 57% / 341 | 196 / 69 / 35% / 1,342 |
| 0.50 | 117 / 61 / 52% / 455 | 64 / 44 / 69% / 149 | 144 / 64 / 44% / 725 |
| 0.75 | 37 / 33 / 89% / 52 | 17 / 17 / 100% / 24 | 62 / 41 / 66% / 153 |

A4 at 0.30: macro known-target recall 0.873, macro end-to-end success 0.245. Per-class detail is
in `a4/full_confidence_0.30_summary.json`; the correct count is carried by Bisaccate (23/26
detected) and Momipites (27/35), while several well-detected categories are never classified
correctly (Ulmipollenites 0/20, Psilatricolpites 0/14, Polyatriopollenites 0/7, Bombacacidites 0/8).

### Established

- **The ignore-region loss fixes detection recall.** Both runs with it (A4, noaug) find 237–252
  of 274 targets at 0.25–0.30, up from A3's best of 158 and at Method B's detector level (258).
- **Initialization alone does not.** initonly starts from the same detector, peaks at 188, and at
  0.5 is below A3 (64 vs 99). Over 2,400 steps the background loss re-teaches suppression and the
  confidences collapse. Because initonly carries the same slide leakage as A4 (below) and does
  not reach A4's recall, the recall gain is attributable to the loss change rather than to
  memorized validation slides.
- **The remaining gap to Method B is classification.** A4's best end-to-end is 85 correct (31%)
  versus B + DINO's 125 (46%). On matched targets at 0.30 the joint head is right 35% of the time;
  DINO on the Spring detector's crops is right 48%.

### Suggestive (single pair of runs; ~8 specimens is the noise floor)

- Flip/rotate augmentation does not change detection (252 vs 250 at 0.25) but A4 classifies
  more of what it finds than noaug (85 vs 67 correct at 0.30). Plausible — orientation is
  irrelevant to pollen identity — but a replicate is needed before relying on it.

### Interpretive notes

- Confidence calibration shifts when "grain here" predictions stop being penalized, so A4's
  scores run lower than A3's. Comparing at a fixed 0.5 (117/61 vs 99/55) understates the change;
  the threshold sweep is the fair view, and cls-on-matched for A3 and initonly is computed over an
  easier set of grains than A4's. End-to-end correct is the comparable column.
- Unmatched predictions are large (2,337 at 0.30) and expected: the model now fires on unlabeled
  grains, of which the pseudo-label pass measured 1.75 per labeled grain. Method B's detector
  produces ~1,500 unmatched on the same grid. They are unreviewed, not established false positives;
  precision and full-scene AP are not claimed.
- **Slide leakage.** The Spring detector was trained on 13 of the 14 validation slides. A3 used
  COCO weights and is a clean unseen-slide measurement; A4, initonly and noaug are not. Report A4
  as "leaked, comparable to Method B." The reserved test set was not used.
- **Chunked training.** The `commons` GPU queue did not schedule for >24 hours, so each run was
  trained as three ~21-minute chunks on the `debug` partition with Lightning checkpoint resume
  (`chain_debug.sh`, `--time-budget-min`, `--resume`). A resumed epoch restarts from its first
  batch, so a few tiles were seen slightly more often than in an unbroken run, and EMA state is
  re-initialized at chunk boundaries (EMA horizon ≈150 steps). Chunk job IDs are in each run's
  `run_contract.json`. An unbroken `commons` copy of A4 (job 2343284) is still queued as a
  consistency check and was not available at the time of writing.
- Single runs, 274 targets. Differences under ~10 specimens should not be read as real.

## Reproduction

Scripts are in `scripts/method_a_ignore_regions/`. Paths follow
`/rhf/allocations/dsci435/Smithsonian_F26` on NOTS and the team's `model_A/env_train`
environment. `spring_nms.py` / `spring_types.py` are the unchanged Spring copies used by the
team's `evaluate.py` (sha256 `ac255082…`, `e162b74c…`).

```bash
# pseudo-label (≈80 s on an L40S), smoke-train 2 steps, smoke-eval 2 tiles
sbatch debug.sbatch
# full pipeline as one job (needs a ≥2 h GPU allocation)
sbatch run.sbatch
# or as a debug-partition chain of 30-minute jobs
bash chain_debug.sh A4_ignore_springinit LABEL
bash chain_debug.sh A4_initonly <A3 dataset dir> "--pollen-row 0"
bash chain_debug.sh A4_noaug <A4 run>/data "--no-extra-aug"
```

Run directories on NOTS: `model_A/runs/A4_ignore_springinit_20261021_debug`,
`A4_initonly_debug`, `A4_noaug_debug` (checkpoints, raw predictions, pseudo-labeled dataset).
This directory holds the aggregate evaluation JSON, per-target match records at each threshold,
run contracts, status, Slurm stdout, and the pseudo-label summary; checkpoints and prediction
archives are not in Git.

## Next step

Detection is at Method B's level within Method A; the lever is the classifier. Candidates: feed
A4's detections to the DINO crop classifier (does class-supervised detection select a better set of
grains than B's detector?); lower the encoder learning rate (1e-6) to preserve DINOv2 features for
the joint head; class-balanced sampling for the categories above with 0 correct. Before quoting any
of this as generalization, evaluate once on the reserved test slides after confirming they were
not in the Spring detector's training set, or re-run from a detector trained on the frozen split.

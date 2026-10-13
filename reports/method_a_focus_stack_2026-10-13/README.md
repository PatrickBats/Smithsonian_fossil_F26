# Method A focus-stack validation — October 13, 2026

## Pipeline

Method A directly predicts 28 broad pollen categories with RF-DETR 2XL. It uses the same 2,283-record assignment, label map, 1024-pixel annotated ROI grid and LoG focus-stacked image pixels as Method B. Source circles become COCO boxes; overlapping-tile predictions are merged before known-object scoring. The held-out test set was not used.

## File locations

- Repository implementation: [`scripts/method_a_focus_stack_v1/`](../../scripts/method_a_focus_stack_v1/README.md); executed code: `/projects/dsci435/Smithsonian_F26/method_a_focus_stack_v1/`.
- Derived data and run outputs: `/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_focus_stack_v1/` (`inputs/`, `plan/`, `dataset/`, `run_artifacts/`). Retained model: `run_artifacts/detector/checkpoint_best_total.pth`.
- Shared Method B images: `/rhf/allocations/dsci435/Smithsonian_F26/model_B/data/abbas_focus_stack_v1/`; Method B comparison: `/rhf/allocations/dsci435/Smithsonian_F26/model_B/runs/abbas_focus_stack_v1/separate_slides/ordinary_baseline/pipeline_validation/summary.json`.
- This report includes the small [`validation_summary.json`](validation_summary.json). Images, weights, row-level manifests and predictions are not in Git.

## Repository structure

`scripts/method_a_focus_stack_v1/` contains input binding, grid planning, COCO dataset creation, RF-DETR training, validation scoring, shared deduplication and Slurm entry points. `reports/method_a_focus_stack_2026-10-13/` contains this handoff and the validation summary.

## Completed run

The adopted assignment has 1,605 training, 347 validation and 331 reserved test records across 75 exact source files. The shared grid contains 5,152 training and 1,432 validation images; it covers 1,061 and 274 unique known records respectively. Another 617 assigned train/validation records are outside the retained ROI grid. Method A links to the verified Method B PNGs without duplicating their payload. Full training ran 16 epochs; the retained checkpoint SHA-256 is `c7dc1fe0e01aadf78c9a30ca1431212a9bb9e68709048100bd094f2adb952afd`.

On the **same 274 known validation objects** at confidence ≥0.5 and IoU ≥0.5:

| Metric | Method A: direct RF-DETR | Method B: detector + Swin |
| --- | ---: | ---: |
| Localized known objects | 24/274 (8.76%) | 32/274 (11.68%) |
| Correct broad class among localized objects | 20/24 (83.33%) | 20/32 (62.50%) |
| Correct location and broad class | **20/274 (7.30%)** | **20/274 (7.30%)** |

Method B localizes eight more known objects, while both pipelines recover 20 with the correct class. Their conditional classification denominators contain different detected objects. These are validation results on the selected ROI grid, not whole-slide or held-out test results. Sparse source annotations leave unmatched detections unreviewed, so this report does not claim full-scene precision or AP. The 28-class mapping contains draft sponsor-review merges.

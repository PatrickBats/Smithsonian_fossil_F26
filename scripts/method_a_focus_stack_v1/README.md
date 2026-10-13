# Method A: direct RF-DETR on shared focus-stacked tiles

## Pipeline

Use the adopted 2,283-record split and 28 broad labels. Match Method B's 1024-pixel annotated ROI grid and reuse its LoG focus-stacked RGB tiles. Attach 28-class COCO boxes from source circles, train RF-DETR 2XL directly, and score known validation objects after boundary-aware tile deduplication. Test inference is disabled.

## Locations

- Repository code: `scripts/method_a_focus_stack_v1/`; executed NOTS copy: `/projects/dsci435/Smithsonian_F26/method_a_focus_stack_v1/`.
- Derived inputs, COCO data, checkpoint and validation outputs: `/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_focus_stack_v1/`.
- Shared fused PNGs (read-only symlink targets): `/rhf/allocations/dsci435/Smithsonian_F26/model_B/data/abbas_focus_stack_v1/`.
- Shared split and label map: `/rhf/allocations/dsci435/Smithsonian_F26/runs/broad_swin_2026-10-08/separate_slides/ordinary_baseline/`.
- Run summary: [`reports/method_a_focus_stack_2026-10-13/`](../../reports/method_a_focus_stack_2026-10-13/README.md). Raw images, row-level manifests, predictions and weights stay outside Git.

## Project structure

| Files | Role |
| --- | --- |
| `build_inputs.py` | Bind the shared assignment and broad map by SHA-256. |
| `plan_grid.py`, `focus_helpers.py` | Read source geometry; verify tile IDs against Method B. |
| `build_linked_dataset.py` | Verify PNGs and create COCO labels with symlinked images. |
| `train_detector.py` | Run one-epoch smoke training, then the full 28-class model. |
| `evaluate_validation.py`, `spring_nms.py`, `spring_types.py` | Merge overlapping-tile predictions and score known validation circles. |
| `run_*.sbatch` | NOTS Slurm entry points. |

The boundary-aware deduplication in `spring_nms.py` and `spring_types.py` follows RiceD2KLab/Smithsonian_fossil_Sp26 revision `1b62b68a0d95178e6275ef55c38ee4765317b334`. Method B's exporter supplies the pixel-wise LoG fusion (5×5 Gaussian and Laplacian, largest absolute response per pixel); this Method A run does not export another PNG copy.

## Executed protocol

`build_inputs.py` checks the shared assignment and label-map hashes before writing `inputs/`. `plan_grid.py` reads original NDPI metadata and NDPA circles, then compares all 5,152 training and 1,432 validation tile IDs with Method B's exported images. `build_linked_dataset.py` verifies 1024×1024 RGB images and writes 28-class COCO labels. The fixed grid covers 1,061 known training and 274 known validation records; 617 assigned train/validation records fall outside retained ROI tiles. The 331 assigned test records remain reserved, with no test image export.

Training starts from generic RF-DETR 2XL weights, uses 1000-pixel model resolution and effective batch size 16, and selects the best checkpoint from a 40-epoch maximum. The completed run stopped after 16 epochs. Validation uses confidence ≥0.5 and known-reference IoU ≥0.5, with the same boundary-aware deduplication as Method B. Source annotations are sparse: unmatched predictions are unreviewed, and trainer COCO AP is not a full-scene quality measure. The broad-category map includes draft groupings pending sponsor review.

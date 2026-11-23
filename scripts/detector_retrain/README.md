# One-class detector retrain on old + new slides (November 2026)

Code for the results in [RESULTS.md](../../reports/new_slide_retrain_2026-11-22/RESULTS.md).
Tiling ran on NOTS; training and evaluation ran on one RTX 5090 (WSL). Paths inside the scripts point at
`/rhf/allocations/dsci435/Smithsonian_F26` (NOTS) or `~/Smithsonian_F26` (PC); change them for your machine.
Environment: torch 2.10.0+cu128, rfdetr 1.6.4, rfdetr-plus 1.0.2.

## Steps

| Step | Files | What it does |
|---|---|---|
| 1. Look at the delivery | `data/profile_new_set.py` | per-slide ROI counts, shapes, box sizes, sites |
| 2. Split | `data/make_split_v2.py` | freezes last semester's slide split, splits new slides by sample / locality lot |
| 3. Tile | `data/tile_boxes.py`, `tile_array.slurm`, `tile_shards.slurm`, `merge_parts.py`, `merge.slurm` | OMERO CSV / NDPA boxes to 1024 px z-stack tiles (H5); the 8 largest slides are tiled in shards and merged |
| 4. Export | `data/export.slurm`, `export_*_splits.json`, `merge_coco.py` | focus-stacked JPEG tiles + COCO JSON using last semester's `export_coco`; merges old and new into `combined/` |
| 5. Retrain 1 | `train/run_detector_v2.sh` | last semester's recipe on `combined/` |
| 6. Ignore boxes | `ignore_boxes/predict_new_train.py`, `ignore_boxes/build_dataset_v3.py` | last semester's detector over new training tiles; builds the retrain 2 dataset |
| 7. Retrain 2 | `train/run_detector_v3.sh` | same recipe with ignore-region loss and per-collection validation |
| 8. Evaluate | `eval/eval_detectors.py`, `eval/oldval_v3.py` | scores checkpoints on the three test sets and on old validation tiles |
| 9. Diagnose | `eval/diag_old_vs_new.py`, `eval/diag2_train_fit.py` | where retrain 1 lost accuracy on old slides |

## Training code

Training uses last semester's repository (`src/models/rfdetr/train.py`). Three files go into its
`src/models/rfdetr/` folder:

- `train/train_sp26_with_local_additions.py`: their `train.py` with three additions, each marked "local PC
  addition" (apply the patches below, resume from `last.ckpt`, drop the `__ignore__` pseudo-category from class names).
- `train/local_patches.py`: (1) NumPy version of rfdetr's validation matching, same results and about 44% less
  validation time; (2) keeps the best-EMA score across a resume; (3) ignore-region loss, on when
  `RFDETR_IGNORE_LABEL` is set; (4) validation mAP reported separately for old and new tiles, on when
  `RFDETR_DOMAIN_SPLIT_ID` is set.
- `train/ignore_patch.py`: the ignore-region criterion patch, copied from `scripts/method_a_ignore_regions/train_ignore.py`.

`train/restart_at_epoch_end.sh` was used once to restart retrain 1 between epochs when the validation patch was added.

## Method A runs on the new delivery

In `scripts/method_a_ignore_regions/`: `run_2b.sh` (ignore boxes regenerated with retrain 1), `run_cv_queue.sh`
and `cv_eval_local.py` (five-fold cross-validation on held-out new slides, wrapping Yunfan's `cv_evaluate.score_fold`).

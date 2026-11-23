# Retraining on the November slide delivery: results (2026-11-18 to 2026-11-22)

Alan Yang (acy3). All training ran on one RTX 5090. Numbers in this file come from the JSON/CSV files in this folder.

## Summary

- **One-class detector.** Retraining last semester's RF-DETR 2XL detector on old + new slides needed two attempts.
  The second retrain beats last semester's detector on new slides by a wide margin (mAP50 0.764 vs 0.593) and is
  within 2 points of it on last semester's own test set (0.860 vs 0.879).
- **Why the first retrain got worse on old slides.** The new labels are incomplete on many slides, old tiles were
  only 14% of training, and the checkpoint was picked on a validation set that was 85% new tiles.
- **Method A (joint detection + classification).** Adding the new delivery did not change results on the old
  274-specimen validation grid, but on held-out new slides it raised correctly named specimens from 89 to 296 of 540.

## 1. Data

- New delivery: 67 slides (62 with OMERO `_rois.csv` boxes, 5 with NDPA circles), about 56,000 usable boxes.
- Split (`splits/`, "split_v2"): last semester's slide-level split is frozen; new slides are split by sample or
  locality lot so the L and R slides of one sample never cross splits.

| Split | Slides | Tiles | Labeled grains |
|---|---|---|---|
| train (old + new) | 58 + 45 | 35,149 | 50,524 |
| val (old + new) | 12 + 16 | 8,837 | 9,689 |
| `old_test`: last semester's test set, unchanged | 12 | 986 | 1,594 |
| `test_new`: 3 densely labeled new slides (2CDST 1808.9 L/R, TADP1 223Q-1-42.5) | 3 | 7,663 | 7,826 |
| `test_new_recall`: 3 sparsely labeled slides from held-out collections (2CDST 617.65, Pislipampa L/R) | 3 | 838 | 1,137 |

On `test_new_recall` unlabeled grains count as false alarms, so only recall is meaningful there.

## 2. Detector results

All three models: RF-DETR 2XL, 1000 px, focus-stacked 1024 px tiles, single class. Scored by
`scripts/detector_retrain/eval/eval_detectors.py` (pycocotools, up to 500 detections per tile). With this script
last semester's checkpoint reproduces its published 0.879 / 0.642 on its own test set.

- **Last semester**: `rfdetr(2xl)_focus_stack.pth`, old collections only.
- **Retrain 1**: old + new tiles as they are, last semester's hyperparameters, COCO starting weights. Best epoch 11 of 21.
- **Retrain 2**: same, plus ignore boxes on new tiles, old tiles sampled 3x, balanced validation (section 4). 28 epochs.

| Test set | Metric | Last semester | Retrain 1 | Retrain 2 |
|---|---|---|---|---|
| `old_test` | mAP50 | **0.879** | 0.809 | 0.860 |
| | mAP50:95 | **0.642** | 0.541 | 0.612 |
| | Best F1 | **0.816** | 0.749 | 0.799 |
| | Recall at confidence 0.5 | 0.757 | 0.590 | 0.750 |
| `test_new` | mAP50 | 0.593 | 0.684 | **0.764** |
| | mAP50:95 | 0.305 | 0.347 | **0.448** |
| | Best F1 | 0.620 | 0.668 | **0.734** |
| | Recall at confidence 0.5 | 0.426 | 0.411 | **0.562** |
| `test_new_recall` | Recall at confidence 0.5 | 0.896 | 0.759 | **0.945** |
| | Recall at confidence 0.3 | 0.944 | 0.936 | **0.967** |

Empty `test_new` tiles with a detection at confidence 0.5 (of 1,532): 113 / 125 / **206**. Retrain 2 raises more
false alarms on empty tiles; see caveats.

Old-collection validation tiles (1,325 tiles, mAP50 / mAP50:95): 0.858 / 0.611, 0.799 / 0.535, 0.844 / 0.606.

Full sweeps over confidence thresholds are in `detector/results.json`. Training curves are in `detector/*.csv`;
`detector/retrain2_validation_by_collection.jsonl` has old and new validation scores per epoch.

## 3. Why retrain 1 lost accuracy on old slides

Checked with `scripts/detector_retrain/eval/diag_old_vs_new.py` and `diag2_train_fit.py`.

Ruled out:
- **Box size.** Old labels are squares (from circle annotations) and new labels are free rectangles, but retrain 1's
  boxes on old tiles are the same size as last semester's (0.99 of label width for both); rescaling them recovers nothing.
- **Missed grains.** Both models box 99.6-99.8% of `old_test` grains at some confidence. Of the 184 grains retrain 1
  loses at confidence 0.3, none is absent; 90% sit between 0.1 and 0.3.
- **Test-set luck.** Retrain 1 is also worse on old validation tiles and on old tiles it trained on (0.88 vs 0.94 AP).

What the numbers show:
- Retrain 1 scores real grains lower (median confidence 0.61 vs 0.83) and separates them less well from false
  alarms (precision at 80% recall 0.68 vs 0.85). It is under-confident even on its own training labels (median 0.65).
- Old tiles were 4,785 of 35,149 training tiles (14%), and the checkpoint was picked on a validation set that was
  85% new tiles.
- New training labels are less complete. On new training tiles 31% of last semester's confident detections have no
  label, against 8-14% on old tiles. GT-17A is about 70% unlabeled and the three Ladriges slides 33-43%.

Missing labels pushing detector confidence down is a published effect (Wu et al., "Soft Sampling for Robust Object
Detection", BMVC 2019; Niitani et al., CVPR 2019). Here it is consistent with the data, and retrain 2 fixed the
symptom, but retrain 2 changed three things at once, so the share of each cause is not established.

## 4. What retrain 2 changed

1. **Ignore boxes.** Last semester's detector was run over all 30,364 new training tiles. Its 28,440 detections with
   confidence >= 0.3 that match no label (IoU < 0.5) became `__ignore__` boxes (41,615 real labels on the same tiles).
   Ignore boxes are removed before matching, and unmatched queries that overlap one (IoU >= 0.5) get no
   classification loss. This is the same patch as Method A A4 (`train_ignore.py`).
2. **Old tiles sampled 3x.** Old tiles are 32% of each epoch instead of 14%.
3. **Balanced validation.** Checkpoint selection uses all 1,325 old validation tiles plus a fixed random 1,500 new
   ones (1,469 vs 1,653 boxes); old and new scores are logged separately each epoch.

Model, starting weights, hyperparameters and slide split are unchanged.

## 5. Method A on the larger dataset

A4 recipe (2,400 steps, COCO starting weights, ignore boxes), run locally. Files in `method_a/`.

Old validation grid (274 known specimens, confidence 0.30):

| Run | Found | Correctly named |
|---|---|---|
| Old data only (`A4_cocoinit_local`) | 227 | 96 |
| + new delivery, ignore boxes from last semester's detector (`2a`) | 218 | 84 |
| + new delivery, ignore boxes from retrain 1 (`2b`) | 216 | 84 |

No gain, and the differences are within run-to-run noise for this grid (near-identical runs flip 40-56 of the 274
specimens). About half the validation specimens are in classes with no new labels, and 363 of the 543 new boxes are
Inaperturopollenites or Laevigatosporites. The source of the ignore boxes made no difference.

Five-fold cross-validation on held-out new slides (Yunfan's folds, 540 specimens, confidence 0.30):

| Training data | Found | Correctly named |
|---|---|---|
| Old data only | 470 | 89 (16%) |
| Old + new delivery | 511 | 296 (55%) |

224 specimens gained and 17 lost. Most of the gain is Inaperturopollenites + Laevigatosporites (61 to 250 of 363);
the other classes go from 28 to 46 of 177. This matches Yunfan's Spring-init cross-validation (522 found / 304 correct).

## 6. Caveats

- Retrain 2 is still about 2 points of mAP50 below last semester's detector on `old_test`.
- Ignore boxes were applied to every new slide, including fully labeled ones, because there is no per-slide record
  of which are sparsely labeled. On fully labeled slides this removes some hard negatives; false alarms on empty
  `test_new` tiles went up.
- `test_new` labels look looser than the predictions: last semester's detector and retrain 1 both draw boxes about
  9% narrower than the labels there (not measured for retrain 2), which lowers mAP50:95 on that set.
- Last semester's team picked their checkpoint on the old validation tiles, which slightly favours their number there.
- Method A has not been rerun with retrain 2's detector. Starting Method A from either retrained detector would
  leak: their training slides overlap Method A's validation and test slides.

## 7. Files

| Path | Contents |
|---|---|
| `detector/results.json` | every (model, test set) score and confidence sweep |
| `detector/retrain*_metrics*.csv` | per-epoch training and validation metrics |
| `detector/retrain2_dataset_build_summary.json` | ignore-box counts per new slide |
| `splits/` | slide lists and manifest for split_v2 |
| `annotations/` | COCO annotations for train, val and the three test sets (see its README for where the images are) |
| `method_a/` | per-run and per-fold evaluation summaries |
| `scripts/detector_retrain/` (repo root) | tiling, training, ignore-box and evaluation code |

Model weights and tile images are not in Git. Weights are on Alan's PC:
`model_A/detector_v2/runs/dv2_2xl_focus_20261119/checkpoint_best_total.pth` (retrain 1) and
`model_A/detector_v3/runs/dv3_ignore_bal_20261120/checkpoint_best_total.pth` (retrain 2), 505 MB each.

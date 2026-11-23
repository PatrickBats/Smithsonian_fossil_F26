# Method A, attempt 4: ignore regions (COCO init)

A3 recipe (RF-DETR-2XL, 1000 px, 2,400 optimizer steps, final EMA weights) plus:

1. **Ignore regions.** `make_ignore_labels.py` runs the Spring one-class pollen detector
   (`weights/rfdetr(2xl)_best_plane.pth`) over the A3 training tiles and adds every grain that
   has no sponsor label as an `__ignore__` box (category 28). `train_ignore.py` strips those boxes
   before Hungarian matching and zeroes the classification loss on unmatched queries that overlap
   them (IoU >= 0.5), so unlabeled pollen is neither rewarded nor penalized.
2. **Augmentation.** VerticalFlip + RandomRotate90 on top of the A3 augmentations.
3. **Init.** Training starts from the COCO RF-DETR-2XL weights (`weights/rf-detr-xxlarge.pth`),
   the same starting point as A3. The Spring detector is used only as the pseudo-labeler, so the
   trained model has never seen the validation slides through its init.

The earlier variant that also initialised training from the Spring detector is still available:
`export INIT="$R/weights/rfdetr(2xl)_best_plane.pth"` before launching. With that checkpoint
`seed_class_head_from_one_class` copies the trained pollen row into all 28 class rows; with the
COCO checkpoint (91-row head) it is a no-op and the contract records `init_head.seeded = false`.

## Running on NOTS

```
R=/rhf/allocations/dsci435/Smithsonian_F26
# debug partition, 30-min chunks with Lightning resume (what the reported runs used):
bash chain_debug.sh A4_cocoinit LABEL                          # pseudo-label A3, train, eval
bash chain_debug.sh A4_noaug "$R/model_A/runs/A4_cocoinit/data" "--no-extra-aug"   # reuse labels
# single commons job (6 h): sbatch debug.sbatch, then sbatch run.sbatch
```

`evaluate_run.py` scores the final weights on the unchanged 1,432-tile validation grid
(274 known specimens, IoU 0.5) at confidence 0.25 / 0.3 / 0.4 / 0.5 / 0.75.
Weights, pseudo-labels and raw outputs stay on NOTS; only `summary.json` and the contract are
copied into `reports/`.

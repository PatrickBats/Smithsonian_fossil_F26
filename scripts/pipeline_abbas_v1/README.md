# Abbas preprocessing → RF-DETR → frozen Swin-Tiny

This corrects the annotation-centred exploratory run. The prior model/results
remain unchanged and must not be described as Abbas-grid results.

## Image processing contract

- Read original NDPI at native 40x; do not copy whole slides.
- Derive fixed grids solely from rectangular annotated ROI bounds. Include
  empty tiles, not just tiles centred on known objects.
- 1024x1024 native RGB, nominal 10% overlap, stride int(1024*0.9)=921.
  Spring edge-backshift is retained; repeated identical tile positions are
  removed. ROI coordinates are rounded inward; smaller-than-tile ROIs are
  explicitly reported rather than silently replaced with centred crops.
- Unchanged Spring focus stack: 5x5 Gaussian then 5x5 Laplacian; maximum
  absolute response at every pixel selects the source RGB focal plane.
- Map nanometres with separate horizontal/vertical mpp and slide offsets.
  Circles become bounding boxes. Retain clipped area >25% and >=16 px²,
  matching Spring code; paper text excludes <25%, so equality is a documented
  tiny implementation difference.
- RF-DETR 2XL inputs resized to 1000. Start from generic pretrained weights,
  not the earlier centred-tile model. AdamW, effective batch16 via accumulation,
  EMA and patience10, max40 epochs. This is not a full reproduction of the
  paper's Optuna search, augmentation or original 82-slide experiment.
- Unchanged Spring boundary-aware union-find: compare only predictions in
  overlapping tiles, union IoU>0.5, retain highest score per component.
- Crop directly from the retained prediction's exact focus-stacked RGB tile;
  fixed10% context, white square padding,224 bicubic and ImageNet normalization.
  This crop handoff is an added classification stage, not part of Abbas paper.

## Data/evaluation contract

Reuse the frozen Swin grouped split and28-class checkpoint. Only32 selected
source YES categories are detector targets; the paper detected broader organic
remains. Image preprocessing is aligned; biological target scope and split are
the current project's adaptation. MAYBE/NO are not reinterpreted as pollen/no
pollen. Labels may be incomplete: do not claim whole-scene precision/AP.

All targets covered by ROI grid enter reference scoring once. Targets outside
the covered ROI grids are explicitly listed as excluded; they are not secretly
added as annotation-centred tiles. Report coverage changes before training.
Test remains untouched. Results characterize complete selected ROI grids,
not a whole-slide scan outside annotated ROIs.

Original Swin used crop-wide Tenengrad best-plane images. Passing focus-stacked
crops changes its input representation, as required by this pipeline. Keep that
difference explicit; do not claim equal-input reproduction of Swin results.

Code/source helper snapshots and hashes, config, split, exports and per-object
outputs are retained. New experiment lives in model_B/runs/abbas_focus_stack_v1;
derived data lives in model_B/data/abbas_focus_stack_v1. The old run is not reused
as initialization and is not overwritten.

## Entry points and execution

`pipeline_config.json` records the executed experiment's external input paths
and checksums. `prepare_pipeline_data.py` exports train/validation ROI grids;
`train_pipeline_detector.py` trains the one-class detector;
`evaluate_pipeline.py` classifies its merged predicted crops. `pipeline_common.py`
contains integrity checks, atomic JSON writes and the shared crop transform.

The vendored `spring_focus_stack.py`, `spring_types.py` and `spring_nms.py` were
derived from RiceD2KLab/Smithsonian_fossil_Sp26, inspected revision
`1b62b68a0d95178e6275ef55c38ee4765317b334`. The NMS import was redirected to
the local types module; the boundary-aware algorithm was retained.
`check_abbas_contract.py` checks grid edge handling, LoG pixel provenance and
connected-component deduplication, including same-tile/non-overlapping cases.

The supplied Slurm scripts expect code under
`~/Smithsonian/scripts/pipeline_abbas_v1`. The GPU job uses the existing
`model_A/env_train` environment read-only because the original shared environment
lacks RF-DETR's training extras. Required packages include torch, torchvision,
rfdetr 1.6.4, rfdetr_plus, pytorch_lightning >=2.6,<3, torchmetrics[detection],
faster-coco-eval, pycocotools, NumPy, Pillow, OpenCV, OpenSlide, tifffile and zarr.

Run `check_abbas_contract.py`, then `prepare_pipeline_data.py --config
pipeline_config.json --plan-only`; inspect coverage/exclusions. Submit
`prepare.sbatch` with array `0-3`, and `train.sbatch` with an `afterok` dependency
on successful export. The training job runs an epoch smoke test and classifier
handoff check before training and validation. No test inference is scheduled.

Do not rerun against the completed experiment's output directory. Choose a new
workspace/data directory and snapshot its config/code before a new experiment.
These scripts are an executed exploratory baseline, not evidence of high
accuracy or an exhaustive replication of the paper. Keep NDPI, PNG exports,
private specimen manifests, logs, predictions and model weights outside Git.

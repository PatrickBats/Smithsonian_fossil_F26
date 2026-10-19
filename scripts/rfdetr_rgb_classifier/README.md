# Frozen RGB RF-DETR crops: Swin-Tiny vs DINO

Inference only. Reuses the existing 28-class, separate-slide Swin and DINO
checkpoints on exactly the same RGB RF-DETR detections. Does not train, rerun
the detector, or use test specimens. See the [verified comparison](../../reports/rfdetr_rgb_dino_comparison/README.md).

## Files and prerequisites

- `compare_rgb_dino.py`: restore fixed tile pixels, construct unchanged crops,
  replay Swin, infer DINO and compare the same matched validation specimens.
- `compare_bestplane.py`: original executed best-plane handoff and shared crop,
  path, hashing and atomic-save helpers. Its detector entry point is historical;
  importing it does not construct or run a detector.
- `compare_color_inputs.py`: historical paired BGR/RGB detector adapter. The
  only detector intervention is removing RGB-to-BGR before `model.predict`.
  This is included for provenance, not run by the classifier comparison.
- `compare.sbatch`: classifier comparison GPU entry point.

External inputs stay on NOTS, outside this repository:

1. `SMITHSONIAN_ROOT` defaults to
   `/rhf/allocations/dsci435/Smithsonian_F26`.
2. The frozen `model_B/runs/abbas_rgb_input_check_v1/` supplies
   `rgb_corrected/predictions.json`, `known_reference_results.json`,
   `configuration.json` and each slide's `tile_grid.json` and
   `paired_tile_inputs.json`. Keep these: they define the fixed experiment.
3. Validation references are the four `export_shard_*_references.json` files in
   `model_B/runs/abbas_focus_stack_v1/separate_slides/ordinary_baseline/`.
   NDPI source paths come from these saved references/predictions.
4. Swin weights:
   `runs/broad_swin_2026-10-08/separate_slides/ordinary_baseline/best.pt`.
5. DINO weights and its original trainer snapshot/provenance:
   `runs/broad_dino_2026-10-08/separate_slides/backbone_finetune/`.
   DINO is ViT-B/14, CLS plus mean patch tokens, with a 1536-to-28 head.
   The complete fine-tuned checkpoint is loaded strictly; no weight download.
6. Unmodified [Spring source](https://github.com/RiceD2KLab/Smithsonian_fossil_Sp26/tree/1b62b68a0d95178e6275ef55c38ee4765317b334)
   at commit `1b62b68a0d95178e6275ef55c38ee4765317b334`, selected by
   `SPRING_SOURCE` (defaults to `upstream/` beside `compare_bestplane.py`). On the existing installation,
   set `SPRING_ADAPTER_ROOT=/home/yt70/Smithsonian/scripts/abbas_best_plane_original_v1`
   to use that preserved adapter/source installation.
7. Unmodified [DINOv2 source](https://github.com/facebookresearch/dinov2/tree/7764ea0f912e53c92e82eb78a2a1631e92725fc8)
   at commit `7764ea0f912e53c92e82eb78a2a1631e92725fc8`, selected by `DINO_SOURCE`.
   Defaults to `dinov2-<commit>/` beside the comparison script.

For a clean installation, clone the two upstream repositories **outside this
repository**, check out the pinned commits, and set `SPRING_SOURCE` and
`DINO_SOURCE` to those checkouts. Leave `SPRING_ADAPTER_ROOT` unset to use this
directory's bundled handoff helpers.
Do not vendor their source, model weights or images into Git.

## Run on the existing NOTS installation

Use the existing `model_A/env_train/bin/python` environment. Verified versions:
Python 3.13.12, torch 2.10.0, torchvision 0.25.0, rfdetr 1.6.4,
rfdetr-plus 1.0.2, numpy 2.4.3, OpenCV 4.13.0.92, tifffile 2026.3.3,
zarr 3.1.5 and Pillow 12.1.1. No environment changes are required.

```bash
export PIPELINE_CODE="/path/to/checkout/scripts/rfdetr_rgb_classifier"
export SPRING_ADAPTER_ROOT=/home/yt70/Smithsonian/scripts/abbas_best_plane_original_v1
export DINO_SOURCE=/home/yt70/Smithsonian/scripts/rfdetr_rgb_dino_v1/dinov2-7764ea0f912e53c92e82eb78a2a1631e92725fc8
export COMPARISON_OUTPUT=/rhf/allocations/dsci435/Smithsonian_F26/model_B/runs/rfdetr_rgb_dino_repeat
export PYTHON=/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" "$PIPELINE_CODE/compare_rgb_dino.py" --preflight
mkdir -p "$COMPARISON_OUTPUT/logs"
sbatch --output="$COMPARISON_OUTPUT/logs/compare-%j.log" "$PIPELINE_CODE/compare.sbatch"
```

Use a fresh output directory. A completed `comparison.json` prevents overwrite.
The CPU preflight verifies checkpoints/categories, not GPU inference correctness.
The historical BGR/RGB script additionally requires the preserved original
best-plane baseline and its environment audit; it is not needed for this run.

## Fixed protocol and acceptance checks

- RF-DETR confidence 0.5; fixed 1,777 candidates over 14 validation slides.
- Native 40x, 1000-pixel tiles, stride 900 (10% overlap), per-tile Tenengrad
  Sobel 3 best-plane selection. Reconstructed RGB tile SHA256 must match the
  frozen run; no crop-wide refocusing or focus stacking here.
- Crop the saved tile box with 10% margin, white square padding, 224-pixel
  bicubic resize and ImageNet normalization. Both classifiers receive the same
  tensor. Each crop gets a pixel hash in the output.
- Preserve original float32 tile-to-slide coordinate arithmetic exactly.
- Preserve `torch.set_float32_matmul_precision('high')`, set globally by the
  original RF-DETR package. Both classifiers use that same inference setting.
- Replay Swin in the original per-slide groups of 32: all top-1 labels must
  reproduce and confidence differences must be below 0.0001.
- Fixed greedy one-to-one matching at IoU >=0.5; all 274 reference detection
  flags and IoUs must reproduce. Compare labels on the same 258 found objects.

`comparison.json` is written only after all checks pass. Detailed predictions,
per-object matches, per-class counts, tile hashes, configuration and successful
job log remain on NOTS. Candidate boxes without known matches are unreviewed;
do not count them all as false positives.

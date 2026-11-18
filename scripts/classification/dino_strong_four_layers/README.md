# DINO: strong augmentation and last-four-block fine-tuning

This is the completed flat 28-class DINO follow-up, not a hierarchical/block classifier. Training code was preserved with line endings normalized to LF from the successful NOTS experiment; new batch wrappers allow a fresh output directory. Other policies remain available to preserve the executed source, but the documented entry point selects strong augmentation and four blocks.

## What changes

DINOv2 ViT-B/14 uses concatenated CLS and mean patch tokens (1536 features) and a linear 28-class head. After 3 head-only epochs, unfreeze blocks **8, 9, 10, 11**, final normalization and head. Earlier blocks remain frozen; trainability and frozen-parameter fingerprints are checked. Backbone LR is **5e-6** (baseline: last 2 blocks, 1e-5), so this compares a combined depth+LR change, not depth alone.

Training-only strong augmentation: uniform sampled angle 0..360 degrees, horizontal/vertical flips each 50%, translation +/-10%, scale 0.8..1.2, brightness/contrast 0.8..1.2, Gaussian blur 20%, kernel 3, sigma 0.1..1.0. White fill, bilinear affine interpolation. A transformed annotation bounding rectangle must fit within a 2 px margin; reject unsafe geometry up to 100 times, then use identity geometry. Accepted transforms are conditional on object size. These checks do not recover material missing from the source crop.

Other settings: original separate-slide split1,605 train / 347 validation / 331 test; exact original assignment SHA checked; official LVD142M initialization (not resumed from the prior trained model); seed 20261007;40 epochs; batch size 32; AdamW weight decay 0.01; head-only LR 1e-3; fine-tuning head LR 1e-4; unweighted CE; shuffled ordinary sampling; float32 deterministic settings. Validation has no augmentation. Select by supported-class validation macro-F1; test is unused.

## Files

- `method_b/classification/train_dinov2.py`: trainer and trainable parameter selection.
- `method_b/classification/crop_dataset.py`: training transforms and geometry protection.
- `check_trainable.py`: CPU checks for head-only/last 2/last 4 modes and frozen digest.
- `qa_augmentation.py`: all-training-image bounds check and 24 paired visual examples.
- `compare_validation.py`: aligns347 expert validation record IDs, labels and split/crop hashes.
- `compare_fixed_crops.py`: compares new scores with saved mild/strong scores on 258 identical detected crops, verifies RGB tile/crop SHA, no detector rerun.
- `recorded_train.sbatch`, `recorded_evaluate.sbatch`: scripts actually executed on NOTS.
- `train_four_layers.sbatch`, `evaluate_four_layers.sbatch`: wrappers for reproducing in a **new** output directory.
- `source_versions.json`: package and pinned DINO source hashes; `verify_source.py` verifies them without Git on compute nodes.

## Reproduce on NOTS

Use the team environment `/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python` (recorded torch 2.10.0+cu128, torchvision 0.25.0+cu128, Python 3.13.12, L40S). Other dependencies: numpy, scikit-learn, Pillow; frozen NDPI replay additionally needs the team's tifffile/zarr/OpenSlide environment.

Copy this directory under your home Smithsonian code area. From that directory:

```bash
mkdir -p external
ln -s /home/yt70/Smithsonian/experiments/dino_mild_augmentation_20261108/external/dinov2 external/dinov2
export DINO_EXPERIMENT_CODE="$PWD"
export DINO_EXPERIMENT_RUN=/rhf/allocations/dsci435/Smithsonian_F26/model_B/runs/CHOOSE_A_NEW_RUN_NAME
PY=/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python
"$PY" verify_source.py
"$PY" check_trainable.py
mkdir -p "$DINO_EXPERIMENT_RUN/logs"
TRAIN=$(sbatch --parsable --output="$DINO_EXPERIMENT_RUN/logs/train-%j.log" train_four_layers.sbatch)
sbatch --dependency=afterok:$TRAIN --output="$DINO_EXPERIMENT_RUN/logs/eval-%j.log" evaluate_four_layers.sbatch
```

Site-specific prerequisites are intentional: the verified classifier input bundle, official pretrained initialization and original split/maps must exist at the paths in the batch script. DINO source revision must match the recorded commit. The bundle is extracted to a job-specific temporary directory and removed on exit. The model output directory must not already exist. Both runs start from official pretrained weights, not from the old fine-tuned checkpoint.

For pre-submission image QA, extract the verified classifier bundle to temporary storage and run `python qa_augmentation.py /temporary/classifier_inputs/dataset /new/qa four_layers`; inspect `augmentation_preview.png` and require zero bounds violations before training. Remove the temporary extraction after review. Completed recorded QA: 1,605 images x 3 transforms = 4,815, zero annotation clipping/fallbacks; 24 preview pairs reviewed.

Frozen-crop evaluation also depends on the existing NOTS modules `/home/yt70/Smithsonian/scripts/rfdetr_rgb_dino_v1/compare_rgb_dino.py`, the prior Abbas replay helpers it imports, frozen tile manifests, source slides, and saved prior scores under `dino_strong_augmentation_20261116/fixed_detector_crops`. This replay is not a standalone whole-slide inference application. The standalone classifier loader is `method_b/classification/load_classifier.py`, which restores a trusted full checkpoint with strict state loading and preserved 28-class order.

## Completed run and results

Code: `/home/yt70/Smithsonian/experiments/dino_followup_20261117`.
Artifacts: `/rhf/allocations/dsci435/Smithsonian_F26/model_B/runs/dino_followup_20261117/four_layers`.
Checkpoint: `best.pt`; selected epoch 26; 40 epochs complete; frozen parameter check passed. Jobs 2770143 (training) and 2770144 (fixed-crop evaluation) completed with exit 0. Geometry comparison jobs 2770141/2770142 also completed; they are context, not the selected method.

| Same 258 RF-DETR crops | Correct | Accuracy | Macro-F1 | Classification macro-AP |
|---|---:|---:|---:|---:|
| Mild / last 2 |129|50.00%|39.49%|49.05%|
| Strong / last 2 |133|51.55%|41.92%|51.69%|
| Strong / last 4 + lower LR |138|53.49%|44.52%|52.65%|

On 347 expert-located validation crops: strong/last 2=181 correct, 52.16% accuracy, 43.30% macro-F1, 47.33% macro-AP; strong/last 4=183 correct, 52.74%, 45.33%, 51.60%. Counting missed detections in the 274 covered references, joint detection+correct classification is 138/274=50.36% versus 133/274=48.54%.

**Limits:** single-seed exploratory validation, no independent test. The original detector saw 13/14 evaluation slides; 258 is the subset of matched detector crops, not all dataset specimens. Classifier has 28 outputs, but 27 classes have validation support; macro metrics exclude unsupported classes. AP is one-vs-rest classification AP, not detection AP. The legacy `execution` provenance label in the copied trainer still says baseline/mild; actual policy, blocks, LR, completed jobs and their configuration identify this strong/four-layer experiment.

[Confusion matrices and compact comparison tables](../../../reports/dino_strong_four_layers/README.md) are included for review. Raw images, crop pixels, pretrained/fine-tuned weights and full per-object score tensors remain on NOTS.

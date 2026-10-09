# Separate 28-group classification experiment

Patrick authorized training on the [broad-v1 map](../../data/current/broad_v1/README.md), then requested Swin as well as partially fine-tuned DINO. Frozen DINO is excluded from this comparison. The name-based map remains an exploratory grouping; this run is not sponsor confirmation of its taxonomy.

Four independent runs use Swin-Tiny and DINOv2 ViT-B/14 with the original separate-slide and shared-slide protocols. Each starts fresh from its original official pretrained backbone with a new 28-output head. No trained 32-class checkpoint is resumed. All 2,283 specimens, their fine labels, source crops and memberships are retained; training/validation/test counts remain 1,605/347/331. The 331 test specimens are excluded from model inference and model selection.

Swin retains its original schedule: three head-only epochs and 37 full-network epochs. DINO retains three head-only epochs and 37 epochs updating only blocks 10–11, the final normalization and the classification head. Both retain seed 20261007, 224-pixel inputs, ordinary sampling, unweighted cross-entropy, quarter-turn and horizontal-flip augmentation for training only, batch size 32, AdamW weight decay 0.01, head warm-up learning rate 0.001, fine-tuning head learning rate 0.0001 and backbone learning rate 0.00001. Best checkpoints use validation macro-F1 over supported broad groups: 27 for separate slides (Retipollenites absent) and 28 for shared slides.

Original manifests and fine-class checkpoint IDs remain unchanged. [The label adapter](../../scripts/classification/broad_labels.py) checks the exact broad-v1 CSV hash and original class namespace, preserves `fine_category`, and only creates a broad target in memory after source and split verification. Each run snapshots its map, broad class IDs, inputs, code and validation predictions. Tests verify every non-target field is unchanged and reject a mismatched original class order. The usual smoke tests and numerical checks precede full runs; DINO additionally verifies that its permanently frozen parameters remain unchanged.

## Broad-label controls

Raw broad-task scores must not be presented as improvements over the old fine-task accuracy. [The control scorer](../../scripts/classification/score_fine_as_broad.py) reads only saved validation probabilities from the previously selected fine-task Swin and adapted DINO checkpoints. It verifies exact validation IDs/labels, then reports two distinct controls: mapping each fine argmax to its broad group, and summing fine probabilities within each broad group before taking the broad argmax. Checkpoint selection remains the original fine-macro-F1 selection. These controls isolate some effects of changing the scoring vocabulary; they are not newly trained broad models or a new test evaluation.

## Execution and artifacts

The four runs execute concurrently on four available, UUID-locked Terminator6 GPUs. Outputs are locally staged outside Git:

- `/mnt/richb/pb52/MADness/smithsonian/broad_swin_2026-10-08/`
- `/mnt/richb/pb52/MADness/smithsonian/broad_dino_2026-10-08/`
- `/mnt/richb/pb52/MADness/smithsonian/broad_label_controls_2026-10-08/`

Each model root has `separate_slides/` and `shared_slides/` runs. The supervisor writes `status.json`, `summary.json` and a verified-transfer report. Successful run directories are copied to matching model-root names under `/rhf/allocations/dsci435/Smithsonian_F26/runs/`, then SHA-256 verified. Local originals remain intact. Copy failures preserve the local runs and failure evidence.

## Completed validation results

All four runs completed 40 epochs. Checkpoints were selected by validation macro-F1.

| Model | Validation split | Accuracy | Macro-F1 |
| --- | --- | ---: | ---: |
| Swin-Tiny | Separate slides | 42.94% | 0.3569 |
| Swin-Tiny | Shared slides | 70.61% | 0.6751 |
| Adapted DINO | Separate slides | 50.14% | 0.4140 |
| Adapted DINO | Shared slides | 74.35% | 0.6890 |

Both DINO frozen-parameter integrity checks passed. All four run copies on RHF were SHA-256 verified. The final test set remains unused. Existing 32-category results and files remain available.

For comparison, mapping the earlier DINO fine-class predictions into broad groups gives 50.14% separate-slide and 74.06% shared-slide accuracy. Broad retraining therefore added little accuracy beyond changing the label vocabulary. These are single-run comparisons, not evidence of statistical significance.

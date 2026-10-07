# Swin Tiny first baseline

Launched October 7, 2026 after Patrick approved the unchanged 32-category vocabulary, grouped split, and ordinary-sampling baseline. Patrick, Yun-Ying, and Alan own the Swin classification work; Yeonju and Bob own the direct multiclass RF-DETR comparison.

## Data and checks

All 2,283 focal-plane-zero crops were re-extracted through read-only NOTS Slurm jobs and streamed to workstation storage outside Git. The crop manifest SHA-256 matches the earlier team export exactly: `b4d803ca764f9941de38014bc5a67eb797f400a595033118c32512f5701e1373`. Independent checks verified all source fields, coordinates, PNG hashes, dimensions, circle containment, and group isolation. No identical PNG hash appeared across partitions. A negative check confirmed that changed source coordinates are rejected.

Training uses 1,605 records; validation uses 347; test reserves 331. One training example per category was inspected visually. Several plane-zero examples are visibly blurred; no examples were removed or relabeled. This run assesses the supplied single-plane representation and must not be treated as an evaluation of best-plane selection or focus stacking.

## Execution

The NOTS project group had approximately 582 MB remaining, so the training run uses an available, UUID-locked user-owned Quadro RTX 8000 and workstation storage. The shared NOTS quota is not repaired. Original slide files remain on NOTS. The first extraction attempt failed because Slurm required an explicit partition time request; its logs were preserved before retrying with the partition maximum.

The two-epoch smoke test passed frozen-head and full-network forward/backward execution with finite values. The ordinary baseline completed all 40 epochs without a recorded failure, in 481.78 seconds (about 8 minutes, including setup). The selected checkpoint is epoch 18, chosen by validation macro-F1. Test inference was not performed.

Configuration: [training workflow](../../scripts/classification/README.md). Forty epochs, three head-only then 37 full fine-tuning; pretrained ImageNet-1K Swin-Tiny; seed 20261007; conservative quarter-turn/reflection augmentation; no training cap or balanced sampler. Category mapping and split: [protocol](../../docs/BASELINE_DATA_PROTOCOL.md).

Checkpoint selection uses validation macro-F1 over the 31 represented categories. Retipollenites has no validation examples; sparse-category uncertainty remains substantial. Test inference is disabled. All metrics produced during training are validation results, not final test results. No push, PR merge, or Drive modification was performed.

Local run identifier: `swin_baseline_2026-10-07/training_attempt_01/ordinary_baseline`. Large images, weights, private manifests, predictions, and logs are stored outside the repository.

## Completed baseline results

| Validation metric at selected epoch 18 | Value |
| --- | ---: |
| Accuracy on 347 specimens | 31.99% |
| Macro-F1 over 31 represented categories | 0.2332 |
| Balanced accuracy over those categories | 29.34% |

The selected model recovered 5 of 11 Arecipites validation examples, zero of 17 Bombacacidites examples, and zero of the single Platycarya platycarioides example. The last count is too small for a reliable category-specific conclusion. Retipollenites is absent from validation.

Training loss continued falling while validation loss worsened in later epochs, consistent with overfitting. These results establish an executable baseline, not satisfactory category identification. The earlier crop review found visible blur in several plane-zero examples; its contribution to these errors has not been isolated. A focused review of validation mistakes and input focus should precede interpreting the model comparison. No balanced-sampling or alternate-focus experiment has run yet.

The best checkpoint, validation predictions, confusion matrix, per-class support, environment, and provenance are preserved in the private run directory. Nothing has been pushed.

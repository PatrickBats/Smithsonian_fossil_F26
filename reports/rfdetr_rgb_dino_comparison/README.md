# RGB RF-DETR → Swin-Tiny / DINO validation comparison

Job **2274617** completed successfully on NOTS in **24m16s**, exit code **0:0**.
All 14 slides completed. Existing 28-class separate-slide classifiers were
reused without training. RF-DETR was not rerun and test data were not used.

| Metric | Swin-Tiny | DINOv2 ViT-B/14 |
|---|---:|---:|
| Known validation objects in covered regions | 274 | 274 |
| Identical detected objects (IoU >=0.5) | 258 | 258 |
| Correct classifications | 93 | **125** |
| Accuracy among 258 detected objects | 36.0% | **48.4%** |
| End-to-end success among 274 references | 33.9% | **45.6%** |

DINO correctly classified **32 more objects**, improving classification accuracy
by **12.4 percentage points**. Of the same 258 detections, both were correct on
75, only DINO on 50, only Swin on 18, and both were wrong on 115. The remaining
16 reference objects were not detected by the fixed detector.

The 1,777 total candidate predictions are not 1,777 verified true specimens.
The 274 references are the validation objects covered by the existing ROI
export, not the entire project dataset or all 347 validation records.

## Verification and limits

Reconstructed tile pixels matched the saved RGB hashes, preserving focal-plane
selection. Boxes and crop geometry were fixed. Both classifiers received the
same normalized crop tensor. All 1,777 Swin labels reproduced; confidence
differences were below 0.0001. Reference matching and IoUs were unchanged.

This supports DINO as the better classifier **for these fixed validation crops**.
It is a diagnostic, not an unseen-test generalization result: Abbas's original
detector had seen 13 of these 14 validation slides during its training.
The classifiers' original accuracy on manually located crops is a different
evaluation and must not be substituted for the numbers above.

## Preserved artifacts

Successful run:
`/rhf/allocations/dsci435/Smithsonian_F26/model_B/runs/rfdetr_rgb_dino_v1/`

- `comparison.json`: aggregate comparison and verification flags.
- `configuration.json`: model/input hashes, categories and precision settings.
- `predictions.json`: all candidate classifications and crop pixel hashes.
- `known_reference_results.json`: 274 per-reference DINO outcomes.
- `per_class_comparison.json`: category-level paired counts.
- `verified_tile_inputs.json`: reconstructed RGB tile hashes.
- `status.json` and `logs/compare-2274617.log`: successful completion evidence.

DINO checkpoint SHA256:
`ad37dea7cf4cdf65254a4f9a7d473ec373907439333665f961ebf1b8fb95058f`.

Swin checkpoint SHA256:
`14d6e2d2727563c077320a82f77163fcd1e25eefaea6a41e84f9b1e415c53e70`.

Frozen predictions SHA256:
`6d48b2221c49d339d3e14acedd1c3385b63064f320d941c8cefa4cd1bbe4ef2e`.

Frozen Swin reference results SHA256:
`3edab13823fffe2cf1ca85b2cb16f0ddeadb5e05948848e9d362aa21fe2ac933`.

See [code and reproduction instructions](../../scripts/rfdetr_rgb_classifier/README.md).
Raw images, weights and generated experiment outputs are intentionally outside
Git; this report contains the verified aggregate findings.

## Cleanup policy

Keep successful outputs, original executed code, pinned upstream source,
checkpoints and frozen comparison inputs. Remove only the two failed attempts'
logs/status files and obsolete code snapshots, redundant source archives, and
per-slide incremental JSON after verifying it duplicates final predictions.
Earlier RF-DETR experiments remain where they are required as input/provenance;
this cleanup does not remove shared data or teammates' experiments.

Cleanup completed: **22 files / 7,243,076 bytes** removed. Hashes of all
preserved successful outputs and executed comparison scripts were unchanged.
The exact deletion list and preserved hashes are recorded in
`cleanup_manifest.json` beside the NOTS results.

The two failed attempts exposed coordinate and arithmetic precision mismatches:
the original adapter uses float32 coordinate addition, and RF-DETR imports
enable `high` matmul precision. The final code preserves both and passes the
original strict replay checks; neither check was relaxed.

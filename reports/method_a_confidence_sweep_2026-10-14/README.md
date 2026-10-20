# Method A confidence threshold sweep — October 14, 2026

## Pipeline

Method A directly predicts 28 broad categories with RF-DETR 2XL. This experiment evaluates confidence thresholds using the existing trained checkpoint and focus-stacked validation images; no retraining was performed. The objective is to measure how confidence filtering changes known-specimen localization and correct-category recovery. The held-out test set was not used.

The evaluator runs inference once at confidence 0.05. For **each threshold separately**, it retains predictions with score >= threshold, performs cross-tile deduplication within each slide, and reruns class-independent one-to-one matching against known reference specimens at IoU >= 0.50. Matching greedily assigns eligible prediction/reference pairs in descending IoU order, without using category correctness. Category correctness is assessed after matching. Deduplication uses the shared Spring boundary-aware routine with IoU 0.50; it is not class-aware. “Raw predictions” are library-returned detections retained at the threshold before cross-tile deduplication, not unfiltered model logits.

## File locations

- Repository evaluator: [evaluate_confidence_sweep.py](../../scripts/method_a_error_analysis/evaluate_confidence_sweep.py), especially `main()` and `evaluate_source()`; Slurm entry point: [run_confidence_sweep.sbatch](../../scripts/method_a_error_analysis/run_confidence_sweep.sbatch).
- Source dataset/run root: `/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_focus_stack_v1/`; inputs are `dataset/valid/`, validation entries in `plan/`, and `inputs/broad_category_map.json`. Checkpoint: `run_artifacts/detector/checkpoint_best_total.pth`.
- NOTS sweep output: `/home/yk86/method_a_reproduction/confidence_sweep_572340f1e8a142c2940a3d75f7f7d5ed/`.
- This report includes the small [summary.json](summary.json). The [original Method A report](../method_a_focus_stack_2026-10-13/README.md) remains unchanged. Images, model weights, and large prediction files are not copied into this report.

## Completed experiment

The validation set contains **1,432 tiles from 14 slides and 274 annotated reference specimens**. The evaluator configures 28 classes and model resolution 1000 for the 1024-pixel source tiles. Confidence thresholds are 0.05, 0.10, 0.30, and 0.50; matching IoU is 0.50.

| Confidence | Raw predictions | Deduplicated predictions | Localized GT | Correctly classified GT | Unmatched predictions | Localization recall | End-to-end known-specimen success |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.05 | 3,805 | 2,764 | 205 | 40 | 2,559 | 74.82% | 14.60% |
| 0.10 | 1,148 | 875 | 137 | 32 | 738 | 50.00% | 11.68% |
| 0.30 | 123 | 105 | 58 | 37 | 47 | 21.17% | 13.50% |
| 0.50 | 41 | 35 | 24 | 20 | 11 | 8.76% | 7.30% |

Localization recall is class-independent: localized GT / 274. Correctly classified GT counts references with **both correct localization and category**; it is not classification accuracy over all tiles. Unmatched predictions are deduplicated predictions not assigned to a known reference. End-to-end known-specimen success is correctly localized-and-classified GT / 274. Table percentages are rounded to two decimal places; exact aggregate values are retained in summary.json.

## Findings and limitations

Lowering confidence from 0.50 to 0.05 increases localized references from 24 to 205 and correctly localized-and-classified references from 20 to 40, while increasing unmatched predictions from 11 to 2,559. Threshold 0.05 has the highest known-reference recovery among the four settings. This alone does not establish an optimal deployment threshold.

Correct-category recovery is not monotonic: 0.30 produces 37 correct references versus 32 at 0.10. Because filtering, deduplication, and matching are rerun separately, the matched prediction/reference assignments can change between thresholds. Threshold-dependent changes in category correctness require further investigation using the row-level matches and predictions; no specific cause is established here.

Annotations may be incomplete. **Unmatched predictions are unreviewed, not confirmed false positives**, so these counts do not establish full-scene precision or AP. Results describe known-object recovery on the selected validation ROI grid, not whole-slide or held-out test performance. The inherited 28-class map includes draft sponsor-review merges.

## Reproducibility

Verified checkpoint SHA256: `c7dc1fe0e01aadf78c9a30ca1431212a9bb9e68709048100bd094f2adb952afd`. The verified baseline check at confidence 0.50 gives 24 localized GT and 20 correctly localized-and-classified GT, matching Bob's reported results.

The evaluator checks the completed training status and checkpoint hash, validates the 1,432-tile/274-reference counts, and reads only validation plans. It is designed to save `run_contract.json` (checkpoint, category-map, plan, script and helper hashes; configuration; PyTorch version; Slurm job ID), `known_references.json`, and `raw_tile_predictions.jsonl`. Each `confidence_<threshold>/` contains `summary.json`, `predictions.json`, and `known_reference_results.json`; the output root contains the aggregate `summary.json`.

The Slurm script uses the deployed helper directory through `PYTHONPATH` and the existing Method A training environment. These deployed dependencies and source image links must remain available to reproduce the run. The experimental counts and aggregate metrics were manually checked by the experimenter against the completed NOTS aggregate summary.json. This verification does not establish independent verification of all runtime artifacts or hashes. Runtime hashes and job details should be taken from that run's `run_contract.json`, not inferred from the current checkout.

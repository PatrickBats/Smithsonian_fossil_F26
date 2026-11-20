# Mixed-delivery final model and test evaluation

This workflow rebuilds the joint detector/classifier from the complete original
priority-label inventory and the mapped additional delivery. It preserves the
28-output category map, native-pixel context crops, LoG k=5 focal fusion, and
ignore-region loss. It does not reuse historical train/validation/test membership.

## Frozen protocol

- Input records: all 2,290 original priority circles and 540 mapped new targets.
  Original annotation versions and all source records are retained. The two
  evidenced punctuation-alias pairs and matching image thumbnails remain in
  indivisible scan groups; no biological grouping is inferred from filenames.
- Reserve approximately 20% of scan groups as test before fitting. Both
  deliveries must be represented. Deterministic label-based stratification
  balances class support and delivery proportions without model predictions.
- Assign the remaining groups to five cross-validation folds. Each fold trains
  on four development folds and predicts the fifth. Test groups never enter
  either proposal-model training or joint-model training/selection.
- Initialize each new proposal detector from the SHA-verified generic RF-DETR
  2XL checkpoint. Fit it using only that fold's training references, then use it
  to propose ignore regions in those training crops. Initialize the joint model
  from this training-only proposal detector. No historical fossil-trained
  checkpoint is used. The final proposal detector uses all development groups.
- Train each joint fold model for a fixed 2,400-step cosine schedule, saving EMA
  snapshots at 1,200 and 2,400 steps. Compare those snapshots at confidence
  0.25/0.30/0.40/0.50/0.75. Select by mean scan-level location-and-category
  recovery, then pooled recovery, higher cutoff, and earlier snapshot step.
- Seal the selected settings and protocol hashes. Train the final joint model
  on all development groups, following the same schedule up to the selected
  step. Evaluate this one checkpoint once on the reserved mixed-delivery test.
  Cross-validation scores are model-selection evidence, not final test results.

The fixed proposal-detector budget is 2,400 optimizer steps. All models use
1,000 px inputs, batch 1 with accumulation 16, LR 1e-4 / encoder LR 1e-5,
flip/90-degree rotation augmentation, EMA, and seed 20261120. Two-step smoke
jobs check the CUDA/training/export path before full fitting. Optional
time-limited chunks record resume checkpoints and preserve optimizer, scheduler,
and EMA state; a resumed partial epoch may revisit its initial batches.

## Storage and entry point

Use `run.py --help` for explicit stage arguments. The script delegates to
[`method_a_final_evaluation`](../../src/method_a_final_evaluation/README.md).
Imports do not parse arguments or access project data. Launching the absolute
script from a different current directory is supported.

| Artifact | NOTS location |
| --- | --- |
| Executed source, Slurm logs, predictions, reports | `/projects/dsci435/Smithsonian_F26/method_a/mixed_final_20261120/` |
| Original source-manifest copy | `/rhf/allocations/dsci435/Smithsonian_F26/processed/mixed_final_inputs_20261120/` |
| Frozen assignment, source plans, focal crops, COCO datasets | `/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_mixed_final_20261120/` |
| New fold/final checkpoints | `/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/mixed_final_20261120/` |
| Generic initializer | `/rhf/allocations/dsci435/Smithsonian_F26/weights/rf-detr-xxlarge.pth` |

Generic initializer SHA-256:
`bf418652d5e07ad441599acfadc65bb1767029079e7a343a6d61675ec5d553ae`.

Stage order: prepare, export each source, assemble fold/final training datasets,
smoke training, train proposal detectors, generate training-only ignore boxes,
train joint fold models, predict development holdouts, seal selection, train the
final joint model, predict test, and publish aggregate results. Run GPU work via
`gpu.sbatch`; use `cpu.sbatch` for preparation/export and aggregation. Supply
`MIXED_CODE_ROOT` and explicit `--root`, `--run-root`, and `--results` paths.
Fresh outputs must not overwrite completed experiments. Record Slurm submissions
and the source hash inventory with the run.

The controller also uses otherwise available short debug allocations for up to
four independent fits. Each fit runs in an exclusive one-GPU Slurm step with
four CPUs and 32 GB RAM; model states and output directories remain separate.
The 29-minute allocation saves resumable chunks after 24 minutes. Only pending
scavenge jobs may be replaced: originals are held before dispatch, then their
IDs and replacement allocation are retained in `jobs.json`. Running jobs are
never moved. Short inference jobs take priority over this fallback. A maximum
of 24 submissions per fit bounds continuation; terminal model failures require
inspection rather than automatic retries.

## Interpretation

Correct means an IoU >= 0.50 location match and the correct category for the
same known source record. Cross-crop NMS and one-to-one matching reuse the
preceding evaluator. Report pooled test counts, mean scan-level recovery,
per-delivery results, class and scan support, and the full confusion matrix.
All inputs are annotation-guided positive context crops. Sparse labels do not
establish whole-slide search, full-scene precision, AP, or verified false
positives. Thumbnail grouping is a conservative identity safeguard, not proof
of complete NDPI byte equality. Conflicting/overlapping source annotations are
preserved and disclosed, not silently adjudicated.

Source provenance: context-window planning and focal fusion follow PR #9's
`method_a_new_delivery` implementation at
`cd5f843bcdfe51774d4b9ec86db831f93c98ca19`. The ignore loss, class-head seeding,
and known-target scorer are reused directly from that package. Partitioning,
training-only proposal generation, checkpoint selection, and the final-test
gate are implemented in this package.

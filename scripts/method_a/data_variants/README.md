# Method A: three training-data variants

A1, A2 and A3 are **data-processing variants of Method A**, not different model
architectures. Each new run uses one RF-DETR 2XL model to detect and classify
28 identification classes. The [result report](../../../reports/method_a_data_variants_2026-10-18/README.md)
contains the completed validation comparison and machine-readable aggregates.

## Names and recorded artifacts

Public names describe the data treatment. Original run-directory IDs are kept
for reproducibility; the `m1` and `m2` prefixes in those old IDs do **not** identify
Method A versus Method B. `train.py`, `evaluate.py` and `prune.py` accept `--variant
A1`, `A2` or `A3`; `--experiment` and the original IDs remain compatible.

| Method A variant | Recorded directory ID | Train tiles | Known train targets | Box instances |
| --- | --- | ---: | ---: | ---: |
| A1: positive ROI grid tiles | `m1_positive_grid` | 884 | 1,061 | 1,586 |
| A2: context crops, original coverage | `m2_retile_matched` | 918 | 1,063 | 1,189 |
| A3: context crops, all train targets | `m2_retile_all` | 1,423 | 1,605 | 1,768 |

A2 uses the original 1,061 targets as crop anchors, but two additional already
labeled train targets occur inside its windows and must keep their labels.
A3 adds the 544 train targets that were not retained by the original ROI-grid
and box-retention policy. Neither variant borrows validation or test targets.
All three preserve the adopted 2,283-record split and existing 28-class map.
This experiment does not replace the repository's 2,290-record source inventory
or resolve the draft category merges pending sponsor review.

## Data processing

A1 links to the existing LoG-fused ROI-grid PNGs and filters out only training
tiles without retained YES boxes. The original grid had 5,152 train tiles,
including 4,268 without a retained YES box. A missing YES annotation does not
establish that the image is empty or that all other visible grains are negatives.

A2/A3 use annotation-guided context windows. Most are 512 pixels square, with
larger 640/768-pixel windows for large targets. The planner searches deterministic
random offsets that fully include each anchor and prefer no known-object boundary
cuts. A generated anchor has 32 pixels of context; another anchor can reuse an
existing window when it fits with at least 16 pixels of margin. This reuses
182 windows. The complete pool has 1,392 windows at 512 pixels, 23 at 640 and
8 at 768. All intersecting YES labels are retained; 40 remaining partial box
instances are clipped and explicitly recorded.

The crop pixels are fused across the full focal series with the same absolute
LoG k=5 rule. Plane zero must match OpenSlide exactly. Each crop is placed at a
deterministic random offset in a 1024-pixel canvas, using the median crop-edge
RGB as uniform padding. Native object scale is preserved before the common
1000-pixel model resize. Padding changes image appearance and context, and
unannotated pollen can still remain inside the real window. These experiments
reduce uncertain exposure; they do not create complete scene annotations.

## Shared training and validation

All new runs use generic RF-DETR 2XL initialization, 28 target classes, model
resolution 1000, seed 20261013, AdamW LR 1e-4 / encoder LR 1e-5, batch 1 with
accumulation 16, cosine LR scheduling, EMA and **2,400 optimizer steps**.
Only direct resize and horizontal flip are applied. The library's secondary
random crop is disabled in the experiment process without editing its installed
files. Each run first passes a two-step training and two-image inference check.

There is no AP-based model selection or early stopping. The saved model is the
fixed final EMA. Epoch counts differ because dataset sizes differ. Validation
uses all 1,432 original grid tiles and the same 274 known references; the 261
positive-tile subset is a diagnostic. Fixed confidence thresholds are 0.25, 0.50
(primary) and 0.75, with IoU >= 0.50 and the original boundary-aware deduplication.
Unmatched predictions are unreviewed. No full-scene precision/AP, recall over
unannotated grains, or held-out test result is claimed.

## Storage and existing inputs

Default paths refer to the completed NOTS runs. **Do not rerun writers against
the completed directories.** For a fresh run, export new user-owned roots below.
No commands in this README submit jobs automatically; run the selected commands
on NOTS only when rebuilding or repeating an experiment.

| Purpose | Default completed-run path / override |
| --- | --- |
| Verified original-grid inputs, plans, COCO and PNG hash manifest | `/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_focus_stack_v1/`; `METHOD_A_BASELINE_ROOT` |
| New images, annotation/split manifests and model checkpoints | `/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_sparse_labels_20261017/`; `METHOD_A_DATA_ROOT` |
| Code | This directory; `METHOD_A_CODE_ROOT` |
| Small Slurm logs | `/projects/dsci435/Smithsonian_F26/runs/method_a_sparse_labels_20261017/`; `METHOD_A_LOG_ROOT` |
| Metrics, compressed predictions and reports | `/projects/dsci435/Smithsonian_F26/results/method_a_sparse_labels_20261017/`; `METHOD_A_RESULTS_ROOT` |
| Generic pretrained weights | `/rhf/allocations/dsci435/Smithsonian_F26/weights/rf-detr-xxlarge.pth`; `METHOD_A_PRETRAINED_WEIGHTS` |
| Observed Python environment | `/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python`; `METHOD_A_PYTHON` for Slurm wrappers |

The baseline root must already contain `inputs/priority_records.csv`,
`inputs/fine_to_broad.csv`, `inputs/broad_category_map.json`, slide `plan/*.json`,
`dataset/{train,valid}/_annotations.coco.json`, linked PNGs, and
`dataset/source_image_hashes.json`. Input hashes and coverage counts are pinned.
The existing artifacts can be used independently of PR #5; rebuilding them from
raw NDPI/NDPA uses the [baseline implementation in PR #5](https://github.com/PatrickBats/Smithsonian_fossil_F26/pull/5).
Do not substitute the full source catalog for the frozen assignment without a
separate protocol change.

Raw and processed image data and row-level manifests stay under `/rhf`. Large
checkpoints also stay there because the shared `/projects` quota was nearly full.
Code, small logs, metrics and compressed predictions use `/projects`. Inputs,
shared images and the shared runtime are read only. A private verified pretrained
copy protects shared weights from library recovery/download behavior. New files
use group-readable permissions; cleanup checks ownership and link counts.

## Reproduction stages

The observed environment used Python 3.13.12, PyTorch 2.10.0+cu128, RF-DETR 1.6.4,
RF-DETR+ 1.0.2 and NVIDIA L40S GPUs. Source reading also needs OpenSlide, tifffile,
Zarr, NumPy, OpenCV and Pillow. Use the existing environment read only; this
package does not install or modify shared dependencies.

Set `METHOD_A_CODE_ROOT` to an absolute NOTS checkout/deployment path. For new
work, choose an unused experiment name and corresponding roots; Slurm output
paths are passed explicitly because `#SBATCH` directives do not expand variables.

```bash
export METHOD_A_CODE_ROOT=/projects/dsci435/Smithsonian_F26/method_a/data_variants_v1
export METHOD_A_DATA_ROOT=/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_data_variants_new_run
export METHOD_A_RESULTS_ROOT=/projects/dsci435/Smithsonian_F26/results/method_a_data_variants_new_run
export METHOD_A_LOG_ROOT=/projects/dsci435/Smithsonian_F26/runs/method_a_data_variants_new_run
mkdir -p "$METHOD_A_LOG_ROOT"

# Run sequentially, waiting for each prerequisite to succeed.
sbatch --output="$METHOD_A_LOG_ROOT/audit-%j.log" "$METHOD_A_CODE_ROOT/run_cpu.sbatch" audit
sbatch --output="$METHOD_A_LOG_ROOT/a1-build-%j.log" "$METHOD_A_CODE_ROOT/run_cpu.sbatch" m1
sbatch --output="$METHOD_A_LOG_ROOT/crop-plan-%j.log" "$METHOD_A_CODE_ROOT/run_cpu.sbatch" plan
sbatch --output="$METHOD_A_LOG_ROOT/crop-pilot-%j.log" "$METHOD_A_CODE_ROOT/run_cpu.sbatch" pilot
sbatch --array=0-46%4 --output="$METHOD_A_LOG_ROOT/export-%A_%a.log" "$METHOD_A_CODE_ROOT/run_cpu.sbatch" export
sbatch --output="$METHOD_A_LOG_ROOT/finalize-%j.log" "$METHOD_A_CODE_ROOT/run_cpu.sbatch" finalize

# First run each variant's smoke check, then its full run after success.
sbatch --output="$METHOD_A_LOG_ROOT/a1-smoke-%j.log" "$METHOD_A_CODE_ROOT/run_gpu.sbatch" smoke A1
sbatch --output="$METHOD_A_LOG_ROOT/a1-full-%j.log" "$METHOD_A_CODE_ROOT/run_gpu.sbatch" full A1
# Repeat the two GPU commands with A2 and A3.

# After all three full jobs succeed, verify protected inputs and publish comparison.
sbatch --output="$METHOD_A_LOG_ROOT/comparison-%j.log" "$METHOD_A_CODE_ROOT/run_cpu.sbatch" collect
```

These example commands are **not a dependency chain**: wait for success or add
Slurm `--dependency=afterok:JOB_ID` arguments. The historical stage `m1` builds
A1; `finalize` builds both A2 and A3 from one verified crop pool. The GPU `full`
stage trains, validates, then prunes only redundant owned checkpoints after final
weight/validation hashes agree. An evaluation-only entry point is available as
`run_evaluate.sbatch A2` (or A1/A3); it also performs guarded post-validation
pruning. Existing output directories intentionally fail rather than overwrite
completed results. The standard-library `inspect_status.py` reads compact state;
its accounting IDs describe the recorded run and recovery jobs, not future runs.

## Validation and source reuse

The package exposes A1/A2/A3 aliases and environment-configurable locations, and
formats the source for review. It does not retrain or change the recorded weights.
The crop planner, geometry, LoG fusion, matching and deduplication functions retain
the same AST as the executed source; recorded hashes are in
[provenance.json](../../../reports/method_a_data_variants_2026-10-18/provenance.json).
This is a scoped code-identity check, not proof that every packaging change or
future environment reproduces identical model behavior. Run
`python3 -m unittest discover -s scripts/method_a/data_variants/tests -v` from the
repository root for dependency-free configuration, output-boundary and result
checks. Cluster matching regression is `check_evaluation_on_cluster.py`.

The evaluator excludes the unassigned sigmoid output slot 28 and records it;
training labels remap to 0–27. Other unexpected IDs still fail. In the completed
runs, only 2 A2 and 1 A3 predictions at confidence >= 0.25 used slot 28, and none
reached the primary 0.50 threshold. Training checkpoints were not changed during
that evaluation recovery.

`spring_nms.py` and `spring_types.py` follow the Spring 2026 boundary-aware
annotator pipeline, revision `1b62b68a0d95178e6275ef55c38ee4765317b334` of
[RiceD2KLab/Smithsonian_fossil_Sp26](https://github.com/RiceD2KLab/Smithsonian_fossil_Sp26).
The fusion follows the same Spring LoG k=5 rule. Images, row-level manifests,
predictions and checkpoint payloads stay on NOTS. The repository package contains
code, documentation and aggregate metrics.

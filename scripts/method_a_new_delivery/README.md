# Method A new-delivery workflow

The runnable entry points in this directory delegate to the importable implementation in [`src/method_a_new_delivery`](../../src/method_a_new_delivery/). The committed [title maps](../../data/current/new_delivery_maps/README.md) and [final report](../../reports/method_a_new_delivery_2026-11-16/README.md) complete the handoff. The code for the final training configuration is in `training.py` and `ignore_regions.py`; the scan-grouped assessment is in `cv.py`, `cv_evaluate.py`, `cv_aggregate.py`, and `confusion.py`. `plot_confusion.py` renders the report figure from the aggregate count CSV.

## NOTS locations

| Item | Path |
| --- | --- |
| Original new NDPI and annotations | `/rhf/allocations/dsci435/smithsonian_full_sp26/new files/New_train_set_detection_model_rice/` |
| Pixel-box audit and mapped positive manifest | `/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_new_delivery/` |
| New crops, merged COCO, pseudo ignore dataset, and fold manifests | `/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_new_delivery/training/` |
| Fixed historical A3 training core | `/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_sparse_labels_20261017/datasets/m2_retile_all/` |
| One-class initializer | `/rhf/allocations/dsci435/Smithsonian_F26/weights/rfdetr(2xl)_best_plane.pth` |
| Full and five fold checkpoints | `/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A4_new_delivery_20261113/` |
| Fold summaries, per-object matches, threshold selection, and raw predictions | `/projects/dsci435/Smithsonian_F26/method_a/new_delivery/runs/results/` |
| Python environment used by the completed run | `/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/` |

The fixed final full-data checkpoint is `full/checkpoint_final_ema.pth` under the checkpoint root; its SHA-256 is `2fd94d63e5f3bcb58b92d5503217ff2cc11aca7774edce89de7c07c9f9912b30`. Fold checkpoints are `cv/fold_0` through `cv/fold_4`. The selected threshold is recorded in `aggregate/selection.json` under the result root. The new-data confusion counts are reproduced from the five `fold_*/confidence_0.30_matches.json` files. The [committed CSV](../../reports/method_a_new_delivery_2026-11-16/confusion_counts.csv) contains aggregate counts only.

## Run order

Use a checkout of this PR on NOTS with the recorded Python environment. Set `REPO_ROOT` to the checkout path and use the absolute entry points under `$REPO_ROOT/scripts/method_a_new_delivery/`; they also work when launched from another current directory. The Python modules use the source and output paths above by default. For a fresh run, set `METHOD_A_NEW_PREP`, `METHOD_A_NEW_RUNS`, and `METHOD_A_NEW_RESULTS` to new user-owned roots before running; completed output paths must not be overwritten. `METHOD_A_NEW_SOURCE` and `METHOD_A_A3_DATASET` can select a different source or A3 core when needed. The input image/annotation manifest stores absolute source paths, so preserve the source identity when reproducing the recorded run.

For example, from a NOTS checkout, create fresh output roots and run the CPU preparation entry points as follows. Replace the three `my_run` destinations with your own unused paths:

    export REPO_ROOT="$PWD"
    export METHOD_A_NEW_PREP=/rhf/allocations/dsci435/Smithsonian_F26/processed/my_run
    export METHOD_A_NEW_RUNS=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/my_run
    export METHOD_A_NEW_RESULTS=/projects/dsci435/Smithsonian_F26/method_a/my_run/results
    PY=/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python
    mkdir -p "$METHOD_A_NEW_PREP/training/plan" "$METHOD_A_NEW_RUNS" "$METHOD_A_NEW_RESULTS/logs"
    "$PY" "$REPO_ROOT/scripts/method_a_new_delivery/audit.py"
    "$PY" "$REPO_ROOT/scripts/method_a_new_delivery/geometry.py"
    "$PY" "$REPO_ROOT/scripts/method_a_new_delivery/unify.py"
    "$PY" "$REPO_ROOT/scripts/method_a_new_delivery/map_labels.py"
    "$PY" "$REPO_ROOT/scripts/method_a_new_delivery/plan.py"

Run the CPU preparation stages in order: `audit.py`, `geometry.py`, `unify.py`, `map_labels.py`, and `plan.py`. Create the preparation root and its `training/plan` directory first. `audit.py` inventories both delivered formats; `geometry.py` converts NDPA nanometer circles with each scan's OpenSlide calibration; `unify.py` produces level-zero pixel boxes; `map_labels.py` selects in-bounds sponsor YES objects; `plan.py` writes deterministic native-pixel context-crop plans.

Submit [`slurm/export.sbatch`](slurm/export.sbatch) as an array for slide indices 0–19, then [`slurm/finalize.sbatch`](slurm/finalize.sbatch), [`slurm/ignore.sbatch`](slurm/ignore.sbatch), and `verify.py`. The crop exporter uses LoG k=5 focal fusion and produces 535 context crops. The finalizer combines those with 1,423 A3 images; the ignore pass adds 3,188 pseudo boxes. `verify.py` checks image references, counts, category IDs, and the unchanged historical validation/test COCO.

For the export array, pass the fresh log root and the exported environment to Slurm:

    sbatch --export=ALL --array=0-19 --output="$METHOD_A_NEW_RESULTS/logs/export-%A_%a.out" "$REPO_ROOT/scripts/method_a_new_delivery/slurm/export.sbatch"

Run `prepare_cv.py` to create five scan-disjoint folds. Submit [`slurm/train_full.sbatch`](slurm/train_full.sbatch) for the final all-data checkpoint and [`slurm/train_cv_chunk.sbatch`](slurm/train_cv_chunk.sbatch) repeatedly until all five fold `status.json` files say `completed`. Then submit [`slurm/evaluate_cv.sbatch`](slurm/evaluate_cv.sbatch) and [`slurm/aggregate_cv.sbatch`](slurm/aggregate_cv.sbatch). The Slurm scripts require exported `REPO_ROOT` and use the recorded NOTS environment. Pass `--output` and `--error` to `sbatch` for a fresh log directory; the checked-in directives show the completed run's log locations. Submit dependent stages only after their prerequisites finish successfully.

Build the complete matrix from the selected fold predictions with `confusion.py --output /path/to/confusion_counts.csv`, then render it with `plot_confusion.py --counts /path/to/confusion_counts.csv --output /path/to/confusion_matrix.png`. The figure aggregates the 12 output classes without new ground-truth support into one display column; the CSV retains all 28 prediction classes.

The completed run used Python 3.13.12, `rfdetr` 1.6.4, `rfdetr-plus` 1.0.2, PyTorch 2.10.0, TorchVision 0.25.0, PyTorch Lightning 2.6.6, OpenSlide Python 1.4.3, tifffile 2026.3.3, zarr 3.1.5, OpenCV 4.13.0.92, and Pillow 12.1.1. The workflow was executed on NOTS Linux with Slurm, CUDA, POSIX symlinks, and its mounted `/rhf` and `/projects` filesystems. Source syntax and aggregate-count checks were also run on macOS; native Windows execution has not been checked.

Handoff verification on NOTS used fresh temporary outputs: the label and crop-plan stages reproduced 67 source scans, 540 selected targets, 535 planned crops, 543 crop-box instances, and the recorded fold object counts (164, 94, 94, 98, 90). One exported crop matched its completed-run PNG SHA-256. Reaggregation of the retained fold matches reproduced the committed confusion CSV byte-for-byte. Full GPU training was not repeated for this code handoff.

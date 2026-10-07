# Full Tenengrad crop export and matched Swin comparison

The full experiment was launched following Patrick's authorization on October 7. Four read-only NOTS CPU jobs (2034670–2034673) select focal planes for the 2,283 adopted specimens across 75 source images. The export and 40-epoch classifier comparison have completed. The best-plane checkpoint selected at epoch 32 achieved validation accuracy 38.04%, macro-F1 0.3392, and balanced accuracy 41.74%, compared with 31.99%, 0.2332, and 29.34% for the zero-plane baseline. These are single-seed validation results; test inference remains disabled. Live status and results are recorded outside Git; this document is not a claim of improved accuracy.

For each specimen, keep the exact baseline crop coordinates and dimensions, read that region at every available focal plane, convert RGB to grayscale, and calculate the mean squared horizontal and vertical 3×3 Sobel gradients (Tenengrad). Select the highest score; ties prefer the plane closest to zero, then its earlier index. Save only the selected PNG plus every plane's score, index, offset, and read/scoring time. This adapts the prior detection-tile method to individual specimen crops. Nearby sharp debris can still dominate the score; it is not a biological quality guarantee or focus stacking.

Each zero-plane crop must match its previously verified PNG hash. Dimensions, geometry, source fields, specimen identity, partition assignments, and ordering remain unchanged. Input and code hashes bind each batch. Completed batch archives can be reused only if those bindings and archive hashes match; failed attempts remain available. A different method requires a new output directory. No source slide is changed or downloaded in full, and outputs are streamed to workstation storage to avoid the shared NOTS quota.

The fixed split remains 1,605 training, 347 validation, and 331 test records in 32 sponsor YES categories. Image-only preprocessing applies identically to all partitions; no test image enters model inference or checkpoint selection. Validation lacks Retipollenites and has sparse support in several categories, as documented in the [baseline protocol](../../docs/BASELINE_DATA_PROTOCOL.md).

After export verification, the detached continuation performs a two-epoch smoke test and the original 40-epoch Swin-Tiny experiment. Seed, pretrained weights, training row order, augmentation, sampling, loss, optimizer, learning rates, and checkpoint selection are unchanged. The continuation checks that the original model/training/evaluation functions are structurally identical, binds the launch-time code hashes, obtains a GPU UUID lock through the launcher, and compares actual configurations and runtime versions afterward. Training uses an available workstation GPU; this remains the previously disclosed storage-quota workaround.

Compare the selected validation checkpoints using macro-F1 over the 31 supported categories, balanced accuracy, ordinary accuracy, per-class results, and recorded probabilities. This is a single-seed comparison on validation data, not final test evidence. No balanced-sampling experiment or additional model search is included.

## Artifacts and commands

Private artifact root: `/mnt/richb/pb52/MADness/smithsonian/tenengrad_full_2026-10-07/`.

- `status.json`, `export.log`, `batch_*/attempt_*.log`: export state and source-processing progress.
- `binding.json`, input snapshots and `batch_*/remote_script.py`: immutable input/method evidence.
- `dataset/crop_manifest.csv`, `focus_scores.json`, `representation.json`: selected images and their provenance, available after assembly.
- `verified_data.json`: full source, image, geometry and partition audit.
- `continuation_status.json`, `continuation.log`, `training_launcher.log`: downstream training state.
- `training_attempt_01/ordinary_baseline/`: model, training history and validation predictions after training starts.
- `comparison.json`: both selected validation results, written only after matched-configuration verification and successful training.

Run [`full_tenengrad.py`](../../scripts/classification/full_tenengrad.py) with `--baseline` (frozen zero-plane crop directory), `--assignments`, `--categories`, `--output` and `--workers 4`. The output must be outside Git. [`continue_focus_training.py`](../../scripts/classification/continue_focus_training.py) takes `--export` and `--baseline-run`; it waits for verified export and stops if extraction fails or bound code changes. Inspect and diagnose recorded failures before resuming. The CPU Slurm jobs request the commons partition's maximum allowed duration; GPU training has no wall-clock cutoff.

Checks before launch: pilot-archive assembly reproduced all eight selections and retained source order/geometry; all model/training/evaluation function definitions match the original baseline; repository source-integrity, links, and syntax checks passed. Full-data verification and training artifacts now report successful completion.

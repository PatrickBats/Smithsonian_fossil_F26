# Swin Tiny baseline

The initial baseline uses the 32 unchanged sponsor YES categories, ordinary shuffled sampling of all 1,605 training crops, and the adopted accession-group split. Validation uses 347 records; 331 test records remain reserved. See [protocol](../../docs/BASELINE_DATA_PROTOCOL.md).

`train_swin.py` verifies the frozen assignment SHA-256, every crop's source fields and byte hash, dimensions, circle containment, and source-group isolation. Integrity checks can read test PNGs; no test image enters a model or model-selection metric. Category IDs come from [the shared map](../../data/current/baseline_category_map.csv). Crop integrity does not establish expert taxonomy or complete image-quality review.

The model uses torchvision Swin-Tiny ImageNet-1K weights. Inputs retain their full field of view, padded to square and resized to 224 pixels, with ImageNet normalization. Training augmentation uses quarter-turns and horizontal reflections only. Three head-only epochs at learning rate 0.001 precede 37 full-network epochs (backbone 0.00001, head 0.0001), batch size 32, AdamW weight decay 0.01, unweighted cross-entropy, gradient norm clipping at 1, float32, and seed 20261007. Numerical failures stop the run with a saved traceback.

Checkpoint selection uses macro-F1 over validation categories with nonzero reference support. All 32 output classes remain active; the absent Retipollenites category is explicitly listed. Per-class counts, confusion matrices, probabilities, software versions, source hashes, optimizer state, random states, and elapsed GPU allocation time are retained outside Git. No resume operation or test-evaluation command is provided. A new invocation must use a new output directory.

`launch_swin.py` locks an available GPU by UUID, rechecks competing compute processes and free memory, runs a two-epoch smoke test, then runs the baseline only if it succeeds. Run it detached, redirecting launcher output to a persistent log. Required arguments are `--gpu`, `--data` (crop directory), `--assignments` (private CSV), `--categories` (shared map), and `--output_root` (new directory outside Git). The interpreter must provide torch, torchvision, NumPy, and Pillow. The verified environment was torch 2.10.0+cu128, torchvision 0.25.0+cu128, and Pillow 12.1.1; every run records its actual environment.

October 7 execution uses Patrick's available workstation GPU because the NOTS project group has only about 582 MB left. Crops are re-extracted read-only through Slurm and streamed to storage outside the repository; no full slide is copied and original NOTS sources remain unchanged. This is an execution-location change from the planned NOTS training workflow. The CPU extraction requires Slurm's partition time request; it uses the maximum commons allocation, not an imposed cumulative compute budget. Workstation GPU training has no wall-clock cutoff. Failed extraction attempts remain recorded.

This first ordinary-sampling run intentionally does not implement the sponsor's earlier 50-grain cap, following Patrick's October 7 approval of the discussed baseline. Balanced sampling is a later controlled comparison, not silently combined with this run. The single-plane experiment does not compare best-plane selection with focus stacking.

Architecture and weights: [official torchvision documentation](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.swin_t.html).

## Full best-plane experiment

`full_tenengrad.py` extends the fixed [pilot](../../reports/tenengrad_pilot_2026-10-07/README.md) to all adopted specimens using four read-only CPU jobs and local streamed output. It preserves crop geometry and row order, verifies every zero-plane image against the frozen baseline, and records all focus scores. Completed batches support input-bound resume; original and failed artifacts are retained.

`continue_focus_training.py` waits for verified export and runs the existing smoke/baseline launcher with unchanged scientific settings. It checks training-function equivalence and actual configuration agreement with the original run. See the [full experiment record](../../reports/tenengrad_full_2026-10-07/README.md) for method, artifact locations, and current launch status. `train_swin.py` admits only the frozen zero-plane manifest or a verified Tenengrad replacement with traceable geometry, scores, and image hashes.

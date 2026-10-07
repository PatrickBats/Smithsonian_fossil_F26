# Detection first: frozen YOLO pilot

Authorized September 24, 2026. Before developing the classifier, test whether the published Spring YOLO checkpoints recover known Fall specimens. No detector retraining or classification training is part of this run.

## Fixed diagnostic protocol

- Select two YES annotation records per supplied category on different slides: 64 targets, 32 categories, 29 slides. Prefer one target centered outside a historical rectangle and one inside; the selected sample has 32 outside centers. Selection is deterministic and fixed before predictions (`scripts/detection/select_pilot.py`). Record whether the complete annotation box is inside as well.
- Extract a 1024×1024 region centered on each target at native 40x. Read every available focal plane at that magnification. Verify image bounds and annotation-file SHA-256 against the Fall inventory.
- Run the published YOLO26 L focus-stack checkpoint on LoG focus-stacked RGB images (kernel 5) and the best-plane checkpoint on Tenengrad-selected planes (kernel 3). This uses the upstream annotator defaults; it does not prove the original checkpoint training used exactly those preprocessing settings.
- Preserve exact specimen positions and original labels. Convert X and Y separately with their metadata pixel sizes; this corrects the upstream conversion helper's assumption that the two pixel sizes are identical.
- Primary endpoint: target recovered by a predicted box with confidence at least 0.5 and IoU at least 0.5. NMS IoU is 0.5. Also report confidence 0.25 as a predeclared sensitivity diagnostic, not a replacement success criterion. Save predictions down to 0.05. No numerical pass threshold is invented.
- Save input tiles, annotated previews, raw boxes/scores, specimen-level results, hashes, environment, prior checkpoint training arguments, GPU UUID, scheduler job IDs, failures and compute usage.

## What results can and cannot establish

This tests recovery of known positives in annotation-centered image regions. It is not a blind whole-slide scan, and centering can make recovery easier than production tiling. Two targets per class do not estimate class performance reliably. Some slides may have been used in the old model's training; provenance must be reported. Outside-rectangle targets are not necessarily unseen slides. Do not infer false positives from unmatched boxes, since the surrounding region is not exhaustively labeled. Do not report precision, AP, or independent generalization from this sample.

Results guide the next validation: inspect failures and coordinates, check historical train/test membership, and expand to a predeclared slide/region evaluation if the pipeline is functioning. Prior weights remain unchanged. Classifier development follows this detection assessment; starting it is not part of this run.

## Execution

Run two Slurm array tasks on NOTS, one allocated GPU per task, sharing the established read-only Spring environment. Each process locks its assigned GPU UUID and does not use GPUs outside its allocation. Output lives under `/projects/dsci435/Smithsonian_F26/runs/`. No agent-imposed time budget is set; the cluster's partition scheduling limits still apply. Original shared images, annotations, and model weights are not overwritten. Run-specific source/configuration snapshots preserve the uncommitted driver code by hash. Git contains scripts and small reports, not checkpoints or image tiles.

## Submitted run

**Completed:** both tasks exited successfully. Best-plane recovered 54/64 targets and focus-stack 51/64 at the preset primary threshold. See the [results and limitations](../reports/detection_pilot_2026-09-24/README.md). This pilot does not establish whole-slide reliability.

Slurm array job **1612309**, run `detection_pilot_20260924T183555Z`. [Frozen configuration and run record](../reports/detection_pilot_2026-09-24/run.json). NOTS rejected an unspecified wall time; submission used the commons partition maximum of 24 hours because its default is zero. This scheduler requirement is recorded in submission.json; it is not an agent GPU budget.

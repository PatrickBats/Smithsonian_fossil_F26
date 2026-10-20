# Approach A, 28 broad categories: RF-DETR find + name in one model

Follow-up to `scripts/approach_a_rfdetr_pilot/` (branch `acy3/approach-a-rfdetr-pilot`).
Same best-plane tiles, boxes and grouped `priority_v0` split as the pilot; only the labels change:
every annotated grain gets a box, using the team's `broad_v1` 28-category map plus one
`other_palynomorph` class (id 28) for annotated grains outside the map.

Results and discussion: [`reports/approach_a_broad28_2026-10-16/README.md`](../../reports/approach_a_broad28_2026-10-16/README.md).

## Files

| File | Purpose |
| --- | --- |
| `data/build_broad28_coco.py` | Relabels the pilot COCO tiles to 28 broad + `other_palynomorph`. Optional repeat-factor sampling (Gupta et al., LVIS, CVPR 2019) duplicates train image entries: `r(c) = max(1, sqrt(t / f(c)))`, image repeat = max over its classes, capped. |
| `train/train_broad28.slurm` | RF-DETR Large, COCO init, 1024 px, cosine LR, 40 epochs, patience 8 (NOTS job 2198490). |
| `train/train_broad28_2xl.slurm` | RF-DETR 2XL initialised from the Sp26 best-plane palynomorph detector, Sp26 hyperparameters, 1000 px (NOTS job 2198498). |
| `eval/eval_broad28_val.slurm` | Validation-only evaluation of both runs with the pilot evaluator `eval_pilot.py` (job 2222489). Test split untouched. |
| `eval/score_known.py` | Known-grain scorer matching Method A's report: a known (non-`other`) grain is *found* if a prediction with score >= thr overlaps it at IoU >= 0.5, and *named right* if the top-scoring such prediction has its category. Counts are per tile box. |

## Reproduce on NOTS

```bash
B=/rhf/allocations/dsci435/Smithsonian_F26/model_A
PY=$B/env_train/bin/python
$PY scripts/approach_a_broad28/data/build_broad28_coco.py --out $B/data/broad28_bestplane_rfs --rfs_t 0.1 --rfs_cap 4
sbatch scripts/approach_a_broad28/train/train_broad28.slurm
sbatch scripts/approach_a_broad28/train/train_broad28_2xl.slurm
sbatch scripts/approach_a_broad28/eval/eval_broad28_val.slurm
```

Inputs that stay on NOTS (not in Git): tiles, `analysis/pilot_boxes_with_records.json`,
`labels/broad_v1_fine_to_broad.csv`, weights, run directories and metrics JSONs.

# Approach A, 28 broad categories: validation results (2026-10-16)

One RF-DETR model that both finds and names grains (Method A), trained on the pilot's
best-plane tiles and grouped `priority_v0` split with every annotated grain labelled:
28 `broad_v1` categories plus `other_palynomorph`. Validation split only; the test split is reserved.
Code: [`scripts/approach_a_broad28/`](../../scripts/approach_a_broad28/README.md).

## What changed vs. the historical Method A baseline (PR #5 / Oct 16 slides 1-4)

1. **Label every annotated grain.** Previously only priority categories had boxes, so most annotated
   grains, and 4,268 of 5,152 training tiles, carried no label and were learned as background.
2. **Repeat-factor sampling** (Gupta et al., LVIS, CVPR 2019), t = 0.1, cap 4: tiles containing rare
   categories are repeated up to 4x. Train set: 5,139 image entries (1,185 RFS duplicates); val 1,113; test 1,064.
3. **Starting point:** Large from COCO weights vs. 2XL from the Sp26 best-plane palynomorph detector.

## Runs

| Run | Model | Init | Job | Wall time | Best epoch | Val mAP50 (29 classes) | Class-agnostic AP50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Large | RF-DETR Large, 1024 px | COCO | 2198490 | 3h03m | 12 | 0.191 | 0.758 |
| 2XL | RF-DETR 2XL, 1000 px | Sp26 detector | 2198498 | 5h03m | 17 | 0.176 | 0.797 |

## Known-grain results (validation, 285 known tile boxes, IoU >= 0.5)

| Confidence | Large found / named right | 2XL found / named right |
| --- | --- | --- |
| 0.50 | 192 (67%) / 27 (9%) | 212 (74%) / 38 (13%) |
| 0.30 | 278 (98%) / 49 (17%) | 282 (99%) / 49 (17%) |
| 0.05 | 285 (100%) / 49 (17%) | 285 (100%) / 49 (17%) |

Momipites (39 boxes): at 0.50, Large found 24 / named 9; 2XL found 31 / named 15; at 0.05 both found 39 / named 18.
Per-class AP50: Bisaccate 0.66 (Large) / 0.63 (2XL); Momipites 0.50 / 0.58; other_palynomorph 0.65 / 0.69.

Historical baseline on the same validation slides (274 specimens, confidence 0.50): 24 found (9%), 20 named right (7%).

## Reading

- Labelling every grain fixed *finding*: at confidence 0.5 the share of known grains found went from 9% to 67-74%.
- *Naming* barely moved: 9-13% at 0.5, ~17% at low thresholds. The model now finds grains but mostly
  calls priority grains `other_palynomorph`. The separate DINOv2 crop classifier names ~48% of comparable crops.
- Next: keep `other` for localisation but stop it competing with the 28 classes (class-mask / ignore), longer
  cosine schedule, rotation augmentation, class-balanced head retraining, distillation from the crop classifier.

## Caveats

- 285 tile boxes vs. the baseline's 274 specimens: different tiling (sharpest focal plane), so grains near tile
  edges can be counted twice. Not matched grain by grain.
- The Sp26 detector used to initialise the 2XL run saw 13 of the 14 validation slides during its training, so
  the 2XL numbers are optimistic. The Large run has no leakage.
- Single seed per run; unmatched predictions are unreviewed, not established false positives.
- Metrics JSONs (`metrics_val.json`, `detections_val.json`, `known_objects_val.json`) remain on NOTS under
  `model_A/runs/A2_val_eval/{large_broad28,2xl_broad28_init_sp26}/`.

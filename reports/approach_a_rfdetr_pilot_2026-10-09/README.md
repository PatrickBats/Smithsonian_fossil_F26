# Approach A RF-DETR pilot — 2026-10-09

First training run of Approach A: one RF-DETR model that finds each palynomorph and names
its category. Code: [scripts/approach_a_rfdetr_pilot](../../scripts/approach_a_rfdetr_pilot/README.md).

## Setup

- Data: Sp26 best-plane (Tenengrad) 1024-px tiles from the annotated regions, relabelled to
  3 classes: Bisaccate, Momipites sp, and other_palynomorph (every other annotated grain).
- Why two categories: they are the two largest inside the annotated regions (Bisaccate 307,
  Momipites sp 182; next is Arecipites with 71). See `class_counts_inside_roi.csv`.
- Split: `priority_v0` grouped split, slides of one specimen kept together. 72 slides,
  6,131 tiles: 3,954 train / 1,113 validation / 1,064 test. See `pilot_summary.json`.
- Models: RF-DETR Large (multiclass, and a one-class reference on the same tiles) and
  RF-DETR 2XL multiclass started from last year's best-plane detector or from COCO weights.
- Starting point checked: last year's 2XL detectors reproduced on our cluster
  (`a0_reproduce_*.json`: AP@50 0.879 focus stack, 0.877 best plane, matching the paper).

## Test results (AP@50)

| Model | Finding grains (labels ignored) | Bisaccate | Momipites | Other |
|---|---|---|---|---|
| Large, one class (reference) | 0.82 | – | – | – |
| Large, multiclass | 0.82 | 0.60 | 0.05 | 0.82 |
| 2XL from last year's detector | 0.87 | 0.56 | 0.09 | 0.87 |
| 2XL from COCO | 0.83 | 0.62 | 0.07 | 0.83 |

Test split: 1,394 grains (29 Bisaccate, 12 Momipites sp, 1,353 other). Full numbers,
per-class precision/recall and confusion matrices are in `test_*.json`.

- Adding category names does not reduce detection.
- No model named a single test Momipites correctly; most were found and called "other".
- Note: the team keeps the test split for final evaluation. These pilot numbers were
  measured on it once; future runs should be compared on validation.

## Why Momipites failed (`q4_train_summary.json`)

The Large model names only 54 of 147 (37%) training Momipites sp boxes correctly, so the
class was not learned even on training images. Likely causes, not yet tested:

- 147 Momipites vs 7,627 other boxes in training, and 75 of the 147 come from one slide (D3408-1_L).
- About 190 grains of similar three-pored pollen (Caryapollenites, Alnipollenites, Betulaceae and others) are in "other".
- 35 grains (39 boxes) labelled with specific Momipites species are in "other".

Next run: oversample Momipites tiles and weight rare classes, merge Momipites species,
add the slides missing from the current tiles (D5825, D1555), and drop duplicate slide copies.

## Files

| File | Contents |
|---|---|
| `test_large_multiclass.json`, `test_large_single_class.json`, `test_2xl_init_sp26.json`, `test_2xl_init_coco.json` | Test metrics per model |
| `a0_reproduce_focus_stack.json`, `a0_reproduce_best_plane.json` | Reproduction of last year's detectors |
| `pilot_summary.json` | Pilot dataset counts and split moves |
| `class_counts_inside_roi.csv`, `class_counts_all.csv`, `inventory_summary.json` | Category counts |
| `q4_train_summary.json` | Large model on training tiles with Momipites |

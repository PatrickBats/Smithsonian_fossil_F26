# Approach A: RF-DETR pilot (find + name in one model)

Code for the first Approach A training run (October 2026): one RF-DETR model that both
detects each palynomorph and names its category. Results are in
[the run report](../../reports/approach_a_rfdetr_pilot_2026-10-09/README.md).

All scripts were run on NOTS. Paths inside them are the NOTS paths used for the run
(`/rhf/allocations/dsci435/Smithsonian_F26/model_A/...`); no images, checkpoints or
large outputs are stored here.

## Folders

| File | What it does |
|---|---|
| `data/label_inventory.py` | Counts annotated grains per category inside the annotated regions and drafts a title → class map. |
| `data/build_pilot_coco.py` | Relabels the Sp26 best-plane 1024-px tiles into a 3-class pilot (Bisaccate, Momipites sp, other_palynomorph) and reassigns slides to the `priority_v0` grouped split. Images are symlinked, not copied. Also builds the matching one-class dataset. |
| `train/train.py` | RF-DETR training entry point from `RiceD2KLab/Smithsonian_fossil_Sp26` (`src/models/rfdetr/train.py`) with four changes, listed below. |
| `train/train_large.slurm` | RF-DETR Large: multiclass (task 0) and one-class reference (task 1). |
| `train/train_2xl.slurm` | RF-DETR 2XL multiclass: started from last year's best-plane detector (task 0) or COCO weights (task 1). |
| `eval/eval_ckpt.py`, `eval/eval_ckpt.slurm` | Reproduces last year's single-class 2XL test results (AP@50 0.879 focus stack, 0.877 best plane). |
| `eval/eval_pilot.py`, `eval/eval_pilot.slurm`, `eval/eval_2xl.slurm` | Test-split evaluation: detection-only AP (labels ignored), per-class AP, and a confusion matrix with missed grains and false boxes at the best-F1 confidence. |
| `figures/make_examples.py` | Side-by-side expert vs model example images. |
| `figures/make_curves.py` | Validation curves (not used in slides). |
| `analysis/momi_*.py` | Investigation of why Momipites fails: label counts per split, labelling convention per slide, and model behaviour on training tiles. |

## Changes to `train.py` (relative to Sp26 commit `1b62b68`)

These four commits are on the local `f26-approach-a` branch of the Sp26 clone on NOTS
(`model_A/code`); they have not been pushed to the Sp26 repository. `train_*.slurm` run it
from that clone as `python -m src.models.rfdetr.train`.

1. `--pretrain_weights`: fine-tune from a given checkpoint (COCO weights or last year's detector).
2. RF-DETR Large (2026 release) needs an image size divisible by 32, not 56.
3. `--model_kwargs` (JSON) passed to the model, and the model is built at the training resolution. RF-DETR Large at 1024 px needs `{"positional_encoding_size": 44}` to keep the pretrained position embeddings.
4. Help-text fix.

## Environment

`model_A/env_train`: a venv on top of `/projects/dsci435/smithsonian_sp26/conda-env` with
`rfdetr[train,loggers]==1.6.4`. RF-DETR XLarge/2XL come from `rfdetr_plus` (Roboflow Platform
Model License); Nano–Large are Apache-2.0.

## Known issues

- The 2XL run started from last year's detector saved `checkpoint_best_total.pth` and `checkpoint_best_ema.pth` at step 0 (untrained), because of a spurious epoch-0 EMA validation score. Its evaluation uses `checkpoint_best_regular.pth`. Check the saved step before using any "best" checkpoint.
- `eval_pilot.py` drops predictions whose class id is outside the dataset's classes (RF-DETR's extra output slot). Detection-only scores match the one-class model, but the scores of the dropped predictions were not checked.
- `analysis/momi_recon.py` rebuilds the box → record mapping from a copy of `record_assignments.csv` because `splits/priority_v0/` was no longer on NOTS at the time.

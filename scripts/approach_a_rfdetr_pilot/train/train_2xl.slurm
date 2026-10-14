#!/bin/bash
#SBATCH --job-name=f26-A1-pilot
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=16:00:00
#SBATCH --array=0-1
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A1_pilot_top2_bestplane/logs/%A_%a.out
#SBATCH --error=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A1_pilot_top2_bestplane/logs/%A_%a.err
# Approach A pilot: Bisaccate + Momipites sp + other_palynomorph, best-plane (Tenengrad) tiles, priority_v0 split.
# Task 0: init from last semester best-plane detector (note: 13 val / 9 test slides were in its training set).
# Task 1: init from RF-DETR-2XL COCO weights (no slide leakage).
# Hyperparameters copied from the Sp26 tuned focus-stack checkpoint args (Optuna trial 2).
set -euo pipefail
PY=/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python
B=/rhf/allocations/dsci435/Smithsonian_F26
R=$B/model_A/runs/A1_pilot_top2_bestplane
DATA=$B/model_A/data/pilot_top2_bestplane
if [ "$SLURM_ARRAY_TASK_ID" = 0 ]; then INIT="$B/weights/rfdetr(2xl)_best_plane.pth"; NAME=init_sp26_detector
else INIT="$B/weights/rf-detr-xxlarge.pth"; NAME=init_coco; fi
OUT=$R/$NAME; mkdir -p $OUT
export MPLCONFIGDIR=$OUT/.mpl TORCH_HOME=$OUT/.torch PYTORCH_KERNEL_CACHE_PATH=/tmp/$USER-kc-$SLURM_JOB_ID NO_ALBUMENTATIONS_UPDATE=1
cd $B/model_A/code
nvidia-smi --query-gpu=name,memory.total --format=csv
$PY -u -m src.models.rfdetr.train \
  --model 2xlarge --pretrain_weights "$INIT" --coco_dir $DATA \
  --epochs 30 --batch_size 4 --grad_accum 2 \
  --lr 2.41e-4 --lr_scheduler cosine --lr_min_factor 0.1 --warmup_epochs 1 \
  --weight_decay 0.0587 --drop_path 0.32 --imgsz 1000 \
  --output_dir $OUT --workers 6 --early_stopping_patience 6 \
  --aug_config custom --aug_json "{\"Rotate\": {\"p\": 0.713}, \"RandomBrightnessContrast\": {\"p\": 0.544}, \"HueSaturationValue\": {\"p\": 0.360}}"

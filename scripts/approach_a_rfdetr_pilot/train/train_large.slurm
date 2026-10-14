#!/bin/bash
#SBATCH --job-name=f26-A1-large
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=16:00:00
#SBATCH --array=0-1
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A1_pilot_large_bestplane/logs/%A_%a.out
#SBATCH --error=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A1_pilot_large_bestplane/logs/%A_%a.err
# Approach A pilot with RF-DETR Large (Apache-2.0), init from COCO weights rf-detr-large-2026.pth.
# Best-plane (Tenengrad) tiles, priority_v0 grouped split.
# Task 0: multiclass  Bisaccate + Momipites sp + other_palynomorph   (A1)
# Task 1: single-class palynomorph baseline on identical tiles/split  (A0-large, clean detection reference)
set -euo pipefail
PY=/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python
B=/rhf/allocations/dsci435/Smithsonian_F26
R=$B/model_A/runs/A1_pilot_large_bestplane
if [ "$SLURM_ARRAY_TASK_ID" = 0 ]; then DATA=$B/model_A/data/pilot_top2_bestplane; NAME=multiclass_top2
else DATA=$B/model_A/data/pilot_1class_bestplane; NAME=single_class; fi
OUT=$R/$NAME; mkdir -p $OUT
export MPLCONFIGDIR=$OUT/.mpl TORCH_HOME=$OUT/.torch PYTORCH_KERNEL_CACHE_PATH=/tmp/$USER-kc-$SLURM_JOB_ID NO_ALBUMENTATIONS_UPDATE=1
cd $B/model_A/code
nvidia-smi --query-gpu=name,memory.total --format=csv
$PY -u -m src.models.rfdetr.train \
  --model large --pretrain_weights $B/weights/rf-detr-large-2026.pth --coco_dir $DATA \
  --epochs 40 --batch_size 4 --grad_accum 4 \
  --lr 1e-4 --lr_scheduler cosine --lr_min_factor 0.1 --warmup_epochs 1 \
  --weight_decay 1e-4 --drop_path 0.1 --imgsz 1024 \
  --output_dir $OUT --workers 6 --early_stopping_patience 8 --aug_config custom \
  --model_kwargs {\"positional_encoding_size\":44}

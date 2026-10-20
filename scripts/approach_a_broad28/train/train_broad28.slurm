#!/bin/bash
#SBATCH --job-name=f26-A2-broad28
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=16:00:00
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A2_broad28_large/logs/%j.out
#SBATCH --error=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A2_broad28_large/logs/%j.err
# Approach A: RF-DETR Large, 28 broad_v1 categories + other_palynomorph (29 classes).
# Same best-plane tiles and grouped split as the A1 pilot; train set uses repeat-factor sampling.
set -euo pipefail
PY=/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python
B=/rhf/allocations/dsci435/Smithsonian_F26
DATA=$B/model_A/data/broad28_bestplane_rfs
OUT=$B/model_A/runs/A2_broad28_large/broad28_rfs; mkdir -p $OUT
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

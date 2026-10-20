#!/bin/bash
#SBATCH --job-name=f26-A2-broad28-2xl
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=20:00:00
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A2_broad28_2xl/logs/%j.out
#SBATCH --error=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A2_broad28_2xl/logs/%j.err
# Approach A: RF-DETR 2XL started from last year's best-plane palynomorph detector,
# 28 broad_v1 categories + other_palynomorph, repeat-factor sampling. Same settings as the A1 2XL pilot.
set -euo pipefail
PY=/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python
B=/rhf/allocations/dsci435/Smithsonian_F26
DATA=$B/model_A/data/broad28_bestplane_rfs
INIT="$B/weights/rfdetr(2xl)_best_plane.pth"
OUT=$B/model_A/runs/A2_broad28_2xl/init_sp26_detector; mkdir -p $OUT
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

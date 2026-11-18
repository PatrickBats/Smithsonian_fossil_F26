#!/bin/bash
#SBATCH --job-name=yt70-dino-eval
#SBATCH --partition=commons
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=40G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=02:00:00
set -euo pipefail
umask 022
CODE=${DINO_EXPERIMENT_CODE:-$SLURM_SUBMIT_DIR}
RUN=${DINO_EXPERIMENT_RUN:?Set DINO_EXPERIMENT_RUN}
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4
export NO_ALBUMENTATIONS_UPDATE=1 PALYNET_NUM_WORKERS=0
export DINO_SOURCE="$CODE/external/dinov2"
cd "$CODE"
/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python -u compare_fixed_crops.py --run "$RUN" --policy four_layers

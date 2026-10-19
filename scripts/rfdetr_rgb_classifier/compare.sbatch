#!/bin/bash
#SBATCH --job-name=yt70-dino
#SBATCH --partition=commons
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=01:00:00
set -euo pipefail
umask 022
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2
export NO_ALBUMENTATIONS_UPDATE=1 PALYNET_NUM_WORKERS=0
: "${PIPELINE_CODE:?Set PIPELINE_CODE to this script directory}"
: "${COMPARISON_OUTPUT:?Set COMPARISON_OUTPUT to a fresh directory outside Git}"
PYTHON=${PYTHON:-/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python}
cd "$PIPELINE_CODE"
"$PYTHON" -u compare_rgb_dino.py

#!/bin/bash
#SBATCH --job-name=A4_new_full
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=1-00:00:00
#SBATCH --output=/projects/dsci435/Smithsonian_F26/method_a/new_delivery/runs/logs/full_%j.out
#SBATCH --error=/projects/dsci435/Smithsonian_F26/method_a/new_delivery/runs/logs/full_%j.err
set -euo pipefail
REPO_ROOT=${REPO_ROOT:?Set REPO_ROOT to the cloned repository path}
export PYTHONPATH="$REPO_ROOT/src"
R=/rhf/allocations/dsci435/Smithsonian_F26
W=${METHOD_A_NEW_RUNS:-$R/model_A/runs/A4_new_delivery_20261113}
export MPLCONFIGDIR=$W/.mpl TORCH_HOME=$W/.torch PYTORCH_KERNEL_CACHE_PATH=/tmp/$USER-a4-full-$SLURM_JOB_ID NO_ALBUMENTATIONS_UPDATE=1
"$R/model_A/env_train/bin/python" -u "$REPO_ROOT/scripts/method_a_new_delivery/train_ignore.py" --dataset "${METHOD_A_NEW_PREP:-$R/processed/method_a_new_delivery}/training/dataset_ignore" --init "$R/weights/rfdetr(2xl)_best_plane.pth" --out "$W/full" --steps 2400

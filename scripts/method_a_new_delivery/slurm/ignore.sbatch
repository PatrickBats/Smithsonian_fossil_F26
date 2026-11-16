#!/bin/bash
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --time=00:45:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --output=/projects/dsci435/Smithsonian_F26/runs/method_a_new_delivery/ignore-%j.log
set -euo pipefail
REPO_ROOT=${REPO_ROOT:?Set REPO_ROOT to the cloned repository path}
export PYTHONPATH="$REPO_ROOT/src"
ROOT=/rhf/allocations/dsci435/Smithsonian_F26
PREP=${METHOD_A_NEW_PREP:-$ROOT/processed/method_a_new_delivery}/training
PY=$ROOT/model_A/env_train/bin/python
DET="$ROOT/weights/rfdetr(2xl)_best_plane.pth"
export MPLCONFIGDIR=$PREP/.mpl TORCH_HOME=$PREP/.torch NO_ALBUMENTATIONS_UPDATE=1
"$PY" -B "$REPO_ROOT/scripts/method_a_new_delivery/make_ignore_labels.py" --dataset "$PREP/dataset_base" --detector "$DET" --out "$PREP/dataset_ignore"

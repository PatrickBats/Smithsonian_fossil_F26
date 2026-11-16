#!/bin/bash
#SBATCH --partition=commons
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --output=/projects/dsci435/Smithsonian_F26/runs/method_a_new_delivery/export-%A_%a.log
set -euo pipefail
REPO_ROOT=${REPO_ROOT:?Set REPO_ROOT to the cloned repository path}
export PYTHONPATH="$REPO_ROOT/src"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 NO_ALBUMENTATIONS_UPDATE=1
PY=/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python
"$PY" -B "$REPO_ROOT/scripts/method_a_new_delivery/export.py" --slide-index "$SLURM_ARRAY_TASK_ID"

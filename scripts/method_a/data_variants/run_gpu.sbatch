#!/bin/bash
#SBATCH --partition=commons
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --output=/projects/dsci435/Smithsonian_F26/runs/method_a_sparse_labels_20261017/gpu-%j.log
set -euo pipefail
umask 0027
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false NO_ALBUMENTATIONS_UPDATE=1
export HF_HOME="${SLURM_TMPDIR:-/tmp}/f26-sparse-${SLURM_JOB_ID}-hf"
export TORCH_HOME="${SLURM_TMPDIR:-/tmp}/f26-sparse-${SLURM_JOB_ID}-torch"
PY=${METHOD_A_PYTHON:-/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python}
CODE=${METHOD_A_CODE_ROOT:-/projects/dsci435/Smithsonian_F26/method_a/experiments/sparse_labels_20261017}
case "$1" in
 smoke)
   "$PY" -B "$CODE/train.py" --experiment "$2" --smoke
   "$PY" -B "$CODE/evaluate.py" --experiment "$2" --smoke
   ;;
 full)
   "$PY" -B "$CODE/train.py" --experiment "$2"
   "$PY" -B "$CODE/evaluate.py" --experiment "$2"
   "$PY" -B "$CODE/prune.py" --experiment "$2"
   ;;
 *) exit 2 ;;
esac

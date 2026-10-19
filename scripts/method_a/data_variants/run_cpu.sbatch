#!/bin/bash
#SBATCH --partition=commons
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --output=/projects/dsci435/Smithsonian_F26/runs/method_a_sparse_labels_20261017/cpu-%j.log
set -euo pipefail
umask 0027
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 NO_ALBUMENTATIONS_UPDATE=1
PY=${METHOD_A_PYTHON:-/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python}
CODE=${METHOD_A_CODE_ROOT:-/projects/dsci435/Smithsonian_F26/method_a/experiments/sparse_labels_20261017}
case "$1" in
  audit) "$PY" -B "$CODE/audit_plan.py" ;;
  m1)
    "$PY" -B "$CODE/verify_inputs.py"
    "$PY" -B "$CODE/prepare_datasets.py" m1
    "$PY" -B "$CODE/copy_weights.py"
    ;;
  plan) "$PY" -B "$CODE/prepare_datasets.py" plan ;;
  pilot) "$PY" -B "$CODE/export_crops.py" --slide-index 0 --limit 1 ;;
  export) "$PY" -B "$CODE/export_crops.py" --slide-index "$SLURM_ARRAY_TASK_ID" ;;
  finalize) "$PY" -B "$CODE/prepare_datasets.py" finalize ;;
  collect) "$PY" -B "$CODE/collect_results.py" ;;
  *) exit 2 ;;
esac

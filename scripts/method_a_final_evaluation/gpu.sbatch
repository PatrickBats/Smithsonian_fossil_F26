#!/bin/bash
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --qos=nots_commons
#SBATCH --time=03:00:00
#SBATCH --gres=gpu:lovelace:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
set -euo pipefail
: "${MIXED_CODE_ROOT:?Set the absolute workflow source directory}"
export PYTHONPATH="$MIXED_CODE_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"
export NO_ALBUMENTATIONS_UPDATE=1
exec /rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python \
    "$MIXED_CODE_ROOT/scripts/method_a_final_evaluation/run.py" "$@"

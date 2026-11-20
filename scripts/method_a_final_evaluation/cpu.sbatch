#!/bin/bash
#SBATCH --account=commons
#SBATCH --partition=debug
#SBATCH --qos=nots_debug
#SBATCH --time=00:25:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
set -euo pipefail
: "${MIXED_CODE_ROOT:?Set the absolute workflow source directory}"
export PYTHONPATH="$MIXED_CODE_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"
exec /rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python \
    "$MIXED_CODE_ROOT/scripts/method_a_final_evaluation/run.py" "$@"

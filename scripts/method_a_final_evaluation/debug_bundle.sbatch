#!/bin/bash
#SBATCH --account=commons
#SBATCH --partition=debug
#SBATCH --qos=nots_debug
#SBATCH --time=00:29:00
#SBATCH --gres=gpu:lovelace:4
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
set -euo pipefail
: "${MIXED_CODE_ROOT:?Set the workflow source directory}"
export PYTHONPATH="$MIXED_CODE_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=4
export NO_ALBUMENTATIONS_UPDATE=1
export MIXED_CHUNK_MINUTES=24
exec /rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python \
    "$MIXED_CODE_ROOT/scripts/method_a_final_evaluation/run.py" bundle --manifest "$1"

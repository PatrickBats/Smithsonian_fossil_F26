#!/bin/bash
#SBATCH --job-name=f26-a-fuse-eval
#SBATCH --partition=commons
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --output=/projects/dsci435/Smithsonian_F26/runs/method_a_focus_stack_v1/eval-%j.log
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=1
export NO_ALBUMENTATIONS_UPDATE=1
/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python -B \
  /projects/dsci435/Smithsonian_F26/method_a_focus_stack_v1/evaluate_validation.py

#!/bin/bash
#SBATCH --job-name=f26-a-fuse-eval
#SBATCH --partition=commons
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --output=/home/yk86/method_a_reproduction/eval-reproduction-%j.log
# Before submission, ensure /home/yk86/method_a_reproduction exists and is writable.
# Slurm opens this combined stdout/stderr log before executing the job script.
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=1
export NO_ALBUMENTATIONS_UPDATE=1
export PYTHONPATH=/projects/dsci435/Smithsonian_F26/method_a_focus_stack_v1${PYTHONPATH:+:$PYTHONPATH}
/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python -B \
  /home/yk86/method_a_reproduction/evaluate_validation_reproduction.py

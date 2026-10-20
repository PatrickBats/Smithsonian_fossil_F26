#!/bin/bash
#SBATCH --job-name=f26-a-confidence-sweep
#SBATCH --partition=commons
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --output=/home/yk86/method_a_reproduction/confidence-sweep-%j.log
# Before submission, create /home/yk86/method_a_reproduction and ensure it is writable.
# Slurm opens the combined stdout/stderr log before running this script.
# After confirming runtime, consider --time=00:30:00; resources initially match reproduction.
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=1
export NO_ALBUMENTATIONS_UPDATE=1
export PYTHONPATH=/projects/dsci435/Smithsonian_F26/method_a_focus_stack_v1${PYTHONPATH:+:$PYTHONPATH}
/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python -B \
  /home/yk86/method_a_reproduction/evaluate_confidence_sweep.py

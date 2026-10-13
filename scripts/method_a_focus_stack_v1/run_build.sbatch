#!/bin/bash
#SBATCH --job-name=f26-a-build-coco
#SBATCH --partition=commons
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --output=/projects/dsci435/Smithsonian_F26/runs/method_a_focus_stack_v1/build-%j.log
set -euo pipefail
export OMP_NUM_THREADS=2
/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python -B \
  /projects/dsci435/Smithsonian_F26/method_a_focus_stack_v1/build_linked_dataset.py

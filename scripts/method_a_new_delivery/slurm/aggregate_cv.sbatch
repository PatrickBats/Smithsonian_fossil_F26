#!/bin/bash
#SBATCH --job-name=A4_new_cv_aggregate
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=/projects/dsci435/Smithsonian_F26/method_a/new_delivery/runs/logs/cv_aggregate_%j.out
#SBATCH --error=/projects/dsci435/Smithsonian_F26/method_a/new_delivery/runs/logs/cv_aggregate_%j.err
set -euo pipefail
REPO_ROOT=${REPO_ROOT:?Set REPO_ROOT to the cloned repository path}
export PYTHONPATH="$REPO_ROOT/src"
/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python "$REPO_ROOT/scripts/method_a_new_delivery/aggregate_cv.py"

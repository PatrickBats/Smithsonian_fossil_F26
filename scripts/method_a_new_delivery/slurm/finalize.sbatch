#!/bin/bash
#SBATCH --partition=commons
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --output=/projects/dsci435/Smithsonian_F26/runs/method_a_new_delivery/finalize-%j.log
set -euo pipefail
REPO_ROOT=${REPO_ROOT:?Set REPO_ROOT to the cloned repository path}
export PYTHONPATH="$REPO_ROOT/src"
/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python -B "$REPO_ROOT/scripts/method_a_new_delivery/finalize.py"

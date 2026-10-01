#!/bin/bash
#SBATCH --job-name=f26-priority-preflight
#SBATCH --partition=commons
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --chdir=/projects/dsci435/Smithsonian_F26/crops/priority_v0
#SBATCH --output=/projects/dsci435/Smithsonian_F26/crops/priority_v0/logs/preflight-%j.out
#SBATCH --error=/projects/dsci435/Smithsonian_F26/crops/priority_v0/logs/preflight-%j.err

set -euo pipefail
/projects/dsci435/smithsonian_sp26/conda-env/bin/python -B preflight.py

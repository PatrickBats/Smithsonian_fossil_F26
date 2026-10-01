#!/bin/bash
#SBATCH --job-name=f26-priority-crops
#SBATCH --partition=commons
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --chdir=/projects/dsci435/Smithsonian_F26/crops/priority_v0
#SBATCH --output=/projects/dsci435/Smithsonian_F26/crops/priority_v0/logs/full-%j.out
#SBATCH --error=/projects/dsci435/Smithsonian_F26/crops/priority_v0/logs/full-%j.err

set -euo pipefail
/projects/dsci435/smithsonian_sp26/conda-env/bin/python -B export_crops.py --mode full
/projects/dsci435/smithsonian_sp26/conda-env/bin/python -B verify_export.py --mode full

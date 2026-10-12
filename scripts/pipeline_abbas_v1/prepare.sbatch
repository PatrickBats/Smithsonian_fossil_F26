#!/bin/bash
#SBATCH --job-name=yt70-rfswin-data
#SBATCH --partition=commons
#SBATCH --time=1-00:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
set -euo pipefail
code="$HOME/Smithsonian/scripts/pipeline_abbas_v1"
export PYTHONDONTWRITEBYTECODE=1
exec /projects/dsci435/smithsonian_sp26/conda-env/bin/python -u "$code/prepare_pipeline_data.py" --config "$code/pipeline_config.json" --shard "$SLURM_ARRAY_TASK_ID" --shards 4

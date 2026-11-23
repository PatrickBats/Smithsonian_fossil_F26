#!/bin/bash
#SBATCH --job-name=dv2-shard
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --array=0-60
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=03:00:00
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/detector_v2/logs/shard_%a.out
set -o pipefail
cd /rhf/allocations/dsci435/Smithsonian_F26/model_A/detector_v2
read ROW SH N < <(sed -n "$((SLURM_ARRAY_TASK_ID+1))p" shard_table.txt)
/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python -u tile_boxes.py --row $ROW --shard $SH --nshards $N 2>&1 | grep --line-buffered -v coercing

#!/bin/bash
#SBATCH --job-name=dv2-merge
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/detector_v2/logs/merge.out
cd /rhf/allocations/dsci435/Smithsonian_F26/model_A/detector_v2
while read ROW N; do /rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python -u merge_parts.py --row $ROW --nshards $N 2>&1 | grep -v coercing; done < shard_plan.txt

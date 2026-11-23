#!/bin/bash
#SBATCH --job-name=dv2-tile
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --array=0-66%40
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/detector_v2/logs/tile_%a.out
cd /rhf/allocations/dsci435/Smithsonian_F26/model_A/detector_v2
/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python tile_boxes.py --row $SLURM_ARRAY_TASK_ID 2>&1 | grep -v coercing

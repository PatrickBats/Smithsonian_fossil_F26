#!/bin/bash
#SBATCH --job-name=f26-A1-test-2xl
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=01:30:00
#SBATCH --array=0-1
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A1_test_eval/logs/%A_%a.out
#SBATCH --error=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A1_test_eval/logs/%A_%a.err
# Task 0: 2XL init from Sp26 detector -> best_regular (best_total/best_ema were saved at step 0, untrained)
# Task 1: 2XL init from COCO -> best_total (= best regular, step 12870)
set -euo pipefail
B=/rhf/allocations/dsci435/Smithsonian_F26/model_A
PY=$B/env_train/bin/python
R=$B/runs/A1_pilot_top2_bestplane
OUT=$B/runs/A1_test_eval
if [ "$SLURM_ARRAY_TASK_ID" = 0 ]; then CK=$R/init_sp26_detector/checkpoint_best_regular.pth; NAME=2xl_init_sp26
else CK=$R/init_coco/checkpoint_best_total.pth; NAME=2xl_init_coco; fi
cd $OUT
export MPLCONFIGDIR=$OUT/.mpl_2xl_$SLURM_ARRAY_TASK_ID
$PY -u $OUT/eval_pilot.py --weights $CK --coco_dir $B/data/pilot_top2_bestplane --split test --variant 2xlarge --resolution 1000 --out $OUT/$NAME

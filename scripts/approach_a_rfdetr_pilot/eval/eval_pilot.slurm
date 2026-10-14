#!/bin/bash
#SBATCH --job-name=f26-A1-test-eval
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
# Task 0: Large multiclass (Bisaccate / Momipites sp / other) ; Task 1: Large single-class baseline
set -euo pipefail
B=/rhf/allocations/dsci435/Smithsonian_F26/model_A
PY=$B/env_train/bin/python
R=$B/runs/A1_pilot_large_bestplane
if [ "$SLURM_ARRAY_TASK_ID" = 0 ]; then CK=$R/multiclass_top2/checkpoint_best_total.pth; D=$B/data/pilot_top2_bestplane; NAME=large_multiclass
else CK=$R/single_class/checkpoint_best_total.pth; D=$B/data/pilot_1class_bestplane; NAME=large_single_class; fi
OUT=$B/runs/A1_test_eval
export MPLCONFIGDIR=$OUT/.mpl_$SLURM_ARRAY_TASK_ID
$PY -u $OUT/eval_pilot.py --weights $CK --coco_dir $D --split test --variant large --resolution 1024 \
  --model_kwargs '{"positional_encoding_size":44}' --out $OUT/$NAME

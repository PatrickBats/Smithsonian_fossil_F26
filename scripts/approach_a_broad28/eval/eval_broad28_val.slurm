#!/bin/bash
#SBATCH --job-name=f26-A2-val-eval
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=01:30:00
#SBATCH --array=0-1
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A2_val_eval/logs/%A_%a.out
#SBATCH --error=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A2_val_eval/logs/%A_%a.err
# Validation-split evaluation of the two 28-category (+ other) runs. Test split is not used.
set -euo pipefail
B=/rhf/allocations/dsci435/Smithsonian_F26/model_A
PY=$B/env_train/bin/python
D=$B/data/broad28_bestplane_rfs
OUT=$B/runs/A2_val_eval
if [ "$SLURM_ARRAY_TASK_ID" = 0 ]; then
  NAME=large_broad28; $PY -u $B/runs/A1_test_eval/eval_pilot.py --weights $B/runs/A2_broad28_large/broad28_rfs/checkpoint_best_total.pth \
    --coco_dir $D --split val --variant large --resolution 1024 --model_kwargs '{"positional_encoding_size":44}' --out $OUT/$NAME
else
  NAME=2xl_broad28_init_sp26; $PY -u $B/runs/A1_test_eval/eval_pilot.py --weights $B/runs/A2_broad28_2xl/init_sp26_detector/checkpoint_best_total.pth \
    --coco_dir $D --split val --variant 2xlarge --resolution 1000 --out $OUT/$NAME
fi
$PY $B/broad28/score_known.py $D/annotations/instances_val.json $OUT/$NAME/detections_val.json $OUT/$NAME/known_objects_val.json

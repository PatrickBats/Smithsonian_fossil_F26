#!/bin/bash
#SBATCH --job-name=f26-A0-reproduce
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=03:00:00
#SBATCH --array=0-1
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A0_reproduce/logs/%A_%a.out
#SBATCH --error=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A0_reproduce/logs/%A_%a.err
# Task 0: focus-stack checkpoint on focus-stack test tiles (paper: AP50 0.879, AP50-95 0.642)
# Task 1: best-plane checkpoint on Tenengrad best-plane test tiles (paper: AP50 0.877, AP50-95 0.637)
set -euo pipefail
PY=/projects/dsci435/smithsonian_sp26/conda-env/bin/python
W=/rhf/allocations/dsci435/Smithsonian_F26/weights
C=/rhf/allocations/dsci435/smithsonian_full_sp26/processed/coco
OUT=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A0_reproduce
if [ "$SLURM_ARRAY_TASK_ID" = 0 ]; then
  CK="$W/rfdetr(2xl)_focus_stack.pth"; CD="$C/coco_focus_stack"; NAME=focus_stack
else
  CK="$W/rfdetr(2xl)_best_plane.pth";  CD="$C/coco_tenengrad_plane"; NAME=best_plane
fi
export MPLCONFIGDIR=$OUT/.mpl_$SLURM_ARRAY_TASK_ID PYTORCH_KERNEL_CACHE_PATH=$OUT/.kcache_$SLURM_ARRAY_TASK_ID
nvidia-smi --query-gpu=name,memory.total --format=csv
$PY -u $OUT/eval_ckpt.py --weights "$CK" --coco_dir "$CD" --split test \
    --resolution 1000 --variant 2xlarge --out "$OUT/$NAME"

#!/bin/bash
#SBATCH --job-name=A4_cv_chunk
#SBATCH --account=commons
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=00:30:00
#SBATCH --array=0-4%1
#SBATCH --output=/projects/dsci435/Smithsonian_F26/method_a/new_delivery/runs/logs/cv_chunk_%A_%a.out
#SBATCH --error=/projects/dsci435/Smithsonian_F26/method_a/new_delivery/runs/logs/cv_chunk_%A_%a.err
set -euo pipefail
REPO_ROOT=${REPO_ROOT:?Set REPO_ROOT to the cloned repository path}
export PYTHONPATH="$REPO_ROOT/src"
R=/rhf/allocations/dsci435/Smithsonian_F26
W=${METHOD_A_NEW_RUNS:-$R/model_A/runs/A4_new_delivery_20261113}
F=$SLURM_ARRAY_TASK_ID
OUT=$W/cv/fold_$F
DATA=${METHOD_A_NEW_PREP:-$R/processed/method_a_new_delivery}/training/cross_validation/fold_$F
export MPLCONFIGDIR=$W/.mpl TORCH_HOME=$W/.torch PYTORCH_KERNEL_CACHE_PATH=/tmp/$USER-a4-cv-chunk-$SLURM_JOB_ID NO_ALBUMENTATIONS_UPDATE=1
if [ -f "$OUT/status.json" ] && grep -q '"status": "completed"' "$OUT/status.json"; then
    echo "Fold $F already completed"
    exit 0
fi
if [ -f "$OUT/resume.ckpt" ]; then
    RESUME=(--resume "$OUT/resume.ckpt")
else
    if [ -e "$OUT" ]; then
        echo "Incomplete fold output without resume checkpoint: $OUT" >&2
        exit 1
    fi
    RESUME=()
fi
"$R/model_A/env_train/bin/python" -u "$REPO_ROOT/scripts/method_a_new_delivery/train_ignore.py" --dataset "$DATA" --init "$R/weights/rfdetr(2xl)_best_plane.pth" --out "$OUT" --steps 2400 --time-budget-min 21 "${RESUME[@]}"
cat "$OUT/status.json"

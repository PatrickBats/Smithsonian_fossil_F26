#!/bin/bash
# Method A held-out-new-scan cross-validation, COCO init, A4 recipe (2,400 steps), one fold after another.
# Usage: run_cv_queue.sh <fold> [<fold> ...]   (run two queues side by side at most)
set -uo pipefail
R=~/Smithsonian_F26; PY=$R/model_A/env_train/bin/python; SC=$R/model_A/scripts
CV=$R/from_nots/yunfan_new_delivery/training/cross_validation
W=$R/model_A/runs/A4_cv_cocoinit
export NO_ALBUMENTATIONS_UPDATE=1 MPLCONFIGDIR=$W/.mpl TORCH_HOME=$W/.torch
cd $SC
for K in "$@"; do
  OUT=$W/fold_$K; EV=$W/eval_fold_$K
  echo "=== fold $K start $(date)"
  if [ -f $OUT/status.json ] && grep -q '"completed"' $OUT/status.json; then echo "[skip train] done"; else
    if [ -f $OUT/resume.ckpt ]; then RES="--resume $OUT/resume.ckpt"; else RES=""; rm -rf $OUT; fi
    $PY -u train_ignore.py --dataset $CV/fold_$K --init $R/weights/rf-detr-xxlarge.pth --out $OUT $RES || { echo "fold $K TRAIN FAILED"; continue; }
  fi
  if [ -f $EV/summary.json ]; then echo "[skip eval] done"; else
    $PY -u cv_eval_local.py --fold $K --checkpoint $OUT/checkpoint_final_ema.pth --out $EV || echo "fold $K EVAL FAILED"
  fi
  echo "=== fold $K end $(date)"
done
echo "QUEUE DONE $(date)"

#!/bin/bash
# Retrain last semester's 2XL focus-stack detector on old+new data (split_v2).
# Hyperparameters = args stored in weights/rfdetr(2xl)_focus_stack.pth (Optuna trial 2);
# only change: 1 GPU, batch B x accum A with B*A = 16 (= their 4 x 2 x 2 GPUs).
# Usage: run_detector_v2.sh <run_name> [coco_dir] [epochs] [batch] [accum]
set -o pipefail
R=~/Smithsonian_F26
RUN=$1; COCO=${2:-$R/processed/coco_detector_v2/combined}; EP=${3:-50}; B=${4:-2}; A=${5:-8}
OUT=$R/model_A/detector_v2/runs/$RUN; mkdir -p $OUT
cd $R/model_A/code_sp26
export PYTHONUNBUFFERED=1
[ -f $OUT/last.ckpt ] && export RESUME=$OUT/last.ckpt && echo "resuming from $RESUME"
if [ -n "$RESUME" ]; then
  export RFDETR_BEST_EMA_INIT=$($R/model_A/env_train/bin/python -c "
import glob, pandas as pd
v=[pd.read_csv(f)['val/ema_mAP_50_95'].max() for f in glob.glob('$OUT/metrics.csv')+glob.glob('$OUT/pre_resume_*/metrics.csv')]
print(max(x for x in v if x==x))")
  echo "seeding best EMA mAP50:95 = $RFDETR_BEST_EMA_INIT" | tee -a $OUT/launch.log
fi
echo "start $(date) run=$RUN coco=$COCO epochs=$EP batch=$B accum=$A" | tee -a $OUT/launch.log
nvidia-smi --query-gpu=name,memory.used --format=csv,noheader | tee -a $OUT/launch.log
$R/model_A/env_train/bin/python -m src.models.rfdetr.train \
  --model 2xlarge --coco_dir $COCO --epochs $EP --batch_size $B --grad_accum $A \
  --lr 0.000241271255870358 --lr_scheduler cosine --lr_min_factor 0.07158449221851396 \
  --warmup_epochs 2 --weight_decay 0.05865951711236849 --imgsz 1000 --workers 8 \
  --early_stopping_patience 10 --drop_path 0.3215124490813669 --aug_config custom \
  --aug_json '{"Rotate":{"p":0.7133940334540116},"RandomBrightnessContrast":{"p":0.5438787210449781},"HueSaturationValue":{"p":0.36040305583071647}}' \
  --pretrain_weights $R/weights/rf-detr-xxlarge.pth \
  --output_dir $OUT
echo "exit $? $(date)" | tee -a $OUT/launch.log

#!/bin/bash
# A6: detector-first, leak-free. Stage 1 trains a one-class pollen detector from COCO weights on the
# training tiles (sponsor labels + ignore-region boxes all as "pollen"). Stage 2 is the A4 recipe
# (28 classes + ignore regions) initialised from stage 1 with the pollen row seeded into every class.
set -uo pipefail
cd ~/Smithsonian_F26/model_A/scripts
R=$HOME/Smithsonian_F26; PY=$R/model_A/env_train/bin/python
D=$R/model_A/runs/A4_ignore_springinit_20261021_debug/data
S1=$R/model_A/runs/A6_oneclass_stage1
export MPLCONFIGDIR=$S1/.mpl TORCH_HOME=$S1/.torch NO_ALBUMENTATIONS_UPDATE=1
mkdir -p $S1/logs
done_() { [ -f "$1/status.json" ] && grep -q '"completed"' "$1/status.json"; }
{
date; echo "=== stage 1a: one-class dataset"
[ -f $S1/data/oneclass_summary.json ] || $PY make_oneclass_dataset.py --src $D --out $S1/data
echo "=== stage 1b: smoke"
if ! done_ $S1/smoke; then rm -rf $S1/smoke; $PY -u train_ignore.py --one-class --dataset $S1/data --init $R/weights/rf-detr-xxlarge.pth --out $S1/smoke --smoke --num-workers 8; fi
echo "=== stage 1c: train one-class detector (2,400 steps)"
if ! done_ $S1/train; then
  if [ -f $S1/train/resume.ckpt ]; then RES="--resume $S1/train/resume.ckpt"; else RES=""; rm -rf $S1/train; fi
  $PY -u train_ignore.py --one-class --dataset $S1/data --init $R/weights/rf-detr-xxlarge.pth --out $S1/train $RES --num-workers 8
fi
cat $S1/train/status.json
} >> $S1/logs/stage1.log 2>&1
done_ $S1/train || { echo "stage 1 failed"; exit 1; }
echo "=== stage 1d: which head row does the one-class detector fire on? (must be 0 for --pollen-row 0)"
$PY - <<P >> $S1/logs/stage1.log 2>&1
import json, glob, collections
from PIL import Image
from rfdetr_plus.models.detection import RFDETR2XLarge
m = RFDETR2XLarge(pretrain_weights="$S1/train/checkpoint_final_ema.pth", num_classes=1, resolution=1000)
hist = collections.Counter(); n = 0
for f in sorted(glob.glob("$S1/data/train/*.png"))[:40]:
    d = m.predict(Image.open(f).convert("RGB"), threshold=0.3); hist.update(int(c) for c in d.class_id); n += len(d.class_id)
print("stage1 pred_class_id_hist:", dict(hist), "detections:", n)
json.dump(dict(pred_class_id_hist=dict(hist), detections=n, tiles=40), open("$S1/fired_rows.json", "w"))
assert n > 50 and set(hist) == {0}, hist
P
grep -q "pred_class_id_hist: {0:" $S1/logs/stage1.log || { echo "stage 1 fired on an unexpected row; see $S1/logs/stage1.log"; exit 1; }
echo "=== stage 2: A4 recipe from the stage-1 detector"
mkdir -p ../runs/A6_detfirst
INIT=$S1/train/checkpoint_final_ema.pth bash run_local.sh A6_detfirst $D "--pollen-row 0 --num-workers 8" >> ../runs/A6_detfirst/nohup.out 2>&1
echo "A6 queue done $(date)"

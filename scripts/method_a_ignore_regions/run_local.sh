#!/bin/bash
# Method A attempt 4 on a local GPU box (tested: RTX 5090 under WSL2 Ubuntu). Same stages as
# run.sbatch without SLURM: pseudo-label -> smoke train -> full train -> eval.
# Expects the NOTS layout mirrored under $R (defaults to ~/Smithsonian_F26):
#   processed/method_a_sparse_labels_20261017/datasets/m2_retile_all   (A3 tiles, symlinks resolved)
#   processed/method_a_focus_stack_v1/{plan,inputs,dataset/valid,dataset/*.json}
#   weights/rfdetr(2xl)_best_plane.pth  weights/rf-detr-xxlarge.pth
#   model_A/env_train  (venv with the same pins as NOTS: torch 2.10 cu128, rfdetr 1.6.4, rfdetr-plus 1.0.2)
# Usage: bash run_local.sh <run_name> [dataset_dir] [extra train args]
#   dataset_dir omitted -> pseudo-label A3 into $W/data (or reuse it if present)
#   INIT=... overrides the training init (default: COCO rf-detr-xxlarge.pth)
set -euo pipefail
NAME=$1; DS=${2:-}; EXTRA=${3:-}
R=${R:-$HOME/Smithsonian_F26}
PY=$R/model_A/env_train/bin/python
A3=$R/processed/method_a_sparse_labels_20261017/datasets/m2_retile_all
BASE=$R/processed/method_a_focus_stack_v1
DET="$R/weights/rfdetr(2xl)_best_plane.pth"          # pseudo-labeler only
INIT="${INIT:-$R/weights/rf-detr-xxlarge.pth}"       # training init
W=$R/model_A/runs/$NAME
SCRIPTS=$(cd "$(dirname "$0")" && pwd)
mkdir -p $W/logs
export MPLCONFIGDIR=$W/.mpl TORCH_HOME=$W/.torch NO_ALBUMENTATIONS_UPDATE=1
cd $SCRIPTS
exec > >(tee -a $W/logs/run_local_$(date +%Y%m%d_%H%M%S).log) 2>&1
date; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
$PY -c "import importlib.metadata as m, torch; print('rfdetr', m.version('rfdetr'), 'rfdetr-plus', m.version('rfdetr-plus'), 'torch', torch.__version__, 'cuda', torch.version.cuda)"
done_() { [ -f "$1/status.json" ] && grep -q '"completed"' "$1/status.json"; }

echo "=== 1. pseudo-labels"
if [ -n "$DS" ]; then DATA=$DS; echo "reusing $DATA"; else
  DATA=$W/data
  if [ -f $DATA/ignore_labels_summary.json ]; then echo "[skip] exists"; else
    rm -rf $DATA; $PY -u make_ignore_labels.py --dataset $A3 --detector "$DET" --out $DATA; fi
fi
$PY -c "import json;s=json.load(open('$DATA/ignore_labels_summary.json'));print({k:v for k,v in s.items() if k!='per_tile'})"

echo "=== 2. smoke train (2 optimizer steps; checks head size, ignore mask, memory)"
if done_ $W/smoke; then echo "[skip] done"; else
  rm -rf $W/smoke; $PY -u train_ignore.py --dataset $DATA --init "$INIT" --out $W/smoke --smoke $EXTRA; fi
$PY -c "
import json; c=json.load(open('$W/smoke/run_contract.json')); p=json.load(open('$W/smoke/progress.json'))
print('init_head:', c['init_head']); assert c['ignore_label']==28, c
assert p['ignore_hits_last_batch'], p; print('ignore mask active, hits last batch:', p['ignore_hits_last_batch'])"

echo "=== 3. full train (2,400 optimizer steps)"
if done_ $W/train; then echo "[skip] done"; else
  rm -rf $W/train; $PY -u train_ignore.py --dataset $DATA --init "$INIT" --out $W/train $EXTRA; fi
cat $W/train/status.json

echo "=== 4. evaluate (unchanged 1,432-tile grid)"
if done_ $W/eval; then echo "[skip] done"; else
  rm -rf $W/eval; $PY -u evaluate_run.py --run $W/train --baseline $BASE --out $W/eval; fi
echo "---- summary ----"
$PY -c "
import json,glob
for f in sorted(glob.glob('$W/eval/full_confidence_*_summary.json')):
    s=json.load(open(f)); print(f.split('/')[-1], {k:s.get(k) for k in ['detected','end_to_end_correct','classification_accuracy_on_matched','unmatched_prediction_count']})"
date

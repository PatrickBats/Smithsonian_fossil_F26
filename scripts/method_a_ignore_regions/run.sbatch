#!/bin/bash
#SBATCH --job-name=a4-ignore-springinit
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=06:00:00
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A4_ignore_springinit_20261021/logs/run_%j.out
#SBATCH --error=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A4_ignore_springinit_20261021/logs/run_%j.err
# A4: A3 recipe + init from Spring one-class detector + ignore regions + flip/rot90 aug.
# full pseudo-label -> full train (2,400 steps) -> eval on the 1,432-tile grid.
# Resubmittable: completed stages are skipped. Requires debug.sbatch to have passed first.
set -euo pipefail
R=/rhf/allocations/dsci435/Smithsonian_F26
PY=$R/model_A/env_train/bin/python
A3=$R/processed/method_a_sparse_labels_20261017/datasets/m2_retile_all
BASE=$R/processed/method_a_focus_stack_v1
DET="$R/weights/rfdetr(2xl)_best_plane.pth"
W=$R/model_A/runs/A4_ignore_springinit_20261021
export MPLCONFIGDIR=$W/.mpl TORCH_HOME=$W/.torch PYTORCH_KERNEL_CACHE_PATH=/tmp/$USER-kc-$SLURM_JOB_ID NO_ALBUMENTATIONS_UPDATE=1
cd $W/scripts
date; nvidia-smi --query-gpu=name,memory.total --format=csv
$PY -c "import importlib.metadata as m, torch; print('rfdetr', m.version('rfdetr'), 'rfdetr-plus', m.version('rfdetr-plus'), 'torch', torch.__version__)"
$PY -c "import json;c=json.load(open('$W/smoke/run_contract.json'));assert c['init_head']['seeded'] and c['ignore_label']==28, c['init_head']; print('smoke contract ok, pollen_row', c['init_head']['pollen_row'])"

done_() { [ -f "$1/status.json" ] && grep -q '"completed"' "$1/status.json"; }

echo "=== 1. full pseudo-labeling pass"
if [ -f $W/data/ignore_labels_summary.json ]; then echo "[skip] exists"; else
  rm -rf $W/data
  $PY -u make_ignore_labels.py --dataset $A3 --detector "$DET" --out $W/data
fi
$PY -c "import json;s=json.load(open('$W/data/ignore_labels_summary.json'));print({k:v for k,v in s.items() if k!='per_tile'})"

echo "=== 2. full train"
if done_ $W/train; then echo "[skip] done"; else
  rm -rf $W/train
  $PY -u train_ignore.py --dataset $W/data --init "$DET" --out $W/train
fi
cat $W/train/status.json

echo "=== 3. evaluate (unchanged 1,432-tile grid)"
if done_ $W/eval; then echo "[skip] done"; else
  rm -rf $W/eval
  $PY -u evaluate_run.py --run $W/train --baseline $BASE --out $W/eval
fi
echo "---- summary (confidence 0.5, full grid) ----"
$PY -c "import json;s=json.load(open('$W/eval/summary.json'));print(json.dumps({k:s[k] for k in ['detected','end_to_end_correct','known_specimen_recall_iou50','classification_accuracy_on_matched','end_to_end_known_specimen_success','unmatched_prediction_count']},indent=2))"
echo "=== RUN OK"; date

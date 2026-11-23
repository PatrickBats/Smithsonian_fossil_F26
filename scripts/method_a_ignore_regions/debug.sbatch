#!/bin/bash
#SBATCH --job-name=a4-ignore-debug
#SBATCH --account=commons
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=00:30:00
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A4_ignore_cocoinit/logs/debug_%j.out
#SBATCH --error=/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A4_ignore_cocoinit/logs/debug_%j.err
# A4 debug: pseudo-label 40 tiles, 2-step smoke train, 2-tile smoke eval.
set -euo pipefail
R=/rhf/allocations/dsci435/Smithsonian_F26
PY=$R/model_A/env_train/bin/python
A3=$R/processed/method_a_sparse_labels_20261017/datasets/m2_retile_all
BASE=$R/processed/method_a_focus_stack_v1
DET="$R/weights/rfdetr(2xl)_best_plane.pth"   # pseudo-labeler only
INIT="${INIT:-$R/weights/rf-detr-xxlarge.pth}"   # training init: COCO RF-DETR-2XL by default; export INIT=... to override
W=${W:-$R/model_A/runs/A4_ignore_cocoinit}
export MPLCONFIGDIR=$W/.mpl TORCH_HOME=$W/.torch PYTORCH_KERNEL_CACHE_PATH=/tmp/$USER-kc-$SLURM_JOB_ID NO_ALBUMENTATIONS_UPDATE=1
cd $W/scripts
date; nvidia-smi --query-gpu=name,memory.total --format=csv
$PY -c "import importlib.metadata as m, torch; print('rfdetr', m.version('rfdetr'), 'rfdetr-plus', m.version('rfdetr-plus'), 'torch', torch.__version__)"

rm -rf $W/data_debug $W/smoke $W/smoke_eval
echo "=== 1. pseudo-label 40 tiles"
$PY -u make_ignore_labels.py --dataset $A3 --detector "$DET" --out $W/data_debug --limit 40
echo "=== 2. smoke train (2 optimizer steps)"
$PY -u train_ignore.py --dataset $W/data_debug --init "$INIT" --out $W/smoke --smoke
$PY - <<EOF
import json
c = json.load(open("$W/smoke/run_contract.json"))
print("init_head:", json.dumps(c["init_head"]))
print("ignore_label:", c["ignore_label"], " train_images:", c["train_images"])
s = json.load(open("$W/data_debug/ignore_labels_summary.json"))
print("pred_class_id_hist:", s["pred_class_id_hist"])
# COCO init has a 91-row head, so no one-class seeding happens; the Spring init seeds and must match the fired row.
assert c["ignore_label"] == 28
rows = [k for k, v in s["pred_class_id_hist"].items() if v > 0]
if c["init_head"]["seeded"]:
    assert rows == [str(c["init_head"]["pollen_row"])], (rows, c["init_head"]["pollen_row"])
p = json.load(open("$W/smoke/progress.json"))
assert p["ignore_hits_last_batch"] is not None and p["ignore_hits_last_batch"] > 0, p
print("OK: init head checked; ignore mask active (hits last batch: %d)" % p["ignore_hits_last_batch"])
EOF
cat $W/smoke/progress.json
echo "=== 3. smoke eval (2 positive tiles)"
$PY -u evaluate_run.py --run $W/smoke --baseline $BASE --out $W/smoke_eval --smoke
cat $W/smoke_eval/summary.json
echo "=== DEBUG OK"; date

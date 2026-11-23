#!/bin/bash
# Submit the A4 pipeline as a dependency chain on the NOTS `debug` partition (30-min wall, 1 running job/user).
# Usage: [INIT=/path/to/init.pth] bash chain_debug.sh <run_name> <dataset_dir|LABEL> [extra train args]
#   INIT defaults to the COCO RF-DETR-2XL weights; set INIT to the Spring one-class detector for the Spring-init variant.
#   dataset_dir = LABEL  -> stage 0 pseudo-labels A3 into $W/data first (A4 itself)
#   dataset_dir = path   -> reuse an existing dataset (ablations)
set -euo pipefail
NAME=$1; DS=$2; EXTRA=${3:-}
R=/rhf/allocations/dsci435/Smithsonian_F26
INIT=${INIT:-$R/weights/rf-detr-xxlarge.pth}
W=$R/model_A/runs/${NAME}
SRC=${SRC:-$(cd "$(dirname "$0")" && pwd)}
mkdir -p $W/logs $W/scripts; cp $SRC/*.py $W/scripts/
[ "$DS" = LABEL ] && DATA=$W/data || DATA=$DS

hdr() { cat <<H
#!/bin/bash
#SBATCH --job-name=$1
#SBATCH --account=commons
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=00:30:00
#SBATCH --output=$W/logs/$2_%j.out
#SBATCH --error=$W/logs/$2_%j.err
set -euo pipefail
R=$R
PY=\$R/model_A/env_train/bin/python
A3=\$R/processed/method_a_sparse_labels_20261017/datasets/m2_retile_all
BASE=\$R/processed/method_a_focus_stack_v1
DET="\$R/weights/rfdetr(2xl)_best_plane.pth"   # pseudo-labeler only
INIT="$INIT"
W=$W
DATA=$DATA
export MPLCONFIGDIR=\$W/.mpl TORCH_HOME=\$W/.torch PYTORCH_KERNEL_CACHE_PATH=/tmp/\$USER-kc-\$SLURM_JOB_ID NO_ALBUMENTATIONS_UPDATE=1
cd \$W/scripts; date; nvidia-smi --query-gpu=name --format=csv,noheader
done_() { [ -f "\$1/status.json" ] && grep -q '"completed"' "\$1/status.json"; }
H
}

# stage 0: pseudo-label (A4 only)
if [ "$DS" = LABEL ]; then
  { hdr ${NAME}-label label; cat <<'B'
if [ -f $W/data/ignore_labels_summary.json ]; then echo "[skip] labels exist"; else
  rm -rf $W/data; $PY -u make_ignore_labels.py --dataset $A3 --detector "$DET" --out $W/data; fi
$PY -c "import json;s=json.load(open('$W/data/ignore_labels_summary.json'));print({k:v for k,v in s.items() if k!='per_tile'})"
date
B
  } > $W/scripts/label.sbatch
  DEP=$(sbatch --parsable $W/scripts/label.sbatch); echo "label: $DEP"
  DEPARG="--dependency=afterok:$DEP"
else
  DEPARG=""
fi

# stages 1-4: train chunks (each resumes if resume.ckpt exists, skips if completed)
{ hdr ${NAME}-train train; cat <<B
if done_ \$W/train; then echo "[skip] train done"; exit 0; fi
if [ -f \$W/train/resume.ckpt ]; then RES="--resume \$W/train/resume.ckpt"; else RES=""; rm -rf \$W/train; fi
\$PY -u train_ignore.py --dataset \$DATA --init "\$INIT" --out \$W/train --time-budget-min 21 \$RES $EXTRA
cat \$W/train/status.json; date
B
} > $W/scripts/train.sbatch
for i in 1 2 3 4; do  # afterany: a chunk that hits the wall before saving must not break the chain
  DEP=$(sbatch --parsable $DEPARG $W/scripts/train.sbatch); echo "train chunk $i: $DEP"; DEPARG="--dependency=afterany:$DEP"
done

# stage 5: eval
{ hdr ${NAME}-eval eval; cat <<'B'
done_ $W/train || { echo "train not completed"; exit 1; }
if done_ $W/eval; then echo "[skip] eval done"; else rm -rf $W/eval; $PY -u evaluate_run.py --run $W/train --baseline $BASE --out $W/eval; fi
$PY -c "import json;c=json.load(open('$W/train/run_contract.json'));print('init_head',c['init_head']);print('ignore_label',c['ignore_label'],'chunks',len(c['chunks']))"
$PY -c "import json;s=json.load(open('$W/eval/summary.json'));print(json.dumps({k:s[k] for k in ['detected','end_to_end_correct','known_specimen_recall_iou50','classification_accuracy_on_matched','unmatched_prediction_count']},indent=2))"
echo "=== CHAIN OK"; date
B
} > $W/scripts/eval.sbatch
DEP=$(sbatch --parsable $DEPARG $W/scripts/eval.sbatch); echo "eval: $DEP"
squeue -u acy3 -o "%i %j %P %T %E"

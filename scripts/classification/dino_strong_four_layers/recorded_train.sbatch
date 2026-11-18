#!/bin/bash
#SBATCH --job-name=yt70-dino-aug
#SBATCH --partition=commons
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=40G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=02:00:00
set -euo pipefail
umask 022
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4
CODE=/home/yt70/Smithsonian/experiments/dino_followup_20261117
RUN=/rhf/allocations/dsci435/Smithsonian_F26/model_B/runs/dino_followup_20261117
BASE=/rhf/allocations/dsci435/Smithsonian_F26
PY=$BASE/model_A/env_train/bin/python
TMPBASE=${SLURM_TMPDIR:-/tmp}
STAGE=$(mktemp -d "$TMPBASE/yt70-dino-aug-${SLURM_JOB_ID}-XXXXXX")
cleanup() {
  # Only the freshly created, job-specific staging directory is removable.
  case "$STAGE" in "$TMPBASE"/yt70-dino-aug-"${SLURM_JOB_ID}"-*) rm -rf -- "$STAGE";; *) return 1;; esac
}
trap cleanup EXIT
export TORCH_HOME="$STAGE/torch"
export DINO_SOURCE="$CODE/external/dinov2"
cd "$CODE"
"$PY" verify_source.py
echo "15a4985e191c215e7c8e915ad2903b3d289171f98887f775f770aa910aa337db  $BASE/software_review_2026-10-20/classifier_inputs.tar.gz" | sha256sum -c -
tar -xzf "$BASE/software_review_2026-10-20/classifier_inputs.tar.gz" -C "$STAGE"
INPUT="$STAGE/classifier_inputs"
BASELINE="$BASE/runs/broad_dino_2026-10-08/separate_slides/backbone_finetune"
mkdir -p "$TORCH_HOME/hub/checkpoints"
cp "$BASE/model_B/runs/dino_hierarchical_20261115/initialization/hub/checkpoints/dinov2_vitb14_pretrain.pth" "$TORCH_HOME/hub/checkpoints/"
echo "0b8b82f85de91b424aded121c7e1dcc2b7bc6d0adeea651bf73a13307fad8c73  $TORCH_HOME/hub/checkpoints/dinov2_vitb14_pretrain.pth" | sha256sum -c -
POLICY="$1"
case "$POLICY" in geometry) AUG=geometry; N=2; LR=0.00001;; four_layers) AUG=strong; N=4; LR=0.000005;; *) exit 2;; esac
for POLICY in "$POLICY"; do
  "$PY" -u -m method_b.classification.train_dinov2 \
    --data "$INPUT/dataset" --assignments "$BASELINE/record_assignments.csv" \
    --categories "$BASELINE/category_map.csv" --broad-map "$BASELINE/fine_to_broad.csv" \
    --output "$RUN/$POLICY" --augmentation "$AUG" --unfreeze-last "$N" --backbone-lr "$LR" \
    --epochs 40 --head-epochs 3 --batch-size 32 --seed 20261007
done
"$PY" -u compare_validation.py --run "$RUN" --policy "$POLICY"
echo "Paired training and expert-crop validation comparison complete."

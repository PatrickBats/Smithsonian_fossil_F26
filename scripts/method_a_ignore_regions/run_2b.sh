#!/bin/bash
# Method A 2b: Yunfan's new-delivery training crops, ignore boxes regenerated with the retrained
# detector (detector_v2 best epoch), COCO init, A4 recipe. Same eval as 2a.
set -euo pipefail
R=~/Smithsonian_F26; P=$R/processed/method_a_new_delivery/training
DET=$R/model_A/detector_v2/runs/dv2_2xl_focus_20261119/checkpoint_best_total.pth
OUT=$P/dataset_ignore_dv2
cd $R/model_A/scripts
if [ ! -f $OUT/ignore_labels_summary.json ]; then
  rm -rf $OUT
  $R/model_A/env_train/bin/python -u make_ignore_labels.py --dataset $P/dataset_base_noignore_pc --detector $DET --out $OUT
fi
exec bash run_local.sh A4_newdeliv_cocoinit_2b $OUT

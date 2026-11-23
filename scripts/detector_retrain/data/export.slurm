#!/bin/bash
#SBATCH --job-name=dv2-export
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/detector_v2/logs/export_%j.out
set -e
cd /rhf/allocations/dsci435/Smithsonian_F26/model_A/code
PY=/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python
OUT=/rhf/allocations/dsci435/Smithsonian_F26/processed/coco_detector_v2
H5=${H5:-/rhf/allocations/dsci435/Smithsonian_F26/processed/detector_v2_tiles}
TAG=${TAG:-}
$PY -u -m src.preprocessing.export_coco --h5_root $H5 --output_dir $OUT/new_main$TAG --mode focus_stack --splits_json /rhf/allocations/dsci435/Smithsonian_F26/model_A/detector_v2/export_main_splits.json --workers 16 --image_format jpeg --single_cls --filter_bboxes 2>&1 | grep -v coercing
$PY -u -m src.preprocessing.export_coco --h5_root $H5 --output_dir $OUT/new_recall$TAG --mode focus_stack --splits_json /rhf/allocations/dsci435/Smithsonian_F26/model_A/detector_v2/export_recall_splits.json --workers 16 --image_format jpeg --single_cls --filter_bboxes 2>&1 | grep -v coercing
echo EXPORT_DONE

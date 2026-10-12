#!/bin/bash
#SBATCH --job-name=yt70-rfswin-train
#SBATCH --partition=commons
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=1-00:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
set -euo pipefail
code="$HOME/Smithsonian/scripts/pipeline_abbas_v1"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=2
export NO_ALBUMENTATIONS_UPDATE=1
py=/rhf/allocations/dsci435/Smithsonian_F26/model_A/env_train/bin/python
"$py" -B -c 'from rfdetr.training import RFDETRDataModule, RFDETRModelModule, build_trainer; print("Training dependency check passed", flush=True)'
"$py" -u "$code/train_pipeline_detector.py" --config "$code/pipeline_config.json" --smoke
"$py" -u "$code/evaluate_pipeline.py" --config "$code/pipeline_config.json" --smoke
"$py" -u "$code/train_pipeline_detector.py" --config "$code/pipeline_config.json"
"$py" -u "$code/evaluate_pipeline.py" --config "$code/pipeline_config.json"

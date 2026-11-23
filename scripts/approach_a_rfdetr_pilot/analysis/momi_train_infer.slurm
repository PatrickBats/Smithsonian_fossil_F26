#!/bin/bash
#SBATCH --job-name=momi-q4
#SBATCH --account=commons
#SBATCH --partition=commons
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --gres=gpu:lovelace:1
#SBATCH --time=00:30:00
#SBATCH --output=/rhf/allocations/dsci435/Smithsonian_F26/model_A/analysis/momi_q4_%j.out
B=/rhf/allocations/dsci435/Smithsonian_F26/model_A
export MPLCONFIGDIR=$B/analysis/.mpl
$B/env_train/bin/python -u $B/analysis/momi_train_infer.py cuda

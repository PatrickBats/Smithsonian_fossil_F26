"""NOTS paths for this run; output roots may be overridden for a new run."""

import os
from pathlib import Path


def configured(name, default):
    return Path(os.environ.get(name, default))


SOURCE = configured(
    "METHOD_A_NEW_SOURCE",
    "/rhf/allocations/dsci435/smithsonian_full_sp26/new files/New_train_set_detection_model_rice",
)
PREP = configured(
    "METHOD_A_NEW_PREP",
    "/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_new_delivery",
)
TRAINING = PREP / "training"
A3 = configured(
    "METHOD_A_A3_DATASET",
    "/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_sparse_labels_20261017/datasets/m2_retile_all",
)
RUNS = configured(
    "METHOD_A_NEW_RUNS",
    "/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs/A4_new_delivery_20261113",
)
RESULTS = configured(
    "METHOD_A_NEW_RESULTS",
    "/projects/dsci435/Smithsonian_F26/method_a/new_delivery/runs/results",
)
MAPS = Path(__file__).resolve().parents[2] / "data" / "current" / "new_delivery_maps"

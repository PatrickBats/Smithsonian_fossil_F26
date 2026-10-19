"""Method A data variants and paths. Historical run IDs stay unchanged on disk."""

import hashlib
import json
import os
from pathlib import Path

_BASE_RHF = Path("/rhf/allocations/dsci435/Smithsonian_F26")
_BASE_PROJECTS = Path("/projects/dsci435/Smithsonian_F26")
BASE = Path(
    os.environ.get("METHOD_A_BASELINE_ROOT", _BASE_RHF / "processed/method_a_focus_stack_v1")
)
ROOT = Path(
    os.environ.get("METHOD_A_DATA_ROOT", _BASE_RHF / "processed/method_a_sparse_labels_20261017")
)
CODE = Path(os.environ.get("METHOD_A_CODE_ROOT", Path(__file__).resolve().parent))
LOGS = Path(
    os.environ.get("METHOD_A_LOG_ROOT", _BASE_PROJECTS / "runs/method_a_sparse_labels_20261017")
)
RESULTS = Path(
    os.environ.get(
        "METHOD_A_RESULTS_ROOT", _BASE_PROJECTS / "results/method_a_sparse_labels_20261017"
    )
)
WEIGHTS = Path(
    os.environ.get("METHOD_A_PRETRAINED_WEIGHTS", _BASE_RHF / "weights/rf-detr-xxlarge.pth")
)
WEIGHT_SHA = "bf418652d5e07ad441599acfadc65bb1767029079e7a343a6d61675ec5d553ae"
SEED = 20261013

# These are three data treatments of Method A, all using the same RF-DETR 2XL.
# Preserve the recorded directory IDs so existing artifacts and hashes still resolve.
VARIANTS = {
    "A1": {"experiment": "m1_positive_grid", "name": "Positive ROI grid tiles"},
    "A2": {"experiment": "m2_retile_matched", "name": "Context crops, original-coverage anchors"},
    "A3": {"experiment": "m2_retile_all", "name": "Context crops, all training anchors"},
}
EXPERIMENTS = tuple(value["experiment"] for value in VARIANTS.values())


def resolve_variant(value):
    """Accept public A1/A2/A3 names or the original recorded experiment IDs."""
    if value.upper() in VARIANTS:
        return VARIANTS[value.upper()]["experiment"]
    if value in EXPERIMENTS:
        return value
    raise ValueError("Choose Method A data variant A1, A2 or A3.")


def variant_id(experiment):
    return next(key for key, value in VARIANTS.items() if value["experiment"] == experiment)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    """Write owned metadata atomically, confined to the configured output roots.

    Validate resolved parents before creating anything. Dataset image links are
    read-only inputs and must never be accepted as metadata destinations.
    """
    path = Path(path).absolute()
    roots = (ROOT, CODE, LOGS, RESULTS)
    parent = path.parent.resolve()
    if not any(parent.is_relative_to(root.resolve()) for root in roots):
        raise ValueError(f"Metadata destination is outside configured output roots: {path}")
    if path.is_symlink():
        raise PermissionError(f"Refusing to overwrite a symlink: {path}")
    if path.exists() and path.stat().st_uid != os.getuid():
        raise PermissionError(f"Refusing to overwrite another owner's file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    created = False
    try:
        with temporary.open("x") as stream:
            created = True
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
        temporary.replace(path)
    finally:
        if created:
            temporary.unlink(missing_ok=True)


def load(path):
    return json.loads(Path(path).read_text())

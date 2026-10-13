"""Train F26 Method A as a 28-class RF-DETR 2XL on LoG-fused tiles."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import time

from focus_helpers import sha256_file


DATA = Path("/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_focus_stack_v1/dataset")
RUNS = Path("/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_focus_stack_v1/run_artifacts")
PRETRAINED = Path("/rhf/allocations/dsci435/Smithsonian_F26/weights/rf-detr-xxlarge.pth")
EXPECTED_PRETRAINED_SHA = "bf418652d5e07ad441599acfadc65bb1767029079e7a343a6d61675ec5d553ae"
SEED = 20261013


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    import torch
    from rfdetr_plus.models.detection import RFDETR2XLarge

    if importlib.metadata.version("rfdetr") != "1.6.4" or not torch.cuda.is_available():
        raise RuntimeError("Expected reviewed RF-DETR 1.6.4 and a Slurm GPU")
    if sha256_file(PRETRAINED) != EXPECTED_PRETRAINED_SHA:
        raise ValueError("Generic RF-DETR 2XL pretrained weights changed")
    summary_path = DATA / "dataset_summary.json"
    summary = json.loads(summary_path.read_text())
    if (summary["status"] != "verified_shared_grid_28_class_sparse_label_dataset"
            or summary["assignment_sha256"] != "da2062a127cf6e14945e50fff097e0db102d7f8203250b47daed6b6bb166478d"
            or summary["fine_to_broad_sha256"] != "a2f8da0b40cf9a1a89ea7fffe360770b2b9eae56f9fdd307bbf1b286bd9f793d"):
        raise ValueError("Dataset does not match shared Method B protocol")
    if not args.smoke:
        smoke_status = RUNS / "smoke/status.json"
        if not smoke_status.is_file() or json.loads(smoke_status.read_text()).get("status") != "completed":
            raise RuntimeError("One-epoch GPU smoke training has not completed")
    out = RUNS / ("smoke" if args.smoke else "detector")
    out.mkdir(exist_ok=False)
    scratch = Path(os.environ.get("SLURM_TMPDIR") or "/tmp") / f"f26_method_a_focus_{os.environ.get('SLURM_JOB_ID', 'manual')}"
    scratch.mkdir(exist_ok=False)
    os.environ["HF_HOME"] = str(scratch / "hf")
    os.environ["TORCH_HOME"] = str(scratch / "torch")
    os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"
    settings = {
        "dataset_dir": str(DATA), "output_dir": str(out), "epochs": 1 if args.smoke else 40,
        "batch_size": 1, "grad_accum_steps": 16, "num_workers": 2,
        "multi_scale": False, "expanded_scales": False,
        "use_ema": True, "early_stopping": not args.smoke, "early_stopping_patience": 10,
        "tensorboard": False, "wandb": False, "run_test": False, "seed": SEED,
        "checkpoint_interval": 10, "lr": 1e-4, "lr_encoder": 1e-5, "lr_drop": 30,
        "compute_val_loss": True, "log_per_class_metrics": False,
    }
    contract = {
        "model": "RFDETR2XLarge", "num_classes": 28, "resolution": 1000,
        "pretrained_sha256": EXPECTED_PRETRAINED_SHA,
        "dataset_summary_sha256": sha256_file(summary_path),
        "training_settings": settings, "torch_version": torch.__version__,
        "rfdetr_version": importlib.metadata.version("rfdetr"),
        "gpu": torch.cuda.get_device_name(0), "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "metric_scope": "Sparse-label COCO metrics are trainer diagnostics; test is reserved.",
    }
    (out / "run_contract.json").write_text(json.dumps(contract, indent=2) + "\n")
    (out / "status.json").write_text(json.dumps({"status": "training"}) + "\n")
    started = time.time()
    model = RFDETR2XLarge(pretrain_weights=str(PRETRAINED), num_classes=28, resolution=1000)
    model.train(**settings)
    if not (out / "checkpoint_best_total.pth").is_file():
        raise FileNotFoundError("Trainer produced no model checkpoint")
    result = {
        "status": "completed", "smoke": args.smoke,
        "elapsed_seconds": time.time() - started, "max_epochs": settings["epochs"],
        "checkpoint_best_total_sha256": sha256_file(out / "checkpoint_best_total.pth"),
        "test_evaluated": False,
        "warning": "Internal AP uses incomplete scene labels and is not a valid whole-scene quality estimate.",
    }
    (out / "status.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()

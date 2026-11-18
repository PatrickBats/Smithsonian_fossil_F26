"""Frozen-split Swin-Tiny baseline. Training/validation only; no test inference.

Outputs must be outside the repository. Each invocation creates a new run.
"""

# Project implementation: Fall 2026 Smithsonian classifier experiments.
# Model implementations: torchvision Swin-Tiny and Meta DINOv2; see NOTICE.md.

import argparse
import csv
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import traceback

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
import torchvision
from torchvision.models import swin_t, Swin_T_Weights
from method_b.utils.file_io import digest, write_json, source_file, snapshot_package
from method_b.utils.input_validation import verify_inputs
from method_b.classification.crop_dataset import Crops
from method_b.evaluation.classification_metrics import evaluate



















def main(args):
    """Run the documented workflow using its command-line or worker configuration.

    Args:
        args: Parsed command-line configuration.

    Returns:
        None: Writes workflow outputs or prints validation status; failures propagate.
    """
    root = Path(args.data).resolve()
    out = Path(args.output).resolve()
    repo = Path(__file__).resolve().parents[2]
    if out.is_relative_to(repo):
        raise ValueError("Run artifacts must stay outside Git")
    out.mkdir(parents=True, exist_ok=False)
    started = time.time()
    try:
        config = vars(args).copy()
        config.update(
            {
                "model": "torchvision.swin_t",
                "weights": "IMAGENET1K_V1",
                "sampling": "ordinary_shuffle_all_training_records",
                "loss": "unweighted_cross_entropy",
                "augmentations": "random_quarter_turn_and_horizontal_flip_train_only",
                "input_size": 224,
                "head_lr": 0.001,
                "finetune_backbone_lr": 0.00001,
                "finetune_head_lr": 0.0001,
                "weight_decay": 0.01,
                "selection": "validation_macro_f1_over_31_present_categories",
                "test_inference": False,
                "precision": "float32",
                "balanced_comparison_launched": False,
            }
        )
        write_json(out / "config.json", config)
        torch.set_num_threads(4)
        random.seed(args.seed)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        torch.cuda.manual_seed_all(args.seed)
        torch.backends.cudnn.benchmark = False
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        # Verify the frozen inventory before any image enters model training.
        rows, labels, audit = verify_inputs(root, Path(args.assignments), Path(args.categories))
        if getattr(args, "specimen_split", None):
            from method_b.preprocessing.data_splits import apply_split

            (out / "specimen_split_helper.py").write_bytes(
                source_file("specimen_split.py").read_bytes()
            )
            rows, diagnostic = apply_split(rows, args.specimen_split)
            audit["diagnostic_split"] = diagnostic
            (out / "specimen_split.json").write_bytes(Path(args.specimen_split).read_bytes())
            config["selection"] = "validation_macro_f1_over_32_present_categories"
            config["evaluation_scope"] = (
                "specimen-level diagnostic with shared train/validation slides"
            )
            write_json(out / "config.json", config)
        if getattr(args, "broad_map", None):
            from method_b.preprocessing.category_mapping import apply_broad

            rows, labels, broad_audit = apply_broad(rows, labels, args.broad_map)
            audit["broad_labels"] = broad_audit
            (out / "fine_to_broad.csv").write_bytes(Path(args.broad_map).read_bytes())
            (out / "broad_labels.py").write_bytes(
                source_file("broad_labels.py").read_bytes()
            )
            write_json(out / "broad_category_map.json", dict(enumerate(labels)))
            config["task"] = "28-group broad_v1 exploratory classification"
            config["selection"] = "validation_macro_f1_over_present_broad_categories"
            write_json(out / "config.json", config)
        write_json(out / "data_audit.json", audit)
        trainrows = [r for r in rows if r["split"] == "train"]
        valrows = [r for r in rows if r["split"] == "val"]
        if args.smoke:
            trainrows = [
                r for c in labels for r in [x for x in trainrows if x["sponsor_category"] == c][:2]
            ]
            valrows = [
                r for c in labels for r in [x for x in valrows if x["sponsor_category"] == c][:2]
            ]
        # Augment training crops only; validation retains the recorded RGB pixels.
        train = Crops(root, trainrows, labels, True)
        val = Crops(root, valrows, labels, False)
        gen = torch.Generator().manual_seed(args.seed)
        trainloader = DataLoader(
            train,
            batch_size=args.batch_size,
            shuffle=True,
            num_workers=0,
            generator=gen,
            pin_memory=True,
        )
        valloader = DataLoader(
            val, batch_size=args.batch_size, shuffle=False, num_workers=0, pin_memory=True
        )
        if not torch.cuda.is_available():
            raise RuntimeError("Expected an allocated CUDA GPU")
        device = torch.device("cuda:0")
        weights = Swin_T_Weights.IMAGENET1K_V1
        model = swin_t(weights=weights)
        model.head = nn.Linear(model.head.in_features, len(labels))
        model.to(device)
        weight_path = Path(torch.hub.get_dir()) / "checkpoints" / weights.url.rsplit("/", 1)[1]
        write_json(
            out / "provenance.json",
            {
                "python": sys.version,
                "torch": torch.__version__,
                "torchvision": torchvision.__version__,
                "cuda": torch.version.cuda,
                "gpu_name": torch.cuda.get_device_name(0),
                "gpu_uuid": os.environ.get("CUDA_VISIBLE_DEVICES"),
                "script_sha256": digest(__file__),
                "git_commit": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=repo, text=True
                ).strip(),
                "weights_url": weights.url,
                "weights_sha256": digest(weight_path),
                "run_started_unix": started,
                "execution": "configured execution environment",
            },
        )
        (out / "train_swin_snapshot.py").write_bytes(Path(__file__).read_bytes())
        snapshot_package(out)
        (out / "record_assignments.csv").write_bytes(Path(args.assignments).read_bytes())
        (out / "category_map.csv").write_bytes(Path(args.categories).read_bytes())
        with (out / "environment.txt").open("w") as f:
            subprocess.run([sys.executable, "-m", "pip", "freeze"], stdout=f, check=True)
        best = -1
        best_epoch = None
        optimizer = None
        total_epochs = 2 if args.smoke else args.epochs
        head_epochs = 1 if args.smoke else args.head_epochs
        # Preserve the recorded head-only and backbone fine-tuning schedule.
        for epoch in range(total_epochs):
            ep_start = time.time()
            head_only = epoch < head_epochs
            if epoch in (0, head_epochs):
                for p in model.parameters():
                    p.requires_grad_(not head_only)
                for p in model.head.parameters():
                    p.requires_grad_(True)
                params = (
                    [{"params": model.head.parameters(), "lr": 0.001}]
                    if head_only
                    else [
                        {
                            "params": [
                                p for n, p in model.named_parameters() if not n.startswith("head.")
                            ],
                            "lr": 0.00001,
                        },
                        {"params": model.head.parameters(), "lr": 0.0001},
                    ]
                )
                optimizer = torch.optim.AdamW(params, weight_decay=0.01)
            if head_only:
                model.eval()
                model.head.train()
            else:
                model.train()
            total_loss = 0
            n = 0
            for x, y, _ in trainloader:
                x = x.to(device)
                y = y.to(device)
                optimizer.zero_grad(set_to_none=True)
                logits = model(x)
                loss = nn.functional.cross_entropy(logits, y)
                if not torch.isfinite(loss):
                    raise FloatingPointError("Nonfinite training loss")
                loss.backward()
                nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad], 1.0, error_if_nonfinite=True
                )
                optimizer.step()
                if (
                    not torch.stack([torch.isfinite(p).all() for p in model.parameters()])
                    .all()
                    .item()
                ):
                    raise FloatingPointError("Nonfinite model parameter")
                total_loss += loss.item() * len(y)
                n += len(y)
            result, indices, probs = evaluate(model, valloader, device, labels)
            summary = {
                "epoch": epoch + 1,
                "phase": "head" if head_only else "full_finetune",
                "train_loss": total_loss / n,
                "validation_loss": result["loss"],
                "validation_macro_f1_present": result["macro_f1_present"],
                "validation_balanced_accuracy_present": result["balanced_accuracy_present"],
                "validation_accuracy": result["accuracy"],
                "epoch_seconds": time.time() - ep_start,
                "gpu_peak_memory_bytes": torch.cuda.max_memory_allocated(),
            }
            with (out / "history.jsonl").open("a") as f:
                f.write(json.dumps(summary, allow_nan=False) + "\n")
            print(json.dumps(summary), flush=True)
            # Model selection uses validation macro-F1; the test split stays reserved.
            if result["macro_f1_present"] > best:
                best = result["macro_f1_present"]
                best_epoch = epoch + 1
                state = {
                    "model": model.state_dict(),
                    "optimizer": optimizer.state_dict(),
                    "epoch": epoch + 1,
                    "categories": labels,
                    "config": config,
                    "audit": audit,
                    "validation_metrics": result,
                    "rng_python": random.getstate(),
                    "rng_numpy": np.random.get_state(),
                    "rng_torch": torch.get_rng_state(),
                    "rng_cuda": torch.cuda.get_rng_state_all(),
                    "loader_rng": gen.get_state(),
                }
                tmp = out / "best.pt.part"
                torch.save(state, tmp)
                tmp.replace(out / "best.pt")
                write_json(out / "best_validation_metrics.json", result)
                with (out / "best_validation_predictions.csv").open("w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        ["record_id", "category", "predicted_category", "confidence"]
                        + [f"p_{i}" for i in range(len(labels))]
                    )
                    for i, p in zip(indices, probs):
                        row = valrows[i]
                        prediction = int(np.argmax(p))
                        writer.writerow(
                            [
                                row["record_id"],
                                row["sponsor_category"],
                                labels[prediction],
                                p[prediction],
                            ]
                            + p
                        )
            write_json(
                out / "status.json",
                {
                    "status": "running",
                    "completed_epochs": epoch + 1,
                    "best_epoch": best_epoch,
                    "best_validation_macro_f1_present": best,
                    "test_evaluated": False,
                },
            )
        write_json(
            out / "status.json",
            {
                "status": "complete",
                "epochs": total_epochs,
                "best_epoch": best_epoch,
                "best_validation_macro_f1_present": best,
                "elapsed_seconds": time.time() - started,
                "allocated_gpu_hours": (time.time() - started) / 3600,
                "test_evaluated": False,
                "smoke": args.smoke,
            },
        )
    except BaseException:
        write_json(
            out / "failure.json",
            {"traceback": traceback.format_exc(), "elapsed_seconds": time.time() - started},
        )
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for field in ("data", "assignments", "categories", "output"):
        p.add_argument("--" + field, required=True)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--head-epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--seed", type=int, default=20261007)
    p.add_argument(
        "--specimen-split", help="Explicit diagnostic split; original test remains reserved"
    )
    p.add_argument(
        "--broad-map", help="Frozen fine-to-broad mapping; default retains original categories"
    )
    p.add_argument("--smoke", action="store_true")
    args = p.parse_args()
    if not (args.epochs > args.head_epochs > 0 and args.batch_size > 0):
        p.error("Invalid epoch/batch settings")
    main(args)

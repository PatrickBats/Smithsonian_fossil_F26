"""Train new fold/final models with recorded initialization and EMA snapshots."""

import importlib.metadata
import json
import math
import os
import time
from pathlib import Path

from .preparation import file_sha
from .protocol import digest, read, write_new


def train(
    root,
    stage,
    run_root,
    results,
    kind,
    generic_init,
    generic_sha,
    fold=None,
    steps=2400,
    smoke=False,
):
    """Fit a training-only proposal model or the joint detection/classification model.

    Candidate joint-model snapshots are saved at steps 1200 and 2400 with one
    fixed cosine schedule. CV chooses a snapshot step and confidence; final
    training uses that same schedule and stops at the selected step. No old
    target-trained model is used for either initialization or ignore proposals.
    """
    import torch
    import pytorch_lightning as pl
    from pytorch_lightning.callbacks import Callback
    from pytorch_lightning.loggers import CSVLogger
    from rfdetr.config import TrainConfig
    from rfdetr_plus.models.detection import RFDETR2XLargeConfig
    from rfdetr.training import RFDETRDataModule, RFDETRModelModule, build_trainer
    from rfdetr.training.callbacks import RFDETREMACallback
    from rfdetr._namespace import build_namespace
    import rfdetr.datasets.coco as coco
    from method_a_new_delivery.training import (
        patch_criterion_for_ignore,
        seed_class_head_from_one_class,
    )

    if not torch.cuda.is_available() or importlib.metadata.version("rfdetr") != "1.6.4":
        raise RuntimeError("Recorded CUDA/RF-DETR runtime required")
    root, run_root, results = Path(root), Path(run_root), Path(results)
    if stage not in {"cv", "final"} or (stage == "cv" and fold not in range(5)):
        raise ValueError("A valid cross-validation fold or final stage is required")
    if not smoke and steps != 2400:
        raise ValueError("This frozen protocol uses a 2400-step candidate schedule")
    if file_sha(generic_init) != generic_sha:
        raise ValueError("Generic initializer provenance mismatch")
    tag = f"fold_{fold}" if stage == "cv" else "final"
    contract = read(root / "datasets" / tag / "contract.json")
    if contract["test_used"] is not False or contract["assignment_digest"] != digest(
        read(root / "assignment.json")
    ):
        raise ValueError("Frozen partition changed")
    out = run_root / tag / (kind + ("_smoke" if smoke else ""))
    out.mkdir(parents=True, exist_ok=True)
    status_path = out / "status.json"
    if status_path.exists() and read(status_path)["status"] == "completed":
        raise FileExistsError("Training already completed")
    resume = out / "resume.ckpt"
    if kind == "teacher":
        dataset, init, classes, ignore = (
            root / "datasets" / tag / "teacher",
            Path(generic_init),
            1,
            None,
        )
    else:
        dataset, classes, ignore = (
            root / "datasets" / tag / ("smoke_ignore" if smoke else "ignore"),
            28,
            28,
        )
        init = (
            run_root
            / tag
            / ("teacher_smoke" if smoke else "teacher")
            / ("checkpoint_step_2.pth" if smoke else "checkpoint_step_2400.pth")
        )
        teacher_status = read(init.parent / "status.json")
        if (
            teacher_status["status"] != "completed"
            or file_sha(init) != teacher_status["checkpoint_sha256"]
        ):
            raise ValueError("Training-only proposal checkpoint changed")
        if stage == "final" and not smoke:
            selection = read(results / "selection.json")
            if selection["assignment_digest"] != digest(read(root / "assignment.json")):
                raise ValueError("Selection does not match the frozen partition")
            steps = selection["selected"]["step"]
    target = 2 if smoke else steps
    data = read(dataset / "train" / "_annotations.coco.json")
    class_names = [
        c["name"]
        for c in sorted(data["categories"], key=lambda c: c["id"])
        if c["name"] != "__ignore__"
    ]
    if len(class_names) != classes:
        raise ValueError("Dataset category map does not match the model head")
    pl.seed_everything(20261120, workers=True)

    def resize_only(scales, *, square, max_size=None):
        if not square or scales != [1000]:
            raise ValueError("Unexpected resize configuration")
        return [{"Resize": {"height": 1000, "width": 1000}}]

    coco._build_train_resize_config = resize_only
    settings = dict(
        dataset_dir=str(dataset),
        output_dir=str(out),
        epochs=math.ceil(2400 / max(1, len(data["images"]) // 16)) + 12,
        batch_size=1,
        grad_accum_steps=16,
        num_workers=2,
        multi_scale=False,
        expanded_scales=False,
        use_ema=True,
        early_stopping=False,
        tensorboard=False,
        wandb=False,
        run_test=False,
        seed=20261120,
        lr=1e-4,
        lr_encoder=1e-5,
        lr_scheduler="cosine",
        compute_val_loss=False,
        log_per_class_metrics=False,
        progress_bar=None,
        save_dataset_grids=False,
        aug_config={
            "HorizontalFlip": {"p": 0.5},
            "VerticalFlip": {"p": 0.5},
            "RandomRotate90": {"p": 0.5},
        },
    )
    mc = RFDETR2XLargeConfig(
        pretrain_weights=str(init), num_classes=classes, resolution=1000
    )
    tc = TrainConfig(**settings)
    module = RFDETRModelModule(mc, tc)
    if kind == "model":
        seed_class_head_from_one_class(module.model, str(init), 0)
        patch_criterion_for_ignore(module.criterion, ignore)
    dm = RFDETRDataModule(mc, tc)
    ema = RFDETREMACallback(
        decay=tc.ema_decay, tau=tc.ema_tau, update_interval_steps=tc.ema_update_interval
    )
    run_contract = {
        "stage": stage,
        "fold": fold,
        "kind": kind,
        "smoke": smoke,
        "target_steps": target,
        "cosine_schedule_steps": 2400,
        "init_path": str(init),
        "init_sha256": file_sha(init),
        "generic_sha256": generic_sha,
        "dataset_sha256": file_sha(dataset / "train" / "_annotations.coco.json"),
        "partition_contract": contract,
        "settings": settings,
        "test_used": False,
        "torch": torch.__version__,
        "rfdetr": importlib.metadata.version("rfdetr"),
        "rfdetr_plus": importlib.metadata.version("rfdetr-plus"),
        "gpu": torch.cuda.get_device_name(),
        "chunks": [],
    }
    contract_path = out / "run_contract.json"
    if contract_path.exists():
        old = read(contract_path)
        for key in (
            "target_steps",
            "init_sha256",
            "dataset_sha256",
            "generic_sha256",
            "partition_contract",
        ):
            if old[key] != run_contract[key]:
                raise ValueError(f"Resume contract changed: {key}")
        run_contract = old
    started = time.monotonic()
    run_contract["chunks"].append(
        {
            "job": os.environ.get("SLURM_JOB_ID"),
            "resume": str(resume) if resume.exists() else None,
        }
    )
    temporary_contract = contract_path.with_suffix(".tmp")
    temporary_contract.write_text(json.dumps(run_contract, indent=2) + "\n")
    temporary_contract.replace(contract_path)
    paused = {"value": False}

    def save_resume(trainer):
        temporary = resume.with_suffix(".tmp.ckpt")
        trainer.save_checkpoint(str(temporary))
        temporary.replace(resume)

    def status(value):
        temporary = status_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, indent=2) + "\n")
        temporary.replace(status_path)

    def save_snapshot(step):
        path = out / f"checkpoint_step_{step}.pth"
        if path.exists():
            return
        args = build_namespace(mc, tc)
        args.class_names = class_names
        state = ema.get_ema_model_state_dict()
        if state is None:
            raise ValueError("EMA not initialized")
        temporary = path.with_suffix(".tmp")
        torch.save(
            {
                "model": {k: v.cpu() for k, v in state.items()},
                "args": args,
                "optimizer_steps": step,
                "selection": "final_ema_snapshot",
                "dataset_sha256": run_contract["dataset_sha256"],
            },
            temporary,
        )
        temporary.replace(path)

    class Record(Callback):
        def on_train_batch_end(self, trainer, module, outputs, batch, batch_idx):
            step = trainer.global_step
            if step in (
                {target} if smoke or kind == "teacher" else {1200, 2400, target}
            ):
                save_snapshot(step)
            if batch_idx % 100 == 0:
                status(
                    {
                        "status": "training",
                        "step": step,
                        "target": target,
                        "elapsed_seconds": time.monotonic() - started,
                        "job": os.environ.get("SLURM_JOB_ID"),
                    }
                )
            if step >= target:
                trainer.should_stop = True
            if (
                not smoke
                and step
                and step < target
                and step % 600 == 0
                and (batch_idx + 1) % 16 == 0
            ):
                save_resume(trainer)
            # Optional short-queue chunks preserve optimizer, scheduler and EMA.
            budget = float(os.environ.get("MIXED_CHUNK_MINUTES", "165")) * 60
            if (
                not smoke
                and not paused["value"]
                and step < target
                and time.monotonic() - started >= budget
                and (batch_idx + 1) % 16 == 0
            ):
                save_resume(trainer)
                paused["value"] = True
                trainer.should_stop = True

    trainer = build_trainer(
        tc,
        mc,
        logger=CSVLogger(
            save_dir=str(out / "logs"),
            name="",
            version=os.environ.get("SLURM_JOB_ID", "local"),
        ),
        callbacks=[ema, Record()],
        max_steps=2 if smoke else 2400,
        limit_val_batches=0,
        num_sanity_val_steps=0,
        enable_model_summary=False,
        enable_checkpointing=not smoke,
    )
    status(
        {"status": "training", "target": target, "job": os.environ.get("SLURM_JOB_ID")}
    )
    trainer.fit(module, dm, ckpt_path=str(resume) if resume.exists() else None)
    if paused["value"]:
        result = {
            "status": "paused",
            "step": trainer.global_step,
            "target": target,
            "elapsed_seconds": time.monotonic() - started,
        }
    else:
        if trainer.global_step != target:
            raise ValueError(f"Incomplete training: {trainer.global_step}/{target}")
        save_snapshot(target)
        result = {
            "status": "completed",
            "step": target,
            "checkpoint_sha256": file_sha(out / f"checkpoint_step_{target}.pth"),
            "elapsed_seconds": time.monotonic() - started,
            "test_used": False,
        }
    status(result)
    return result

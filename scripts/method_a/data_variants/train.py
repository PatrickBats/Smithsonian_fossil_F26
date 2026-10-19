"""Equal optimizer-step budgets, fixed final EMA weights; no sparse-AP selection."""

import argparse, importlib.metadata, math, os, sys, time, traceback, subprocess
from pathlib import Path
import json
from common import (
    BASE,
    CODE,
    EXPERIMENTS,
    RESULTS,
    ROOT,
    SEED,
    WEIGHT_SHA,
    load,
    resolve_variant,
    sha,
    write,
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--variant",
        "--experiment",
        dest="experiment",
        type=resolve_variant,
        choices=EXPERIMENTS,
        required=True,
        metavar="A1|A2|A3",
    )
    p.add_argument("--smoke", action="store_true")
    a = p.parse_args()
    if not a.smoke:
        subprocess.run(
            [sys.executable, "-B", str(CODE / "verify_inputs.py"), "--label", a.experiment],
            check=True,
        )
    import torch, pytorch_lightning as pl
    from pytorch_lightning.callbacks import Callback, ModelCheckpoint
    from pytorch_lightning.loggers import CSVLogger
    from rfdetr.config import TrainConfig
    from rfdetr_plus.models.detection import RFDETR2XLargeConfig
    from rfdetr.training import RFDETRDataModule, RFDETRModelModule, build_trainer
    from rfdetr.training.callbacks import RFDETREMACallback
    from rfdetr._namespace import build_namespace
    import rfdetr.datasets.coco as coco

    assert importlib.metadata.version("rfdetr") == "1.6.4" and torch.cuda.is_available()
    data = ROOT / "datasets" / a.experiment
    summary = load(data / "dataset_summary.json")
    assert summary["status"] == "verified"
    assert summary["train_coco_sha256"] == sha(data / "train/_annotations.coco.json")
    assert summary["valid_coco_sha256"] == sha(BASE / "dataset/valid/_annotations.coco.json")
    pretrained = ROOT / "inputs/rf-detr-xxlarge.pth"
    assert sha(pretrained) == WEIGHT_SHA
    kind = "smoke" if a.smoke else "training"
    out = ROOT / "run_artifacts" / a.experiment / kind
    if not a.smoke:
        assert load(out.parent / "smoke/status.json")["status"] == "completed"
    out.mkdir(parents=True, exist_ok=False)
    scratch = (
        Path(os.environ.get("SLURM_TMPDIR") or "/tmp")
        / f"f26_sparse_{os.environ.get('SLURM_JOB_ID','manual')}"
    )
    scratch.mkdir(exist_ok=False)
    os.environ.update(
        HF_HOME=str(scratch / "hf"), TORCH_HOME=str(scratch / "torch"), NO_ALBUMENTATIONS_UPDATE="1"
    )
    pl.seed_everything(SEED, workers=True)

    # The default RF-DETR transform adds a second random crop even with multi_scale=False.
    # Disable that crop in this process only, identically for all three experiments.
    def resize_only(scales, *, square, max_size=None):
        assert square and scales == [1000]
        return [{"Resize": {"height": 1000, "width": 1000}}]

    coco._build_train_resize_config = resize_only
    steps = 2 if a.smoke else 2400
    epochs = (
        1 if a.smoke else math.ceil(steps / max(1, math.floor(summary["train_images"] / 16))) + 1
    )
    mc = RFDETR2XLargeConfig(pretrain_weights=str(pretrained), num_classes=28, resolution=1000)
    settings = {
        "dataset_dir": str(data),
        "output_dir": str(out),
        "epochs": epochs,
        "batch_size": 1,
        "grad_accum_steps": 16,
        "num_workers": 2,
        "multi_scale": False,
        "expanded_scales": False,
        "use_ema": True,
        "early_stopping": False,
        "tensorboard": False,
        "wandb": False,
        "run_test": False,
        "seed": SEED,
        "lr": 1e-4,
        "lr_encoder": 1e-5,
        "lr_scheduler": "cosine",
        "compute_val_loss": False,
        "log_per_class_metrics": False,
        "progress_bar": None,
        "save_dataset_grids": False,
        "aug_config": {"HorizontalFlip": {"p": 0.5}},
    }
    tc = TrainConfig(**settings)
    contract = {
        "experiment": a.experiment,
        "smoke": a.smoke,
        "max_optimizer_steps": steps,
        "selection": "fixed final EMA, no validation-based selection or early stopping",
        "training_settings": settings,
        "model_config": mc.model_dump(),
        "dataset_summary_sha256": sha(data / "dataset_summary.json"),
        "pretrained_sha256": WEIGHT_SHA,
        "rfdetr": importlib.metadata.version("rfdetr"),
        "rfdetr_plus": importlib.metadata.version("rfdetr-plus"),
        "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(),
        "slurm_job": os.environ.get("SLURM_JOB_ID"),
        "augmentation": "resize-only + horizontal flip; default secondary random crop disabled in this process",
        "code_sha256": {p.name: sha(p) for p in sorted(CODE.glob("*.py"))},
        "baseline_comparison_limit": "Old baseline used AP-based early stopping and different training duration/augmentation; new runs have equal step budgets.",
    }
    write(out / "run_contract.json", contract)
    started = time.time()

    class Progress(Callback):
        def on_train_batch_end(self, trainer, module, outputs, batch, batch_idx):
            if batch_idx % 100 == 0:
                write(
                    out / "progress.json",
                    {
                        "status": "training",
                        "optimizer_step": trainer.global_step,
                        "max_steps": steps,
                        "epoch": trainer.current_epoch,
                        "elapsed_seconds": time.time() - started,
                    },
                )

        def on_train_epoch_end(self, trainer, module):
            print(
                json.dumps(
                    {
                        "epoch": trainer.current_epoch,
                        "optimizer_step": trainer.global_step,
                        "elapsed_seconds": time.time() - started,
                    }
                ),
                flush=True,
            )

    callbacks = [
        RFDETREMACallback(
            decay=tc.ema_decay, tau=tc.ema_tau, update_interval_steps=tc.ema_update_interval
        ),
        Progress(),
    ]
    if not a.smoke:
        callbacks.append(
            ModelCheckpoint(
                dirpath=str(out),
                filename="resume",
                every_n_epochs=5,
                save_top_k=1,
                save_last=False,
                enable_version_counter=False,
                auto_insert_metric_name=False,
                save_on_train_epoch_end=True,
            )
        )
    module = RFDETRModelModule(mc, tc)
    dm = RFDETRDataModule(mc, tc)
    trainer = build_trainer(
        tc,
        mc,
        logger=CSVLogger(save_dir=str(RESULTS / a.experiment / kind), name="", version=""),
        callbacks=callbacks,
        max_steps=steps,
        limit_val_batches=0,
        num_sanity_val_steps=0,
        enable_model_summary=False,
        enable_checkpointing=not a.smoke,
    )
    write(out / "status.json", {"status": "training"})
    try:
        trainer.fit(module, dm)
        assert trainer.global_step == steps
        # EMA callback leaves the module at final EMA weights on_train_end.
        args = build_namespace(mc, tc)
        args.class_names = [
            c["name"] for c in load(data / "train/_annotations.coco.json")["categories"]
        ]
        state = {k: v.detach().cpu() for k, v in module.model.state_dict().items()}
        torch.save(
            {
                "model": state,
                "args": args,
                "epoch": trainer.current_epoch,
                "optimizer_steps": trainer.global_step,
                "selection": "fixed_final_ema",
            },
            out / "checkpoint_final_ema.pth",
        )
        result = {
            "status": "completed",
            "optimizer_steps": trainer.global_step,
            "epochs_started": trainer.current_epoch,
            "elapsed_seconds": time.time() - started,
            "checkpoint_sha256": sha(out / "checkpoint_final_ema.pth"),
            "test_used": False,
        }
        write(out / "status.json", result)
        write(out / "progress.json", result)
        write(RESULTS / a.experiment / kind / "status.json", result)
        write(RESULTS / a.experiment / kind / "run_contract.json", contract)
        print(json.dumps(result, indent=2), flush=True)
    except BaseException as exc:
        write(
            out / "status.json",
            {"status": "failed", "error": str(exc), "traceback": traceback.format_exc()},
        )
        raise


if __name__ == "__main__":
    main()

"""Method A3 recipe + (1) init from the one-class Spring detector, (2) ignore-region
loss for pseudo-labeled unlabeled grains, (3) flip/rotate augmentation.

Everything else (2XL, 1000 px, batch 1 x 16 accum, lr 1e-4 / encoder 1e-5, cosine,
2,400 optimizer steps, final EMA weights, no validation-based selection) follows
scripts/method_a/data_variants/train.py in the team repo so the run is comparable.
"""

import argparse, hashlib, importlib.metadata, json, math, os, time
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2))


def patch_criterion_for_ignore(criterion, ignore_label, iou_thresh=0.5):
    """Exclude ignore boxes from matching and zero the no-object loss on queries
    whose predicted box overlaps an ignore box (IoU >= iou_thresh)."""
    import torch
    import torch.nn.functional as F
    from rfdetr.utilities import box_ops

    assert criterion.ia_bce_loss, "patch written for the ia_bce_loss branch RF-DETR uses by default"
    orig_forward = criterion.forward

    def forward(outputs, targets):
        kept, ign = [], []
        for t in targets:
            m = t["labels"] != ignore_label
            kept.append({**t, "labels": t["labels"][m], "boxes": t["boxes"][m]})
            ign.append(t["boxes"][~m])
        criterion._ignore_boxes = ign
        criterion._ignore_hits = 0
        try:
            return orig_forward(outputs, kept)
        finally:
            criterion._ignore_boxes = None

    def ignore_mask(pred_boxes):
        B, Q, _ = pred_boxes.shape
        mask = torch.zeros(B, Q, dtype=torch.bool, device=pred_boxes.device)
        for b, ib in enumerate(criterion._ignore_boxes or []):
            if len(ib) == 0:
                continue
            iou = box_ops.box_iou(
                box_ops.box_cxcywh_to_xyxy(pred_boxes[b].detach()),
                box_ops.box_cxcywh_to_xyxy(ib.to(pred_boxes.device)),
            )[0]
            mask[b] = iou.max(1).values >= iou_thresh
        return mask

    def loss_labels(outputs, targets, indices, num_boxes, log=True):
        src_logits = outputs["pred_logits"]
        idx = criterion._get_src_permutation_idx(indices)
        target_classes_o = torch.cat([t["labels"][J] for t, (_, J) in zip(targets, indices)])
        alpha, gamma = criterion.focal_alpha, 2
        src_boxes = outputs["pred_boxes"][idx]
        target_boxes = torch.cat([t["boxes"][i] for t, (_, i) in zip(targets, indices)], dim=0)
        iou_targets = torch.diag(box_ops.box_iou(
            box_ops.box_cxcywh_to_xyxy(src_boxes.detach()), box_ops.box_cxcywh_to_xyxy(target_boxes))[0])
        pos_ious = iou_targets.clone().detach()
        prob = src_logits.sigmoid()
        pos_weights = torch.zeros_like(src_logits)
        neg_weights = prob ** gamma
        pos_ind = [i for i in idx]
        pos_ind.append(target_classes_o)
        t = torch.clamp(prob[tuple(pos_ind)].pow(alpha) * pos_ious.pow(1 - alpha), 0.01).detach()
        pos_weights[tuple(pos_ind)] = t.to(pos_weights.dtype)
        neg_weights[tuple(pos_ind)] = 1 - t.to(neg_weights.dtype)
        loss_ce = neg_weights * src_logits - F.logsigmoid(src_logits) * (pos_weights + neg_weights)
        # --- ignore regions: unmatched queries sitting on a pseudo-labeled grain get no loss
        mask = ignore_mask(outputs["pred_boxes"])
        mask[idx] = False
        criterion._ignore_hits += int(mask.sum())
        loss_ce = loss_ce * (~mask).unsqueeze(-1).to(loss_ce.dtype)
        rw = getattr(criterion, "_row_weight", None)   # --balance cb: class weights on matched rows
        if rw is not None:
            loss_ce = loss_ce * rw.unsqueeze(-1)
        losses = {"loss_ce": loss_ce.sum() / num_boxes}
        if log:
            from rfdetr.models.math import accuracy
            losses["class_error"] = 100 - accuracy(src_logits[idx], target_classes_o)[0]
        return losses

    criterion.forward = forward
    criterion.loss_labels = loss_labels
    return criterion


def seed_class_head_from_one_class(model, init_path, pollen, n_real=28):
    """rfdetr tiles a smaller checkpoint head by repeating its rows. A one-class checkpoint has
    2 rows (pollen + an unused slot that was trained toward always-negative), so tiling to 29
    alternates pollen / unused across the 28 classes. Overwrite every real-class row with the
    trained pollen row so all 28 classes start from the same objectness prior.

    `pollen` is the row index the one-class model actually fires on (rfdetr's PostProcess sets
    class_id = topk_index % n_rows, so make_ignore_labels.py's `pred_class_id_hist` measures it
    directly). Bias/weight-norm heuristics were tried and got it wrong for the Spring checkpoint
    (row 1 had the higher bias and norm, but every detection came from row 0), so they are only
    recorded here, never used to pick the row."""
    import torch
    sd = torch.load(init_path, map_location="cpu", weights_only=False)["model"]
    b = sd["class_embed.bias"]
    if b.shape[0] != 2:
        return {"seeded": False, "checkpoint_head_rows": int(b.shape[0])}
    assert pollen in (0, 1), pollen
    norms = sd["class_embed.weight"].norm(dim=1)
    w = sd["class_embed.weight"][pollen]
    heads = [("class_embed", model.class_embed, w, b[pollen])]
    if getattr(model, "two_stage", False):
        for g, m in enumerate(model.transformer.enc_out_class_embed):
            key = f"transformer.enc_out_class_embed.{g}"
            heads.append((key, m, sd[f"{key}.weight"][pollen], sd[f"{key}.bias"][pollen]))
    with torch.no_grad():
        for _, m, wr, br in heads:
            m.weight[:n_real] = wr.to(m.weight)
            m.bias[:n_real] = br.to(m.bias)
    return {"seeded": True, "pollen_row": pollen, "pollen_row_source": "pred_class_id_hist / --pollen-row",
            "heads": len(heads), "bias_rows": [float(x) for x in b],
            "weight_norm_rows": [float(x) for x in norms]}


def pollen_row_for(dataset_dir, override):
    """Row the one-class model fires on: from make_ignore_labels.py's summary when the dataset
    has one, else from --pollen-row (needed for the init-only ablation on the plain A3 dir)."""
    import json
    p = Path(dataset_dir) / "ignore_labels_summary.json"
    if p.exists():
        hist = json.loads(p.read_text())["pred_class_id_hist"]
        rows = [int(k) for k, v in hist.items() if v > 0]
        assert len(rows) == 1, f"one-class model fired on several rows: {hist}"
        if override is not None:
            assert override == rows[0], (override, hist)
        return rows[0]
    assert override is not None, "dataset has no ignore_labels_summary.json; pass --pollen-row"
    return override


def class_balance_stats(train_coco, ignore_label, a):
    """Per-class label counts, class-balanced loss weights (Cui et al. 2019, effective number
    (1-b)/(1-b^n), normalised to mean 1) and per-image repeat factors (Gupta et al. 2019:
    r(img) = max over its classes of max(1, sqrt(t / f(c))), f = fraction of tiles containing c)."""
    import collections, math
    cats = sorted(train_coco["categories"], key=lambda c: c["id"])
    remap = {c["id"]: i for i, c in enumerate(cats)}            # same contiguous remap rfdetr uses
    names = {remap[c["id"]]: c["name"] for c in cats}
    img_classes = collections.defaultdict(set)
    for ann in train_coco["annotations"]:
        lab = remap[ann["category_id"]]
        if lab != ignore_label:
            img_classes[ann["image_id"]].add(lab)
    n_img = len(train_coco["images"])
    counts = collections.Counter(remap[x["category_id"]] for x in train_coco["annotations"] if remap[x["category_id"]] != ignore_label)
    freq = {c: sum(1 for s in img_classes.values() if c in s) / n_img for c in counts}
    b = a.cb_beta
    w = {c: (1 - b) / (1 - b ** n) for c, n in counts.items()}
    mean_w = sum(w.values()) / len(w)
    class_weight = {c: w[c] / mean_w for c in w}
    image_repeat = {}
    for img in train_coco["images"]:
        cs = img_classes.get(img["id"], set())
        image_repeat[img["id"]] = max([1.0] + [math.sqrt(a.rfs_t / freq[c]) for c in cs if freq[c] < a.rfs_t])
    hist = collections.Counter(round(r, 1) for r in image_repeat.values())
    return dict(class_counts={names[c]: n for c, n in sorted(counts.items())},
                class_weight={names[c]: round(v, 3) for c, v in sorted(class_weight.items())},
                class_weight_by_label=class_weight, image_repeat=image_repeat,
                repeat_factor_hist={str(k): v for k, v in sorted(hist.items())})


def patch_datamodule_rfs(dm, image_repeat, tc):
    """Replace the shuffle=True train loader with a WeightedRandomSampler over tiles (weights =
    repeat factors, with replacement, one epoch = len(dataset) draws rounded to the accumulation
    window) so rare-class tiles are seen more often. Everything else in the loader is unchanged."""
    import torch
    from torch.utils.data import DataLoader, WeightedRandomSampler
    from rfdetr.training.module_data import collate_fn
    orig = dm.train_dataloader

    def train_dataloader():
        ds = dm._dataset_train
        ids = list(getattr(ds, "ids", None) or ds.coco.getImgIds())
        assert len(ids) == len(ds), (len(ids), len(ds))
        weights = torch.tensor([image_repeat[i] for i in ids], dtype=torch.double)
        eff = tc.batch_size * tc.grad_accum_steps
        n = (len(ds) // eff) * eff
        sampler = WeightedRandomSampler(weights, num_samples=n, replacement=True)
        print(json.dumps(dict(rfs_sampler=True, tiles=len(ds), draws_per_epoch=n,
                              mean_weight=float(weights.mean()), max_weight=float(weights.max()))), flush=True)
        return DataLoader(ds, batch_size=tc.batch_size, sampler=sampler, drop_last=True, collate_fn=collate_fn,
                          num_workers=dm._num_workers, pin_memory=dm._pin_memory,
                          persistent_workers=dm._persistent_workers, prefetch_factor=dm._prefetch_factor)
    dm.train_dataloader = train_dataloader
    return dm


def patch_criterion_class_weights(criterion, class_weight_by_label):
    """Scale each matched query's IA-BCE row by its target class weight (applied after the
    ignore-region patch, which must already be installed)."""
    import torch
    inner = criterion.loss_labels
    table = torch.tensor([class_weight_by_label[i] for i in range(len(class_weight_by_label))], dtype=torch.float32)

    def loss_labels(outputs, targets, indices, num_boxes, log=True):
        # recompute the per-element loss with the same code path, then weight matched rows
        src_logits = outputs["pred_logits"]
        idx = criterion._get_src_permutation_idx(indices)
        target_classes_o = torch.cat([t["labels"][J] for t, (_, J) in zip(targets, indices)])
        w = table.to(src_logits.device)[target_classes_o]
        row_w = torch.ones(src_logits.shape[:2], device=src_logits.device, dtype=src_logits.dtype)
        row_w[idx] = w.to(src_logits.dtype)
        criterion._row_weight = row_w
        try:
            return inner(outputs, targets, indices, num_boxes, log)
        finally:
            criterion._row_weight = None
    criterion.loss_labels = loss_labels
    return criterion


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True, help="dataset dir produced by make_ignore_labels.py")
    p.add_argument("--init", required=True, help="pretrained .pth to train from (COCO rf-detr-xxlarge.pth by default in the launchers; the Spring one-class detector also works and gets its head seeded)")
    p.add_argument("--out", required=True)
    p.add_argument("--steps", type=int, default=2400)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--lr-encoder", type=float, default=1e-5)
    p.add_argument("--no-extra-aug", action="store_true", help="ablation: hflip only like the team")
    p.add_argument("--balance", choices=["none", "rfs", "cb"], default="none",
                   help="rfs: repeat-factor sampling of tiles (Gupta et al. 2019, LVIS); "
                        "cb: class-balanced weights on matched queries' IA-BCE loss (Cui et al. 2019)")
    p.add_argument("--rfs-t", type=float, default=0.1, help="RFS threshold t: tiles whose rarest class has image frequency < t are repeated sqrt(t/f) times")
    p.add_argument("--cb-beta", type=float, default=0.999)
    p.add_argument("--multi-scale", action="store_true", help="rfdetr multi-scale resize (expanded scales) instead of fixed 1000 px")
    p.add_argument("--color-jitter", action="store_true", help="HueSaturationValue + RandomBrightnessContrast (stain/illumination shift)")
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--num-workers", type=int, default=2, help="dataloader workers (throughput only; the A3 recipe used 2)")
    p.add_argument("--seed", type=int, default=20261013)
    p.add_argument("--pollen-row", type=int, default=None,
                   help="head row the one-class init fires on; read from the dataset summary when present")
    p.add_argument("--time-budget-min", type=float, default=None,
                   help="chunked mode: save resume.ckpt and stop cleanly after this many minutes of training")
    p.add_argument("--resume", default=None, help="chunked mode: Lightning checkpoint written by a previous chunk")
    a = p.parse_args()

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
    data, out = Path(a.dataset), Path(a.out)
    out.mkdir(parents=True, exist_ok=a.resume is not None)
    if a.resume:
        assert Path(a.resume).exists() and json.loads((out / "status.json").read_text())["status"] in ("paused", "training")
    train_coco = json.loads((data / "train/_annotations.coco.json").read_text())
    cats = sorted(train_coco["categories"], key=lambda c: c["id"])
    real = [c for c in cats if c["name"] != "__ignore__"]
    assert len(real) == 28, len(real)
    # rfdetr 1.6.4 trains with remap_category_ids=True: contiguous labels in sorted id order,
    # so __ignore__ (the max id) becomes label 28 and the 28 real classes are 0..27.
    ignore_label = len(real) if len(real) != len(cats) else None
    # ablation "init only": point --dataset at the original A3 dir (28 categories -> ignore_label None)
    n_train = len(train_coco["images"])
    os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"
    pl.seed_everything(a.seed, workers=True)

    def resize_only(scales, *, square, max_size=None):  # same as team: no secondary random crop
        # fixed: [1000]; --multi-scale: one random square scale per tile from rfdetr's scale set
        return [{"OneOf": [{"Resize": {"height": s, "width": s, "p": 1.0}} for s in scales]}]
    coco._build_train_resize_config = resize_only

    steps = 2 if a.smoke else a.steps
    epochs = 1 if a.smoke else math.ceil(steps / max(1, n_train // 16)) + 1
    if a.time_budget_min or a.resume:
        # a resumed epoch restarts from its first batch, so chunking/resuming can consume a few extra
        # epochs; max_steps still caps estimated_stepping_batches, so the cosine schedule is unchanged.
        epochs += 6
    aug = {"HorizontalFlip": {"p": 0.5}}
    if not a.no_extra_aug:
        aug.update({"VerticalFlip": {"p": 0.5}, "RandomRotate90": {"p": 0.5}})
    if a.color_jitter:
        aug.update({"HueSaturationValue": {"hue_shift_limit": 10, "sat_shift_limit": 20, "val_shift_limit": 15, "p": 0.5},
                    "RandomBrightnessContrast": {"brightness_limit": 0.15, "contrast_limit": 0.15, "p": 0.5}})
    mc = RFDETR2XLargeConfig(pretrain_weights=a.init, num_classes=28, resolution=1000)
    settings = dict(dataset_dir=str(data), output_dir=str(out), epochs=epochs, batch_size=1,
                    grad_accum_steps=16, num_workers=a.num_workers, multi_scale=a.multi_scale, expanded_scales=a.multi_scale,
                    use_ema=True, early_stopping=False, tensorboard=False, wandb=False, run_test=False,
                    seed=a.seed, lr=a.lr, lr_encoder=a.lr_encoder, lr_scheduler="cosine",
                    compute_val_loss=False, log_per_class_metrics=False, progress_bar=None,
                    save_dataset_grids=False, aug_config=aug)
    tc = TrainConfig(**settings)
    module = RFDETRModelModule(mc, tc)
    assert module.model.class_embed.out_features == 29, module.model.class_embed.out_features
    init_head = seed_class_head_from_one_class(module.model, a.init, pollen_row_for(data, a.pollen_row))
    if ignore_label is not None:
        patch_criterion_for_ignore(module.criterion, ignore_label)
    dm = RFDETRDataModule(mc, tc)
    balance = class_balance_stats(train_coco, ignore_label, a)
    if a.balance == "rfs":
        patch_datamodule_rfs(dm, balance["image_repeat"], tc)
    elif a.balance == "cb":
        patch_criterion_class_weights(module.criterion, balance["class_weight_by_label"])
    contract = dict(experiment="A4_ignore_cocoinit" if init_head.get("seeded") is False else "A4_ignore_springinit", smoke=a.smoke, max_optimizer_steps=steps,
                    init_checkpoint=a.init, init_sha256=sha(a.init), init_head=init_head, ignore_label=ignore_label,
                    train_images=n_train, train_coco_sha256=sha(data / "train/_annotations.coco.json"),
                    training_settings=settings, model_config=mc.model_dump(), torch=torch.__version__,
                    balance=dict(mode=a.balance, rfs_t=a.rfs_t, cb_beta=a.cb_beta,
                                 class_counts=balance["class_counts"], class_weight=balance["class_weight"],
                                 repeat_factor_hist=balance["repeat_factor_hist"]),
                    aug_config=aug, multi_scale=a.multi_scale,
                    rfdetr=importlib.metadata.version("rfdetr"), gpu=torch.cuda.get_device_name(),
                    slurm_job=os.environ.get("SLURM_JOB_ID"),
                    selection="fixed final EMA, no validation-based selection",
                    chunked=bool(a.time_budget_min), chunks=[])
    if a.resume:  # keep the original contract; append this chunk
        contract = json.loads((out / "run_contract.json").read_text())
    contract["chunks"].append(dict(slurm_job=os.environ.get("SLURM_JOB_ID"), resume=a.resume,
                                   time_budget_min=a.time_budget_min, epochs_cap=epochs))
    write(out / "run_contract.json", contract)
    started = time.time()
    paused = {"flag": False}

    class TimeBudget(Callback):
        """Chunked mode: save a full Lightning checkpoint (model, optimizer, LR schedule, EMA state)
        and stop before the partition wall limit. Saved mid-step, before any callback swaps weights."""
        def on_train_batch_end(self, trainer, module, outputs, batch, batch_idx):
            if a.time_budget_min and not paused["flag"] and trainer.global_step < steps \
                    and time.time() - started > a.time_budget_min * 60 and (batch_idx + 1) % 16 == 0:
                trainer.save_checkpoint(str(out / "resume.ckpt"))
                write(out / "status.json", dict(status="paused", optimizer_step=trainer.global_step, max_steps=steps,
                      epoch=trainer.current_epoch, chunk_elapsed_seconds=time.time() - started))
                paused["flag"] = True
                trainer.should_stop = True

    class Progress(Callback):
        def on_train_batch_end(self, trainer, module, outputs, batch, batch_idx):
            if batch_idx % 100 == 0:
                write(out / "progress.json", dict(status="training", optimizer_step=trainer.global_step,
                      max_steps=steps, epoch=trainer.current_epoch, elapsed_seconds=time.time() - started,
                      ignore_hits_last_batch=getattr(module.criterion, "_ignore_hits", None)))
        def on_train_epoch_end(self, trainer, module):
            print(json.dumps(dict(epoch=trainer.current_epoch, optimizer_step=trainer.global_step,
                  elapsed_seconds=round(time.time() - started))), flush=True)

    callbacks = [RFDETREMACallback(decay=tc.ema_decay, tau=tc.ema_tau, update_interval_steps=tc.ema_update_interval),
                 TimeBudget(), Progress()]
    if not a.smoke and not a.time_budget_min:
        callbacks.append(ModelCheckpoint(dirpath=str(out), filename="resume", every_n_epochs=5, save_top_k=1,
                         save_last=False, enable_version_counter=False, auto_insert_metric_name=False,
                         save_on_train_epoch_end=True))
    trainer = build_trainer(tc, mc, logger=CSVLogger(save_dir=str(out / "logs"), name="", version=""),
                            callbacks=callbacks, max_steps=steps, limit_val_batches=0, num_sanity_val_steps=0,
                            enable_model_summary=False, enable_checkpointing=not a.smoke)
    write(out / "status.json", {"status": "training", "resumed_from": a.resume})
    trainer.fit(module, dm, ckpt_path=a.resume)
    if paused["flag"]:
        print(json.dumps(json.loads((out / "status.json").read_text())), flush=True)
        return
    assert trainer.global_step == steps, trainer.global_step
    if a.resume:
        os.remove(a.resume)
    args = build_namespace(mc, tc)
    args.class_names = [c["name"] for c in real]
    state = {k: v.detach().cpu() for k, v in module.model.state_dict().items()}
    torch.save({"model": state, "args": args, "epoch": trainer.current_epoch, "optimizer_steps": trainer.global_step,
                "selection": "fixed_final_ema"}, out / "checkpoint_final_ema.pth")
    result = dict(status="completed", optimizer_steps=trainer.global_step, epochs_started=trainer.current_epoch,
                  elapsed_seconds=time.time() - started, checkpoint_sha256=sha(out / "checkpoint_final_ema.pth"),
                  test_used=False)
    write(out / "status.json", result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()

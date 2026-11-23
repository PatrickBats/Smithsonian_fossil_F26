"""Local PC-only patches for rfdetr 1.6.4 (not in the team repo).

1) Fast bbox matching for validation metrics.
   rfdetr.evaluation.matching._match_single_class loops over every prediction in
   Python doing tiny GPU tensor ops; each comparison forces a GPU->CPU sync
   (profiled on NOTS 2026-11-19: ~44% of validation time, 3.7M .cpu() calls).
   This version keeps the exact same algorithm (same argsort, same box_iou call,
   same greedy order and tie-breaking) but copies the IoU matrix to the CPU once
   and runs the loop in NumPy. Mask (segm) matching falls back to the original.

2) Resume-safe best-EMA tracking.
   BestModelCallback keeps its best EMA score in a plain attribute that is not
   saved in last.ckpt, so after a resume it restarts at 0.0 and the next epoch
   would overwrite checkpoint_best_ema.pth even if worse. If the env var
   RFDETR_BEST_EMA_INIT is set, it seeds that value.
"""
import os
import numpy as np
import torch
from torchvision.ops import box_iou
import rfdetr.evaluation.matching as _m
from rfdetr.training.callbacks import best_model as _bm

_orig_match = _m._match_single_class


def _match_single_class_fast(pred_scores, pred_items, gt_items, gt_crowd, iou_threshold, iou_type):
    if iou_type != "bbox":
        return _orig_match(pred_scores, pred_items, gt_items, gt_crowd, iou_threshold, iou_type)
    n = pred_scores.shape[0]
    sort_idx = torch.argsort(pred_scores, descending=True)
    pred_scores_sorted = pred_scores[sort_idx]
    pred_sorted = pred_items[sort_idx]
    iou = box_iou(pred_sorted, gt_items).cpu().numpy()          # one transfer per image/class
    crowd = gt_crowd.cpu().numpy().astype(bool)
    m = crowd.shape[0]
    gt_matched = np.zeros(m, dtype=bool)
    pred_match = np.zeros(n, dtype=np.int64)
    pred_ignore = np.zeros(n, dtype=bool)
    any_crowd = bool(crowd.any())
    for i in range(n):
        ious = iou[i]
        nc = ious.copy()
        nc[crowd] = -1.0
        nc[gt_matched & ~crowd] = -1.0
        j = int(nc.argmax())                                      # first max, like torch.max(dim=0)
        if nc[j] >= iou_threshold:
            pred_match[i] = 1
            gt_matched[j] = True
        elif any_crowd:
            c = ious.copy()
            c[~crowd] = -1.0
            if c.max() >= iou_threshold:
                pred_ignore[i] = True
    total_gt = int((~crowd).sum())
    return (pred_scores_sorted.float().cpu().numpy().astype(np.float32), pred_match, pred_ignore, total_gt)



def _install_ignore(ignore_label):
    """RFDETR_IGNORE_LABEL=<label>: patch every RFDETRModelModule's criterion for ignore regions."""
    import json
    from rfdetr.training import module_model as _mm
    from src.models.rfdetr.ignore_patch import patch_criterion_for_ignore
    stats_path = os.environ.get("RFDETR_IGNORE_STATS")
    _orig = _mm.RFDETRModelModule.__init__

    def _init(self, *a, **k):
        _orig(self, *a, **k)
        crit = patch_criterion_for_ignore(self.criterion, ignore_label)
        inner = crit.forward
        tot = {"calls": 0, "train_calls": 0, "ignore_boxes": 0, "ignore_hits": 0, "leaked_labels": 0}

        def forward(outputs, targets):
            n_ign = sum(int((t["labels"] == ignore_label).sum()) for t in targets)
            out = inner(outputs, targets)
            tot["calls"] += 1; tot["train_calls"] += int(crit.training)
            tot["ignore_boxes"] += n_ign; tot["ignore_hits"] += int(getattr(crit, "_ignore_hits", 0) or 0)
            tot["leaked_labels"] += sum(int((t["labels"] > ignore_label).sum()) for t in targets)
            tot["labels_seen"] = sorted(set(tot.get("labels_seen", [])) | {int(v) for t in targets for v in t["labels"].unique().tolist()})
            if stats_path and tot["calls"] % int(os.environ.get("RFDETR_IGNORE_STATS_EVERY", "200")) == 0:
                with open(stats_path, "w") as h: json.dump(tot, h)
            return out
        crit.forward = forward
        crit._ignore_totals = tot
        print(f"[local_patches] ignore-region loss enabled (ignore label {ignore_label})", flush=True)
    _mm.RFDETRModelModule.__init__ = _init


def _install_domain_metrics(split_id):
    """RFDETR_DOMAIN_SPLIT_ID=<n>: also report validation mAP separately for images with id < n ("old")
    and id >= n ("new"). Logged as val_old/* and val_new/* (regular and EMA); selection is unchanged."""
    import json
    import rfdetr.training.callbacks.coco_eval as ce
    Base = ce.MeanAveragePrecision
    state = {"cb": None, "dom": None}

    class DomainMAP(Base):
        def update(self, preds, target):
            super().update(preds, target)
            cb, dom = state["cb"], state["dom"]
            if cb is None or dom is None:
                return
            kind = "reg" if self is cb.map_metric else "ema"
            store = cb.__dict__.setdefault("_dom_metrics", {})
            for name, flag in (("old", False), ("new", True)):
                idx = [i for i, d in enumerate(dom) if d == flag]
                if not idx:
                    continue
                if (name, kind) not in store:
                    store[(name, kind)] = Base(iou_type="bbox", max_detection_thresholds=[1, 10, cb._max_dets],
                                               backend="faster_coco_eval").to(preds[0]["boxes"].device)
                store[(name, kind)].update([preds[i] for i in idx], [target[i] for i in idx])
    ce.MeanAveragePrecision = DomainMAP

    _ob = ce.COCOEvalCallback.on_validation_batch_end
    def on_validation_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        state["cb"] = self
        state["dom"] = [int(t["image_id"]) >= split_id for t in outputs["targets"]]
        try:
            _ob(self, trainer, pl_module, outputs, batch, batch_idx)
        finally:
            state["dom"] = None
    ce.COCOEvalCallback.on_validation_batch_end = on_validation_batch_end

    _oc = ce.COCOEvalCallback._compute_and_log
    def _compute_and_log(self, trainer, pl_module, split):
        store = getattr(self, "_dom_metrics", {})
        if split == "val" and store and not getattr(trainer, "sanity_checking", False):
            row = {"epoch": int(trainer.current_epoch)}
            for (name, kind), m in sorted(store.items()):
                r = m.compute()
                for out_k, in_k in (("mAP_50_95", "map"), ("mAP_50", "map_50"), ("mAP_75", "map_75")):
                    tag = f"val_{name}/{'ema_' if kind == 'ema' else ''}{out_k}"
                    row[tag] = round(float(r[in_k]), 4)
                    pl_module.log(tag, float(r[in_k]))
                m.reset()
            print("[domain_val] " + json.dumps(row), flush=True)
            path = os.environ.get("RFDETR_DOMAIN_LOG")
            if path:
                with open(path, "a") as h: h.write(json.dumps(row) + "\n")
        else:
            for m in store.values():
                m.reset()
        return _oc(self, trainer, pl_module, split)
    ce.COCOEvalCallback._compute_and_log = _compute_and_log
    print(f"[local_patches] per-domain validation metrics enabled (new = image id >= {split_id})", flush=True)


def apply():
    _m._match_single_class = _match_single_class_fast
    init = os.environ.get("RFDETR_BEST_EMA_INIT")
    if init:
        _orig_init = _bm.BestModelCallback.__init__
        def _init(self, *a, **k):
            _orig_init(self, *a, **k)
            self._best_ema = float(init)
            print(f"[local_patches] BestModelCallback._best_ema seeded to {self._best_ema}", flush=True)
        _bm.BestModelCallback.__init__ = _init
    print("[local_patches] fast bbox matching enabled", flush=True)
    if os.environ.get("RFDETR_IGNORE_LABEL"):
        _install_ignore(int(os.environ["RFDETR_IGNORE_LABEL"]))
    if os.environ.get("RFDETR_DOMAIN_SPLIT_ID"):
        _install_domain_metrics(int(os.environ["RFDETR_DOMAIN_SPLIT_ID"]))

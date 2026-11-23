"""Ignore-region loss for RF-DETR 1.6.4 (local PC only).

patch_criterion_for_ignore is copied verbatim from model_A/scripts/train_ignore.py (Method A, A4 recipe):
boxes labelled with the __ignore__ category are removed before Hungarian matching, and unmatched queries
whose predicted box overlaps one (IoU >= 0.5) get no classification loss.
"""


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

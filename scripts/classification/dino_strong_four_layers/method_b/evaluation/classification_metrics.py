"""Classifier metrics and class-independent known-reference box matching."""
import numpy as np
import torch
from torch import nn
from torchvision.ops import box_iou

def metrics(truth, predictions, labels):
    """Compute accuracy, supported-class macro-F1, balanced accuracy and confusion counts.

    Args:
        truth: Reference class indices aligned with predictions.
        predictions: Predicted class indices or detection records, as required by this function.
        labels: Class names in checkpoint output order.

    Returns:
        dict: Aggregate metrics, per-class metrics, and confusion matrix.
    """
    cm = np.zeros((len(labels), len(labels)), dtype=np.int64)
    np.add.at(cm, (truth, predictions), 1)
    support = cm.sum(1)
    predicted = cm.sum(0)
    tp = np.diag(cm)
    precision = np.divide(tp, predicted, out=np.zeros(len(labels), float), where=predicted > 0)
    recall = np.divide(tp, support, out=np.zeros(len(labels), float), where=support > 0)
    f1 = np.divide(
        2 * tp,
        support + predicted,
        out=np.zeros(len(labels), float),
        where=(support + predicted) > 0,
    )
    present = support > 0
    return {
        "accuracy": float(tp.sum() / support.sum()),
        "macro_f1_present": float(f1[present].mean()),
        "balanced_accuracy_present": float(recall[present].mean()),
        "evaluated_categories": [labels[i] for i in np.flatnonzero(present)],
        "absent_categories": [labels[i] for i in np.flatnonzero(~present)],
        "per_class": [
            {
                "category": c,
                "support": int(support[i]),
                "precision": float(precision[i]),
                "recall": float(recall[i]) if present[i] else None,
                "f1": float(f1[i]) if present[i] else None,
            }
            for i, c in enumerate(labels)
        ],
        "confusion_matrix": cm.tolist(),
    }


def evaluate(model, loader, device, labels):
    """Evaluate classification on the supplied non-test loader without gradients.

    Args:
        model: PyTorch model to inspect or evaluate.
        loader: DataLoader yielding images, targets and specimen indices.
        device: PyTorch device or device string for inference.
        labels: Class names in checkpoint output order.

    Returns:
        tuple: Metrics, specimen indices, and class probabilities in loader order.
    """
    model.eval()
    truth = []
    predictions = []
    probabilities = []
    indices = []
    loss_sum = 0
    with torch.inference_mode():
        for x, y, idx in loader:
            x = x.to(device)
            y = y.to(device)
            logits = model(x)
            if not torch.isfinite(logits).all():
                raise FloatingPointError("Nonfinite validation logits")
            loss_sum += nn.functional.cross_entropy(logits, y, reduction="sum").item()
            p = logits.softmax(1).cpu()
            truth.extend(y.cpu().tolist())
            predictions.extend(p.argmax(1).tolist())
            probabilities.extend(p.tolist())
            indices.extend(idx.tolist())
    result = metrics(truth, predictions, labels)
    result["loss"] = loss_sum / len(truth)
    return result, indices, probabilities


def metric(items):
    """Summarize known-target recovery and classification with explicit denominators.

    Args:
        items: Per-reference outcomes containing detected and correct flags.

    Returns:
        dict: Counts and rates; undefined rates are None.
    """
    found = sum(x["detected"] for x in items)
    correct = sum(x["correct"] for x in items)
    n = len(items)
    return {
        "known_specimens": n,
        "detected": found,
        "correct": correct,
        "detection_recall_iou50": found / n if n else None,
        "classification_accuracy_on_matched": correct / found if found else None,
        "end_to_end_known_specimen_success": correct / n if n else None,
    }


def match_boxes(predictions, references):
    """Match slide boxes greedily at IoU >= 0.5 without repeated credit.

    Args:
        predictions: Predicted class indices or detection records, as required by this function.
        references: Reference records containing slide-coordinate boxes.

    Returns:
        dict: Reference index to (prediction index, IoU) assignment.
    """
    if not predictions or not references:
        return {}
    p = torch.tensor([r["box_slide"] for r in predictions], dtype=torch.float32)
    t = torch.tensor([r["box_slide"] for r in references], dtype=torch.float32)
    if (
        not torch.isfinite(p).all()
        or not torch.isfinite(t).all()
        or (p[:, 2:] <= p[:, :2]).any()
        or (t[:, 2:] <= t[:, :2]).any()
    ):
        raise ValueError("Invalid boxes")
    overlap = box_iou(p, t)
    usedp = set()
    usedt = set()
    assigned = {}
    pairs = [(float(overlap[i, j]), i, j) for i, j in torch.nonzero(overlap >= 0.5).tolist()]
    for iou, i, j in sorted(pairs, reverse=True):
        if i not in usedp and j not in usedt:
            usedp.add(i)
            usedt.add(j)
            assigned[j] = (i, iou)
    return assigned

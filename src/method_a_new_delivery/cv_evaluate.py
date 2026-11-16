"""Known-specimen evaluation on held-out scans; unmarked predictions are unreviewed."""

import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path

from PIL import Image

from .cv import ROOT, DEST, read, write

from .paths import RUNS, RESULTS

THRESHOLDS = (0.25, 0.30, 0.40, 0.50, 0.75)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def score_fold(plans, raw, categories, threshold):
    import torch
    from torchvision.ops import box_iou, nms

    matches = []
    count_predictions = 0
    for plan in plans:
        source = plan["source"]
        truths = {o["record_id"]: o for o in plan["objects"]}
        candidates = []
        for crop in plan["crops"]:
            for pred in raw[crop["tile_id"]]:
                if pred["score"] < threshold:
                    continue
                b = pred["box"]
                # Discard detections centered in synthetic padding.
                cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                if not (
                    crop["pad_left"] <= cx < crop["pad_left"] + crop["side"]
                    and crop["pad_top"] <= cy < crop["pad_top"] + crop["side"]
                ):
                    continue
                # The exporter pads each native-pixel crop to 1024 without resizing it.
                bb = [
                    b[0] + crop["left"] - crop["pad_left"],
                    b[1] + crop["top"] - crop["pad_top"],
                    b[2] + crop["left"] - crop["pad_left"],
                    b[3] + crop["top"] - crop["pad_top"],
                ]
                candidates.append(
                    {
                        "box_slide": bb,
                        "score": pred["score"],
                        "category": categories[pred["class_id"]],
                    }
                )
        if candidates:
            boxes = torch.tensor([c["box_slide"] for c in candidates], dtype=torch.float32)
            scores = torch.tensor([c["score"] for c in candidates], dtype=torch.float32)
            kept = nms(boxes, scores, 0.5).tolist()
            candidates = [candidates[i] for i in kept]
        count_predictions += len(candidates)
        ids = list(truths)
        assigned = {}
        used_pred = set()
        used_truth = set()
        if candidates and ids:
            overlaps = box_iou(
                torch.tensor([c["box_slide"] for c in candidates], dtype=torch.float32),
                torch.tensor([truths[r]["box_slide"] for r in ids], dtype=torch.float32),
            )
            pairs = [
                (float(overlaps[i, j]), i, j) for i, j in torch.nonzero(overlaps >= 0.5).tolist()
            ]
            for iou, i, j in sorted(pairs, reverse=True):
                if i not in used_pred and j not in used_truth:
                    assigned[j] = (i, iou)
                    used_pred.add(i)
                    used_truth.add(j)
        for j, record_id in enumerate(ids):
            found = j in assigned
            pred = candidates[assigned[j][0]] if found else None
            matches.append(
                {
                    "record_id": record_id,
                    "source": source,
                    "true_category": truths[record_id]["category"],
                    "predicted_category": pred["category"] if pred else None,
                    "detected": found,
                    "correct": bool(found and pred["category"] == truths[record_id]["category"]),
                    "iou": assigned[j][1] if found else None,
                }
            )
    assert len(matches) == len({m["record_id"] for m in matches})
    detected = sum(m["detected"] for m in matches)
    correct = sum(m["correct"] for m in matches)
    classes = sorted({m["true_category"] for m in matches})
    per_class = []
    for name in classes:
        group = [m for m in matches if m["true_category"] == name]
        per_class.append(
            {
                "category": name,
                "support": len(group),
                "slide_support": len({m["source"] for m in group}),
                "detected": sum(m["detected"] for m in group),
                "correct": sum(m["correct"] for m in group),
            }
        )
    summary = {
        "known_specimens": len(matches),
        "held_out_scans": len(plans),
        "detected": detected,
        "correct": correct,
        "known_recall_iou50": detected / len(matches),
        "end_to_end_success": correct / len(matches),
        "class_accuracy_among_matches": correct / detected if detected else None,
        "predictions_after_nms": count_predictions,
        "unmatched_predictions_unreviewed": count_predictions - detected,
        "threshold": threshold,
        "match_iou": 0.5,
        "per_class": per_class,
        "interpretation": "Sparse labels: unmatched predictions are unreviewed, not verified false positives.",
    }
    return summary, matches


def main():
    from rfdetr_plus.models.detection import RFDETR2XLarge

    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=range(5))
    args = parser.parse_args()
    fold = args.fold
    output = RESULTS / f"fold_{fold}"
    output.mkdir(parents=True, exist_ok=False)
    fold_data = DEST / f"fold_{fold}"
    manifest = read(fold_data / "manifest.json")
    status = read(RUNS / "cv" / f"fold_{fold}" / "status.json")
    checkpoint = RUNS / "cv" / f"fold_{fold}" / "checkpoint_final_ema.pth"
    assert status["status"] == "completed"
    assert sha256(checkpoint) == status["checkpoint_sha256"]
    model = RFDETR2XLarge(pretrain_weights=str(checkpoint), num_classes=28, resolution=1000)
    cats = sorted(
        read(fold_data / "valid" / "_annotations.coco.json")["categories"],
        key=lambda item: item["id"],
    )
    categories = {index: cat["name"] for index, cat in enumerate(cats)}
    plans = [
        read(path)
        for path in sorted((ROOT / "plan").glob("*.json"))
        if read(path)["source"] in manifest["held_out_scans"]
    ]
    assert len(plans) == 4
    raw = {}
    invalid = 0
    for plan in plans:
        for crop in plan["crops"]:
            name = crop["tile_id"] + ".png"
            with Image.open(fold_data / "valid" / name) as image:
                result = model.predict(image.convert("RGB"), threshold=0.25)
            values = []
            for box, confidence, category in zip(result.xyxy, result.confidence, result.class_id):
                cid = int(category)
                if cid == 28:
                    invalid += 1
                    continue
                assert 0 <= cid < 28
                values.append(
                    {"box": [float(x) for x in box], "score": float(confidence), "class_id": cid}
                )
            raw[crop["tile_id"]] = values
    with gzip.open(output / "raw_predictions.json.gz", "wt", compresslevel=6) as handle:
        json.dump(raw, handle)
    summaries = []
    for threshold in THRESHOLDS:
        summary, matches = score_fold(plans, raw, categories, threshold)
        assert summary["known_specimens"] == manifest["held_out_source_objects"]
        summary.update(
            fold=fold,
            checkpoint_sha256=status["checkpoint_sha256"],
            invalid_slot_predictions=invalid,
            test_used=False,
        )
        tag = f"confidence_{threshold:.2f}"
        write(output / f"{tag}_summary.json", summary)
        write(output / f"{tag}_matches.json", matches)
        summaries.append(summary)
    write(
        output / "summary.json",
        {
            "fold": fold,
            "status": "completed",
            "held_out_scans": manifest["held_out_scans"],
            "thresholds": list(THRESHOLDS),
            "results": [
                {
                    "threshold": s["threshold"],
                    "known": s["known_specimens"],
                    "detected": s["detected"],
                    "correct": s["correct"],
                }
                for s in summaries
            ],
            "checkpoint_sha256": status["checkpoint_sha256"],
            "test_used": False,
        },
    )
    print(json.dumps(read(output / "summary.json"), indent=2))


if __name__ == "__main__":
    main()

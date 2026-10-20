"""Score known validation references on the same ROI grid as Method B."""

from __future__ import annotations

import collections
import json
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

from focus_helpers import sha256_file
from spring_nms import deduplicate
from spring_types import Detection, TileSpec


ROOT = Path("/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_focus_stack_v1")
DATA = ROOT / "dataset"
RUN = ROOT / "run_artifacts/detector"
OUTPUT = Path("/home/yk86/method_a_reproduction") / f"validation_reproduction_{uuid.uuid4().hex}"
CONFIDENCE = 0.5
MATCH_IOU = 0.5


def main() -> None:
    import torch
    from torchvision.ops import box_iou
    from rfdetr_plus.models.detection import RFDETR2XLarge

    if not torch.cuda.is_available() or not (RUN / "status.json").is_file():
        raise RuntimeError("Completed training and a Slurm GPU are required")
    train_status = json.loads((RUN / "status.json").read_text())
    if train_status["status"] != "completed":
        raise RuntimeError("Detector training is incomplete")
    checkpoint = RUN / "checkpoint_best_total.pth"
    if sha256_file(checkpoint) != train_status["checkpoint_best_total_sha256"]:
        raise ValueError("Trained checkpoint hash changed")
    if OUTPUT.exists():
        raise FileExistsError("Validation output directory already exists")
    OUTPUT.mkdir()
    detector = RFDETR2XLarge(pretrain_weights=str(checkpoint), num_classes=28, resolution=1000)
    category_map = json.loads((ROOT / "inputs/broad_category_map.json").read_text())
    grouped = collections.defaultdict(list)
    for path in sorted((ROOT / "plan").glob("*.json")):
        plan = json.loads(path.read_text())
        if plan["split"] == "valid":
            grouped[plan["source_image"]].extend(plan["tiles"])
    if sum(map(len, grouped.values())) != 1432:
        raise ValueError("Validation grid differs from Method B")
    predictions, matches = [], []
    for source, tiles in sorted(grouped.items()):
        truth = {}
        by_tile = {}
        origin = {}
        for tile in tiles:
            image_path = DATA / "valid" / f"{tile['tile_id']}.png"
            if not image_path.is_file() or not image_path.is_symlink():
                raise FileNotFoundError("Shared validation image link changed")
            for label in tile["objects"]:
                truth[label["record_id"]] = {
                    "box": label["box_slide"], "category": label["broad_category"]}
            with Image.open(image_path) as handle:
                detected = detector.predict(handle.convert("RGB"), threshold=CONFIDENCE)
            spec = TileSpec(tile["left"], tile["top"], 1024, 1024, tile["left"], tile["top"])
            by_tile[spec] = []
            for box, score, class_id in zip(detected.xyxy, detected.confidence, detected.class_id):
                local = [float(v) for v in box]
                slide_box = [local[0] + tile["left"], local[1] + tile["top"],
                             local[2] + tile["left"], local[3] + tile["top"]]
                detection = Detection(*slide_box, float(score), 0., 0., 0., 0.)
                by_tile[spec].append(detection)
                class_id = int(class_id)
                if not 0 <= class_id < 28:
                    raise ValueError("Predicted category ID outside shared mapping")
                origin[id(detection)] = {
                    "box_slide": slide_box, "score": float(score), "source": source,
                    "category_id": class_id, "category": category_map[str(class_id)],
                    "tile_id": tile["tile_id"],
                }
        candidates = [origin[id(detection)] for detection in deduplicate(by_tile, MATCH_IOU)]
        ids = list(truth)
        if candidates and ids:
            overlap = box_iou(torch.tensor([item["box_slide"] for item in candidates]),
                              torch.tensor([truth[ident]["box"] for ident in ids]))
            pairs = [(float(overlap[i, j]), i, j)
                     for i, j in torch.nonzero(overlap >= MATCH_IOU).tolist()]
            assigned, used_candidates, used_targets = {}, set(), set()
            for iou, i, j in sorted(pairs, reverse=True):
                if i not in used_candidates and j not in used_targets:
                    assigned[j] = (i, iou)
                    used_candidates.add(i)
                    used_targets.add(j)
            for j, ident in enumerate(ids):
                candidate = candidates[assigned[j][0]] if j in assigned else None
                matches.append({
                    "record_id": ident, "source": source,
                    "true_category": truth[ident]["category"],
                    "detected": candidate is not None,
                    "predicted_category": candidate["category"] if candidate else None,
                    "category_correct": candidate is not None and candidate["category"] == truth[ident]["category"],
                    "iou": assigned[j][1] if candidate else None,
                })
            for i, item in enumerate(candidates):
                item["matched_known_reference"] = i in used_candidates
        else:
            matches.extend({"record_id": ident, "source": source,
                            "true_category": item["category"], "detected": False,
                            "predicted_category": None, "category_correct": False, "iou": None}
                           for ident, item in truth.items())
        predictions.extend(candidates)
        print(json.dumps({"source": source, "known": len(truth),
                          "predictions": len(candidates)}), flush=True)
    known = len(matches)
    if known != 274:
        raise ValueError("Known validation reference coverage differs from Method B grid")
    found = sum(item["detected"] for item in matches)
    correct = sum(item["category_correct"] for item in matches)
    summary = {
        "status": "complete", "scope": "shared fixed-grid annotated-ROI validation",
        "known_specimens": known,
        "known_specimen_recall_iou50": found / known,
        "classification_accuracy_on_matched": correct / found if found else None,
        "end_to_end_known_specimen_success": correct / known,
        "confidence_threshold": CONFIDENCE, "match_iou": MATCH_IOU,
        "deduplication": "same Spring boundary-aware union-find as Method B",
        "checkpoint_sha256": train_status["checkpoint_best_total_sha256"],
        "unmatched_predictions": "unreviewed; not automatically false positives",
        "test_used": False,
    }
    (OUTPUT / "predictions.json").write_text(json.dumps(predictions) + "\n")
    (OUTPUT / "known_reference_results.json").write_text(json.dumps(matches) + "\n")
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()

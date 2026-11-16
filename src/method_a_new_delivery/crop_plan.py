"""Plan A3-style context crops for mapped priority objects in new scans."""

import collections
import csv
import hashlib
import json
import math
import random
from pathlib import Path

import openslide

from .focus_helpers import crc32_file

from .paths import PREP as ROOT, TRAINING

SEED = 20261113


def overlap(box, left, top, side):
    x0, y0 = max(box[0], left), max(box[1], top)
    x1, y1 = min(box[2], left + side), min(box[3], top + side)
    return max(0, x1 - x0) * max(0, y1 - y0)


def main():
    grouped = collections.defaultdict(list)
    with (ROOT / "priority_32_objects.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grouped[row["scan_path"]].append(row)
    report = {
        "scans": len(grouped),
        "source_boxes": sum(map(len, grouped.values())),
        "planned_crops": 0,
        "label_instances": 0,
    }
    for index, (path, records) in enumerate(sorted(grouped.items())):
        source = Path(path)
        annotation = Path(records[0]["annotation_path"])
        if any(row["annotation_path"] != str(annotation) for row in records):
            raise ValueError(f"Multiple annotation files for {source}")
        with openslide.OpenSlide(str(source)) as slide:
            width, height = slide.dimensions
        stat = source.stat()
        objects = []
        for row in records:
            box = [
                float(row[key]) for key in ("bbox_x_min", "bbox_y_min", "bbox_x_max", "bbox_y_max")
            ]
            if not (0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height):
                raise ValueError(f"Invalid target box in {source}")
            objects.append(
                {
                    "record_id": f"{source.name}:{row['annotation_format']}:{row['object_id']}",
                    "box_slide": box,
                    "category_id": int(row["a4_broad_class_id"]) + 1,
                    "category": row["a4_broad_category"],
                }
            )
        crops = []
        for anchor in sorted(objects, key=lambda item: item["record_id"]):
            box = anchor["box_slide"]
            needed = max(box[2] - box[0], box[3] - box[1]) + 64
            side = next((size for size in (512, 640, 768, 896, 1024) if needed <= size), None)
            if side is None:
                raise ValueError(f"Target exceeds A3 crop sizes in {source}")
            existing = next(
                (
                    crop
                    for crop in crops
                    if crop["left"] + 16 <= box[0]
                    and crop["top"] + 16 <= box[1]
                    and crop["left"] + crop["side"] - 16 >= box[2]
                    and crop["top"] + crop["side"] - 16 >= box[3]
                ),
                None,
            )
            if existing:
                existing["anchor_record_ids"].append(anchor["record_id"])
                continue
            low_x = max(0, math.ceil(box[2] + 32 - side))
            high_x = min(width - side, math.floor(box[0] - 32))
            low_y = max(0, math.ceil(box[3] + 32 - side))
            high_y = min(height - side, math.floor(box[1] - 32))
            if low_x > high_x or low_y > high_y:
                raise ValueError(f"No valid crop around {anchor['record_id']}")
            rng = random.Random(f"{SEED}:{anchor['record_id']}")
            candidates = []
            for attempt in range(128):
                left, top = rng.randint(low_x, high_x), rng.randint(low_y, high_y)
                partial = sum(
                    0
                    < overlap(obj["box_slide"], left, top, side)
                    < (obj["box_slide"][2] - obj["box_slide"][0])
                    * (obj["box_slide"][3] - obj["box_slide"][1])
                    - 1e-6
                    for obj in objects
                )
                candidates.append((partial, attempt, left, top))
            partial, _, left, top = min(candidates)
            pad_left, pad_top = rng.randint(0, 1024 - side), rng.randint(0, 1024 - side)
            tile_id = hashlib.sha256(
                f"{source}:{left}:{top}:{side}:{pad_left}:{pad_top}:log5-sparse-v1".encode()
            ).hexdigest()[:24]
            crop = {
                "tile_id": tile_id,
                "source": str(source),
                "left": left,
                "top": top,
                "side": side,
                "pad_left": pad_left,
                "pad_top": pad_top,
                "anchor_record_ids": [anchor["record_id"]],
                "matched_anchors": [],
                "objects": [],
                "known_partial_boxes": partial,
            }
            for obj in objects:
                box = obj["box_slide"]
                covered = overlap(box, left, top, side)
                if covered <= 0:
                    continue
                x0, y0 = max(box[0], left) - left + pad_left, max(box[1], top) - top + pad_top
                x1, y1 = (
                    min(box[2], left + side) - left + pad_left,
                    min(box[3], top + side) - top + pad_top,
                )
                area = (box[2] - box[0]) * (box[3] - box[1])
                crop["objects"].append(
                    {
                        **obj,
                        "bbox": [x0, y0, x1 - x0, y1 - y0],
                        "visible_fraction": covered / area,
                    }
                )
            crops.append(crop)
        plan = {
            "index": index,
            "source": str(source),
            "annotation": str(annotation),
            "annotation_crc32": crc32_file(annotation),
            "source_stat": [stat.st_size, stat.st_mtime_ns, stat.st_ino],
            "width": width,
            "height": height,
            "objects": objects,
            "crops": crops,
        }
        for crop in crops:
            for record_id in crop["anchor_record_ids"]:
                if not any(
                    obj["record_id"] == record_id and abs(obj["visible_fraction"] - 1) < 1e-8
                    for obj in crop["objects"]
                ):
                    raise ValueError(f"Anchor cut in {crop['tile_id']}")
        (TRAINING / "plan" / f"{index:02d}.json").write_text(json.dumps(plan))
        report["planned_crops"] += len(crops)
        report["label_instances"] += sum(len(crop["objects"]) for crop in crops)
    (TRAINING / "plan_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

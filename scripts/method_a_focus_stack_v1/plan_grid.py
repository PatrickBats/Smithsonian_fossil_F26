"""Rebuild the Method B Sp26 ROI grid with 28-class Method A box labels.

This reads the frozen 2,283-record assignment and original NDPA/NDPI metadata.
It verifies that every planned tile is exactly one currently exported Method B
LoG-fused PNG, without copying any source or derived image.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import openslide

from focus_helpers import crc32_file, geometry, sha256_file


ROOT = Path("/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_focus_stack_v1")
IMAGE_ROOT = Path("/rhf/allocations/dsci435/Smithsonian_F26/model_B/data/abbas_focus_stack_v1")
SIDE = 1024
STRIDE = int(SIDE * 0.9)
EXPECTED_RECORD_SHA = "d2dedb6bbb7e4c0e6c428c0d1cd4fce77d1f34bc6a829a515b172078913628f2"


def positions(start: int, end: int) -> list[int]:
    if end - start < SIDE:
        return []
    return sorted({min(p, end - SIDE) for p in range(start, end, STRIDE)})


def rectangle(annotation: ET.Element):
    if annotation.get("type") != "freehand":
        return None
    pts = [(float(p.findtext("x")), float(p.findtext("y"))) for p in annotation.findall(".//point")]
    if len(pts) < 4:
        return None
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    corners = [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]
    if x1 <= x0 or y1 <= y0:
        return None
    if not all(any(abs(x - cx) <= 1 and abs(y - cy) <= 1 for cx, cy in corners) for x, y in pts):
        return None
    if not all(any(abs(x - cx) <= 1 and abs(y - cy) <= 1 for x, y in pts) for cx, cy in corners):
        return None
    return x0, y0, x1, y1


def main() -> None:
    input_path = ROOT / "inputs/priority_records.csv"
    if sha256_file(input_path) != EXPECTED_RECORD_SHA:
        raise ValueError("Method B assignment binding changed")
    with input_path.open(newline="", encoding="utf-8") as stream:
        records = list(csv.DictReader(stream))
    if len(records) != 2283:
        raise ValueError("Wrong adopted record count")
    grouped = collections.defaultdict(list)
    for row in records:
        grouped[row["image_nots_path"]].append(row)
    if len(grouped) != 75:
        raise ValueError("Wrong number of exact source image files")
    plan_dir = ROOT / "plan"
    if plan_dir.exists():
        raise FileExistsError("Plan directory must be new")
    plan_dir.mkdir()
    counts = collections.Counter()
    covered_by_split = collections.defaultdict(set)
    excluded = []
    for index, (image_path, rows) in enumerate(sorted(grouped.items())):
        split = rows[0]["method_a_split"]
        if {row["method_a_split"] for row in rows} != {split}:
            raise ValueError("Source image crosses partitions")
        if split == "test":
            counts["reserved_test_source_files"] += 1
            continue
        annotation_path = Path(rows[0]["annotation_nots_path"])
        if {row["annotation_nots_path"] for row in rows} != {str(annotation_path)}:
            raise ValueError("One source image has multiple annotation versions")
        if crc32_file(annotation_path) != rows[0]["annotation_crc32"]:
            raise ValueError("Source NDPA CRC changed")
        states = list(ET.fromstring(annotation_path.read_bytes()).iter("ndpviewstate"))
        by_id = {state.get("id"): state for state in states}
        with openslide.OpenSlide(image_path) as slide:
            width, height = slide.dimensions
            if float(slide.properties["openslide.objective-power"]) != 40:
                raise ValueError("Expected native 40x image")
            xnm = float(slide.properties["openslide.mpp-x"]) * 1000
            ynm = float(slide.properties["openslide.mpp-y"]) * 1000
            xoff = float(slide.properties["hamamatsu.XOffsetFromSlideCentre"])
            yoff = float(slide.properties["hamamatsu.YOffsetFromSlideCentre"])

            def xy(x_nm: float, y_nm: float):
                return (x_nm - xoff) / xnm + width / 2, (y_nm - yoff) / ynm + height / 2

            objects = []
            for row in rows:
                annotation = by_id[row["viewstate_id"]].find("annotation")
                if annotation is None or annotation.get("type") != "circle":
                    raise ValueError("Shared target is not a source NDPA circle")
                for key, field in (("x", "x_nm"), ("y", "y_nm"), ("radius", "radius_nm")):
                    if float(annotation.findtext(key)) != float(row[field]):
                        raise ValueError("Source circle geometry changed")
                cx, cy, rx, ry = geometry(slide, row)
                box = [cx - rx, cy - ry, cx + rx, cy + ry]
                if rx <= 0 or ry <= 0 or not all(math.isfinite(v) for v in box):
                    raise ValueError("Invalid source circle geometry")
                objects.append({
                    "record_id": row["record_id"], "box_slide": box,
                    "fine_category": row["sponsor_category"],
                    "broad_category": row["broad_category"],
                    "category_id": int(row["broad_class_id"]) + 1,
                })
            grid = {}
            roi_report = []
            for state in states:
                annotation = state.find("annotation")
                if annotation is None:
                    continue
                bounds = rectangle(annotation)
                if bounds is None:
                    continue
                x0, y0 = xy(bounds[0], bounds[1])
                x1, y1 = xy(bounds[2], bounds[3])
                roi = [max(0, math.ceil(x0)), max(0, math.ceil(y0)),
                       min(width, math.floor(x1)), min(height, math.floor(y1))]
                roi_report.append({"state_id": state.get("id"), "bounds": roi})
                for top in positions(roi[1], roi[3]):
                    for left in positions(roi[0], roi[2]):
                        grid.setdefault((left, top), []).append(state.get("id"))
            if not roi_report:
                raise ValueError("No rectangular source ROI")
            tiles = []
            covered = set()
            for (left, top), roi_ids in sorted(grid.items(), key=lambda p: (p[0][1], p[0][0])):
                labels = []
                for obj in objects:
                    b = obj["box_slide"]
                    x0, y0 = max(0.0, b[0] - left), max(0.0, b[1] - top)
                    x1, y1 = min(float(SIDE), b[2] - left), min(float(SIDE), b[3] - top)
                    area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
                    fraction = area / ((b[2] - b[0]) * (b[3] - b[1]))
                    if area >= 16 and fraction > 0.25:
                        labels.append({**obj, "bbox": [x0, y0, x1 - x0, y1 - y0],
                                       "area": area, "visible_fraction": fraction})
                        covered.add(obj["record_id"])
                identity = f"{image_path}:{left}:{top}:{SIDE}:abbas-log-k5"
                tile_id = hashlib.sha256(identity.encode()).hexdigest()[:24]
                tiles.append({
                    "tile_id": tile_id, "image": image_path, "annotation": str(annotation_path),
                    "annotation_crc32": rows[0]["annotation_crc32"],
                    "split": split, "group": rows[0]["accession_group_id"],
                    "left": left, "top": top, "size": SIDE, "roi_ids": roi_ids,
                    "objects": labels, "anchors": [label["record_id"] for label in labels],
                    "identity": identity, "representation": "abbas_log_focus_stack_k5",
                })
            covered_by_split[split].update(covered)
            excluded.extend({"record_id": obj["record_id"], "split": split,
                             "image": image_path, "reason": "outside_retained_ROI_grid"}
                            for obj in objects if obj["record_id"] not in covered)
            counts[split] += len(tiles)
            counts["empty_tiles"] += sum(not tile["objects"] for tile in tiles)
            manifest = {"slide_index": index, "source_image": image_path,
                        "source_annotation": str(annotation_path), "split": split,
                        "rois": roi_report, "tiles": tiles,
                        "covered_record_ids": sorted(covered),
                        "excluded_record_ids": sorted({obj["record_id"] for obj in objects} - covered)}
            (plan_dir / f"{index:02d}.json").write_text(json.dumps(manifest) + "\n")
            print(json.dumps({"slide_index": index, "split": split, "tiles": len(tiles),
                              "covered": len(covered), "excluded": len(objects) - len(covered)}), flush=True)
    for split, expected_images in (("train", 5152), ("valid", 1432)):
        planned = {tile["tile_id"] for path in plan_dir.glob("*.json")
                   for tile in json.loads(path.read_text())["tiles"] if tile["split"] == split}
        actual = {path.stem for path in (IMAGE_ROOT / split).glob("*.png")}
        if len(planned) != expected_images or planned != actual:
            raise ValueError(f"ROI grid differs from Method B images: {split}: planned={len(planned)} actual={len(actual)}")
    report = {"status": "plan_matches_current_Method_B_grid",
              "shared_assignment_sha256": "da2062a127cf6e14945e50fff097e0db102d7f8203250b47daed6b6bb166478d",
              "fine_to_broad_sha256": "a2f8da0b40cf9a1a89ea7fffe360770b2b9eae56f9fdd307bbf1b286bd9f793d",
              "grid_images": {"train": counts["train"], "valid": counts["valid"]},
              "empty_tiles": counts["empty_tiles"],
              "covered_priority_records": {split: len(values) for split, values in covered_by_split.items()},
              "excluded_priority_records": len(excluded),
              "reserved_test_source_files": counts["reserved_test_source_files"],
              "image_source": str(IMAGE_ROOT),
              "scope": "Identical source assignment, ROI grid, and LoG fused PNGs as current Method B; boxes mapped to 28 broad categories. Test untouched.",
              }
    (ROOT / "plan_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    (ROOT / "excluded_records.json").write_text(json.dumps(excluded, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

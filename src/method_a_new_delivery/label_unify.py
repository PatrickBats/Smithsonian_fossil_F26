"""Inventory both annotation formats as level-zero pixel boxes."""

import csv
import json
from collections import Counter
from pathlib import Path

import openslide
from .paths import MAPS, PREP, SOURCE as SOURCE_ROOT


def main():
    source = SOURCE_ROOT
    output = PREP
    names = {
        name: int(index)
        for index, name in json.loads((MAPS / "broad_category_map.json").read_text()).items()
    }
    fields = (
        "scan_path",
        "annotation_path",
        "annotation_format",
        "object_id",
        "raw_title",
        "exact_a4_class_id",
        "shape_type",
        "bbox_x_min",
        "bbox_y_min",
        "bbox_x_max",
        "bbox_y_max",
        "fully_inside_image",
    )
    counts = Counter()
    selected = Counter()

    with (output / "objects_pixels.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()

        for group in sorted(p for p in source.iterdir() if p.is_dir()):
            scan = next(group.glob("*.ndpi"))
            annotation = next(group.glob("*_rois.csv"))
            slide = openslide.OpenSlide(str(scan))
            width, height = slide.dimensions
            slide.close()
            with annotation.open(newline="", encoding="utf-8-sig") as source_file:
                for original in csv.DictReader(source_file):
                    counts["csv_rows"] += 1
                    shape = original["shape_type"]
                    if shape == "Point":
                        counts["points_without_box"] += 1
                        continue
                    try:
                        bounds = [
                            float(original[key])
                            for key in ("bbox_x_min", "bbox_y_min", "bbox_x_max", "bbox_y_max")
                        ]
                    except ValueError:
                        counts["missing_bounds"] += 1
                        continue
                    if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
                        counts["invalid_bounds"] += 1
                        continue
                    inside = (
                        0 <= bounds[0]
                        and 0 <= bounds[1]
                        and bounds[2] <= width
                        and bounds[3] <= height
                    )
                    title = original["text"].strip()
                    class_id = names.get(title, "")
                    row = dict(
                        zip(
                            fields,
                            (
                                str(scan),
                                str(annotation),
                                "roi_csv",
                                original["roi_id"] + ":" + original["shape_id"],
                                title,
                                class_id,
                                shape,
                                *bounds,
                                inside,
                            ),
                        )
                    )
                    writer.writerow(row)
                    counts["csv_boxes"] += 1
                    counts["csv_inside"] += inside
                    if class_id != "" and inside:
                        selected[title] += 1

        with (output / "ndpa_circles_pixels.csv").open(newline="", encoding="utf-8") as source_file:
            for original in csv.DictReader(source_file):
                row = {
                    "scan_path": original["scan_path"],
                    "annotation_path": original["annotation_path"],
                    "annotation_format": "ndpa",
                    "object_id": original["view_state_id"],
                    "raw_title": original["raw_title"],
                    "exact_a4_class_id": original["exact_a4_class_id"],
                    "shape_type": "circle",
                    "bbox_x_min": original["bbox_x_min"],
                    "bbox_y_min": original["bbox_y_min"],
                    "bbox_x_max": original["bbox_x_max"],
                    "bbox_y_max": original["bbox_y_max"],
                    "fully_inside_image": original["fully_inside_image"],
                }
                writer.writerow(row)
                counts["ndpa_boxes"] += 1
                if row["exact_a4_class_id"] != "" and row["fully_inside_image"] == "True":
                    selected[row["raw_title"]] += 1

    summary = {"counts": dict(counts), "exact_a4_inside_by_title": dict(sorted(selected.items()))}
    (output / "objects_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

"""Inventory the new detector delivery without modifying source files."""

import csv
import json
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
from .paths import MAPS, PREP, SOURCE as SOURCE_ROOT


def main():
    SOURCE = SOURCE_ROOT
    OUTPUT = PREP
    categories = json.loads((MAPS / "broad_category_map.json").read_text())
    category_to_id = {name: int(index) for index, name in categories.items()}
    counts = Counter()
    shapes = Counter()
    source_rows = []
    target_rows = []
    ndpa_titles = Counter()

    for scan in sorted(SOURCE.rglob("*.ndpi")):
        csv_files = list(scan.parent.glob("*_rois.csv")) if scan.parent != SOURCE else []
        annotation = scan.with_name(scan.name + ".ndpa")
        if scan.parent != SOURCE and (len(csv_files) != 1 or annotation.exists()):
            raise ValueError(f"Unexpected annotation layout for {scan}")
        if scan.parent == SOURCE and (csv_files or not annotation.exists()):
            raise ValueError(f"Unexpected annotation layout for {scan}")

        source_rows.append(
            {
                "scan_path": str(scan),
                "scan_size_bytes": scan.stat().st_size,
                "annotation_path": str(csv_files[0] if csv_files else annotation),
                "annotation_format": "roi_csv" if csv_files else "ndpa",
            }
        )
        if csv_files:
            with csv_files[0].open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    label = row["text"].strip()
                    counts[label] += 1
                    shapes[row["shape_type"]] += 1
                    if label in category_to_id:
                        target_rows.append(
                            {
                                "scan_path": str(scan),
                                "annotation_path": str(csv_files[0]),
                                "image_id": row["image_id"],
                                "roi_id": row["roi_id"],
                                "shape_id": row["shape_id"],
                                "shape_type": row["shape_type"],
                                "raw_title": label,
                                "class_id": category_to_id[label],
                                "bbox_x_min": row["bbox_x_min"],
                                "bbox_y_min": row["bbox_y_min"],
                                "bbox_x_max": row["bbox_x_max"],
                                "bbox_y_max": row["bbox_y_max"],
                            }
                        )
        else:
            root = ET.parse(annotation).getroot()
            for view in root.findall("ndpviewstate"):
                ndpa_titles[(view.findtext("title") or "").strip()] += 1

    def write_csv(name, fieldnames, rows):
        with (OUTPUT / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    write_csv("source_inventory.csv", source_rows[0].keys(), source_rows)
    write_csv("exact_28_class_roi_candidates.csv", target_rows[0].keys(), target_rows)
    write_csv(
        "roi_title_counts.csv",
        ["raw_title", "count", "exact_a4_class_id"],
        (
            {"raw_title": title, "count": count, "exact_a4_class_id": category_to_id.get(title, "")}
            for title, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ),
    )
    write_csv(
        "ndpa_title_counts.csv",
        ["raw_title", "count"],
        ({"raw_title": title, "count": count} for title, count in ndpa_titles.most_common()),
    )
    summary = {
        "scan_count": len(source_rows),
        "roi_csv_count": sum(row["annotation_format"] == "roi_csv" for row in source_rows),
        "ndpa_count": sum(row["annotation_format"] == "ndpa" for row in source_rows),
        "roi_rows": sum(counts.values()),
        "roi_blank_title_rows": counts[""],
        "roi_distinct_nonblank_titles": len(counts) - int("" in counts),
        "exact_28_class_rows": len(target_rows),
        "exact_28_class_scans": len({row["scan_path"] for row in target_rows}),
        "exact_28_class_categories": sorted({row["raw_title"] for row in target_rows}),
        "shape_counts": dict(shapes),
        "ndpa_view_states": sum(ndpa_titles.values()),
        "ndpa_distinct_nonblank_titles": len(ndpa_titles) - int("" in ndpa_titles),
    }
    (OUTPUT / "audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))

    ndpa_candidates = []
    for scan in sorted(SOURCE.glob("*.ndpi")):
        annotation = scan.with_name(scan.name + ".ndpa")
        for state in ET.parse(annotation).getroot().findall("ndpviewstate"):
            title = (state.findtext("title") or "").strip()
            if title not in category_to_id:
                continue
            for shape in state.findall("annotation"):
                if shape.get("type") != "circle":
                    continue
                ndpa_candidates.append(
                    {
                        "scan_path": str(scan),
                        "annotation_path": str(annotation),
                        "view_state_id": state.get("id"),
                        "raw_title": title,
                        "class_id": category_to_id[title],
                        "coordformat": state.findtext("coordformat"),
                        "x_nm": shape.findtext("x"),
                        "y_nm": shape.findtext("y"),
                        "radius_nm": shape.findtext("radius"),
                    }
                )

    write_csv("exact_28_class_ndpa_candidates.csv", ndpa_candidates[0].keys(), ndpa_candidates)
    print("NDPA circle candidates:", len(ndpa_candidates))


if __name__ == "__main__":
    main()

"""Convert delivered NDPA circles to pixel boxes using each source NDPI."""

import csv
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import openslide
from .paths import MAPS, PREP, SOURCE as SOURCE_ROOT


def main():
    source = SOURCE_ROOT
    output = PREP
    category_to_id = {
        name: int(index)
        for index, name in json.loads((MAPS / "broad_category_map.json").read_text()).items()
    }
    rows = []
    audit = Counter()

    for image in sorted(source.glob("*.ndpi")):
        slide = openslide.OpenSlide(str(image))
        props = slide.properties
        width, height = slide.dimensions
        scale_x = float(props["openslide.mpp-x"]) * 1000
        scale_y = float(props["openslide.mpp-y"]) * 1000
        offset_x = float(props["hamamatsu.XOffsetFromSlideCentre"])
        offset_y = float(props["hamamatsu.YOffsetFromSlideCentre"])

        for state in (
            ET.parse(image.with_name(image.name + ".ndpa")).getroot().findall("ndpviewstate")
        ):
            title = (state.findtext("title") or "").strip()
            if state.findtext("coordformat") != "nanometers":
                raise ValueError(f"Unexpected coordinate system in {image.name}")
            for annotation in state.findall("annotation"):
                audit[annotation.get("type")] += 1
                if annotation.get("type") != "circle":
                    continue
                x = width / 2 + (float(annotation.findtext("x")) - offset_x) / scale_x
                y = height / 2 + (float(annotation.findtext("y")) - offset_y) / scale_y
                radius_x = float(annotation.findtext("radius")) / scale_x
                radius_y = float(annotation.findtext("radius")) / scale_y
                bounds = (x - radius_x, y - radius_y, x + radius_x, y + radius_y)
                valid = bounds[0] < bounds[2] and bounds[1] < bounds[3]
                in_bounds = (
                    0 <= bounds[0] and 0 <= bounds[1] and bounds[2] <= width and bounds[3] <= height
                )
                rows.append(
                    {
                        "scan_path": str(image),
                        "annotation_path": str(image.with_name(image.name + ".ndpa")),
                        "view_state_id": state.get("id"),
                        "raw_title": title,
                        "exact_a4_class_id": category_to_id.get(title, ""),
                        "x_px": x,
                        "y_px": y,
                        "radius_x_px": radius_x,
                        "radius_y_px": radius_y,
                        "bbox_x_min": bounds[0],
                        "bbox_y_min": bounds[1],
                        "bbox_x_max": bounds[2],
                        "bbox_y_max": bounds[3],
                        "image_width": width,
                        "image_height": height,
                        "valid_box": valid,
                        "fully_inside_image": in_bounds,
                    }
                )
        slide.close()

    with (output / "ndpa_circles_pixels.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "shape_types": dict(audit),
        "circles": len(rows),
        "valid_boxes": sum(row["valid_box"] for row in rows),
        "fully_inside_image": sum(row["fully_inside_image"] for row in rows),
        "exact_a4_class_circles": sum(row["exact_a4_class_id"] != "" for row in rows),
        "exact_a4_class_fully_inside": sum(
            row["exact_a4_class_id"] != "" and row["fully_inside_image"] for row in rows
        ),
    }
    (output / "ndpa_geometry_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

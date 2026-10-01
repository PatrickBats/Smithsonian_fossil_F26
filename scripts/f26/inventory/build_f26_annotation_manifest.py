"""Build a source-traceable F26 annotation inventory from the sponsor ZIP.

Reads the ZIP's NDPA members, the already verified NOTS file manifest, and the
sponsor's two title/category tables. Never edits the source files or NOTS.
Run with a Python environment containing openpyxl.
"""

import collections
import argparse
import csv
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import openpyxl


def write_csv(path, fields, records):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def canonical_slide_id(name):
    """Conservatively group punctuation-only aliases of a source slide."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--file-manifest", type=Path, required=True)
    parser.add_argument("--title-counts", type=Path, required=True)
    parser.add_argument("--category-totals", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    with args.file_manifest.open(newline="", encoding="utf-8") as file:
        file_rows = {row["annotation_filename"]: row for row in csv.DictReader(file)}
    with args.title_counts.open(newline="", encoding="utf-8-sig") as file:
        title_rows = list(csv.DictReader(file))
    title_map = {}
    title_counts = {}
    for row in title_rows:
        title = row["Annotation title"]
        if title in title_map:
            raise ValueError(f"Duplicate title in sponsor mapping: {title!r}")
        title_map[title] = row["Category"]
        title_counts[title] = int(row["n"])

    workbook = openpyxl.load_workbook(args.category_totals, read_only=True, data_only=True)
    values = list(workbook.active.values)
    if values[0][:3] != ("Category", "n", "Classify"):
        raise ValueError("Unexpected category workbook header")
    categories = [(str(name), int(count), str(flag)) for name, count, flag in values[1:] if name]
    workbook.close()
    category_map = {name: (count, flag) for name, count, flag in categories}
    if len(category_map) != len(categories):
        raise ValueError("Duplicate category in sponsor workbook")
    for title, category in title_map.items():
        if category not in category_map:
            raise ValueError(f"Unrecognized sponsor category: {category!r}")

    records = []
    with zipfile.ZipFile(args.archive) as archive:
        members = sorted((info for info in archive.infolist() if info.filename.endswith(".ndpi.ndpa")), key=lambda info: info.filename)
        if set(info.filename for info in members) != set(file_rows):
            raise ValueError("ZIP annotation members differ from verified NOTS manifest")
        for info in members:
            file_row = file_rows[info.filename]
            if f"{info.CRC:08x}" != file_row["zip_annotation_crc32"]:
                raise ValueError(f"NDPA CRC mismatch: {info.filename}")
            root = ET.fromstring(archive.read(info))
            slide = info.filename.removesuffix(".ndpi.ndpa")
            split_group = canonical_slide_id(slide)
            seen_ids = set()
            for state in root.findall("ndpviewstate"):
                state_id = state.get("id")
                if not state_id or state_id in seen_ids:
                    raise ValueError(f"Missing/duplicate viewstate ID: {info.filename} {state_id}")
                seen_ids.add(state_id)
                annotation = state.find("annotation")
                if annotation is None:
                    raise ValueError(f"Missing annotation: {info.filename} {state_id}")
                kind = annotation.get("type")
                coordinate_format = state.findtext("coordformat")
                if coordinate_format != "nanometers":
                    raise ValueError(f"Unexpected coordinate units: {info.filename} {state_id}")
                raw_title = state.findtext("title") or ""
                lookup_title = raw_title.strip()
                category = title_map.get(lookup_title, "") if kind == "circle" else ""
                flag = category_map[category][1] if category else ""
                record = {
                    "record_id": f"{slide}::ndpviewstate:{state_id}",
                    "slide_id": slide,
                    "split_group_id": split_group,
                    "image_filename": file_row["image_filename"],
                    "image_nots_path": file_row["nots_image_path"],
                    "annotation_filename": info.filename,
                    "annotation_nots_path": file_row["matching_nots_annotation_path"],
                    "annotation_crc32": f"{info.CRC:08x}",
                    "viewstate_id": state_id,
                    "annotation_type": kind,
                    "coordinate_format": coordinate_format,
                    "original_title": raw_title,
                    "lookup_title": lookup_title,
                    "sponsor_category": category,
                    "sponsor_classify": flag,
                    "mapping_status": "mapped" if category else ("untitled_circle" if kind == "circle" and not lookup_title else "noncircle" if kind != "circle" else "unmapped_title"),
                    "x_nm": "", "y_nm": "", "radius_nm": "",
                    "point_count": "", "bbox_xmin_nm": "", "bbox_ymin_nm": "",
                    "bbox_xmax_nm": "", "bbox_ymax_nm": "",
                    "alias_geometry_overlap": "", "alias_title_conflict": "",
                }
                if kind == "circle":
                    x = int(annotation.findtext("x"))
                    y = int(annotation.findtext("y"))
                    radius = int(annotation.findtext("radius"))
                    if radius <= 0:
                        raise ValueError(f"Nonpositive radius: {record['record_id']}")
                    record.update(x_nm=x, y_nm=y, radius_nm=radius)
                else:
                    points = [(int(point.findtext("x")), int(point.findtext("y"))) for point in annotation.findall("./pointlist/point")]
                    if not points:
                        raise ValueError(f"Noncircle with no points: {record['record_id']}")
                    record.update(point_count=len(points), bbox_xmin_nm=min(x for x, _ in points), bbox_ymin_nm=min(y for _, y in points), bbox_xmax_nm=max(x for x, _ in points), bbox_ymax_nm=max(y for _, y in points))
                records.append(record)

    if len(records) != 11502:
        raise ValueError(f"Unexpected annotation count: {len(records)}")
    circle_rows = [r for r in records if r["annotation_type"] == "circle"]
    actual_title_counts = collections.Counter(r["lookup_title"] for r in circle_rows if r["lookup_title"])
    if actual_title_counts != title_counts:
        diffs = {title: (actual_title_counts[title], title_counts[title]) for title in actual_title_counts.keys() | title_counts.keys() if actual_title_counts[title] != title_counts[title]}
        raise ValueError(f"Sponsor title counts differ from XML: {diffs}")

    # Same-position records in punctuation-only slide aliases could represent
    # the same grain twice. Mark them; do not silently choose a title/version.
    by_geometry = collections.defaultdict(list)
    for record in circle_rows:
        key = (record["split_group_id"], record["x_nm"], record["y_nm"], record["radius_nm"])
        by_geometry[key].append(record)
    overlaps = []
    for key, group in sorted(by_geometry.items()):
        if len({r["slide_id"] for r in group}) < 2:
            continue
        title_conflict = len({r["lookup_title"] for r in group}) > 1
        for record in group:
            record["alias_geometry_overlap"] = "yes"
            record["alias_title_conflict"] = "yes" if title_conflict else "no"
        overlaps.append({
            "split_group_id": key[0], "x_nm": key[1], "y_nm": key[2], "radius_nm": key[3],
            "record_count": len(group), "title_conflict": "yes" if title_conflict else "no",
            "slide_ids": " | ".join(sorted({r["slide_id"] for r in group})),
            "record_ids": " | ".join(r["record_id"] for r in group),
            "titles": " | ".join(r["lookup_title"] or "[untitled]" for r in group),
            "categories": " | ".join(r["sponsor_category"] or "[unmapped]" for r in group),
        })

    support = []
    for name, sponsor_n, flag in categories:
        group = [r for r in circle_rows if r["sponsor_category"] == name]
        if len(group) != sponsor_n:
            raise ValueError(f"Sponsor category count differs from XML: {name}")
        support.append({
            "category": name, "classify": flag, "sponsor_n": sponsor_n,
            "manifest_n": len(group),
            "source_image_files": len({r["image_filename"] for r in group}),
            "provisional_slide_groups": len({r["split_group_id"] for r in group}),
            "records_in_alias_overlap": sum(r["alias_geometry_overlap"] == "yes" for r in group),
            "records_in_alias_title_conflict": sum(r["alias_title_conflict"] == "yes" for r in group),
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "f26_annotation_manifest.csv", list(records[0]), records)
    write_csv(args.output_dir / "f26_category_support.csv", list(support[0]), support)
    write_csv(args.output_dir / "f26_alias_overlap.csv", list(overlaps[0]), overlaps)
    print("NDPA files", len(file_rows), "records", len(records), "circles", len(circle_rows))
    print("mapped circles", sum(r["mapping_status"] == "mapped" for r in circle_rows), "untitled circles", sum(r["mapping_status"] == "untitled_circle" for r in circle_rows))
    print("YES circles", sum(r["sponsor_classify"] == "YES" for r in circle_rows), "provisional slide groups", len({r["split_group_id"] for r in records}))
    print("alias-overlap geometries", len(overlaps), "title conflicts", sum(r["title_conflict"] == "yes" for r in overlaps))


if __name__ == "__main__":
    main()

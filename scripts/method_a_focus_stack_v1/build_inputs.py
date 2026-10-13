"""Bind Method A to the existing Method B specimen split and broad labels."""

from __future__ import annotations

import collections
import csv
import hashlib
import json
from pathlib import Path


SHARED_RUN = Path("/rhf/allocations/dsci435/Smithsonian_F26/runs/broad_swin_2026-10-08/separate_slides/ordinary_baseline")
ASSIGNMENTS = SHARED_RUN / "record_assignments.csv"
FINE_TO_BROAD = SHARED_RUN / "fine_to_broad.csv"
OUT = Path("/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_focus_stack_v1/inputs")
EXPECTED_ASSIGNMENTS_SHA = "da2062a127cf6e14945e50fff097e0db102d7f8203250b47daed6b6bb166478d"
EXPECTED_MAP_SHA = "a2f8da0b40cf9a1a89ea7fffe360770b2b9eae56f9fdd307bbf1b286bd9f793d"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if sha(ASSIGNMENTS) != EXPECTED_ASSIGNMENTS_SHA or sha(FINE_TO_BROAD) != EXPECTED_MAP_SHA:
        raise ValueError("Shared assignment or broad mapping differs from Method B")
    with ASSIGNMENTS.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        records = list(reader)
    with FINE_TO_BROAD.open(newline="", encoding="utf-8") as stream:
        mapping = list(csv.DictReader(stream))
    if len(records) != 2283 or len(mapping) != 32:
        raise ValueError("Unexpected shared record or fine-category count")
    by_fine = {row["fine_category"]: row for row in mapping}
    if len(by_fine) != 32:
        raise ValueError("Duplicate fine category")
    broad_names = {}
    for row in mapping:
        broad_id = int(row["broad_class_id"])
        if broad_id in broad_names and broad_names[broad_id] != row["broad_category"]:
            raise ValueError("Broad class ID has two names")
        broad_names[broad_id] = row["broad_category"]
    if sorted(broad_names) != list(range(28)):
        raise ValueError("Expected broad class IDs 0..27")
    if {row["sponsor_category"] for row in records} != set(by_fine):
        raise ValueError("The shared assignment categories differ from broad mapping")

    split_lookup = {"train": "train", "val": "valid", "test": "test"}
    slide_split = {}
    counts = collections.Counter()
    seen = set()
    for row in records:
        if row["record_id"] in seen:
            raise ValueError("Duplicate record ID")
        seen.add(row["record_id"])
        if row["annotation_type"] != "circle" or row["sponsor_classify"] != "YES":
            raise ValueError("Nonpriority or noncircle record in shared assignment")
        split = split_lookup[row["split"]]
        previous = slide_split.setdefault(row["slide_id"], split)
        if previous != split:
            raise ValueError("A source image crosses partitions")
        mapped = by_fine[row["sponsor_category"]]
        row["method_a_split"] = split
        row["broad_class_id"] = mapped["broad_class_id"]
        row["broad_category"] = mapped["broad_category"]
        row["tile_id"] = hashlib.sha256(row["record_id"].encode()).hexdigest()[:24]
        counts[split] += 1
    if len({row["tile_id"] for row in records}) != len(records):
        raise ValueError("Tile ID collision")
    if dict(counts) != {"train": 1605, "valid": 347, "test": 331}:
        raise ValueError("Shared split counts differ")
    if len(slide_split) != 75:
        raise ValueError("Expected 75 exact image files")

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "priority_records.csv"
    if target.exists():
        raise FileExistsError(target)
    with target.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields + ["method_a_split", "broad_class_id", "broad_category", "tile_id"])
        writer.writeheader()
        writer.writerows(records)
    category_target = OUT / "broad_category_map.json"
    if category_target.exists():
        raise FileExistsError(category_target)
    category_target.write_text(json.dumps(broad_names, indent=2) + "\n", encoding="utf-8")
    summary = {
        "shared_assignment_sha256": EXPECTED_ASSIGNMENTS_SHA,
        "shared_fine_to_broad_sha256": EXPECTED_MAP_SHA,
        "priority_records_sha256": sha(target),
        "broad_category_map_sha256": sha(category_target),
        "records": len(records), "exact_source_files": len(slide_split),
        "splits": dict(counts), "broad_categories": len(broad_names),
        "scope": "Same adopted records, source files, split, and broad category mapping as Method B; original NDPI/NDPA paths retained per record.",
    }
    summary_target = OUT / "summary.json"
    if summary_target.exists():
        raise FileExistsError(summary_target)
    summary_target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

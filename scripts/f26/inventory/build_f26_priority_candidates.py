"""Build reversible priority-only candidate and exclusion manifests.

The source annotation manifest already points to ZIP-matching F26 NDPA files.
This script does not read or modify NDPI/NDPA sources and does not export crops.
"""

import collections
import argparse
import csv
from pathlib import Path


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.resolve(strict=False).is_relative_to(Path("/projects")):
        parser.error("Dataset manifests belong under RHF, not /projects")
    with args.source.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        source_fields = reader.fieldnames
        rows = list(reader)
    if not source_fields:
        raise ValueError("Missing source manifest header")

    priority = [
        row for row in rows
        if row["annotation_type"] == "circle" and row["sponsor_classify"] == "YES"
    ]
    by_geometry = collections.defaultdict(list)
    for row in priority:
        geometry = (
            row["split_group_id"], row["x_nm"],
            row["y_nm"], row["radius_nm"],
        )
        by_geometry[geometry].append(row)

    candidates = []
    exclusions = []
    for geometry, group in sorted(by_geometry.items()):
        group = sorted(group, key=lambda row: row["record_id"])
        categories = sorted({row["sponsor_category"] for row in group})
        if len(categories) > 1:
            for row in group:
                exclusions.append({
                    **row,
                    "exclusion_reason": "conflicting_priority_categories",
                    "retained_record_id": "",
                    "geometry_priority_categories": " | ".join(categories),
                })
        else:
            # Deterministic representative for an exact-geometry, same-category
            # duplicate. It is not a judgment that its raw title is more correct.
            representative = group[0]
            candidates.append(representative)
            for row in group[1:]:
                exclusions.append({
                    **row,
                    "exclusion_reason": "duplicate_priority_geometry_same_category",
                    "retained_record_id": representative["record_id"],
                    "geometry_priority_categories": categories[0],
                })

    candidates.sort(key=lambda row: row["record_id"])
    exclusions.sort(key=lambda row: row["record_id"])
    candidate_ids = {row["record_id"] for row in candidates}
    excluded_ids = {row["record_id"] for row in exclusions}
    source_ids = {row["record_id"] for row in priority}
    if candidate_ids & excluded_ids or candidate_ids | excluded_ids != source_ids:
        raise ValueError("Priority candidate/exclusion partition is invalid")
    if len(priority) != 2290 or len(candidates) != 2283 or len(exclusions) != 7:
        raise ValueError("Unexpected priority candidate/exclusion counts")
    if len({row["sponsor_category"] for row in candidates}) != 32:
        raise ValueError("A priority category was lost")
    if collections.Counter(row["exclusion_reason"] for row in exclusions) != {
        "duplicate_priority_geometry_same_category": 5,
        "conflicting_priority_categories": 2,
    }:
        raise ValueError("Unexpected exclusion reasons")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "f26_priority_candidates.csv", source_fields, candidates)
    write_csv(
        args.output_dir / "f26_priority_exclusions.csv",
        source_fields + [
            "exclusion_reason", "retained_record_id", "geometry_priority_categories"
        ],
        exclusions,
    )
    print(f"Priority records: {len(priority)}")
    print(f"Candidates: {len(candidates)}")
    print(f"Exclusions: {len(exclusions)} (5 duplicates; 2 class-conflict records)")
    print(f"Categories in candidates: {len({r['sponsor_category'] for r in candidates})}")


if __name__ == "__main__":
    main()

"""Explicit broad-v1 targets applied only after original input/split verification."""

# Project implementation: Fall 2026 Smithsonian classifier experiments.
# Model implementations: torchvision Swin-Tiny and Meta DINOv2; see NOTICE.md.

import csv
import hashlib
from pathlib import Path

MAP_SHA = "a2f8da0b40cf9a1a89ea7fffe360770b2b9eae56f9fdd307bbf1b286bd9f793d"


def apply_broad(rows, fine_labels, path):
    """Map fine categories to broad groups while preserving specimen identity and split.

    Args:
        rows: Specimen manifest records, including record IDs, labels and split membership.
        fine_labels: Ordered original category names.
        path: Path to the file to read or validate.

    Returns:
        tuple: Updated records, ordered broad labels, and mapping audit.
    """
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != MAP_SHA:
        raise ValueError("Broad-v1 mapping fingerprint changed")
    with path.open(newline="") as f:
        m = list(csv.DictReader(f))
    if [r["fine_category"] for r in m] != fine_labels or [
        int(r["fine_class_id"]) for r in m
    ] != list(range(32)):
        raise ValueError("Fine class namespace mismatch")
    by_name = {r["fine_category"]: r for r in m}
    ids = {int(r["broad_class_id"]): r["broad_category"] for r in m}
    if sorted(ids) != list(range(28)) or len(set(ids.values())) != 28:
        raise ValueError("Invalid broad namespace")
    if any(ids[int(r["broad_class_id"])] != r["broad_category"] for r in m):
        raise ValueError("Conflicting broad names")
    updated = []
    for row in rows:
        original = row["sponsor_category"]
        target = by_name[original]
        updated.append(
            {**row, "fine_category": original, "sponsor_category": target["broad_category"]}
        )
    return (
        updated,
        [ids[i] for i in range(28)],
        {
            "version": "broad_v1_draft",
            "mapping_sha256": MAP_SHA,
            "fine_categories": 32,
            "broad_categories": 28,
            "specimens_preserved": len(rows),
            "split_membership_unchanged": True,
        },
    )

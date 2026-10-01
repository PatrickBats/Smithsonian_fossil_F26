"""Check a copied F26 split bundle without NumPy, SciPy, or source images."""

import collections
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    summary = json.loads((ROOT / "split_summary.json").read_text(encoding="utf-8"))
    candidates_path = ROOT / "inputs" / "f26_priority_candidates.csv"
    exclusions_path = ROOT / "inputs" / "f26_priority_exclusions.csv"
    assert sha256(candidates_path) == summary["input_candidates_sha256"]
    assert sha256(exclusions_path) == summary["input_exclusions_sha256"]

    candidates = read_csv(candidates_path)
    exclusions = read_csv(exclusions_path)
    records = read_csv(ROOT / "record_assignments.csv")
    groups = read_csv(ROOT / "group_assignments.csv")
    coverage = read_csv(ROOT / "class_coverage.csv")
    candidate_ids = {r["record_id"] for r in candidates}
    assigned_ids = {r["record_id"] for r in records}
    excluded_ids = {r["record_id"] for r in exclusions}
    assert len(candidates) == len(records) == len(candidate_ids) == 2283
    assert len(exclusions) == len(excluded_ids) == 7
    assert candidate_ids == assigned_ids and not candidate_ids & excluded_ids
    assert len(groups) == 57 and len(coverage) == 32
    assert {r["split"] for r in records} == {"train", "val", "test"}

    by_group = collections.defaultdict(list)
    for record in records:
        by_group[record["accession_group_id"]].append(record)
    assignment = {r["accession_group_id"]: r["split"] for r in groups}
    assert len(assignment) == len(groups) == len(by_group)
    for group_id, members in by_group.items():
        assert {r["split"] for r in members} == {assignment[group_id]}
    assert collections.Counter(assignment.values()) == {"train": 40, "val": 9, "test": 8}
    assert dict(collections.Counter(r["split"] for r in records)) == summary["actual_record_counts"]

    for row in coverage:
        members = [r for r in records if r["sponsor_category"] == row["category"]]
        assert len(members) == int(row["total_records"])
        for split in ("train", "val", "test"):
            selected = [r for r in members if r["split"] == split]
            assert len(selected) == int(row[f"{split}_records"])
            assert len({r["accession_group_id"] for r in selected}) == int(row[f"{split}_groups"])
        assert int(row["test_records"]) >= 1

    assert sum(int(r["train_records"]) for r in coverage) == 1605
    assert sum(int(r["val_records"]) for r in coverage) == 347
    assert sum(int(r["test_records"]) for r in coverage) == 331
    print("Split bundle verified: 2283 records, 57 nonleaking groups, 32 categories")


if __name__ == "__main__":
    main()

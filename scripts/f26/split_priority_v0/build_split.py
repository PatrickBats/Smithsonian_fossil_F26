"""Rebuild the F26 priority-only, accession-grouped split metadata.

Run with the local base Python environment containing NumPy and SciPy:
    python build_split.py

Inputs and outputs live beside this script. No NDPI/NDPA file is opened or
modified; the script only reads two copied CSV manifests and writes metadata.
"""

import collections
import csv
import hashlib
import json
import math
import os
import re
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


ROOT = Path(os.environ.get("F26_SPLIT_ROOT", Path(__file__).resolve().parent))
INPUT_CANDIDATES = ROOT / "inputs" / "f26_priority_candidates.csv"
INPUT_EXCLUSIONS = ROOT / "inputs" / "f26_priority_exclusions.csv"
SPLITS = ("train", "val", "test")
TARGET_GROUPS = {"train": 40, "val": 9, "test": 8}
TARGET_RECORD_FRACTIONS = {"train": 0.70, "val": 0.15, "test": 0.15}
RECORD_FRACTION_BOUNDS = {
    "train": (0.65, 0.75),
    "val": (0.10, 0.20),
    "test": (0.10, 0.20),
}
MIN_TRAIN_RECORDS_PER_CATEGORY = 5
MIN_TRAIN_CATEGORY_FRACTION = 0.40
MIN_HELDOUT_RECORDS_FOR_DEPTH_CREDIT = 3
RECORD_DEVIATION_WEIGHT = 1.0
DOMINANT_GROUP_TRAIN_THRESHOLD = 0.50


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames, list(reader)


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def group_key(slide_id):
    """Keep all scans with one D#### accession together; otherwise L/R key."""
    match = re.search(r"D\d+", slide_id)
    if match:
        return match.group().lower()
    timestamp = re.search(r"_20\d{2}[-_]\d{2}[-_]\d{2}", slide_id)
    prefix = slide_id[: timestamp.start()] if timestamp else slide_id
    prefix = re.sub(r"[_-][LR]$", "", prefix, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]", "", prefix.lower())


def solve(groups, categories, group_category_counts):
    """Maximize held-out class support with hard group and size safeguards."""
    group_count = len(groups)
    category_count = len(categories)
    total_records = int(group_category_counts.sum())
    if group_count != 57 or total_records != 2283 or category_count != 32:
        raise ValueError("Unexpected candidate-group inventory")

    variable_names = []
    for group in groups:
        for split in SPLITS:
            variable_names.append(("assignment", group, split))
    for category in categories:
        for split in ("val", "test"):
            variable_names.append(("heldout_presence", category, split))
            variable_names.append(("heldout_at_least_three", category, split))
    for split in SPLITS:
        variable_names.append(("over_target", split))
        variable_names.append(("under_target", split))
    index = {name: i for i, name in enumerate(variable_names)}
    nvars = len(variable_names)

    objective = np.zeros(nvars)
    integral = np.zeros(nvars)
    upper = np.full(nvars, np.inf)
    for name, i in index.items():
        if name[0] == "assignment":
            integral[i] = 1
            upper[i] = 1
        elif name[0] == "heldout_presence":
            objective[i] = -100
            integral[i] = 1
            upper[i] = 1
        elif name[0] == "heldout_at_least_three":
            objective[i] = -20
            integral[i] = 1
            upper[i] = 1
        else:
            objective[i] = RECORD_DEVIATION_WEIGHT

    constraint_rows = []
    lows = []
    highs = []

    def constrain(coefficients, low=-np.inf, high=np.inf):
        constraint_rows.append(coefficients)
        lows.append(low)
        highs.append(high)

    for group in groups:
        constrain({index[("assignment", group, split)]: 1 for split in SPLITS}, 1, 1)

    group_record_counts = group_category_counts.sum(axis=1)
    for split in SPLITS:
        constrain(
            {index[("assignment", group, split)]: 1 for group in groups},
            TARGET_GROUPS[split], TARGET_GROUPS[split],
        )
        lower_fraction, upper_fraction = RECORD_FRACTION_BOUNDS[split]
        coefficients = {
            index[("assignment", group, split)]: int(group_record_counts[gi])
            for gi, group in enumerate(groups)
        }
        constrain(
            coefficients,
            math.ceil(total_records * lower_fraction),
            math.floor(total_records * upper_fraction),
        )
        target = round(total_records * TARGET_RECORD_FRACTIONS[split])
        constrain(
            {
                **coefficients,
                index[("over_target", split)]: -1,
                index[("under_target", split)]: 1,
            },
            target, target,
        )

    for ci, category in enumerate(categories):
        category_total = int(group_category_counts[:, ci].sum())
        largest_group_index = int(np.argmax(group_category_counts[:, ci]))
        largest_group_count = int(group_category_counts[largest_group_index, ci])
        if largest_group_count / category_total > DOMINANT_GROUP_TRAIN_THRESHOLD:
            dominant_group = groups[largest_group_index]
            constrain({index[("assignment", dominant_group, "train")]: 1}, 1, 1)
        train_counts = {
            index[("assignment", group, "train")]: int(group_category_counts[gi, ci])
            for gi, group in enumerate(groups)
            if group_category_counts[gi, ci] > 0
        }
        constrain(
            train_counts,
            max(MIN_TRAIN_RECORDS_PER_CATEGORY,
                math.ceil(category_total * MIN_TRAIN_CATEGORY_FRACTION)),
        )
        # Prefer a defined final test population over validation coverage.
        # Retipollenites has only one source group outside dominant train
        # groups, so it cannot appear independently in both held-out sets.
        test_groups = {
            index[("assignment", group, "test")]: 1
            for gi, group in enumerate(groups)
            if group_category_counts[gi, ci] > 0
        }
        constrain(test_groups, 1)
        for split in ("val", "test"):
            presence = index[("heldout_presence", category, split)]
            depth = index[("heldout_at_least_three", category, split)]
            active_groups = {
                index[("assignment", group, split)]: 1
                for gi, group in enumerate(groups)
                if group_category_counts[gi, ci] > 0
            }
            constrain({**active_groups, presence: -1}, 0)
            counts = {
                index[("assignment", group, split)]: int(group_category_counts[gi, ci])
                for gi, group in enumerate(groups)
                if group_category_counts[gi, ci] > 0
            }
            constrain({**counts, depth: -MIN_HELDOUT_RECORDS_FOR_DEPTH_CREDIT}, 0)
            constrain({depth: 1, presence: -1}, high=0)

    matrix = lil_matrix((len(constraint_rows), nvars), dtype=float)
    for row_number, coefficients in enumerate(constraint_rows):
        for column, value in coefficients.items():
            matrix[row_number, column] = value
    result = milp(
        c=objective,
        integrality=integral,
        bounds=Bounds(np.zeros(nvars), upper),
        constraints=LinearConstraint(matrix.tocsr(), lows, highs),
        options={"time_limit": 60.0, "mip_rel_gap": 0.01},
    )
    if result.x is None or result.status not in (0, 1):
        raise RuntimeError(f"Split optimization failed: {result.message}")

    assignment = {}
    for group in groups:
        chosen = [
            split for split in SPLITS
            if result.x[index[("assignment", group, split)]] > 0.5
        ]
        if len(chosen) != 1:
            raise ValueError(f"Invalid assignment for {group}: {chosen}")
        assignment[group] = chosen[0]
    return assignment, {
        "scipy_version": scipy.__version__,
        "solver_status": int(result.status),
        "solver_message": result.message,
        "objective": float(result.fun),
        "mip_gap": None if result.mip_gap is None else float(result.mip_gap),
    }


def main():
    if ROOT.resolve(strict=False).is_relative_to(Path("/projects")):
        raise RuntimeError("Do not store row-level split data under /projects; set F26_SPLIT_ROOT to an RHF data path")
    candidate_fields, records = read_csv(INPUT_CANDIDATES)
    _, exclusions = read_csv(INPUT_EXCLUSIONS)
    if not candidate_fields or len(records) != 2283 or len(exclusions) != 7:
        raise ValueError("Input manifests do not match the reviewed priority inventory")
    record_ids = {row["record_id"] for row in records}
    excluded_ids = {row["record_id"] for row in exclusions}
    if len(record_ids) != len(records) or record_ids & excluded_ids:
        raise ValueError("Duplicate or overlapping input record IDs")

    for row in records:
        if row["sponsor_classify"] != "YES" or row["annotation_type"] != "circle":
            raise ValueError("Non-priority record in candidate input")
    groups = sorted({group_key(row["slide_id"]) for row in records})
    categories = sorted({row["sponsor_category"] for row in records})
    group_index = {group: i for i, group in enumerate(groups)}
    category_index = {category: i for i, category in enumerate(categories)}
    counts = np.zeros((len(groups), len(categories)), dtype=int)
    for row in records:
        counts[group_index[group_key(row["slide_id"])], category_index[row["sponsor_category"]]] += 1

    assignment, solver = solve(groups, categories, counts)
    assigned_records = [
        {**row, "accession_group_id": group_key(row["slide_id"]),
         "split": assignment[group_key(row["slide_id"])]}
        for row in records
    ]
    assigned_records.sort(key=lambda row: row["record_id"])
    by_group = collections.defaultdict(list)
    for row in assigned_records:
        by_group[row["accession_group_id"]].append(row)
    group_rows = []
    for group in groups:
        members = by_group[group]
        group_rows.append({
            "accession_group_id": group,
            "split": assignment[group],
            "priority_record_count": len(members),
            "source_image_file_count": len({r["image_nots_path"] for r in members}),
            "normalized_image_group_count": len({r["split_group_id"] for r in members}),
            "slide_ids": " | ".join(sorted({r["slide_id"] for r in members})),
            "categories_present": len({r["sponsor_category"] for r in members}),
        })

    coverage_rows = []
    for category in categories:
        members = [r for r in assigned_records if r["sponsor_category"] == category]
        row = {"category": category, "total_records": len(members)}
        for split in SPLITS:
            subset = [r for r in members if r["split"] == split]
            row[f"{split}_records"] = len(subset)
            row[f"{split}_groups"] = len({r["accession_group_id"] for r in subset})
        coverage_rows.append(row)

    split_record_counts = collections.Counter(r["split"] for r in assigned_records)
    split_group_counts = collections.Counter(assignment.values())
    if split_group_counts != TARGET_GROUPS:
        raise ValueError("Incorrect group counts")
    if sum(split_record_counts.values()) != 2283:
        raise ValueError("Lost priority records")
    if any(
        row["train_records"] < max(
            MIN_TRAIN_RECORDS_PER_CATEGORY,
            math.ceil(row["total_records"] * MIN_TRAIN_CATEGORY_FRACTION),
        )
        for row in coverage_rows
    ):
        raise ValueError("Training class coverage constraint failed")
    if any(row["test_records"] < 1 for row in coverage_rows):
        raise ValueError("A priority category is absent from the test split")
    for ci, category in enumerate(categories):
        total = int(counts[:, ci].sum())
        gi = int(np.argmax(counts[:, ci]))
        if int(counts[gi, ci]) / total > DOMINANT_GROUP_TRAIN_THRESHOLD:
            if assignment[groups[gi]] != "train":
                raise ValueError(f"Dominant group for {category} was not trained")
    if len({r["record_id"] for r in assigned_records}) != 2283:
        raise ValueError("Record duplication in assignment")
    if any(len({r["split"] for r in members}) != 1 for members in by_group.values()):
        raise ValueError("Accession group leaked across partitions")

    summary = {
        "status": "draft_for_review",
        "input_candidates_sha256": sha256(INPUT_CANDIDATES),
        "input_exclusions_sha256": sha256(INPUT_EXCLUSIONS),
        "group_rule": "D#### accession prefix; otherwise normalized scan prefix with timestamp and terminal L/R removed",
        "grouping_rationale": "Conservative shared-accession grouping; distinct L/R images stay in the same partition when their accession matches",
        "target_group_counts": TARGET_GROUPS,
        "target_record_fractions": TARGET_RECORD_FRACTIONS,
        "record_fraction_bounds": RECORD_FRACTION_BOUNDS,
        "minimum_train_records_per_category": MIN_TRAIN_RECORDS_PER_CATEGORY,
        "minimum_train_category_fraction": MIN_TRAIN_CATEGORY_FRACTION,
        "dominant_group_train_threshold": DOMINANT_GROUP_TRAIN_THRESHOLD,
        "minimum_test_source_groups_per_category": 1,
        "heldout_depth_credit_at_records": MIN_HELDOUT_RECORDS_FOR_DEPTH_CREDIT,
        "record_deviation_objective_weight": RECORD_DEVIATION_WEIGHT,
        "solver": solver,
        "actual_group_counts": dict(split_group_counts),
        "actual_record_counts": dict(split_record_counts),
        "heldout_categories_with_at_least_one_record": {
            split: sum(row[f"{split}_records"] >= 1 for row in coverage_rows)
            for split in ("val", "test")
        },
        "heldout_categories_with_at_least_three_records": {
            split: sum(row[f"{split}_records"] >= 3 for row in coverage_rows)
            for split in ("val", "test")
        },
    }
    write_csv(
        ROOT / "group_assignments.csv",
        ["accession_group_id", "split", "priority_record_count", "source_image_file_count",
         "normalized_image_group_count", "slide_ids", "categories_present"],
        group_rows,
    )
    write_csv(ROOT / "record_assignments.csv", candidate_fields + ["accession_group_id", "split"], assigned_records)
    write_csv(
        ROOT / "class_coverage.csv",
        ["category", "total_records", "train_records", "train_groups", "val_records",
         "val_groups", "test_records", "test_groups"],
        coverage_rows,
    )
    (ROOT / "split_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

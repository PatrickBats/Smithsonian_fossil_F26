"""Aggregate Method A validation results without exposing specimen identities.

Example:
    python analyze_validation.py --results known_reference_results.json \
        --train-coco _annotations.coco.json

Slides are displayed by original filename only, without source directories. Training
record counts are deduplicated within each category; annotation counts include
repeated instances of a specimen in overlapping tiles. Validation recall is
known-object localization recall, independent of predicted category correctness.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path, PureWindowsPath
import sys


def load_json(path: Path):
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, ValueError):
        raise ValueError("Unable to read a supplied JSON input.") from None


def text_field(row: dict, field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid {field} field.")
    return value


def category_label(name: str) -> str:
    # Reject path-shaped labels rather than inadvertently printing source paths.
    if "/" in name or "\\" in name or ":" in name:
        raise ValueError("Category names must not contain paths.")
    return " ".join(name.split())


def training_counts(coco):
    if not isinstance(coco, dict):
        raise ValueError("Training COCO input must be an object.")
    categories = coco.get("categories")
    annotations = coco.get("annotations")
    if not isinstance(categories, list) or not isinstance(annotations, list):
        raise ValueError("Training COCO requires categories and annotations lists.")
    names = {}
    for row in categories:
        if not isinstance(row, dict) or type(row.get("id")) is not int:
            raise ValueError("Invalid COCO category entry.")
        ident = row["id"]
        name = text_field(row, "name")
        category_label(name)
        if ident in names or name in names.values():
            raise ValueError("Duplicate COCO category ID or name.")
        names[ident] = name
    counts = Counter()
    records = defaultdict(set)
    record_categories = {}
    for row in annotations:
        if not isinstance(row, dict) or type(row.get("category_id")) is not int:
            raise ValueError("Invalid training annotation category.")
        ident = row["category_id"]
        if ident not in names:
            raise ValueError("Training annotation references an unknown category.")
        record = text_field(row, "record_id")
        if record in record_categories and record_categories[record] != ident:
            raise ValueError("A training record has conflicting categories.")
        record_categories[record] = ident
        counts[ident] += 1
        records[ident].add(record)
    return {name: (counts[ident], len(records[ident]))
            for ident, name in names.items()}


def validation_counts(results):
    if not isinstance(results, list):
        raise ValueError("Validation input must be a list of known-reference results.")
    categories = defaultdict(Counter)
    slides = defaultdict(Counter)
    category_slides = defaultdict(Counter)
    seen = set()
    for row in results:
        if not isinstance(row, dict):
            raise ValueError("Invalid validation result entry.")
        record = text_field(row, "record_id")
        if record in seen:
            raise ValueError("Duplicate validation record; expected one row per object.")
        seen.add(record)
        category = text_field(row, "true_category")
        category_label(category)
        source = text_field(row, "source")
        detected = row.get("detected")
        if type(detected) is not bool:
            raise ValueError("Validation detected field must be a JSON boolean.")
        for counter in (categories[category], slides[source],
                        category_slides[category, source]):
            counter["total"] += 1
            counter["detected"] += int(detected)
    return categories, slides, category_slides


def recall(counter) -> str:
    total = counter["total"]
    return f"{100 * counter['detected'] / total:.2f}%" if total else "N/A"


def print_table(title: str, headers, rows) -> None:
    print(f"\n{title}")
    print("\t".join(headers))
    for row in rows:
        print("\t".join(str(value) for value in row))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=Path,
                        help="Path to known_reference_results.json")
    parser.add_argument("--train-coco", required=True, type=Path,
                        help="Path to training _annotations.coco.json")
    args = parser.parse_args()
    try:
        training = training_counts(load_json(args.train_coco))
        categories, slides, category_slides = validation_counts(load_json(args.results))
        # Handle both POSIX and Windows source paths without exposing directories.
        slide_labels = {source: PureWindowsPath(source).name
                        for source in sorted(slides)}
        all_categories = sorted(set(training) | set(categories))
        labels = {name: category_label(name) for name in all_categories}
        if len(set(labels.values())) != len(labels):
            raise ValueError("Category display labels are ambiguous.")
    except ValueError as error:
        print(f"Input error: {error}", file=sys.stderr)
        return 2

    print("Known-object localization recall; predicted class correctness is not used.")
    print("Slides use original filenames only; source directories and record IDs are omitted.")
    print_table("Training counts", ("Category", "Annotations", "Unique records"),
                ((labels[name], *training.get(name, (0, 0))) for name in all_categories))
    print_table("Validation recall by category", ("Category", "Detected", "Total", "Recall"),
                ((labels[name], categories[name]["detected"], categories[name]["total"],
                  recall(categories[name])) for name in all_categories))
    print_table("Validation recall by source slide", ("Slide", "Detected", "Total", "Recall"),
                ((slide_labels[source], slides[source]["detected"], slides[source]["total"],
                  recall(slides[source])) for source in sorted(slides)))
    print_table("Validation category-by-slide breakdown (observed pairs)",
                ("Category", "Slide", "Detected", "Total", "Recall"),
                ((labels[name], slide_labels[source], counter["detected"], counter["total"],
                  recall(counter))
                 for (name, source), counter in sorted(category_slides.items())))
    overall = Counter()
    for counter in slides.values():
        overall.update(counter)
    print(f"\nOverall validation: {overall['detected']}/{overall['total']} "
          f"known objects localized ({recall(overall)}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

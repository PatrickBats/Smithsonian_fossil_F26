"""Apply the existing sponsor title map to prepared pixel-box annotations."""

import csv
import json
from collections import Counter
from pathlib import Path
from .paths import MAPS, PREP, SOURCE as SOURCE_ROOT


def main():
    output = PREP
    with (MAPS / "sponsor_title_map.csv").open(newline="", encoding="utf-8") as handle:
        sponsor = {row["lookup_title"]: row for row in csv.DictReader(handle)}
    with (MAPS / "fine_to_broad.csv").open(newline="", encoding="utf-8") as handle:
        broad = {
            row["fine_category"]: (row["broad_class_id"], row["broad_category"])
            for row in csv.DictReader(handle)
        }
    counts = Counter()
    categories = Counter()

    with (output / "objects_pixels.csv").open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames + [
            "sponsor_category",
            "sponsor_classify",
            "a4_broad_class_id",
            "a4_broad_category",
        ]
        with (output / "priority_32_objects.csv").open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fields)
            writer.writeheader()
            for row in reader:
                title = row["raw_title"].strip()
                mapped = sponsor.get(title)
                counts["all_boxes"] += 1
                if mapped is None:
                    counts["unmapped_boxes"] += 1
                    continue
                flag = mapped["sponsor_classify"]
                counts[f"{flag}_boxes"] += 1
                if flag != "YES":
                    continue
                category = mapped["sponsor_category"]
                if category not in broad:
                    raise ValueError(f"Missing A4 broad map for {category}")
                if row["fully_inside_image"] not in ("True", "1"):
                    counts["priority_outside"] += 1
                    continue
                class_id, class_name = broad[category]
                row.update(
                    {
                        "sponsor_category": category,
                        "sponsor_classify": flag,
                        "a4_broad_class_id": class_id,
                        "a4_broad_category": class_name,
                    }
                )
                writer.writerow(row)
                counts["priority_inside"] += 1
                counts[f"priority_{row['annotation_format']}"] += 1
                categories[category] += 1

    summary = {"counts": dict(counts), "priority_categories": dict(sorted(categories.items()))}
    (output / "sponsor_mapping_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

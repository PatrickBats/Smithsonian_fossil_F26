"""Check the prepared A4 dataset without opening held-out test images."""

import json
from collections import Counter
from pathlib import Path
from .paths import TRAINING


def main():
    ROOT = TRAINING
    data = ROOT / "dataset_ignore"
    summary = json.loads((ROOT / "dataset_base" / "dataset_summary.json").read_text())
    ignore_summary = json.loads((data / "ignore_labels_summary.json").read_text())
    coco = json.loads((data / "train" / "_annotations.coco.json").read_text())

    images = coco["images"]
    annotations = coco["annotations"]
    image_ids = {image["id"] for image in images}
    categories = {category["id"]: category["name"] for category in coco["categories"]}
    assert len(images) == summary["total_train_images"] == 1958
    assert len(image_ids) == len(images)
    assert len(categories) == 29 and categories[max(categories)] == "__ignore__"
    assert all((data / "train" / image["file_name"]).is_file() for image in images)
    assert all(ann["image_id"] in image_ids for ann in annotations)
    assert all(ann["category_id"] in categories for ann in annotations)
    assert all(
        len(ann["bbox"]) == 4 and ann["bbox"][2] > 0 and ann["bbox"][3] > 0 for ann in annotations
    )
    known = sum(ann["category_id"] != max(categories) for ann in annotations)
    ignored = len(annotations) - known
    assert known == summary["total_train_box_instances"] == 2311
    assert ignored == ignore_summary["ignore_boxes"]
    assert ignore_summary["tiles"] == len(images)
    assert (data / "valid" / "_annotations.coco.json").samefile(
        ROOT / "dataset_base" / "valid" / "_annotations.coco.json"
    )
    assert (data / "test" / "_annotations.coco.json").samefile(
        ROOT / "dataset_base" / "test" / "_annotations.coco.json"
    )
    counts = Counter(ann["category_id"] for ann in annotations)
    report = {
        "status": "verified",
        "train_images": len(images),
        "known_boxes": known,
        "ignore_boxes": ignored,
        "categories": len(categories) - 1,
        "new_train_images": summary["new_train_images"],
        "new_train_box_instances": summary["new_train_box_instances"],
        "per_category_box_instances": {
            categories[key]: value
            for key, value in sorted(counts.items())
            if key != max(categories)
        },
        "validation_unchanged": True,
        "test_unchanged_and_unopened": True,
    }
    (ROOT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "per_category_box_instances"},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

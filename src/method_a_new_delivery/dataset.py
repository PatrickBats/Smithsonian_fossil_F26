"""Merge verified new crops with the frozen A3 train dataset for A4."""

import hashlib
import json
import os
from pathlib import Path

from .paths import A3 as OLD, TRAINING as ROOT

BUILD = ROOT / ".dataset_base.building"
DEST = ROOT / "dataset_base"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    if DEST.exists() or BUILD.exists():
        raise FileExistsError("Dataset destination already exists")
    plans = [json.loads(path.read_text()) for path in sorted((ROOT / "plan").glob("*.json"))]
    if len(plans) != 20:
        raise ValueError("Expected 20 new source scans")
    base = json.loads((OLD / "train" / "_annotations.coco.json").read_text())
    images = list(base["images"])
    annotations = list(base["annotations"])
    if len(images) != 1423 or len(annotations) != 1768:
        raise ValueError("Frozen A3 input changed")
    next_image = max(image["id"] for image in images) + 1
    next_annotation = max(ann["id"] for ann in annotations) + 1
    BUILD.mkdir()
    train = BUILD / "train"
    train.mkdir()
    for image in images:
        source = (OLD / "train" / image["file_name"]).resolve()
        (train / image["file_name"]).symlink_to(source)
    for plan in plans:
        for crop in plan["crops"]:
            filename = crop["tile_id"] + ".png"
            image_path = ROOT / "images" / "crops" / filename
            metadata_path = image_path.with_suffix(".json")
            if not image_path.is_file() or not metadata_path.is_file():
                raise FileNotFoundError(f"Missing exported crop {filename}")
            metadata = json.loads(metadata_path.read_text())
            if metadata["status"] != "verified" or metadata["crop"] != crop:
                raise ValueError(f"Crop provenance mismatch {filename}")
            if metadata["sha256"] != sha256(image_path):
                raise ValueError(f"Crop hash mismatch {filename}")
            (train / filename).symlink_to(image_path)
            images.append({"id": next_image, "file_name": filename, "width": 1024, "height": 1024})
            for obj in crop["objects"]:
                x, y, width, height = obj["bbox"]
                if not (0 <= x < x + width <= 1024 and 0 <= y < y + height <= 1024):
                    raise ValueError(f"Invalid crop box {filename}")
                annotations.append(
                    {
                        "id": next_annotation,
                        "image_id": next_image,
                        "category_id": obj["category_id"],
                        "bbox": [x, y, width, height],
                        "area": width * height,
                        "iscrowd": 0,
                        "record_id": obj["record_id"],
                    }
                )
                next_annotation += 1
            next_image += 1
    if len({image["file_name"] for image in images}) != len(images):
        raise ValueError("Duplicate image filename")
    if len({image["id"] for image in images}) != len(images):
        raise ValueError("Duplicate image ID")
    if len({ann["id"] for ann in annotations}) != len(annotations):
        raise ValueError("Duplicate annotation ID")
    if {ann["image_id"] for ann in annotations} != {image["id"] for image in images}:
        raise ValueError("Missing or unannotated image")
    coco = {**base, "images": images, "annotations": annotations}
    (train / "_annotations.coco.json").write_text(json.dumps(coco))
    (BUILD / "valid").symlink_to((OLD / "valid").resolve())
    (BUILD / "test").symlink_to((OLD / "test").resolve())
    summary = {
        "old_train_images": 1423,
        "new_train_images": len(images) - 1423,
        "total_train_images": len(images),
        "old_train_boxes": 1768,
        "new_train_box_instances": len(annotations) - 1768,
        "total_train_box_instances": len(annotations),
        "new_source_scans": len(plans),
        "category_count": len(base["categories"]),
        "old_validation_unchanged": True,
        "old_test_unchanged": True,
        "train_coco_sha256": sha256(train / "_annotations.coco.json"),
    }
    (BUILD / "dataset_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    os.rename(BUILD, DEST)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

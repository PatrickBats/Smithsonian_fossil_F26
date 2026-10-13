"""Add 28-class COCO labels to Method B's identical read-only fused grid images."""

from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image

from focus_helpers import sha256_file


ROOT = Path("/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_focus_stack_v1")
IMAGE_ROOT = Path("/rhf/allocations/dsci435/Smithsonian_F26/model_B/data/abbas_focus_stack_v1")
STAGING = ROOT / "dataset_staging"
FINAL = ROOT / "dataset"


def main() -> None:
    plan_summary = json.loads((ROOT / "plan_summary.json").read_text())
    if plan_summary["status"] != "plan_matches_current_Method_B_grid":
        raise ValueError("Method B grid identity has not been established")
    if FINAL.exists() or STAGING.exists():
        raise FileExistsError("Dataset destination must be new")
    category_names = json.loads((ROOT / "inputs/broad_category_map.json").read_text())
    categories = [{"id": i + 1, "name": category_names[str(i)], "supercategory": "F26 broad YES"}
                  for i in range(28)]
    STAGING.mkdir()
    counts = {}
    image_hashes = {}
    for split in ("train", "valid"):
        folder = STAGING / split
        folder.mkdir()
        tiles = [tile for path in sorted((ROOT / "plan").glob("*.json"))
                 for tile in json.loads(path.read_text())["tiles"] if tile["split"] == split]
        if len(tiles) != plan_summary["grid_images"][split]:
            raise ValueError("Incomplete grid plan")
        images, annotations = [], []
        covered = set()
        for image_id, tile in enumerate(sorted(tiles, key=lambda item: item["tile_id"]), 1):
            source = IMAGE_ROOT / split / f"{tile['tile_id']}.png"
            if not source.is_file() or source.is_symlink():
                raise FileNotFoundError("Original Method B fused PNG is missing or linked")
            with Image.open(source) as handle:
                if handle.size != (1024, 1024) or handle.mode != "RGB":
                    raise ValueError("Method B image is not 1024 px RGB")
            image_hashes[tile["tile_id"]] = sha256_file(source)
            destination = folder / source.name
            os.symlink(source, destination)
            if not destination.is_file():
                raise FileNotFoundError("Dataset image link is broken")
            images.append({"id": image_id, "file_name": source.name,
                           "width": 1024, "height": 1024, "slide_path": tile["image"],
                           "tile_left_px": tile["left"], "tile_top_px": tile["top"]})
            for label in tile["objects"]:
                category_id = int(label["category_id"])
                if not 1 <= category_id <= 28 or categories[category_id - 1]["name"] != label["broad_category"]:
                    raise ValueError("Broad category mapping mismatch")
                x, y, width, height = label["bbox"]
                if min(x, y) < 0 or width <= 0 or height <= 0 or x + width > 1024 or y + height > 1024:
                    raise ValueError("Label bbox is outside shared tile")
                covered.add(label["record_id"])
                annotations.append({"id": len(annotations) + 1, "image_id": image_id,
                                    "category_id": category_id, "bbox": label["bbox"],
                                    "area": label["area"], "iscrowd": 0,
                                    "record_id": label["record_id"]})
        coco = {"info": {"description": "Method A 28-class labels on shared Sp26 LoG ROI grid"},
                "licenses": [], "images": images, "annotations": annotations, "categories": categories}
        (folder / "_annotations.coco.json").write_text(json.dumps(coco, indent=2) + "\n")
        if len(covered) != plan_summary["covered_priority_records"][split]:
            raise ValueError("Known reference coverage differs from plan")
        annotated_image_ids = {a["image_id"] for a in annotations}
        counts[split] = {"grid_images": len(images), "box_instances": len(annotations),
                         "unique_known_records": len(covered),
                         "empty_images": len(images) - len(annotated_image_ids)}
    test_folder = STAGING / "test"
    test_folder.mkdir()
    (test_folder / "_annotations.coco.json").write_text(json.dumps({
        "info": {"description": "Reserved test set intentionally not prepared or loaded"},
        "licenses": [], "images": [], "annotations": [], "categories": categories,
    }) + "\n")
    (STAGING / "source_image_hashes.json").write_text(json.dumps(image_hashes) + "\n")
    summary = {
        "status": "verified_shared_grid_28_class_sparse_label_dataset",
        "assignment_sha256": plan_summary["shared_assignment_sha256"],
        "fine_to_broad_sha256": plan_summary["fine_to_broad_sha256"],
        "source_image_root": str(IMAGE_ROOT), "image_storage": "read-only symlinks; no duplicate PNG payload",
        "focus_representation": "Sp26 per-pixel absolute LoG k=5, native 1024 px ROI grid",
        "counts": counts,
        "excluded_priority_records_outside_ROI_grid": plan_summary["excluded_priority_records"],
        "test_images_loaded": False,
        "limitations": "Only fixed rectangular ROI grids are covered. Labels are sparse; COCO AP and unmatched predictions cannot be interpreted as whole-scene performance.",
    }
    (STAGING / "dataset_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    STAGING.rename(FINAL)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()

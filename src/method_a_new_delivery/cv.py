"""Build scan-grouped cross-validation datasets from the prepared A4 delivery."""

import collections
import hashlib
import json
from pathlib import Path

from .paths import TRAINING as ROOT, A3 as OLD

DEST = ROOT / "cross_validation"
FOLDS = 5


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def assign_folds(plans):
    """Balance slide counts and source-object counts, keeping each slide intact."""
    ordered = sorted(plans, key=lambda p: (-len(p["objects"]), p["source"]))
    counts = [0] * FOLDS
    boxes = [0] * FOLDS
    result = {}
    for plan in ordered:
        available = [i for i in range(FOLDS) if counts[i] < len(plans) // FOLDS]
        fold = min(available, key=lambda i: (boxes[i], counts[i], i))
        result[plan["source"]] = fold
        counts[fold] += 1
        boxes[fold] += len(plan["objects"])
    assert counts == [4] * FOLDS
    return result


def subset(coco, image_ids):
    result = dict(coco)
    result["images"] = [image for image in coco["images"] if image["id"] in image_ids]
    result["annotations"] = [a for a in coco["annotations"] if a["image_id"] in image_ids]
    return result


def main():
    if DEST.exists():
        raise FileExistsError(DEST)
    plans = [read(path) for path in sorted((ROOT / "plan").glob("*.json"))]
    assert len(plans) == 20
    assignment = assign_folds(plans)
    tile_source = {}
    for plan in plans:
        for crop in plan["crops"]:
            name = crop["tile_id"] + ".png"
            assert name not in tile_source
            tile_source[name] = plan["source"]
    assert len(tile_source) == 535

    train_source = ROOT / "dataset_ignore" / "train"
    known = read(ROOT / "dataset_base" / "train" / "_annotations.coco.json")
    ignored = read(train_source / "_annotations.coco.json")
    assert len(known["images"]) == len(ignored["images"]) == 1958
    assert len(ignored["annotations"]) == 5499
    image_by_name = {im["file_name"]: im for im in ignored["images"]}
    assert set(tile_source) <= set(image_by_name)
    old_ids = {im["id"] for im in ignored["images"] if im["file_name"] not in tile_source}
    assert len(old_ids) == 1423
    category_names = {c["id"]: c["name"] for c in known["categories"]}
    assert len(category_names) == 28

    DEST.mkdir()
    manifest = {
        "fold_count": FOLDS,
        "fixed_old_train_images": len(old_ids),
        "new_scans": 20,
        "new_images": len(tile_source),
        "folds": [],
    }
    hist = read(ROOT / "dataset_ignore" / "ignore_labels_summary.json")["pred_class_id_hist"]
    for fold in range(FOLDS):
        fold_scans = {source for source, index in assignment.items() if index == fold}
        valid_ids = {
            image_by_name[name]["id"]
            for name, source in tile_source.items()
            if source in fold_scans
        }
        train_ids = {im["id"] for im in ignored["images"]} - valid_ids
        assert old_ids <= train_ids and train_ids.isdisjoint(valid_ids)
        fold_dir = DEST / f"fold_{fold}"
        for split, source_coco, ids in (("train", ignored, train_ids), ("valid", known, valid_ids)):
            split_dir = fold_dir / split
            split_dir.mkdir(parents=True)
            data = subset(source_coco, ids)
            if split == "valid":
                data["categories"] = known["categories"]
            write(split_dir / "_annotations.coco.json", data)
            for im in data["images"]:
                src = train_source / im["file_name"]
                assert src.is_file()
                (split_dir / im["file_name"]).symlink_to(src)
        (fold_dir / "test").symlink_to(OLD / "test", target_is_directory=True)
        write(fold_dir / "ignore_labels_summary.json", {"pred_class_id_hist": hist})
        train_data = read(fold_dir / "train" / "_annotations.coco.json")
        valid_data = read(fold_dir / "valid" / "_annotations.coco.json")
        known_valid = [a for a in valid_data["annotations"] if a["category_id"] in category_names]
        source_objects = [
            o for plan in plans if plan["source"] in fold_scans for o in plan["objects"]
        ]
        per_class = collections.Counter(category_names[o["category_id"]] for o in source_objects)
        info = {
            "fold": fold,
            "held_out_scans": sorted(fold_scans),
            "held_out_source_objects": len(source_objects),
            "held_out_images": len(valid_data["images"]),
            "held_out_box_instances": len(known_valid),
            "train_images": len(train_data["images"]),
            "train_known_boxes": sum(
                a["category_id"] in category_names for a in train_data["annotations"]
            ),
            "train_ignore_boxes": sum(
                a["category_id"] not in category_names for a in train_data["annotations"]
            ),
            "held_out_class_support": dict(sorted(per_class.items())),
            "valid_coco_sha256": hashlib.sha256(
                (fold_dir / "valid" / "_annotations.coco.json").read_bytes()
            ).hexdigest(),
        }
        assert len(valid_data["categories"]) == 28
        assert len(valid_ids) == info["held_out_images"]
        write(fold_dir / "manifest.json", info)
        manifest["folds"].append(info)
    assert sum(f["held_out_source_objects"] for f in manifest["folds"]) == 540
    assert sum(f["held_out_images"] for f in manifest["folds"]) == 535
    write(DEST / "manifest.json", manifest)
    print(
        json.dumps(
            [
                {
                    "fold": f["fold"],
                    "scans": len(f["held_out_scans"]),
                    "objects": f["held_out_source_objects"],
                    "images": f["held_out_images"],
                }
                for f in manifest["folds"]
            ]
        )
    )


if __name__ == "__main__":
    main()

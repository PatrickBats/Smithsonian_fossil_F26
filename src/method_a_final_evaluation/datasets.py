"""COCO datasets scoped to a frozen training fold or final development pool."""

from pathlib import Path

from .preparation import file_sha
from .protocol import digest, read, split_plans, write_new


def load_plans(root):
    return [read(p) for p in sorted((Path(root) / "plans").glob("*.json"))]


def assemble(root, stage, fold=None):
    """Build known-label and one-class datasets without including test scans."""
    root = Path(root)
    if stage not in {"cv", "final"}:
        raise ValueError(stage)
    plans, assignment = load_plans(root), read(root / "assignment.json")
    selected = split_plans(
        plans, assignment, "train" if stage == "cv" else "final_train", fold
    )
    tag = f"fold_{fold}" if stage == "cv" else "final"
    out = root / "datasets" / tag
    if out.exists():
        raise FileExistsError(out)
    names = read(root / "categories.json")
    cats = [{"id": int(i), "name": name} for i, name in names.items()]
    images, annotations = [], []
    for plan in selected:
        status = read(root / "export_status" / f"{plan['index']:03d}.json")
        if status["status"] != "completed":
            raise ValueError("Crop export incomplete")
        for crop in plan["crops"]:
            path = root / "images" / (crop["tile_id"] + ".png")
            meta = read(path.with_suffix(".json"))
            if meta["crop_digest"] != digest(crop) or meta["sha256"] != file_sha(path):
                raise ValueError("Crop verification failed")
            iid = len(images) + 1
            images.append(
                {"id": iid, "file_name": path.name, "width": 1024, "height": 1024}
            )
            for obj in crop["objects"]:
                x, y, w, h = obj["bbox"]
                annotations.append(
                    {
                        "id": len(annotations) + 1,
                        "image_id": iid,
                        "category_id": obj["category_id"],
                        "bbox": [x, y, w, h],
                        "area": w * h,
                        "iscrowd": 0,
                        "record_id": obj["record_id"],
                    }
                )
    for kind in ("known", "teacher", "smoke_ignore"):
        categories = [{"id": 1, "name": "pollen"}] if kind == "teacher" else cats
        if kind == "smoke_ignore":
            categories = cats + [{"id": 29, "name": "__ignore__"}]
        anns = (
            [{**a, "category_id": 1} for a in annotations]
            if kind == "teacher"
            else annotations
        )
        data = {"images": images, "annotations": anns, "categories": categories}
        write_new(out / kind / "train" / "_annotations.coco.json", data)
        # Validation/test loaders exist for library setup, but no test imagery is
        # linked here; selection is performed by the separate scan-level scorer.
        for empty in ("valid", "test"):
            write_new(
                out / kind / empty / "_annotations.coco.json",
                {"images": [], "annotations": [], "categories": categories},
            )
        for im in images:
            (out / kind / "train" / im["file_name"]).symlink_to(
                root / "images" / im["file_name"]
            )
    contract = {
        "stage": stage,
        "fold": fold,
        "train_sources": sorted(p["source"] for p in selected),
        "train_groups": sorted({p["group_id"] for p in selected}),
        "assignment_digest": digest(assignment),
        "images": len(images),
        "known_boxes": len(annotations),
        "test_used": False,
    }
    write_new(out / "contract.json", contract)
    return contract


def add_ignore(root, stage, run_root, fold=None):
    """Use a training-only proposal model, never a target-exposed old model."""
    import torch
    from PIL import Image
    from torchvision.ops import box_iou
    from rfdetr_plus.models.detection import RFDETR2XLarge

    root, run_root = Path(root), Path(run_root)
    tag = f"fold_{fold}" if stage == "cv" else "final"
    base = root / "datasets" / tag
    teacher = run_root / tag / "teacher" / "checkpoint_step_2400.pth"
    status = read(run_root / tag / "teacher" / "status.json")
    if status["status"] != "completed" or status["checkpoint_sha256"] != file_sha(
        teacher
    ):
        raise ValueError("Proposal checkpoint missing or changed")
    coco = read(base / "known" / "train" / "_annotations.coco.json")
    coco["categories"].append({"id": 29, "name": "__ignore__"})
    by_image = {}
    for ann in coco["annotations"]:
        by_image.setdefault(ann["image_id"], []).append(ann)
    model = RFDETR2XLarge(pretrain_weights=str(teacher), num_classes=1, resolution=1000)
    count = 0
    proposal_count = 0
    known_instance_hits = 0
    class_histogram = {}
    for im in coco["images"]:
        path = base / "known" / "train" / im["file_name"]
        with Image.open(path) as image:
            pred = model.predict(image.convert("RGB"), threshold=0.30)
        for cid in pred.class_id:
            key = str(int(cid))
            class_histogram[key] = class_histogram.get(key, 0) + 1
        boxes = torch.tensor(
            [
                [
                    a["bbox"][0],
                    a["bbox"][1],
                    a["bbox"][0] + a["bbox"][2],
                    a["bbox"][1] + a["bbox"][3],
                ]
                for a in by_image[im["id"]]
            ],
            dtype=torch.float32,
        )
        pollen_boxes = torch.tensor(
            pred.xyxy[pred.class_id == 0], dtype=torch.float32
        ).reshape(-1, 4)
        proposal_count += len(pollen_boxes)
        if len(pollen_boxes) and len(boxes):
            known_instance_hits += int(
                (box_iou(pollen_boxes, boxes).max(0).values >= 0.5).sum()
            )
        for box, score, cid in zip(pred.xyxy, pred.confidence, pred.class_id):
            if int(cid) != 0:
                continue
            if (
                len(boxes)
                and float(box_iou(torch.tensor(box).reshape(1, 4), boxes).max()) >= 0.5
            ):
                continue
            x0, y0, x1, y1 = map(float, box)
            if x1 - x0 <= 2 or y1 - y0 <= 2:
                continue
            coco["annotations"].append(
                {
                    "id": len(coco["annotations"]) + 1,
                    "image_id": im["id"],
                    "category_id": 29,
                    "bbox": [x0, y0, x1 - x0, y1 - y0],
                    "area": (x1 - x0) * (y1 - y0),
                    "iscrowd": 0,
                    "pseudo_score": float(score),
                }
            )
            count += 1
    out = base / "ignore"
    write_new(out / "train" / "_annotations.coco.json", coco)
    for im in coco["images"]:
        (out / "train" / im["file_name"]).symlink_to(root / "images" / im["file_name"])
    for empty in ("valid", "test"):
        write_new(
            out / empty / "_annotations.coco.json",
            {"images": [], "annotations": [], "categories": coco["categories"]},
        )
    result = {
        "teacher_checkpoint_sha256": file_sha(teacher),
        "teacher_training_contract": read(base / "contract.json"),
        "ignore_boxes": count,
        "proposal_count": proposal_count,
        "known_box_instance_hits": known_instance_hits,
        "proposal_class_histogram": class_histogram,
        "known_boxes": len(coco["annotations"]) - count,
        "test_used": False,
    }
    write_new(out / "ignore_summary.json", result)
    return result

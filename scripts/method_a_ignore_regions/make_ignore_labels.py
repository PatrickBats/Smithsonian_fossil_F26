"""Pseudo-label unlabeled grains in Method A training tiles as ignore regions.

Runs the one-class (Spring / Shaikh et al.) RF-DETR over every A3 training tile,
keeps detections that do not overlap a known labeled box, and writes a new COCO
dataset where those boxes carry an extra `__ignore__` category. The training
script excludes that category from matching and suppresses the no-object loss on
queries that land on it. Known labels and validation data are copied unchanged.
"""

import argparse, collections, json, os, shutil, time
from pathlib import Path

import torch
from PIL import Image
from torchvision.ops import box_iou


def link_or_copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        return
    try:
        os.symlink(os.path.realpath(src), dst)  # NOTS: train tiles are already symlinks; no disk cost
    except OSError:
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True, help="A3 dataset dir with train/ valid/")
    p.add_argument("--detector", required=True, help="one-class RF-DETR .pth")
    p.add_argument("--out", required=True, help="new dataset dir to create")
    p.add_argument("--conf", type=float, default=0.3)
    p.add_argument("--iou", type=float, default=0.5)
    p.add_argument("--resolution", type=int, default=1000)
    p.add_argument("--limit", type=int, default=0, help="debug: only first N tiles")
    a = p.parse_args()

    src, out = Path(a.dataset), Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    coco = json.loads((src / "train/_annotations.coco.json").read_text())
    ignore_id = max(c["id"] for c in coco["categories"]) + 1
    coco["categories"].append({"id": ignore_id, "name": "__ignore__", "supercategory": "none"})

    from rfdetr_plus.models.detection import RFDETR2XLarge

    det = RFDETR2XLarge(pretrain_weights=a.detector, num_classes=1, resolution=a.resolution)
    by_img = collections.defaultdict(list)
    for ann in coco["annotations"]:
        by_img[ann["image_id"]].append(ann)
    images = coco["images"][: a.limit] if a.limit else coco["images"]
    next_id = max(x["id"] for x in coco["annotations"]) + 1
    stats = {"tiles": 0, "known_boxes": 0, "detections": 0, "ignore_boxes": 0,
             "tiles_with_ignore": 0, "known_boxes_hit_by_detector": 0, "per_tile": {}}
    class_id_hist = collections.Counter()  # which head row the one-class model fires on
    t0 = time.time()
    for i, im in enumerate(images):
        path = src / "train" / im["file_name"]
        link_or_copy(path, out / "train" / im["file_name"])
        with Image.open(path) as pil:
            ds = det.predict(pil.convert("RGB"), threshold=a.conf)
        class_id_hist.update(int(c) for c in ds.class_id)
        pred = torch.tensor(ds.xyxy, dtype=torch.float32).reshape(-1, 4)
        gt = torch.tensor(
            [[b["bbox"][0], b["bbox"][1], b["bbox"][0] + b["bbox"][2], b["bbox"][1] + b["bbox"][3]]
             for b in by_img[im["id"]]], dtype=torch.float32).reshape(-1, 4)
        keep = torch.ones(len(pred), dtype=torch.bool)
        gt_hit = 0
        if len(pred) and len(gt):
            iou = box_iou(pred, gt)
            keep = iou.max(1).values < a.iou
            gt_hit = int((iou.max(0).values >= a.iou).sum())
        added = 0
        for box, score in zip(pred[keep].tolist(), torch.tensor(ds.confidence)[keep].tolist()):
            x0, y0, x1, y1 = box
            w, h = x1 - x0, y1 - y0
            if w <= 2 or h <= 2:
                continue
            coco["annotations"].append({
                "id": next_id, "image_id": im["id"], "category_id": ignore_id,
                "bbox": [x0, y0, w, h], "area": w * h, "iscrowd": 0,
                "pseudo_score": float(score), "source": "one_class_detector",
            })
            next_id += 1
            added += 1
        stats["tiles"] += 1
        stats["known_boxes"] += len(gt)
        stats["detections"] += len(pred)
        stats["ignore_boxes"] += added
        stats["tiles_with_ignore"] += int(added > 0)
        stats["known_boxes_hit_by_detector"] += gt_hit
        stats["per_tile"][im["file_name"]] = {"known": len(gt), "detected": len(pred), "ignore": added}
        if i % 100 == 0:
            print(json.dumps({"done": i + 1, "total": len(images), "ignore_so_far": stats["ignore_boxes"],
                              "elapsed_s": round(time.time() - t0)}), flush=True)
    if a.limit:
        coco["images"] = images
        keep_ids = {im["id"] for im in images}
        coco["annotations"] = [x for x in coco["annotations"] if x["image_id"] in keep_ids]
    (out / "train/_annotations.coco.json").write_text(json.dumps(coco))
    # validation and (empty) test are unchanged
    for split in ("valid", "test"):
        for f in (src / split).iterdir():
            link_or_copy(f, out / split / f.name)
    stats.update(ignore_category_id=ignore_id, conf=a.conf, iou=a.iou, detector=a.detector,
                 limit=a.limit, pred_class_id_hist=dict(class_id_hist),
                 ignore_to_known_ratio=(stats["ignore_boxes"] / stats["known_boxes"]) if stats["known_boxes"] else None,
                 elapsed_s=round(time.time() - t0))
    (out / "ignore_labels_summary.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps({k: v for k, v in stats.items() if k != "per_tile"}, indent=2))


if __name__ == "__main__":
    main()

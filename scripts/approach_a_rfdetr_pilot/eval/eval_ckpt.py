"""Reproduce Shaikh et al. 2026 Table 1 with the released RF-DETR-2XL checkpoints.

Runs a checkpoint over a COCO split of pre-made 1024px tiles, writes COCO-format
detections, and scores them with pycocotools (AP@50, AP@50-95, best-F1 P/R).
Single-class (palynomorph) only: this is the detection reference (A0).
"""
import argparse, json, time
from pathlib import Path

import numpy as np
from PIL import Image
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    return inter / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter + 1e-9)


def best_f1(gt, dets, iou_thr=0.5):
    """Greedy per-image matching at IoU>iou_thr; sweep confidence for max F1."""
    by_img = {}
    for d in dets:
        by_img.setdefault(d["image_id"], []).append(d)
    gts = {}
    for a in gt.dataset["annotations"]:
        x, y, w, h = a["bbox"]
        gts.setdefault(a["image_id"], []).append([x, y, x+w, y+h])
    n_gt = sum(len(v) for v in gts.values())
    scored = []  # (score, is_tp)
    for img_id, ds in by_img.items():
        ds = sorted(ds, key=lambda d: -d["score"])
        used = set()
        for d in ds:
            x, y, w, h = d["bbox"]; box = [x, y, x+w, y+h]
            best, bj = 0, -1
            for j, g in enumerate(gts.get(img_id, [])):
                if j in used: continue
                v = iou(box, g)
                if v > best: best, bj = v, j
            tp = best > iou_thr
            if tp: used.add(bj)
            scored.append((d["score"], tp))
    scored.sort(key=lambda t: -t[0])
    tp_cum = np.cumsum([t for _, t in scored]); k = np.arange(1, len(scored)+1)
    prec, rec = tp_cum / k, tp_cum / max(n_gt, 1)
    f1 = 2*prec*rec/(prec+rec+1e-9); i = int(np.argmax(f1))
    return dict(f1=float(f1[i]), precision=float(prec[i]), recall=float(rec[i]),
                threshold=float(scored[i][0]), n_gt=n_gt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--coco_dir", required=True, help="dir with images/<split>/ and annotations/")
    ap.add_argument("--split", default="test")
    ap.add_argument("--resolution", type=int, default=1000)
    ap.add_argument("--variant", default="2xlarge", choices=["2xlarge", "base"])
    ap.add_argument("--conf", type=float, default=0.001)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max_images", type=int, default=0)
    a = ap.parse_args()

    if a.variant == "2xlarge":
        from rfdetr_plus import RFDETR2XLarge as M
    else:
        from rfdetr.detr import RFDETRBase as M
    model = M(pretrain_weights=a.weights, num_classes=1, resolution=a.resolution)
    model.optimize_for_inference()

    ann = Path(a.coco_dir) / "annotations" / f"instances_{a.split}.json"
    gt = COCO(str(ann))
    imgs = gt.dataset["images"][: a.max_images or None]
    img_dir = Path(a.coco_dir) / "images" / a.split
    dets, t0 = [], time.time()
    for n, im in enumerate(imgs):
        pil = Image.open(img_dir / im["file_name"]).convert("RGB")
        r = model.predict(pil, threshold=a.conf)
        for b, s in zip(r.xyxy, r.confidence):
            x1, y1, x2, y2 = map(float, b)
            dets.append(dict(image_id=im["id"], category_id=0,
                             bbox=[x1, y1, x2-x1, y2-y1], score=float(s)))
        if n % 100 == 0:
            print(f"{n}/{len(imgs)} images, {time.time()-t0:.0f}s", flush=True)

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    json.dump(dets, open(out / f"detections_{a.split}.json", "w"))
    if a.max_images:
        gt.dataset["images"] = imgs
        keep = {i["id"] for i in imgs}
        gt.dataset["annotations"] = [x for x in gt.dataset["annotations"] if x["image_id"] in keep]
        gt.createIndex()
    E = COCOeval(gt, gt.loadRes(dets) if dets else COCO(), "bbox")
    E.params.imgIds = [i["id"] for i in imgs]
    E.params.maxDets = [1, 10, 100]
    E.evaluate(); E.accumulate(); E.summarize()
    res = dict(weights=a.weights, coco_dir=a.coco_dir, split=a.split, n_images=len(imgs),
               AP50_95=float(E.stats[0]), AP50=float(E.stats[1]), **best_f1(gt, dets),
               seconds=time.time()-t0)
    print(json.dumps(res, indent=2))
    json.dump(res, open(out / f"metrics_{a.split}.json", "w"), indent=2)


if __name__ == "__main__":
    main()

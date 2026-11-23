"""Score one-class detectors on the detector_v2 test sets (same code path for every checkpoint).

Per (checkpoint, test set): COCO mAP50 / mAP50:95 (pycocotools, maxDets 500), and precision / recall / F1
at IoU 0.5 over a confidence sweep (greedy highest-score-first one-to-one matching).
Predictions are cached per (checkpoint, set), so a rerun only recomputes metrics.
"""
import argparse, gzip, json, os, time
from pathlib import Path
import numpy as np
from PIL import Image

H = Path(os.path.expanduser("~/Smithsonian_F26"))
C = H / "processed/coco_detector_v2"
SETS = {"old_test": C / "combined", "test_new": C / "test_new", "test_new_recall": C / "test_new_recall"}
CKPTS = {"last_semester": H / "weights/rfdetr(2xl)_focus_stack.pth",
         "new_detector": H / "model_A/detector_v2/runs/dv2_2xl_focus_20261119/checkpoint_best_total.pth",
         "v3_detector": H / "model_A/detector_v3/runs/dv3_ignore_bal_20261120/checkpoint_best_total.pth"}
THRS = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7]


def iou_matrix(a, b):
    x1 = np.maximum(a[:, None, 0], b[None, :, 0]); y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2]); y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area = lambda r: (r[:, 2] - r[:, 0]) * (r[:, 3] - r[:, 1])
    return inter / (area(a)[:, None] + area(b)[None, :] - inter + 1e-9)


def prf(gt_by_img, pred_by_img, thr):
    tp = fp = fn = 0
    for iid, gt in gt_by_img.items():
        p = [d for d in pred_by_img.get(iid, []) if d[4] >= thr]
        if not p:
            fn += len(gt); continue
        p = np.array(sorted(p, key=lambda d: -d[4]))
        if not len(gt):
            fp += len(p); continue
        m = iou_matrix(p[:, :4], gt); used = np.zeros(len(gt), bool)
        for i in range(len(p)):
            row = np.where(used, -1.0, m[i]); j = int(row.argmax())
            if row[j] >= 0.5: used[j] = True; tp += 1
            else: fp += 1
        fn += int((~used).sum())
    pr = tp / (tp + fp) if tp + fp else 0.0; rc = tp / (tp + fn) if tp + fn else 0.0
    return {"threshold": thr, "tp": tp, "fp": fp, "fn": fn, "precision": pr, "recall": rc, "f1": 2 * pr * rc / (pr + rc) if pr + rc else 0.0}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval
    from rfdetr_plus.models.detection import RFDETR2XLarge
    results = {}
    for cname, ckpt in CKPTS.items():
        model = None
        for sname, root in SETS.items():
            gt = json.loads((root / "annotations/instances_test.json").read_text())
            images = gt["images"][: a.limit] if a.limit else gt["images"]
            keep = {im["id"] for im in images}
            cache = out / f"pred_{cname}_{sname}.json.gz"
            if cache.exists() and not a.limit:
                preds = {int(k): v for k, v in json.load(gzip.open(cache, "rt")).items()}
            else:
                if model is None:
                    model = RFDETR2XLarge(pretrain_weights=str(ckpt), num_classes=1, resolution=1000)
                preds = {}; t0 = time.time()
                for i, im in enumerate(images):
                    with Image.open(root / "images/test" / im["file_name"]) as pil:
                        ds = model.predict(pil.convert("RGB"), threshold=0.02)
                    preds[im["id"]] = [[float(v) for v in box] + [float(s)] for box, s in zip(ds.xyxy, ds.confidence)]
                    if i % 500 == 0:
                        print(json.dumps({"ckpt": cname, "set": sname, "done": i + 1, "total": len(images), "elapsed_s": round(time.time() - t0)}), flush=True)
                if not a.limit:
                    with gzip.open(cache, "wt") as h: json.dump(preds, h)
            # COCO mAP (category remapped to 1 for pycocotools)
            g = {"images": images, "categories": [{"id": 1, "name": "palynomorph"}],
                 "annotations": [{**x, "category_id": 1} for x in gt["annotations"] if x["image_id"] in keep]}
            coco = COCO(); coco.dataset = g; coco.createIndex()
            dets = [{"image_id": iid, "category_id": 1, "bbox": [b[0], b[1], b[2] - b[0], b[3] - b[1]], "score": b[4]} for iid, bs in preds.items() for b in bs]
            row = {"images": len(images), "gt_boxes": len(g["annotations"]), "empty_images": len(keep - {x["image_id"] for x in g["annotations"]})}
            if dets:
                ev = COCOeval(coco, coco.loadRes(dets), "bbox"); ev.params.maxDets = [1, 100, 500]
                ev.evaluate(); ev.accumulate()
                p = ev.eval["precision"]  # [T, R, K, A, M]
                row["mAP50_95"] = float(p[:, :, 0, 0, 2][p[:, :, 0, 0, 2] > -1].mean()); row["mAP50"] = float(p[0, :, 0, 0, 2][p[0, :, 0, 0, 2] > -1].mean())
                row["mAP75"] = float(p[5, :, 0, 0, 2][p[5, :, 0, 0, 2] > -1].mean())
            gt_by = {iid: np.zeros((0, 4)) for iid in keep}
            tmp = {}
            for x in g["annotations"]:
                tmp.setdefault(x["image_id"], []).append([x["bbox"][0], x["bbox"][1], x["bbox"][0] + x["bbox"][2], x["bbox"][1] + x["bbox"][3]])
            for k, v in tmp.items(): gt_by[k] = np.array(v, float)
            row["sweep"] = [prf(gt_by, preds, t) for t in THRS]
            row["best_f1"] = max(row["sweep"], key=lambda r: r["f1"])
            # false positives on empty tiles (tiles with no annotation), at 0.5
            emp = [iid for iid in keep if not len(gt_by[iid])]
            row["dets_on_empty_tiles_at_0.5"] = int(sum(sum(1 for b in preds.get(i, []) if b[4] >= 0.5) for i in emp)); row["empty_tiles_with_det_at_0.5"] = int(sum(any(b[4] >= 0.5 for b in preds.get(i, [])) for i in emp))
            results[f"{cname}|{sname}"] = row
            print("RESULT", cname, sname, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items() if k != "sweep"}), flush=True)
            (out / "results.json").write_text(json.dumps(results, indent=1))
        del model
    print("EVAL DONE", flush=True)


if __name__ == "__main__":
    main()

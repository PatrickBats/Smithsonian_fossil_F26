"""Test-split evaluation for Approach A pilot checkpoints (RF-DETR Large / 2XL).

Reports: class-agnostic AP50 / AP50-95 (detection only), per-class AP50 / AP50-95,
and, at the class-agnostic best-F1 confidence threshold, per-class P/R and a confusion
matrix on IoU>=0.5 matches (rows = expert class, cols = predicted class / missed).
Unmatched predictions are counted as false positives in a 'background' row.
"""
import argparse, copy, json, time, contextlib, io
from pathlib import Path
import numpy as np
from PIL import Image
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1]); x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2-x1)*max(0, y2-y1)
    return inter/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter+1e-9)


def xyxy(b): return [b[0], b[1], b[0]+b[2], b[1]+b[3]]


def coco_eval(gt_ds, dets, agnostic):
    g = copy.deepcopy(gt_ds); d = copy.deepcopy(dets)
    if agnostic:
        g["categories"] = [{"id": 0, "name": "palynomorph"}]
        for a in g["annotations"]: a["category_id"] = 0
        for x in d: x["category_id"] = 0
    G = COCO(); G.dataset = g
    with contextlib.redirect_stdout(io.StringIO()):
        G.createIndex(); D = G.loadRes(d) if d else COCO()
        E = COCOeval(G, D, "bbox"); E.params.maxDets = [1, 10, 100]
        E.evaluate(); E.accumulate(); E.summarize()
    out = dict(AP50_95=float(E.stats[0]), AP50=float(E.stats[1]))
    if not agnostic:
        per = {}
        P = E.eval["precision"]  # T,R,K,A,M
        for k, cid in enumerate(E.params.catIds):
            name = [c["name"] for c in g["categories"] if c["id"] == cid][0]
            p = P[:, :, k, 0, -1]; p50 = P[0, :, k, 0, -1]
            per[name] = dict(AP50_95=float(np.mean(p[p > -1])) if (p > -1).any() else None,
                             AP50=float(np.mean(p50[p50 > -1])) if (p50 > -1).any() else None)
        out["per_class"] = per
    return out


def match(gt_ds, dets, thr, iou_thr=0.5):
    """Greedy class-agnostic matching per image at score>=thr."""
    gts = {}
    for a in gt_ds["annotations"]: gts.setdefault(a["image_id"], []).append(a)
    by = {}
    for d in dets:
        if d["score"] >= thr: by.setdefault(d["image_id"], []).append(d)
    pairs, fps, misses = [], [], []
    for img in gt_ds["images"]:
        G = gts.get(img["id"], []); used = set()
        for d in sorted(by.get(img["id"], []), key=lambda d: -d["score"]):
            best, bj = 0, -1
            for j, g in enumerate(G):
                if j in used: continue
                v = iou(xyxy(d["bbox"]), xyxy(g["bbox"]))
                if v > best: best, bj = v, j
            if best >= iou_thr: used.add(bj); pairs.append((G[bj]["category_id"], d["category_id"]))
            else: fps.append(d["category_id"])
        misses += [g["category_id"] for j, g in enumerate(G) if j not in used]
    return pairs, fps, misses


def best_f1_thr(gt_ds, dets):
    n_gt = len(gt_ds["annotations"]); best = (0, 0.5)
    for t in np.arange(0.05, 0.96, 0.01):
        p, f, m = match(gt_ds, dets, t)
        tp = len(p); prec = tp/max(tp+len(f), 1); rec = tp/max(n_gt, 1)
        f1 = 2*prec*rec/(prec+rec+1e-9)
        if f1 > best[0]: best = (f1, float(t))
    return best[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True); ap.add_argument("--coco_dir", required=True)
    ap.add_argument("--split", default="test"); ap.add_argument("--variant", default="large")
    ap.add_argument("--resolution", type=int, default=1024)
    ap.add_argument("--model_kwargs", default="{}"); ap.add_argument("--out", required=True)
    ap.add_argument("--conf", type=float, default=0.001); ap.add_argument("--max_images", type=int, default=0); ap.add_argument("--device", default="")
    a = ap.parse_args()
    gt_ds = json.load(open(Path(a.coco_dir)/"annotations"/f"instances_{a.split}.json"))
    if a.max_images:
        gt_ds["images"] = gt_ds["images"][:a.max_images]; keep = {i["id"] for i in gt_ds["images"]}
        gt_ds["annotations"] = [x for x in gt_ds["annotations"] if x["image_id"] in keep]
    cats = {c["id"]: c["name"] for c in gt_ds["categories"]}; K = len(cats)
    if a.variant == "2xlarge":
        from rfdetr_plus import RFDETR2XLarge as M
    else:
        from rfdetr.detr import RFDETRLarge as M
    kw = json.loads(a.model_kwargs)
    if a.device: kw["device"] = a.device
    model = M(pretrain_weights=a.weights, num_classes=K, resolution=a.resolution, **kw)
    dets, t0, unknown = [], time.time(), 0
    img_dir = Path(a.coco_dir)/"images"/a.split
    for n, im in enumerate(gt_ds["images"]):
        r = model.predict(Image.open(img_dir/im["file_name"]).convert("RGB"), threshold=a.conf)
        for b, c, s in zip(r.xyxy, r.class_id, r.confidence):
            c = int(c)
            if c not in cats: unknown += 1; continue
            x1, y1, x2, y2 = map(float, b)
            dets.append(dict(image_id=im["id"], category_id=c, bbox=[x1, y1, x2-x1, y2-y1], score=float(s)))
        if n % 200 == 0: print(f"{n}/{len(gt_ds['images'])} {time.time()-t0:.0f}s", flush=True)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    json.dump(dets, open(out/f"detections_{a.split}.json", "w"))
    res = dict(weights=a.weights, split=a.split, n_images=len(gt_ds["images"]),
               n_gt=len(gt_ds["annotations"]), unknown_class_preds=unknown)
    res["class_agnostic"] = coco_eval(gt_ds, dets, True)
    thr = best_f1_thr(gt_ds, dets); pairs, fps, misses = match(gt_ds, dets, thr)
    tp = len(pairs); res["detection_at_bestF1"] = dict(threshold=thr, precision=tp/max(tp+len(fps), 1),
                                                     recall=tp/max(len(gt_ds["annotations"]), 1))
    if K > 1:
        res["multiclass"] = coco_eval(gt_ds, dets, False)
        names = [cats[i] for i in sorted(cats)]
        cm = np.zeros((K+1, K+1), int)  # rows: gt classes + background ; cols: pred classes + missed
        for g, p in pairs: cm[g, p] += 1
        for p in fps: cm[K, p] += 1
        for g in misses: cm[g, K] += 1
        res["confusion"] = dict(rows=names+["background(FP)"], cols=names+["missed"], matrix=cm.tolist())
        pc = {}
        for k in sorted(cats):
            tpk = cm[k, k]; predk = cm[:, k].sum(); gtk = cm[k, :].sum()
            pc[cats[k]] = dict(precision=tpk/max(predk, 1), recall=tpk/max(gtk, 1), n_gt=int(gtk),
                               detected_any_class=int(cm[k, :K].sum()), correct_class=int(tpk))
        res["per_class_at_bestF1"] = pc
        tot = sum(cm[k, :K].sum() for k in range(K))
        res["classification_acc_on_detected"] = float(np.trace(cm[:K, :K])/max(tot, 1))
    res["seconds"] = time.time()-t0
    print(json.dumps(res, indent=2, default=float))
    json.dump(res, open(out/f"metrics_{a.split}.json", "w"), indent=2, default=float)


if __name__ == "__main__":
    main()

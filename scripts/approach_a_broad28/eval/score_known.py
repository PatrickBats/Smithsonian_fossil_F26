"""Score known (priority-category) grains like Method A's report: a known grain is 'localized' if a
prediction with score >= thr overlaps it at IoU >= 0.5, and 'correct' if the highest-scoring such
prediction has the right category. 'other_palynomorph' grains are excluded from the known set.
Counts are per tile box (overlapping tiles can contain the same grain twice)."""
import json, sys
from pathlib import Path

gt_path, det_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
gt = json.load(open(gt_path)); dets = json.load(open(det_path))
other = [c["id"] for c in gt["categories"] if c["name"] == "other_palynomorph"][0]
names = {c["id"]: c["name"] for c in gt["categories"]}

def iou(a, b):
    ax2, ay2, bx2, by2 = a[0]+a[2], a[1]+a[3], b[0]+b[2], b[1]+b[3]
    iw = max(0, min(ax2, bx2) - max(a[0], b[0])); ih = max(0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    return inter / (a[2]*a[3] + b[2]*b[3] - inter + 1e-9)

by_img = {}
for d in dets:
    by_img.setdefault(d["image_id"], []).append(d)
known = [a for a in gt["annotations"] if a["category_id"] != other]
res = {"n_known": len(known)}
for thr in [0.05, 0.1, 0.3, 0.5]:
    loc = cor = 0; per = {}
    for a in known:
        cands = [d for d in by_img.get(a["image_id"], []) if d["score"] >= thr and iou(d["bbox"], a["bbox"]) >= 0.5]
        n = names[a["category_id"]]; p = per.setdefault(n, [0, 0, 0]); p[0] += 1
        if cands:
            loc += 1; p[1] += 1
            if max(cands, key=lambda d: d["score"])["category_id"] == a["category_id"]:
                cor += 1; p[2] += 1
    res[f"thr_{thr}"] = {"localized": loc, "correct": cor, "per_class_n_loc_correct": per}
json.dump(res, open(out_path, "w"), indent=2)
print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk != "per_class_n_loc_correct"}) for k, v in res.items()}))

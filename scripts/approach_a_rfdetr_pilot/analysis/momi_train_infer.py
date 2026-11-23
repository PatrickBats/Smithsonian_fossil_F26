"""Q4: run Large multiclass on train tiles containing Momipites (sp or species-level) + 50 random train tiles.
Writes analysis/q4_train_dets.json and q4_train_summary.json. Read-only on data/checkpoints."""
import json, random, collections, sys
from pathlib import Path
from PIL import Image
B = Path("/rhf/allocations/dsci435/Smithsonian_F26/model_A"); OUT = B / "analysis"
D = B / "data/pilot_top2_bestplane"
CK = B / "runs/A1_pilot_large_bestplane/multiclass_top2/checkpoint_best_total.pth"
dev = sys.argv[1] if len(sys.argv) > 1 else "cuda"
boxes = [b for b in json.load(open(OUT / "pilot_boxes_with_records.json")) if b["split"] == "train"]
def grp(b):
    c = b["sponsor_category"]
    if c == "Momipites sp": return "Momipites sp (cls1)"
    if "momip" in c.lower(): return "Momipites species (cls2)"
    if c == "Bisaccate": return "Bisaccate (cls0)"
    if c: return "other priority category (cls2)"
    return "other non-priority (cls2)"
tiles_m = sorted({b["file_name"] for b in boxes if "Momipites" in grp(b)})
alltiles = sorted({b["file_name"] for b in boxes}); random.seed(0)
rand = random.sample([t for t in alltiles if t not in set(tiles_m)], 50)
tiles = tiles_m + rand
print(len(tiles_m), "momipites tiles +", len(rand), "random", flush=True)
from rfdetr.detr import RFDETRLarge
model = RFDETRLarge(pretrain_weights=str(CK), num_classes=3, resolution=1024, positional_encoding_size=44, device=dev)
def iou(a, b):
    ax, ay, aw, ah = a; bx1, by1, bx2, by2 = b
    ix = max(0, min(ax+aw, bx2) - max(ax, bx1)); iy = max(0, min(ay+ah, by2) - max(ay, by1))
    i = ix*iy; return i / (aw*ah + (bx2-bx1)*(by2-by1) - i + 1e-9)
dets = {}; rows = []
for n, t in enumerate(tiles):
    r = model.predict(Image.open(D / "images/train" / t).convert("RGB"), threshold=0.001)
    P = [(list(map(float, b)), int(c), float(s)) for b, c, s in zip(r.xyxy, r.class_id, r.confidence)]
    dets[t] = P
    for b in boxes:
        if b["file_name"] != t: continue
        ov = [p for p in P if iou(b["bbox"], p[0]) >= 0.5]
        top = max(ov, key=lambda p: p[2]) if ov else None
        bm = lambda k: max([p[2] for p in ov if p[1] == k], default=0.0)
        rows.append(dict(tile=t, random=t in rand, group=grp(b), record_id=b["record_id"], title=b["original_title"],
                         top_cls=top[1] if top else None, top_score=top[2] if top else 0.0,
                         best0=bm(0), best1=bm(1), best2=bm(2)))
    if n % 20 == 0: print(n, flush=True)
json.dump(rows, open(OUT / "q4_train_rows.json", "w"))
summ = {}
for thr in [0.0, 0.3]:
    cm = collections.defaultdict(collections.Counter)
    for r in rows:
        cm[r["group"]][("cls%d" % r["top_cls"]) if (r["top_cls"] is not None and r["top_score"] >= thr) else "missed"] += 1
    summ[f"top_pred_score>={thr}"] = {g: dict(c) for g, c in cm.items()}
for g in sorted({r["group"] for r in rows}):
    R = [r for r in rows if r["group"] == g]
    summ.setdefault("mean_best_scores", {})[g] = dict(n=len(R), best0=sum(r["best0"] for r in R)/len(R),
        best1=sum(r["best1"] for r in R)/len(R), best2=sum(r["best2"] for r in R)/len(R),
        frac_best1_gt_best2=sum(r["best1"] > r["best2"] for r in R)/len(R))
print(json.dumps(summ, indent=1)); json.dump(summ, open(OUT / "q4_train_summary.json", "w"), indent=1)

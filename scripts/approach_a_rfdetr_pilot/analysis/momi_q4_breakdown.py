import json, collections
from pathlib import Path
B = Path("/rhf/allocations/dsci435/Smithsonian_F26/model_A"); OUT = B / "analysis"
pr = lambda *a: print(*a, flush=True)
rows = json.load(open(OUT / "q4_train_rows.json"))
boxes = json.load(open(OUT / "pilot_boxes_with_records.json"))
slide = {(b["file_name"], b["record_id"]): b["slide"] for b in boxes}
pr("top_cls==3 count:", sum(r["top_cls"] == 3 for r in rows), "of", len(rows))
# train Momipites sp: correct (best1>best2 and top==1) by slide
c = collections.defaultdict(collections.Counter)
for r in rows:
    if r["group"] == "Momipites sp (cls1)":
        s = slide.get((r["tile"], r["record_id"]), "?")
        k = "D3408-1_L" if s.startswith("D3408-1_L") else "other slides"
        c[k]["n"] += 1; c[k]["top1"] += r["top_cls"] == 1; c[k]["top2"] += r["top_cls"] == 2
        c[k]["top1_ge0.3"] += (r["top_cls"] == 1 and r["top_score"] >= 0.3)
pr("train Momipites sp by slide group:", {k: dict(v) for k, v in c.items()})
# per raw title among train Momipites sp
c = collections.defaultdict(collections.Counter)
for r in rows:
    if r["group"] == "Momipites sp (cls1)":
        c[r["title"].lower()]["n"] += 1; c[r["title"].lower()]["top1"] += r["top_cls"] == 1
pr("train Momipites sp by title:", {k: dict(v) for k, v in c.items()})
# species-level per species
c = collections.defaultdict(collections.Counter)
for r in rows:
    if r["group"].startswith("Momipites species"):
        c[r["title"].lower()][str(r["top_cls"])] += 1
pr("train species-level top_cls:", {k: dict(v) for k, v in c.items()})
# test: species-level Momipites (GT other) from saved large_multiclass dets
gt = json.load(open(B / "data/pilot_top2_bestplane/annotations/instances_test.json"))
imname = {im["id"]: im["file_name"] for im in gt["images"]}
key = {(b["file_name"], tuple(b["bbox"])): b for b in boxes if b["split"] == "test"}
def iou(a, b):
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    ix = max(0, min(ax+aw, bx+bw) - max(ax, bx)); iy = max(0, min(ay+ah, by+bh) - max(ay, by))
    i = ix*iy; return i / (aw*ah + bw*bh - i + 1e-9)
for run in ["large_multiclass", "2xl_init_sp26", "2xl_init_coco"]:
    dets = json.load(open(B / "runs/A1_test_eval" / run / "detections_test.json"))
    by = collections.defaultdict(list)
    for d in dets: by[d["image_id"]].append(d)
    out = collections.defaultdict(list)
    for a in gt["annotations"]:
        b = key.get((imname[a["image_id"]], tuple(a["bbox"])))
        if not b: continue
        g = b["sponsor_category"]
        if not ("momip" in g.lower() or g in ("Caryapollenites sp.", "Caryapollenites veripites", "Alnipollenites verus", "Betulaceae", "Platycarya platycarioides", "Platycaryapollenites swasticoidus", "Polyatriopollenites type")): continue
        if g == "Momipites sp": continue
        ov = [d for d in by[a["image_id"]] if iou(a["bbox"], d["bbox"]) >= 0.5]
        top = max(ov, key=lambda d: d["score"]) if ov else None
        out["momi-species" if "momip" in g.lower() else "other triporate/juglandaceous"].append(
            (top["category_id"] if top else None, round(max([d["score"] for d in ov if d["category_id"] == 1], default=0), 3)))
    for k, v in out.items():
        pr(run, k, "n", len(v), "top_cls counts", dict(collections.Counter(x[0] for x in v)), "mean best_momi", round(sum(x[1] for x in v)/len(v), 3), "max", max(x[1] for x in v))

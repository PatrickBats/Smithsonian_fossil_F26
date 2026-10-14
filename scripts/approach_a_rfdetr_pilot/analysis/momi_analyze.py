"""Q1-Q3 + raw-title analysis for the Momipites label-conflict claim. Reads analysis/pilot_boxes_with_records.json."""
import csv, json, collections, re
from pathlib import Path
B = Path("/rhf/allocations/dsci435/Smithsonian_F26/model_A"); OUT = B / "analysis"
RA = "/rhf/allocations/dsci435/Smithsonian_F26/runs/dino_finetune_2026-10-07/separate_slides/smoke/record_assignments.csv"
ANN = Path("/rhf/allocations/dsci435/smithsonian_full_sp26/annotations_F26")
norm = lambda t: " ".join(t.strip().lower().split())
boxes = json.load(open(OUT / "pilot_boxes_with_records.json"))
rows = list(csv.DictReader(open(RA)))
pr = lambda *a: print(*a, flush=True)

def grp(b):
    c = b["sponsor_category"]
    if c == "Momipites sp": return "Momipites sp"
    if "momip" in c.lower(): return "species:" + c
    return None
pr("=== Q1: Momipites tile-boxes and unique grains per split ===")
tb = collections.Counter(); ug = collections.defaultdict(set); tt = collections.Counter(); tug = collections.defaultdict(set)
for b in boxes:
    g = grp(b)
    if not g: continue
    tb[(g, b["pilot_class"], b["split"])] += 1; ug[(g, b["pilot_class"], b["split"])].add(b["record_id"])
    if g == "Momipites sp":
        t = norm(b["original_title"]); tt[(t, b["split"])] += 1; tug[(t, b["split"])].add(b["record_id"])
for k in sorted(tb): pr(k, "tile_boxes", tb[k], "unique_grains", len(ug[k]))
pr("--- raw titles folded into 'Momipites sp' (tile_boxes / unique grains) ---")
for k in sorted(tt): pr(k, tt[k], len(tug[k]))

pr("=== priority records (all, any ROI) with momip category or title, by split ===")
c = collections.Counter((r["sponsor_category"], norm(r["original_title"]), r["split"]) for r in rows
                        if "momip" in (r["sponsor_category"] + r["original_title"]).lower())
for k in sorted(c): pr(k, c[k])

pr("=== Q2: per-slide Momipites labels in ALL raw circles (annotations_summary) ===")
split_of = {}
for r in rows: split_of[r["annotation_filename"]] = r["split"]
raw = collections.defaultdict(collections.Counter); colors = collections.defaultdict(collections.Counter)
allmomi_files = set()
for r in csv.DictReader(open(ANN / "annotations_summary.csv")):
    if r["annotation_type"] != "circle": continue
    t = norm(r["title"])
    if "momip" in t:
        raw[r["file"]][t] += 1; colors[r["file"]][r["color"]] += 1
for f in sorted(raw, key=lambda f: (split_of.get(f, "zz"), f)):
    pr(split_of.get(f, "NOSPLIT"), f.replace(".ndpi.ndpa", ""), dict(raw[f]), "colors:", dict(colors[f]))
sp_sp = [f for f in raw if any(t.startswith("momipites sp") or t in ("momipites", "momipites?") for t in raw[f])]
sp_species = [f for f in raw if any(("flexus" in t or "wyoming" in t or "fluminis" in t) for t in raw[f])]
pr("slides with sp-type labels:", len(sp_sp), " with species labels:", len(sp_species), " both:", len(set(sp_sp) & set(sp_species)))

pr("=== Q3: test Momipites sp GT and detections ===")
gt = json.load(open(B / "data/pilot_top2_bestplane/annotations/instances_test.json"))
imname = {im["id"]: im["file_name"] for im in gt["images"]}
key = {(b["file_name"], tuple(b["bbox"])): b for b in boxes if b["split"] == "test"}
G = [a for a in gt["annotations"] if a["category_id"] == 1]
def iou(a, b):
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    ix = max(0, min(ax+aw, bx+bw) - max(ax, bx)); iy = max(0, min(ay+ah, by+bh) - max(ay, by))
    i = ix*iy; return i / (aw*ah + bw*bh - i + 1e-9)
res = {}
for run in ["large_multiclass", "2xl_init_sp26", "2xl_init_coco"]:
    p = B / "runs/A1_test_eval" / run / "detections_test.json"
    dets = json.load(open(p)); dets = dets["detections"] if isinstance(dets, dict) else dets
    by = collections.defaultdict(list)
    for d in dets: by[d["image_id"]].append(d)
    pr(f"--- {run} ---")
    out = []
    for a in G:
        ov = [d for d in by[a["image_id"]] if iou(a["bbox"], d["bbox"]) >= 0.5]
        top = max(ov, key=lambda d: d["score"]) if ov else None
        mom = max([d["score"] for d in ov if d["category_id"] == 1], default=0.0)
        oth = max([d["score"] for d in ov if d["category_id"] == 2], default=0.0)
        bi = max([d["score"] for d in ov if d["category_id"] == 0], default=0.0)
        b = key.get((imname[a["image_id"]], tuple(a["bbox"])), {})
        row = dict(file=imname[a["image_id"]], slide=b.get("slide"), rec=b.get("record_id"), title=b.get("original_title"),
                   top_cls=top["category_id"] if top else None, top_score=round(top["score"], 3) if top else 0,
                   best_momi=round(mom, 3), best_other=round(oth, 3), best_bisacc=round(bi, 3))
        out.append(row); pr(row)
    res[run] = out
json.dump(res, open(OUT / "q3_test_momipites_dets.json", "w"), indent=1)

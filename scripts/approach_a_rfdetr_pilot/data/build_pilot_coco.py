"""Relabel the Sp26 single-class COCO tiles into a small multiclass pilot for Approach A.

Reuses existing 1024px ROI tiles (best-plane by default), so no NDPI re-reading.
Each existing box (all annotated palynomorphs in the ROI) becomes either one of the
pilot classes (if an F26 priority record of that category sits inside it) or
'other_palynomorph'. Slides are re-assigned to train/val/test by splits/priority_v0;
slides with no priority_v0 assignment are dropped. Images are symlinked, not copied.
"""
import argparse, csv, json, re, collections
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--src", default="/rhf/allocations/dsci435/smithsonian_full_sp26/processed/coco/coco_tenengrad_plane")
ap.add_argument("--manifest", default="/rhf/allocations/dsci435/Smithsonian_F26/processed/priority_2d_v0/crop_manifest.csv")
ap.add_argument("--old_split", default="/rhf/allocations/dsci435/smithsonian_full_sp26/processed/train_val_test.json")
ap.add_argument("--classes", nargs="+", default=["Bisaccate", "Momipites sp"])
ap.add_argument("--out", required=True)
a = ap.parse_args()
src, out = Path(a.src), Path(a.out)
TILE_RE = re.compile(r"^(.*)_tile_(\d+)_(\d+)\.(jpe?g|png)$")

# priority records: slide -> list of (cx, cy, category, split, record_id)
recs, slide_split = collections.defaultdict(list), {}
for r in csv.DictReader(open(a.manifest)):
    recs[r["slide_id"]].append((float(r["center_x_px"]), float(r["center_y_px"]),
                                r["sponsor_category"], r["split"], r["record_id"]))
    slide_split.setdefault(r["slide_id"], r["split"])
classes = list(a.classes) + ["other_palynomorph"]
cid = {c: i for i, c in enumerate(classes)}
cats = [{"id": i, "name": c, "supercategory": "palynomorph"} for i, c in enumerate(classes)]

new = {s: {"images": [], "annotations": []} for s in ["train", "val", "test"]}
stats = collections.Counter(); per_class = collections.Counter()
matched_recs, inside_recs = set(), set()
dropped_slides = collections.Counter()
for old_split in ["train", "val", "test"]:
    d = json.load(open(src / "annotations" / f"instances_{old_split}.json"))
    by_img = collections.defaultdict(list)
    for an in d["annotations"]:
        by_img[an["image_id"]].append(an)
    for im in d["images"]:
        m = TILE_RE.match(im["file_name"]); slide, tx, ty = m.group(1), int(m.group(2)), int(m.group(3))
        sp = slide_split.get(slide)
        if sp is None:
            dropped_slides[slide] += 1; continue
        stats[f"old_{old_split}->new_{sp}"] += 1
        anns = by_img[im["id"]]
        # which priority records fall inside this tile, and which box contains each
        box_label = {}
        for (cx, cy, cat, _, rid) in recs[slide]:
            lx, ly = cx - tx, cy - ty
            if not (0 <= lx < im["width"] and 0 <= ly < im["height"]):
                continue
            inside_recs.add(rid)
            best, bd = None, 1e18
            for an in anns:
                x, y, w, h = an["bbox"]
                if x <= lx <= x + w and y <= ly <= y + h:
                    dist = (x + w / 2 - lx) ** 2 + (y + h / 2 - ly) ** 2
                    if dist < bd: best, bd = an["id"], dist
            if best is None:
                stats["record_in_tile_no_box"] += 1; continue
            matched_recs.add(rid)
            if best in box_label and box_label[best] != cat:
                stats["box_with_conflicting_records"] += 1
            box_label[best] = cat
        nid = len(new[sp]["images"])
        new[sp]["images"].append({**im, "id": nid})
        for an in anns:
            cat = box_label.get(an["id"])
            c = cat if cat in cid else "other_palynomorph"
            per_class[(sp, c)] += 1
            new[sp]["annotations"].append({**an, "id": len(new[sp]["annotations"]), "image_id": nid,
                                           "category_id": cid[c]})
        # link image
        dst = out / "images" / sp / im["file_name"]; dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists(): dst.symlink_to(src / "images" / old_split / im["file_name"])

(out / "annotations").mkdir(parents=True, exist_ok=True)
for sp, dd in new.items():
    json.dump({"info": {"description": f"Approach A pilot ({', '.join(a.classes)} + other) relabeled from {src.name}"},
               "licenses": [], "categories": cats, **dd},
              open(out / "annotations" / f"instances_{sp}.json", "w"))
(out / "dataset.yaml").write_text(
    f"path: {out}\ntrain: images/train\nval: images/val\ntest: images/test\nnc: {len(classes)}\nnames: {classes}\n")

# leakage check vs the split the pretrained checkpoint was trained on
leak = {}
try:
    old = json.load(open(a.old_split))
    old_train = set(old.get("train", []))
    for sp in ["val", "test"]:
        leak[sp] = sorted(s for s, v in slide_split.items() if v == sp and s in old_train)
except Exception as e:
    leak = {"error": str(e)}

summary = {
    "classes": classes,
    "images": {s: len(v["images"]) for s, v in new.items()},
    "boxes_per_class": {s: {c: per_class[(s, c)] for c in classes} for s in ["train", "val", "test"]},
    "priority_records_inside_any_tile": len(inside_recs),
    "priority_records_matched_to_box": len(matched_recs),
    "tile_split_moves": {k: v for k, v in stats.items() if k.startswith("old_")},
    "record_in_tile_no_box": stats["record_in_tile_no_box"],
    "box_with_conflicting_records": stats["box_with_conflicting_records"],
    "dropped_slides_no_new_split": dict(dropped_slides),
    "new_val_test_slides_seen_in_checkpoint_training": leak,
}
json.dump(summary, open(out / "pilot_summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2))

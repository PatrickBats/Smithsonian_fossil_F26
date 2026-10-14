"""Reconstruct pilot box -> priority record assignment (mirrors data/build_pilot_coco.py) with record ids/titles.
Read-only on inputs; writes outputs to model_A/analysis/."""
import csv, json, re, collections, sys
from pathlib import Path
import openslide
B = Path("/rhf/allocations/dsci435/Smithsonian_F26/model_A")
OUT = B / "analysis"
RA = "/rhf/allocations/dsci435/Smithsonian_F26/runs/dino_finetune_2026-10-07/separate_slides/smoke/record_assignments.csv"
SRC = Path("/rhf/allocations/dsci435/smithsonian_full_sp26/processed/coco/coco_tenengrad_plane")
CLASSES = ["Bisaccate", "Momipites sp"]
TILE_RE = re.compile(r"^(.*)_tile_(\d+)_(\d+)\.(jpe?g|png)$")

rows = list(csv.DictReader(open(RA)))
conv = {}
def get_conv(path):
    if path not in conv:
        s = openslide.OpenSlide(path); p = s.properties
        mx, my = float(p["openslide.mpp-x"]) * 1000, float(p["openslide.mpp-y"]) * 1000
        ox, oy = float(p["hamamatsu.XOffsetFromSlideCentre"]), float(p["hamamatsu.YOffsetFromSlideCentre"])
        W, H = s.dimensions
        conv[path] = (mx, my, ox, oy, W, H); s.close()
    return conv[path]
def to_px(path, xn, yn):
    mx, my, ox, oy, W, H = get_conv(path)
    return (xn - ox) / mx + W / 2, (yn - oy) / my + H / 2

recs = collections.defaultdict(list); slide_split = {}; recinfo = {}
for r in rows:
    cx, cy = to_px(r["image_nots_path"], float(r["x_nm"]), float(r["y_nm"]))
    recs[r["slide_id"]].append((cx, cy, r["sponsor_category"], r["split"], r["record_id"]))
    slide_split.setdefault(r["slide_id"], r["split"])
    recinfo[r["record_id"]] = r

boxes = []
per_class = collections.Counter()
for old in ["train", "val", "test"]:
    d = json.load(open(SRC / "annotations" / f"instances_{old}.json"))
    by_img = collections.defaultdict(list)
    for an in d["annotations"]: by_img[an["image_id"]].append(an)
    for im in d["images"]:
        m = TILE_RE.match(im["file_name"]); slide, tx, ty = m.group(1), int(m.group(2)), int(m.group(3))
        sp = slide_split.get(slide)
        if sp is None: continue
        anns = by_img[im["id"]]; box_rec = {}
        for (cx, cy, cat, _, rid) in recs[slide]:
            lx, ly = cx - tx, cy - ty
            if not (0 <= lx < im["width"] and 0 <= ly < im["height"]): continue
            best, bd = None, 1e18
            for an in anns:
                x, y, w, h = an["bbox"]
                if x <= lx <= x + w and y <= ly <= y + h:
                    dd = (x + w/2 - lx)**2 + (y + h/2 - ly)**2
                    if dd < bd: best, bd = an["id"], dd
            if best is not None: box_rec[best] = rid
        for an in anns:
            rid = box_rec.get(an["id"]); cat = recinfo[rid]["sponsor_category"] if rid else ""
            c = cat if cat in CLASSES else "other_palynomorph"
            per_class[(sp, c)] += 1
            boxes.append({"split": sp, "file_name": im["file_name"], "slide": slide, "bbox": an["bbox"],
                          "pilot_class": c, "record_id": rid or "", "sponsor_category": cat,
                          "original_title": recinfo[rid]["original_title"] if rid else ""})
print({f"{s}/{c}": n for (s, c), n in sorted(per_class.items())})
json.dump(boxes, open(OUT / "pilot_boxes_with_records.json", "w"))
json.dump({k: list(v) for k, v in conv.items()}, open(OUT / "slide_nm_px_conv.json", "w"))

"""detector_v3 step 2: build the training set for the retrain that tests why detector_v2 lost accuracy on the
old collections.

Changes relative to processed/coco_detector_v2/combined (split_v2, unchanged slides in every split):
  1. ignore boxes  - on NEW-collection training tiles, every detection of last semester's detector with
                     score >= CONF that does not overlap a label (max IoU < IOU) becomes an `__ignore__` box
                     (category 1). Training gives no "background" loss to queries sitting on them.
  2. rebalancing   - each OLD-collection training tile appears OLD_REPEAT times per epoch.
  3. validation    - all old validation tiles + a fixed random NEW_VAL_N of the new ones (roughly equal box
                     counts); new tiles get image ids >= 1,000,000 so metrics can be reported per collection.
Test json is the frozen old test set, copied (never used for selection).
"""
import json, gzip, os, re, random, collections, sys
import numpy as np
H = os.path.expanduser("~/Smithsonian_F26"); SRC = H + "/processed/coco_detector_v2/combined"
CONF, IOU, OLD_REPEAT, NEW_VAL_N, SPLIT_ID, SEED = 0.3, 0.5, 3, 1500, 1_000_000, 20261120
OUT = sys.argv[1] if len(sys.argv) > 1 else H + "/processed/coco_detector_v3"
SMOKE = len(sys.argv) > 2 and sys.argv[2] == "smoke"
def isnew(fn):
    m = re.search(r"_tile_(\d+)_(\d+)\.", fn); return int(m.group(1)) % 1024 == 0 and int(m.group(2)) % 1024 == 0
def iou(b, g):
    x1 = np.maximum(b[:, None, 0], g[None, :, 0]); y1 = np.maximum(b[:, None, 1], g[None, :, 1])
    x2 = np.minimum(b[:, None, 2], g[None, :, 2]); y2 = np.minimum(b[:, None, 3], g[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    return inter / (((b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1]))[:, None] + ((g[:, 2] - g[:, 0]) * (g[:, 3] - g[:, 1]))[None, :] - inter).clip(1e-9)
rng = random.Random(SEED)
tr = json.load(open(SRC + "/annotations/instances_train.json")); va = json.load(open(SRC + "/annotations/instances_val.json")); te = json.load(open(SRC + "/annotations/instances_test.json"))
assert [c["id"] for c in tr["categories"]] == [0], tr["categories"]
CATS = [tr["categories"][0], {"id": 1, "name": "__ignore__", "supercategory": "none"}]
pred = json.load(gzip.open(H + "/model_A/detector_v3/prep/pred_last_semester_new_train.json.gz", "rt"))
by = collections.defaultdict(list)
for a in tr["annotations"]: by[a["image_id"]].append(a)
images, anns = [], []; next_img = max(i["id"] for i in tr["images"]) + 1
stats = collections.defaultdict(lambda: collections.Counter()); class_rows = collections.Counter()
def add(img, a_list): 
    images.append(img)
    for a in a_list: anns.append({**a, "id": len(anns), "image_id": img["id"]})
for im in tr["images"]:
    fn = im["file_name"]; sl = re.sub(r"_tile_.*", "", fn); known = by.get(im["id"], [])
    if not isnew(fn):
        add(im, known)
        for _ in range(OLD_REPEAT - 1):
            add({**im, "id": next_img}, known); next_img += 1
        stats["__old__"]["tiles"] += 1; stats["__old__"]["labels"] += len(known); continue
    assert fn in pred, fn
    p = np.array([q for q in pred[fn] if q[4] >= CONF], float).reshape(-1, 6); class_rows.update(int(c) for c in p[:, 5])
    g = np.array([[a["bbox"][0], a["bbox"][1], a["bbox"][0] + a["bbox"][2], a["bbox"][1] + a["bbox"][3]] for a in known], float).reshape(-1, 4)
    keep = np.ones(len(p), bool)
    if len(p) and len(g): keep = iou(p[:, :4], g).max(1) < IOU
    ign = []
    for x0, y0, x1, y1, s, _ in p[keep]:
        x0, y0, x1, y1 = max(x0, 0.0), max(y0, 0.0), min(x1, float(im["width"])), min(y1, float(im["height"]))
        w, h = x1 - x0, y1 - y0
        if w <= 2 or h <= 2: continue
        ign.append({"category_id": 1, "bbox": [round(x0, 2), round(y0, 2), round(w, 2), round(h, 2)], "area": round(w * h, 2), "iscrowd": 0,
                    "pseudo_score": float(s), "source": "last_semester_detector"})
    add(im, known + ign)
    st = stats[sl]; st["tiles"] += 1; st["labels"] += len(known); st["ignore"] += len(ign); st["tiles_with_ignore"] += int(bool(ign))
# validation: old all + NEW_VAL_N new, re-id so new >= SPLIT_ID
vby = collections.defaultdict(list)
for a in va["annotations"]: vby[a["image_id"]].append(a)
old_v = [i for i in va["images"] if not isnew(i["file_name"])]; new_v = sorted([i for i in va["images"] if isnew(i["file_name"])], key=lambda i: i["file_name"])
new_v = rng.sample(new_v, NEW_VAL_N)
vimgs, vanns = [], []
for k, im in enumerate(old_v + new_v):
    nid = k if k < len(old_v) else SPLIT_ID + (k - len(old_v))
    vimgs.append({**im, "id": nid})
    for a in vby.get(im["id"], []): vanns.append({**a, "id": len(vanns), "image_id": nid})
if SMOKE:   # tiny set that still exercises every code path
    ign_ids = {a["image_id"] for a in anns if a["category_id"] == 1}
    with_ign = [i for i in images if i["id"] in ign_ids][:16]
    olds = [i for i in images if not isnew(i["file_name"])][:16]
    keep_ids = {i["id"] for i in with_ign + olds}; images = with_ign + olds; anns = [a for a in anns if a["image_id"] in keep_ids]
    has = {a["image_id"] for a in vanns}
    vk = [i for i in vimgs[:len(old_v)] if i["id"] in has][:12] + vimgs[len(old_v):len(old_v) + 12]; kid = {i["id"] for i in vk}; vimgs = vk; vanns = [a for a in vanns if a["image_id"] in kid]
os.makedirs(OUT + "/annotations", exist_ok=True); os.makedirs(OUT + "/images", exist_ok=True)
json.dump({"images": images, "annotations": anns, "categories": CATS}, open(OUT + "/annotations/instances_train.json", "w"))
json.dump({"images": vimgs, "annotations": vanns, "categories": CATS}, open(OUT + "/annotations/instances_val.json", "w"))
json.dump({"images": te["images"], "annotations": te["annotations"], "categories": CATS}, open(OUT + "/annotations/instances_test.json", "w"))
for s in ("train", "val", "test"):
    if not os.path.lexists(f"{OUT}/images/{s}"): os.symlink(f"{SRC}/images/{s}", f"{OUT}/images/{s}")
n_old = sum(1 for i in images if not isnew(i["file_name"])); n_lab = sum(1 for a in anns if a["category_id"] == 0); n_ign = sum(1 for a in anns if a["category_id"] == 1)
new_slides = {k: dict(v) for k, v in stats.items() if k != "__old__"}
summary = dict(out=OUT, smoke=SMOKE, conf=CONF, iou=IOU, old_repeat=OLD_REPEAT, seed=SEED,
               train=dict(image_entries=len(images), old_entries=n_old, new_entries=len(images) - n_old, labels=n_lab, ignore_boxes=n_ign,
                          old_share_of_entries=round(n_old / len(images), 3),
                          new_tiles_with_ignore=sum(v.get("tiles_with_ignore", 0) for v in new_slides.values()),
                          new_labels=sum(v.get("labels", 0) for v in new_slides.values())),
               val=dict(images=len(vimgs), old_images=sum(1 for i in vimgs if i["id"] < SPLIT_ID), new_images=sum(1 for i in vimgs if i["id"] >= SPLIT_ID),
                        old_boxes=sum(1 for a in vanns if a["image_id"] < SPLIT_ID), new_boxes=sum(1 for a in vanns if a["image_id"] >= SPLIT_ID)),
               detector_head_rows_fired=dict(class_rows), per_new_slide=new_slides)
json.dump(summary, open(OUT + "/build_summary.json", "w"), indent=1)
print(json.dumps({k: v for k, v in summary.items() if k != "per_new_slide"}, indent=1))
print("new slides by ignore boxes: slide, tiles, labels, ignore, ignore/labels")
for k, v in sorted(new_slides.items(), key=lambda kv: -kv[1].get("ignore", 0))[:25]:
    print(f"  {k[:52]:52s} {v['tiles']:5d} {v['labels']:6d} {v.get('ignore', 0):6d}  {v.get('ignore', 0) / max(v['labels'], 1):.2f}")

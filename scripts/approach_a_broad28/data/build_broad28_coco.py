"""Relabel the Approach A pilot tiles to the team's 28 broad categories (broad_v1) + other_palynomorph.

Same tiles, boxes and grouped split as data/pilot_top2_bestplane; only the category of each box changes.
Box -> priority record mapping comes from analysis/pilot_boxes_with_records.json (built by
analysis/momi_recon.py, which reproduces the pilot box counts exactly).
Optional repeat-factor sampling (Gupta et al., LVIS, CVPR 2019) duplicates train image entries:
r(c) = max(1, sqrt(t / f(c))), f(c) = fraction of train images containing class c; image repeat = max r(c), capped.
"""
import argparse, csv, json, math, collections, os
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--src", default="/rhf/allocations/dsci435/Smithsonian_F26/model_A/data/pilot_top2_bestplane")
ap.add_argument("--boxes", default="/rhf/allocations/dsci435/Smithsonian_F26/model_A/analysis/pilot_boxes_with_records.json")
ap.add_argument("--map", default="/rhf/allocations/dsci435/Smithsonian_F26/model_A/labels/broad_v1_fine_to_broad.csv")
ap.add_argument("--out", required=True)
ap.add_argument("--rfs_t", type=float, default=0.0, help="repeat-factor threshold; 0 disables")
ap.add_argument("--rfs_cap", type=int, default=4)
a = ap.parse_args()

rows = list(csv.DictReader(open(a.map)))
fine2broad = {r["fine_category"]: r["broad_category"] for r in rows}
broad = sorted({(int(r["broad_class_id"]), r["broad_category"]) for r in rows})
assert [i for i, _ in broad] == list(range(28)), broad
names = [n for _, n in broad] + ["other_palynomorph"]
cid = {n: i for i, n in enumerate(names)}

key = lambda split, fn, bb: (split, fn, tuple(round(float(v), 1) for v in bb))
lab = {}
for b in json.load(open(a.boxes)):
    sc = b["sponsor_category"]
    if sc and sc not in fine2broad:
        raise SystemExit(f"unmapped sponsor category {sc!r}")
    lab[key(b["split"], b["file_name"], b["bbox"])] = fine2broad[sc] if sc else "other_palynomorph"

out = Path(a.out); (out / "annotations").mkdir(parents=True, exist_ok=True); (out / "images").mkdir(exist_ok=True)
summary = {"classes": names, "boxes_per_class": {}, "images": {}, "missing_box_records": 0, "rfs": None}
for split in ["train", "val", "test"]:
    link = out / "images" / split
    if not link.exists():
        os.symlink((Path(a.src) / "images" / split).resolve(), link)
    d = json.load(open(Path(a.src) / "annotations" / f"instances_{split}.json"))
    fn = {im["id"]: im["file_name"] for im in d["images"]}
    for an in d["annotations"]:
        k = key(split, fn[an["image_id"]], an["bbox"])
        if k not in lab:
            summary["missing_box_records"] += 1
            raise SystemExit(f"no record for box {k}")
        an["category_id"] = cid[lab[k]]
    d["categories"] = [{"id": i, "name": n, "supercategory": "palynomorph"} for i, n in enumerate(names)]
    cnt = collections.Counter(names[an["category_id"]] for an in d["annotations"])
    summary["boxes_per_class"][split] = {n: cnt.get(n, 0) for n in names}
    if split == "train" and a.rfs_t > 0:
        per_img = collections.defaultdict(set)
        for an in d["annotations"]:
            per_img[an["image_id"]].add(an["category_id"])
        n_img = len(d["images"])
        f = collections.Counter(c for cs in per_img.values() for c in cs)
        r = {c: max(1.0, math.sqrt(a.rfs_t / (f[c] / n_img))) for c in f}
        new_imgs, new_anns = list(d["images"]), list(d["annotations"])
        next_img = max(im["id"] for im in d["images"]) + 1
        next_ann = max(an["id"] for an in d["annotations"]) + 1
        anns_by_img = collections.defaultdict(list)
        for an in d["annotations"]:
            anns_by_img[an["image_id"]].append(an)
        extra = 0
        for im in d["images"]:
            rep = min(a.rfs_cap, round(max([r[c] for c in per_img.get(im["id"], ())] or [1.0])))
            for _ in range(rep - 1):
                new_imgs.append(dict(im, id=next_img))
                for an in anns_by_img[im["id"]]:
                    new_anns.append(dict(an, id=next_ann, image_id=next_img)); next_ann += 1
                next_img += 1; extra += 1
        d["images"], d["annotations"] = new_imgs, new_anns
        summary["rfs"] = {"t": a.rfs_t, "cap": a.rfs_cap, "extra_image_entries": extra,
                          "repeat_factor": {names[c]: round(v, 2) for c, v in sorted(r.items())}}
    summary["images"][split] = len(d["images"])
    json.dump(d, open(out / "annotations" / f"instances_{split}.json", "w"))
json.dump(summary, open(out / "broad28_summary.json", "w"), indent=2)
print(json.dumps({k: summary[k] for k in ["images", "rfs"]}, indent=1))
print(json.dumps(summary["boxes_per_class"]["train"]))

"""Stage 1 of detector-first training: turn the ignore-region dataset into a one-class dataset.
Every box (sponsor label or ignore region found by last semester's detector on TRAINING tiles)
becomes category "pollen". Images are hard-linked, so this costs no disk. Validation slides are
not involved: the ignore regions were produced on training tiles only."""
import argparse, json, os, shutil
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--src", required=True, help="dataset dir produced by make_ignore_labels.py")
p.add_argument("--out", required=True)
a = p.parse_args()
src, out = Path(a.src), Path(a.out)
assert not out.exists(), out
for split in ("train", "valid", "test"):
    d = src / split
    if not d.exists():
        continue
    (out / split).mkdir(parents=True)
    coco = json.loads((d / "_annotations.coco.json").read_text())
    cat = dict(coco["categories"][0]); cat.update(id=1, name="pollen")
    for k in ("supercategory",):
        if k in cat: cat[k] = "pollen"
    n_ign = sum(1 for x in coco["annotations"] if any(c["id"] == x["category_id"] and c["name"] == "__ignore__" for c in coco["categories"]))
    for x in coco["annotations"]:
        x["category_id"] = 1
    coco["categories"] = [cat]
    (out / split / "_annotations.coco.json").write_text(json.dumps(coco))
    for img in coco["images"]:
        s, t = d / img["file_name"], out / split / img["file_name"]
        try:
            os.link(s.resolve(), t)
        except OSError:
            shutil.copy2(s, t)
    print(json.dumps(dict(split=split, images=len(coco["images"]), boxes=len(coco["annotations"]), from_ignore_regions=n_ign)))
summary = {}
if (src / "ignore_labels_summary.json").exists():
    summary = {k: v for k, v in json.loads((src / "ignore_labels_summary.json").read_text()).items() if k != "per_tile"}
(out / "oneclass_summary.json").write_text(json.dumps(dict(source=str(src), source_ignore_summary=summary), indent=2))

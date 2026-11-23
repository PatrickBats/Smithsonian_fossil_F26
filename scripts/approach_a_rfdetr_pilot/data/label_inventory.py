"""Draft Approach-A label map + per-class counts inside annotated ROIs.

Inputs (read-only):
  annotations_F26/annotations_summary.csv, annotations_points.csv  (all circles + ROI rectangles)
  splits/priority_v0/record_assignments.csv                        (2,283 priority records, split, sponsor_category)
  splits/priority_v0/group_assignments.csv                         (slide -> split)
Outputs (in --out):
  label_map_draft.csv        title -> model class (32 priority categories or 'other_palynomorph')
  class_counts_inside_roi.csv  class x split counts, inside ROIs only (what A1 can train/eval on)
  class_counts_all.csv       same, including outside-ROI priority records
  inventory_summary.json
"""
import argparse, csv, collections, json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--ann", default="/rhf/allocations/dsci435/smithsonian_full_sp26/annotations_F26")
ap.add_argument("--split", default="/rhf/allocations/dsci435/Smithsonian_F26/splits/priority_v0")
ap.add_argument("--out", required=True)
a = ap.parse_args()
A, S, O = Path(a.ann), Path(a.split), Path(a.out)
O.mkdir(parents=True, exist_ok=True)
norm = lambda t: " ".join(t.strip().lower().split())

# --- priority records: title -> sponsor category, (file, viewstate) -> record
prio = list(csv.DictReader(open(S / "record_assignments.csv")))
title2cat = collections.defaultdict(collections.Counter)
prio_key = {}
for r in prio:
    title2cat[norm(r["original_title"])][r["sponsor_category"]] += 1
    title2cat[norm(r["lookup_title"])][r["sponsor_category"]] += 1
    prio_key[(r["annotation_filename"], r["viewstate_id"])] = r
conflicts = {t: dict(c) for t, c in title2cat.items() if len(c) > 1}
t2c = {t: c.most_common(1)[0][0] for t, c in title2cat.items()}
classes = sorted({r["sponsor_category"] for r in prio})

# --- slide -> split (via the split group of any priority record on that slide's annotation file)
file_split = {}
for r in prio:
    file_split.setdefault(r["annotation_filename"], r["split"])

# --- ROIs and circles
pts = collections.defaultdict(list)
for p in csv.DictReader(open(A / "annotations_points.csv")):
    pts[(p["file"], p["ndpviewstate_id"])].append((int(p["x"]), int(p["y"])))
rois, circles = collections.defaultdict(list), []
for r in csv.DictReader(open(A / "annotations_summary.csv")):
    if r["specialtype"] == "rectangle":
        P = pts[(r["file"], r["ndpviewstate_id"])]
        xs, ys = [x for x, _ in P], [y for _, y in P]
        rois[r["file"]].append((min(xs), min(ys), max(xs), max(ys)))
    elif r["annotation_type"] == "circle":
        circles.append(r)
inroi = lambda f, x, y: any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in rois[f])

inside = collections.Counter(); allc = collections.Counter()
other_titles = collections.Counter(); leaked = collections.Counter(); no_split = collections.Counter()
for c in circles:
    f, v, t = c["file"], c["ndpviewstate_id"], c["title"]
    x, y = int(c["x_center"]), int(c["y_center"])
    sp = file_split.get(f)
    if (f, v) in prio_key:
        cls = prio_key[(f, v)]["sponsor_category"]; sp = prio_key[(f, v)]["split"]
    else:
        cls = "other_palynomorph"
        if norm(t) in t2c:  # priority title but not a retained priority record (exclusion/duplicate)
            leaked[(t2c[norm(t)])] += 1
        other_titles[norm(t) or "<untitled>"] += 1
    if sp is None:
        no_split[f] += 1; sp = "unassigned"
    allc[(cls, sp)] += 1
    if inroi(f, x, y):
        inside[(cls, sp)] += 1

def table(cnt, path):
    rows = []
    for cls in classes + ["other_palynomorph"]:
        row = {"class": cls}
        for sp in ["train", "val", "test", "unassigned"]:
            row[sp] = cnt.get((cls, sp), 0)
        row["total"] = sum(row[s] for s in ["train", "val", "test", "unassigned"])
        rows.append(row)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return rows

r_in = table(inside, O / "class_counts_inside_roi.csv")
r_all = table(allc, O / "class_counts_all.csv")
with open(O / "label_map_draft.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["title_normalized", "model_class", "source"])
    for t, c in sorted(t2c.items()): w.writerow([t, c, "priority_v0 sponsor_category"])
    for t, n in other_titles.most_common():
        if t not in t2c: w.writerow([t, "other_palynomorph", f"non-priority ({n} annotations)"])

pc = [r for r in r_in if r["class"] != "other_palynomorph"]
summary = dict(
    n_classes=len(classes) + 1, n_priority_records=len(prio), n_circles=len(circles),
    slides_with_rois=len(rois), slides_without_split=dict(no_split),
    inside_roi_priority_by_split={s: sum(r[s] for r in pc) for s in ["train", "val", "test"]},
    inside_roi_other_by_split={s: next(r for r in r_in if r["class"] == "other_palynomorph")[s] for s in ["train", "val", "test", "unassigned"]},
    classes_lt10_train_inside_roi=[r["class"] for r in pc if r["train"] < 10],
    classes_zero_val_inside_roi=[r["class"] for r in pc if r["val"] == 0],
    classes_zero_test_inside_roi=[r["class"] for r in pc if r["test"] == 0],
    priority_titles_seen_as_other=dict(leaked), title_category_conflicts=conflicts,
    top_other_titles=other_titles.most_common(25),
)
json.dump(summary, open(O / "inventory_summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2))
print("\nclass                              train  val test  (inside ROI)")
for r in r_in: print(f"{r['class'][:34]:34s} {r['train']:5d} {r['val']:4d} {r['test']:4d}")

import json, collections, csv
from pathlib import Path
B = Path("/rhf/allocations/dsci435/Smithsonian_F26/model_A"); OUT = B / "analysis"
boxes = json.load(open(OUT / "pilot_boxes_with_records.json"))
pr = lambda *a: print(*a, flush=True)
for sp in ["train", "val", "test"]:
    c = collections.Counter(b["slide"] for b in boxes if b["split"] == sp and b["sponsor_category"] == "Momipites sp")
    u = collections.defaultdict(set)
    for b in boxes:
        if b["split"] == sp and b["sponsor_category"] == "Momipites sp": u[b["slide"]].add(b["record_id"])
    pr(sp, "Momipites sp boxes per slide:", c.most_common(), " n_slides", len(c))
    s = collections.Counter(b["slide"] for b in boxes if b["split"] == sp and "momip" in b["sponsor_category"].lower() and b["sponsor_category"] != "Momipites sp")
    pr(sp, "species-Momipites boxes per slide:", s.most_common())
pr("=== train 'other' boxes by source: priority categories (tile-boxes) ===")
c = collections.Counter((b["sponsor_category"] or "<non-priority>") for b in boxes if b["split"] == "train" and b["pilot_class"] == "other_palynomorph")
pr(c.most_common())
pr("=== test 'other' boxes by source ===")
c = collections.Counter((b["sponsor_category"] or "<non-priority>") for b in boxes if b["split"] == "test" and b["pilot_class"] == "other_palynomorph")
pr(c.most_common())
# raw non-priority circle titles that look triporate / juglandaceous
ANN = Path("/rhf/allocations/dsci435/smithsonian_full_sp26/annotations_F26")
keys = ["momip", "carya", "engelhard", "triporopoll", "plicatopoll", "betula", "juglan", "platycar", "triatriopoll", "alnipoll", "pterocar"]
c = collections.Counter()
for r in csv.DictReader(open(ANN / "annotations_summary.csv")):
    t = " ".join(r["title"].lower().split())
    if r["annotation_type"] == "circle" and any(k in t for k in keys): c[t] += 1
pr("raw circle titles (all slides) matching triporate/juglandaceous keys:", c.most_common(40))

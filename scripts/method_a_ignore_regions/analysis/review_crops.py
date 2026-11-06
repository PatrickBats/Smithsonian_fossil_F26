"""Cut example crops for the sponsor review slide: misclassified tail-class specimens next to
correctly identified specimens of the class they were mistaken for. Validation tiles only."""
import json, glob, collections, sys
from pathlib import Path
from PIL import Image

R = Path.home() / "Smithsonian_F26"
BASE = R / "processed/method_a_focus_stack_v1"
EVAL = R / "model_A/runs/A4_cocoinit_local/eval"
OUT = R / "model_A/runs/review_crops"; OUT.mkdir(exist_ok=True)

plans = [json.load(open(p)) for p in sorted((BASE / "plan").glob("*.json"))]
plans = [p for p in plans if p["split"] == "valid"]
# record -> (tile_id, pixel box) choosing a tile that fully contains the box
loc = {}
for p in plans:
    for t in p["tiles"]:
        for o in t["objects"]:
            x0, y0, x1, y1 = o["box_slide"]
            px = [x0 - t["left"], y0 - t["top"], x1 - t["left"], y1 - t["top"]]
            inside = px[0] >= 0 and px[1] >= 0 and px[2] <= 1024 and px[3] <= 1024
            if o["record_id"] not in loc or (inside and not loc[o["record_id"]][2]):
                loc[o["record_id"]] = (t["tile_id"], px, inside)

m = json.load(open(EVAL / "full_confidence_0.30_matches.json"))
det = [x for x in m if x["detected"]]
groups = [  # (true class, predicted class)
    ("Ulmipollenites sp.", "Alnipollenites verus"),
    ("Ulmipollenites sp.", "Momipites"),
    ("Psilatricolpites sp.", "Rhoipites sp."),
    ("Taxodium sp.", "Inaperturopollenites sp."),
    ("Bombacacidites sp.", "Momipites"),
    ("Betulaceae", "Momipites"),
]
PAD = 0.6; MIN = 140; UP = 3

def crop(rec, name):
    tile_id, px, inside = loc[rec]
    im = Image.open(BASE / "dataset/valid" / f"{tile_id}.png")
    w, h = px[2] - px[0], px[3] - px[1]
    s = max(w, h) * (1 + PAD); s = max(s, MIN)
    cx, cy = (px[0] + px[2]) / 2, (px[1] + px[3]) / 2
    box = [int(cx - s / 2), int(cy - s / 2), int(cx + s / 2), int(cy + s / 2)]
    c = im.crop(box).resize((int(s * UP), int(s * UP)), Image.LANCZOS)
    c.save(OUT / f"{name}.png"); return w, h

index = []
for gi, (tc, pc) in enumerate(groups):
    mis = [x for x in det if x["true_category"] == tc and x["predicted_category"] == pc]
    ref = [x for x in det if x["true_category"] == pc and x["category_correct"]]
    ok = [x for x in det if x["true_category"] == tc and x["category_correct"]]
    print(f"{tc} -> {pc}: {len(mis)} misclassified, {len(ref)} correct refs of {pc}, {len(ok)} correct {tc}")
    for j, x in enumerate(mis[:3]):
        w, h = crop(x["record_id"], f"g{gi}_mis{j}"); index.append(dict(g=gi, kind="mis", i=j, true=tc, pred=pc, rec=x["record_id"], w=w, h=h, slide=x["source"].split("/")[-1][:30]))
    for j, x in enumerate(ref[:3]):
        w, h = crop(x["record_id"], f"g{gi}_ref{j}"); index.append(dict(g=gi, kind="ref", i=j, true=pc, pred=pc, rec=x["record_id"], w=w, h=h, slide=x["source"].split("/")[-1][:30]))
    for j, x in enumerate(ok[:2]):
        w, h = crop(x["record_id"], f"g{gi}_ok{j}"); index.append(dict(g=gi, kind="ok", i=j, true=tc, pred=tc, rec=x["record_id"], w=w, h=h, slide=x["source"].split("/")[-1][:30]))
json.dump(index, open(OUT / "index.json", "w"), indent=1)
print("wrote", len(index), "crops to", OUT)

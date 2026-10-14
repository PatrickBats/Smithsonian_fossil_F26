"""Draw expert boxes vs model predictions on example val/test tiles (Approach A pilot)."""
import json, re, sys, collections, warnings
from pathlib import Path
import numpy as np, cv2
warnings.filterwarnings("ignore")
from rfdetr.detr import RFDETRLarge

B = Path("/rhf/allocations/dsci435/Smithsonian_F26/model_A")
DATA = B / "data/pilot_top2_bestplane"
CKPT = B / "runs/A1_pilot_large_bestplane/multiclass_top2/checkpoint_best_ema.pth"
OUT = B / "figures"; OUT.mkdir(exist_ok=True)
NAMES = ["Bisaccate", "Momipites sp", "other_palynomorph"]
SHORT = {"Bisaccate": "Bisaccate", "Momipites sp": "Momipites", "other_palynomorph": "other"}
# reference categorical palette slots 1-3 (BGR for cv2)
HEX = {"Momipites sp": "#2a78d6", "Bisaccate": "#eb6834", "other_palynomorph": "#1baf7a"}
BGR = {k: tuple(int(v[i:i+2], 16) for i in (5, 3, 1)) for k, v in HEX.items()}
THR = float(sys.argv[1]) if len(sys.argv) > 1 else 0.35

def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    i = max(0, x2 - x1) * max(0, y2 - y1)
    return i / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i + 1e-9)

def pick(split, n):
    d = json.load(open(DATA / f"annotations/instances_{split}.json"))
    by = collections.defaultdict(list)
    for a in d["annotations"]: by[a["image_id"]].append(a)
    scored = []
    for im in d["images"]:
        anns = by[im["id"]]
        nb = sum(a["category_id"] == 0 for a in anns); nm = sum(a["category_id"] == 1 for a in anns)
        full = sum(a["bbox"][2] > 40 and a["bbox"][3] > 40 for a in anns if a["category_id"] in (0, 1))
        if nb + nm: scored.append((nm > 0, full, nb + nm, im, anns))
    # half the tiles richest in whole Bisaccate grains, half containing Momipites; one tile per slide
    def nb_full(t): return sum(a["category_id"] == 0 and a["bbox"][2] > 40 and a["bbox"][3] > 40 for a in t[4])
    bis = sorted([t for t in scored if nb_full(t) > 0], key=lambda t: (nb_full(t), t[1]), reverse=True)
    mom = sorted([t for t in scored if t[0]], key=lambda t: t[1], reverse=True)
    chosen, slides = [], set()
    for pool in (bis, mom):
        k = 0
        for s in pool:
            sl = s[3]["file_name"].split("_tile_")[0]
            if sl in slides: continue
            chosen.append(s); slides.add(sl); k += 1
            if k == n // 2: break
    return [(split, im, anns) for *_, im, anns in chosen]

model = RFDETRLarge(pretrain_weights=str(CKPT), num_classes=3, resolution=1024,
                    positional_encoding_size=44, device="cpu")
model.optimize_for_inference()
tiles = pick("test", 4) + pick("val", 4)

# empirically determine predicted-id -> category mapping (rfdetr may offset ids)
votes = collections.Counter(); results = []
for split, im, anns in tiles:
    img = cv2.imread(str(DATA / "images" / split / im["file_name"]))
    det = model.predict(img[:, :, ::-1].copy(), threshold=THR)
    gts = [([a["bbox"][0], a["bbox"][1], a["bbox"][0]+a["bbox"][2], a["bbox"][1]+a["bbox"][3]], a["category_id"]) for a in anns]
    for b, c in zip(det.xyxy, det.class_id):
        best = max(gts, key=lambda g: iou(b, g[0]), default=None)
        if best is not None and iou(b, best[0]) > 0.5: votes[(int(c), best[1])] += 1
    results.append((split, im, img, gts, det))
# rfdetr returns class ids equal to our COCO category ids (0..2); votes are printed as a check
mapping = {0: 0, 1: 1, 2: 2}
print("pred-id -> gt-category votes:", dict(votes)); print("mapping:", {p: NAMES[g] for p, g in mapping.items()})

def draw(img, boxes, title):
    out = img.copy()
    for (x1, y1, x2, y2), name, score in boxes:
        col = BGR[name]
        cv2.rectangle(out, (int(x1), int(y1)), (int(x2), int(y2)), col, 4 if name != "other_palynomorph" else 2)
        if name != "other_palynomorph":
            lab = SHORT[name] + (f" {score:.2f}" if score is not None else "")
            (tw, th), _ = cv2.getTextSize(lab, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
            ty = int(y1) - 8 if y1 > th + 12 else int(y2) + th + 8
            cv2.rectangle(out, (int(x1), ty - th - 6), (int(x1) + tw + 8, ty + 6), (252, 252, 251), -1)
            cv2.putText(out, lab, (int(x1) + 4, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (11, 11, 11), 2, cv2.LINE_AA)
    bar = np.full((70, out.shape[1], 3), 252, np.uint8)
    cv2.putText(bar, title, (16, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (11, 11, 11), 2, cv2.LINE_AA)
    return np.vstack([bar, out])

summary = []
for i, (split, im, img, gts, det) in enumerate(results):
    g = [(b, NAMES[c], None) for b, c in gts]
    p = [(b, NAMES[mapping.get(int(c), 2)], float(s)) for b, c, s in zip(det.xyxy, det.class_id, det.confidence)]
    gap = np.full((img.shape[0] + 70, 16, 3), 252, np.uint8)
    panel = np.hstack([draw(img, g, "Expert annotations"), gap, draw(img, p, f"Model predictions (conf >= {THR})")])
    slide = im["file_name"].split("_tile_")[0]
    name = f"example_{i+1:02d}_{split}.png"
    cv2.imwrite(str(OUT / name), cv2.resize(panel, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA))
    cnt = lambda L: dict(collections.Counter(SHORT[n] for _, n, _ in L))
    summary.append({"file": name, "split": split, "slide": slide, "tile": im["file_name"], "gt": cnt(g), "pred": cnt(p)})
    print(name, split, slide, "GT", cnt(g), "PRED", cnt(p))
json.dump({"checkpoint": str(CKPT), "threshold": THR, "mapping": {str(k): NAMES[v] for k, v in mapping.items()}, "tiles": summary},
          open(OUT / "examples_summary.json", "w"), indent=2)

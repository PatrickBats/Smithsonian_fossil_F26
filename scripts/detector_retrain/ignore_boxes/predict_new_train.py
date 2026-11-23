"""detector_v3 step 1: run last semester's one-class detector over every NEW-collection training tile
(tile offsets on the 1024 grid) and cache all detections with score >= 0.02, keyed by file name.
build_dataset_v3.py turns the confident ones that do not overlap a label into __ignore__ boxes."""
import json, gzip, os, re, time
from PIL import Image
H = os.path.expanduser("~/Smithsonian_F26"); C = H + "/processed/coco_detector_v2/combined"
OUT = H + "/model_A/detector_v3/prep/pred_last_semester_new_train.json.gz"
def isnew(fn):
    m = re.search(r"_tile_(\d+)_(\d+)\.", fn); return int(m.group(1)) % 1024 == 0 and int(m.group(2)) % 1024 == 0
tr = json.load(open(C + "/annotations/instances_train.json"))
files = sorted({i["file_name"] for i in tr["images"] if isnew(i["file_name"])})
print("new train tiles", len(files), flush=True)
from rfdetr_plus.models.detection import RFDETR2XLarge
m = RFDETR2XLarge(pretrain_weights=H + "/weights/rfdetr(2xl)_focus_stack.pth", num_classes=1, resolution=1000)
P = {}; t0 = time.time()
for k, fn in enumerate(files):
    with Image.open(f"{C}/images/train/{fn}") as pil: ds = m.predict(pil.convert("RGB"), threshold=0.02)
    P[fn] = [[round(float(v), 2) for v in b] + [round(float(s), 4), int(c)] for b, s, c in zip(ds.xyxy, ds.confidence, ds.class_id)]
    if k % 1000 == 0: print(json.dumps({"done": k + 1, "total": len(files), "elapsed_s": round(time.time() - t0)}), flush=True)
with gzip.open(OUT + ".tmp", "wt") as h: json.dump(P, h)
os.replace(OUT + ".tmp", OUT)
print("PREP DONE", len(P), round(time.time() - t0), "s", flush=True)

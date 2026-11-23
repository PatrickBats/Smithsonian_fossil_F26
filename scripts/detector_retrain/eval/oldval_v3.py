"""Score the detector_v3 checkpoint on the old-collection validation tiles (same pycocotools code path used for
last semester's detector and detector_v2 on 2026-11-21)."""
import json, gzip, os, re, io, contextlib
from PIL import Image
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval
H = os.path.expanduser("~/Smithsonian_F26"); C = H + "/processed/coco_detector_v2/combined"; E = H + "/model_A/detector_v2/eval_20261120"
def isnew(fn):
    m = re.search(r"_tile_(\d+)_(\d+)\.", fn); return int(m.group(1)) % 1024 == 0 and int(m.group(2)) % 1024 == 0
va = json.load(open(C + "/annotations/instances_val.json"))
ims = [i for i in va["images"] if not isnew(i["file_name"])]; ids = {i["id"] for i in ims}
gt = {"images": ims, "annotations": [{**a, "category_id": 1} for a in va["annotations"] if a["image_id"] in ids], "categories": [{"id": 1, "name": "p"}]}
from rfdetr_plus.models.detection import RFDETR2XLarge
m = RFDETR2XLarge(pretrain_weights=H + "/model_A/detector_v3/runs/dv3_ignore_bal_20261120/checkpoint_best_total.pth", num_classes=1, resolution=1000)
P = []
for im in ims:
    with Image.open(f"{C}/images/val/{im['file_name']}") as pil: ds = m.predict(pil.convert("RGB"), threshold=0.02)
    P.append([[float(v) for v in b] + [float(s)] for b, s in zip(ds.xyxy, ds.confidence)])
json.dump({"old_val": P}, gzip.open(E + "/diag2_pred_v3_detector_oldval.json.gz", "wt"))
dets = [{"image_id": im["id"], "category_id": 1, "bbox": [x1, y1, x2 - x1, y2 - y1], "score": s} for im, p in zip(ims, P) for x1, y1, x2, y2, s in p]
with contextlib.redirect_stdout(io.StringIO()):
    g = COCO(); g.dataset = gt; g.createIndex(); ev = COCOeval(g, g.loadRes(dets), "bbox"); ev.params.maxDets = [1, 100, 500]; ev.evaluate(); ev.accumulate(); ev.summarize()
print("OLDVAL v3_detector mAP50 %.4f mAP50:95 %.4f" % (ev.stats[1], ev.stats[0]), flush=True)
print("OLDVAL DONE", flush=True)

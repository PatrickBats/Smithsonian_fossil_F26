"""Score a Method A checkpoint on one held-out new-scan fold (Yunfan's 5-fold split).

Local (PC) wrapper around method_a_new_delivery.cv_evaluate.score_fold: same crops, same
padding rule, same class-agnostic NMS and one-to-one IoU>=0.5 matching; only paths differ.
"""
import argparse, gzip, json, os, sys
from pathlib import Path
from PIL import Image

H = Path(os.path.expanduser("~/Smithsonian_F26"))
sys.path.insert(0, str(H / "from_nots/yunfan_method_a_code/new_delivery/src"))
from method_a_new_delivery.cv_evaluate import score_fold, THRESHOLDS  # noqa: E402

TRAINING = H / "from_nots/yunfan_new_delivery/training"


def main():
    from rfdetr_plus.models.detection import RFDETR2XLarge
    p = argparse.ArgumentParser()
    p.add_argument("--fold", type=int, required=True, choices=range(5))
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    fold_data = TRAINING / "cross_validation" / f"fold_{a.fold}"
    manifest = json.loads((fold_data / "manifest.json").read_text())
    cats = sorted(json.loads((fold_data / "valid/_annotations.coco.json").read_text())["categories"], key=lambda c: c["id"])
    assert len(cats) == 28, len(cats)
    categories = {i: c["name"] for i, c in enumerate(cats)}
    plans = [json.loads(f.read_text()) for f in sorted((TRAINING / "plan").glob("*.json"))]
    plans = [pl for pl in plans if pl["source"] in manifest["held_out_scans"]]
    assert len(plans) == 4, len(plans)
    model = RFDETR2XLarge(pretrain_weights=a.checkpoint, num_classes=28, resolution=1000)
    raw, invalid = {}, 0
    for pl in plans:
        for crop in pl["crops"]:
            with Image.open(fold_data / "valid" / (crop["tile_id"] + ".png")) as im:
                res = model.predict(im.convert("RGB"), threshold=0.25)
            vals = []
            for box, conf, cid in zip(res.xyxy, res.confidence, res.class_id):
                cid = int(cid)
                if cid == 28:
                    invalid += 1; continue
                assert 0 <= cid < 28
                vals.append({"box": [float(x) for x in box], "score": float(conf), "class_id": cid})
            raw[crop["tile_id"]] = vals
    with gzip.open(out / "raw_predictions.json.gz", "wt") as h:
        json.dump(raw, h)
    results = []
    for t in THRESHOLDS:
        summary, matches = score_fold(plans, raw, categories, t)
        assert summary["known_specimens"] == manifest["held_out_source_objects"]
        summary.update(fold=a.fold, checkpoint=a.checkpoint, invalid_slot_predictions=invalid)
        (out / f"confidence_{t:.2f}_summary.json").write_text(json.dumps(summary, indent=1))
        (out / f"confidence_{t:.2f}_matches.json").write_text(json.dumps(matches))
        results.append({"threshold": t, "known": summary["known_specimens"], "detected": summary["detected"], "correct": summary["correct"]})
    (out / "summary.json").write_text(json.dumps({"fold": a.fold, "status": "completed", "checkpoint": a.checkpoint, "results": results}, indent=1))
    print(json.dumps({"fold": a.fold, "results": results}))


if __name__ == "__main__":
    main()

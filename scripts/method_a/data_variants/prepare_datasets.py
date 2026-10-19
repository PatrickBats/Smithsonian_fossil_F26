"""Create new COCO datasets; Method B and baseline inputs are never modified."""

import collections, csv, math, random
import hashlib
import json
from common import BASE, EXPERIMENTS, ROOT, SEED, load, sha, write


def link(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    assert not dst.exists() and not dst.is_symlink()
    dst.symlink_to(src)


def coco_base():
    return {
        k: v
        for k, v in load(BASE / "dataset/train/_annotations.coco.json").items()
        if k not in ("images", "annotations")
    }


def make_dataset(name, tiles=None):
    dest = ROOT / "datasets" / name
    dest.mkdir(parents=True, exist_ok=False)
    link(BASE / "dataset/valid", dest / "valid")
    (dest / "test").mkdir()
    write(dest / "test/_annotations.coco.json", {**coco_base(), "images": [], "annotations": []})
    train = dest / "train"
    train.mkdir()
    if name == "m1_positive_grid":
        old = load(BASE / "dataset/train/_annotations.coco.json")
        ids = {a["image_id"] for a in old["annotations"]}
        images = [i for i in old["images"] if i["id"] in ids]
        assert len(images) == 884
        for i in images:
            link(BASE / "dataset/train" / i["file_name"], train / i["file_name"])
        data = {**old, "images": images}
    else:
        images = []
        annotations = []
        for tile in tiles:
            meta = load(ROOT / "images/crops" / f"{tile['tile_id']}.json")
            assert meta["status"] == "verified" and meta["sha256"] == sha(
                ROOT / "images/crops" / f"{tile['tile_id']}.png"
            )
            iid = len(images) + 1
            fn = f"{tile['tile_id']}.png"
            images.append({"id": iid, "file_name": fn, "width": 1024, "height": 1024})
            link(ROOT / "images/crops" / fn, train / fn)
            for obj in tile["objects"]:
                annotations.append(
                    {
                        "id": len(annotations) + 1,
                        "image_id": iid,
                        "category_id": obj["category_id"],
                        "bbox": obj["bbox"],
                        "area": obj["bbox"][2] * obj["bbox"][3],
                        "iscrowd": 0,
                        "record_id": obj["record_id"],
                    }
                )
        data = {**coco_base(), "images": images, "annotations": annotations}
        data["info"] = {
            "description": f"Method A {name}: annotation-guided native context crops on padded 1024 canvas"
        }
    write(train / "_annotations.coco.json", data)
    ann_ids = {a["image_id"] for a in data["annotations"]}
    assert len(ann_ids) == len(data["images"])
    records = {a["record_id"] for a in data["annotations"]}
    summary = {
        "status": "verified",
        "experiment": name,
        "train_images": len(data["images"]),
        "train_boxes": len(data["annotations"]),
        "train_known_records": len(records),
        "train_record_ids": sorted(records),
        "validation_images": 1432,
        "validation_known_records": 274,
        "validation_scope": "unchanged complete fixed grid",
        "test_images_loaded": False,
        "source_assignment_sha256": sha(BASE / "inputs/priority_records.csv"),
        "train_coco_sha256": sha(train / "_annotations.coco.json"),
        "valid_coco_sha256": sha(dest / "valid/_annotations.coco.json"),
        "representation": (
            "baseline LoG k5"
            if tiles is None
            else "native LoG k5 context crops, no rescaling, random-offset 1024 canvas padding"
        ),
        "warning": "Incomplete annotations; no unannotated region is certified negative.",
    }
    write(dest / "dataset_summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "train_record_ids"}), flush=True)


def intersection(b, l, t, s):
    x0, y0 = max(b[0], l), max(b[1], t)
    x1, y1 = min(b[2], l + s), min(b[3], t + s)
    return max(0, x1 - x0) * max(0, y1 - y0)


def plan_crops():
    slides = load(ROOT / "audit/train_source_geometry.json")
    audit = load(ROOT / "audit/train_geometry.json")
    if audit["box_max_dimension_percentiles"]["max"] + 64 > 1024:
        raise ValueError("Target needs larger than 1024: review required")
    plans = []
    stats = collections.Counter()
    for slide in slides:
        objects = slide["objects"]
        crops = []
        for anchor in sorted(objects, key=lambda o: (not o["old_grid_covered"], o["record_id"])):
            b = anchor["box_slide"]
            need = max(b[2] - b[0], b[3] - b[1]) + 64
            side = next(s for s in (512, 640, 768, 896, 1024) if need <= s)
            rng = random.Random(f"{SEED}:{anchor['record_id']}")
            # Reuse a prior window only if the whole new anchor has a 16 px margin.
            existing = next(
                (
                    c
                    for c in crops
                    if c["left"] + 16 <= b[0]
                    and c["top"] + 16 <= b[1]
                    and c["left"] + c["side"] - 16 >= b[2]
                    and c["top"] + c["side"] - 16 >= b[3]
                ),
                None,
            )
            if existing:
                existing["anchor_record_ids"].append(anchor["record_id"])
                if anchor["old_grid_covered"]:
                    existing["matched_anchors"].append(anchor["record_id"])
                stats["reused_windows"] += 1
                continue
            lo_x = max(0, math.ceil(b[2] + 32 - side))
            hi_x = min(slide["width"] - side, math.floor(b[0] - 32))
            lo_y = max(0, math.ceil(b[3] + 32 - side))
            hi_y = min(slide["height"] - side, math.floor(b[1] - 32))
            if lo_x > hi_x or lo_y > hi_y:
                raise ValueError("No feasible crop with target margin")
            candidates = []
            for k in range(128):
                l = rng.randint(lo_x, hi_x)
                t = rng.randint(lo_y, hi_y)
                partial = 0
                for o in objects:
                    bb = o["box_slide"]
                    area = intersection(bb, l, t, side)
                    full = (bb[2] - bb[0]) * (bb[3] - bb[1])
                    if 0 < area < full - 1e-6:
                        partial += 1
                candidates.append((partial, k, l, t))
            partial, _, left, top = min(candidates)
            px = rng.randint(0, 1024 - side)
            py = rng.randint(0, 1024 - side)
            tile_id = hashlib.sha256(
                f"{slide['source']}:{left}:{top}:{side}:{px}:{py}:log5-sparse-v1".encode()
            ).hexdigest()[:24]
            c = {
                "tile_id": tile_id,
                "source": slide["source"],
                "left": left,
                "top": top,
                "side": side,
                "pad_left": px,
                "pad_top": py,
                "anchor_record_ids": [anchor["record_id"]],
                "matched_anchors": [anchor["record_id"]] if anchor["old_grid_covered"] else [],
                "objects": [],
                "known_partial_boxes": partial,
            }
            for o in objects:
                bb = o["box_slide"]
                if intersection(bb, left, top, side) <= 0:
                    continue
                x0 = max(bb[0], left) - left + px
                y0 = max(bb[1], top) - top + py
                x1 = min(bb[2], left + side) - left + px
                y1 = min(bb[3], top + side) - top + py
                c["objects"].append(
                    {
                        **o,
                        "bbox": [x0, y0, x1 - x0, y1 - y0],
                        "visible_fraction": intersection(bb, left, top, side)
                        / ((bb[2] - bb[0]) * (bb[3] - bb[1])),
                    }
                )
            crops.append(c)
            stats[f"side_{side}"] += 1
            stats["known_partial_boxes"] += partial
        plans.append({**slide, "crops": crops})
        write(ROOT / "plan" / f"{slide['index']:02d}.json", plans[-1])
    all_crops = [c for p in plans for c in p["crops"]]
    matched = [c for c in all_crops if c["matched_anchors"]]
    assert len({r for c in all_crops for r in c["anchor_record_ids"]}) == 1605
    assert len({r for c in matched for r in c["matched_anchors"]}) == 1061
    report = {
        "status": "planned",
        "train_source_files": 47,
        "all_crop_windows": len(all_crops),
        "matched_crop_windows": len(matched),
        "train_anchor_records": 1605,
        "matched_anchor_records": 1061,
        "matched_label_records": len({o["record_id"] for c in matched for o in c["objects"]}),
        "all_label_records": len({o["record_id"] for c in all_crops for o in c["objects"]}),
        "stats": dict(stats),
        "canvas_side": 1024,
        "padding": "uniform RGB median of crop edge pixels, no real object copied into padding",
        "scale": "native pixels preserved; no crop resizing",
        "partial_known_objects": "avoid boundaries by 128 candidate search; every remaining intersecting YES box is retained clipped",
        "warning": "Matched-anchor crops may incidentally supervise additional known train targets; counts reported explicitly. Padding introduces a train/inference appearance difference. Unknown interior pollen remain incompletely annotated.",
    }
    write(ROOT / "plan_summary.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["m1", "plan", "finalize"])
    a = p.parse_args()
    if a.stage == "m1":
        make_dataset("m1_positive_grid")
    elif a.stage == "plan":
        plan_crops()
    else:
        plans = [load(p) for p in sorted((ROOT / "plan").glob("*.json"))]
        all_tiles = [c for p in plans for c in p["crops"]]
        for n, tiles in [
            ("m2_retile_matched", [c for c in all_tiles if c["matched_anchors"]]),
            ("m2_retile_all", all_tiles),
        ]:
            make_dataset(n, tiles)
        write(
            ROOT / "build_status.json",
            {"status": "verified", "datasets": list(EXPERIMENTS), "test_used": False},
        )

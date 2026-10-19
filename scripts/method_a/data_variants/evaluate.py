"""Known-reference validation on the unchanged 1,432-image grid; predictions unreviewed."""

import argparse, collections, time, gzip, json
import numpy as np
from PIL import Image
from common import BASE, EXPERIMENTS, RESULTS, ROOT, load, resolve_variant, sha, write
from spring_nms import deduplicate
from spring_types import Detection, TileSpec


def summarize(raw, plans, categories, threshold, positive_only):
    import torch
    from torchvision.ops import box_iou

    grouped = collections.defaultdict(list)
    for p in plans:
        for tile in p["tiles"]:
            if not positive_only or tile["objects"]:
                grouped[p["source_image"]].append(tile)
    predictions = []
    matches = []
    for source, tiles in sorted(grouped.items()):
        truth = {}
        by_tile = {}
        origin = {}
        for tile in tiles:
            for label in tile["objects"]:
                truth[label["record_id"]] = {
                    "box": label["box_slide"],
                    "category": label["broad_category"],
                }
            spec = TileSpec(tile["left"], tile["top"], 1024, 1024, tile["left"], tile["top"])
            by_tile[spec] = []
            for pred in raw[tile["tile_id"]]:
                if pred["score"] < threshold:
                    continue
                b = pred["box"]
                bb = [
                    b[0] + tile["left"],
                    b[1] + tile["top"],
                    b[2] + tile["left"],
                    b[3] + tile["top"],
                ]
                det = Detection(*bb, pred["score"], 0.0, 0.0, 0.0, 0.0)
                by_tile[spec].append(det)
                origin[id(det)] = {
                    "box_slide": bb,
                    "score": pred["score"],
                    "source": source,
                    "category": categories[str(pred["class_id"])],
                    "tile_id": tile["tile_id"],
                }
        candidates = [origin[id(d)] for d in deduplicate(by_tile, 0.5)]
        ids = list(truth)
        assigned = {}
        used_c = set()
        used_t = set()
        if candidates and ids:
            overlaps = box_iou(
                torch.tensor([c["box_slide"] for c in candidates]),
                torch.tensor([truth[r]["box"] for r in ids]),
            )
            pairs = [
                (float(overlaps[i, j]), i, j) for i, j in torch.nonzero(overlaps >= 0.5).tolist()
            ]
            for iou, i, j in sorted(pairs, reverse=True):
                if i not in used_c and j not in used_t:
                    assigned[j] = (i, iou)
                    used_c.add(i)
                    used_t.add(j)
        for j, rid in enumerate(ids):
            pred = candidates[assigned[j][0]] if j in assigned else None
            matches.append(
                {
                    "record_id": rid,
                    "source": source,
                    "true_category": truth[rid]["category"],
                    "detected": pred is not None,
                    "predicted_category": pred["category"] if pred else None,
                    "category_correct": pred is not None
                    and pred["category"] == truth[rid]["category"],
                    "iou": assigned[j][1] if pred else None,
                }
            )
        for i, c in enumerate(candidates):
            c["matched_known_reference"] = i in used_c
        predictions.extend(candidates)
    assert len(matches) == 274 and len({m["record_id"] for m in matches}) == 274
    found = sum(m["detected"] for m in matches)
    correct = sum(m["category_correct"] for m in matches)
    per_class = []
    for cls in sorted(set(m["true_category"] for m in matches)):
        ms = [m for m in matches if m["true_category"] == cls]
        n = len(ms)
        d = sum(m["detected"] for m in ms)
        c = sum(m["category_correct"] for m in ms)
        per_class.append(
            {
                "category": cls,
                "support": n,
                "slide_file_support": len({m["source"] for m in ms}),
                "detected": d,
                "correct": c,
                "recall": d / n,
                "end_to_end_success": c / n,
            }
        )
    summary = {
        "scope": (
            "positive-tile diagnostic"
            if positive_only
            else "unchanged complete fixed-grid validation"
        ),
        "validation_tiles": sum(map(len, grouped.values())),
        "known_specimens": 274,
        "detected": found,
        "end_to_end_correct": correct,
        "known_specimen_recall_iou50": found / 274,
        "classification_accuracy_on_matched": correct / found if found else None,
        "end_to_end_known_specimen_success": correct / 274,
        "macro_known_recall": sum(c["recall"] for c in per_class) / len(per_class),
        "macro_end_to_end_success": sum(c["end_to_end_success"] for c in per_class)
        / len(per_class),
        "predictions_after_deduplication": len(predictions),
        "unmatched_prediction_count": len(predictions) - found,
        "unmatched_prediction_interpretation": "Unreviewed, not established false positives. Precision and full-scene AP are not claimed.",
        "confidence_threshold": threshold,
        "match_iou": 0.5,
        "per_class": per_class,
        "test_used": False,
    }
    return summary, matches, predictions


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--variant",
        "--experiment",
        dest="experiment",
        type=resolve_variant,
        choices=EXPERIMENTS,
        required=True,
        metavar="A1|A2|A3",
    )
    p.add_argument("--smoke", action="store_true")
    a = p.parse_args()
    import torch
    from rfdetr_plus.models.detection import RFDETR2XLarge

    assert torch.cuda.is_available()
    kind = "smoke" if a.smoke else "training"
    run = ROOT / "run_artifacts" / a.experiment / kind
    status = load(run / "status.json")
    checkpoint = run / "checkpoint_final_ema.pth"
    assert status["status"] == "completed" and sha(checkpoint) == status["checkpoint_sha256"]
    out = RESULTS / a.experiment / ("smoke_validation" if a.smoke else "validation")
    out.mkdir(parents=True, exist_ok=False)
    model = RFDETR2XLarge(pretrain_weights=str(checkpoint), num_classes=28, resolution=1000)
    plans = [load(p) for p in sorted((BASE / "plan").glob("*.json")) if load(p)["split"] == "valid"]
    cats = load(BASE / "inputs/broad_category_map.json")
    tiles = [t for p in plans for t in p["tiles"]]
    assert len(tiles) == 1432
    if a.smoke:
        tiles = [t for t in tiles if t["objects"]][:2]
    raw = {}
    invalid_outputs = []
    started = time.time()
    hashes = load(BASE / "dataset/source_image_hashes.json")
    for index, tile in enumerate(tiles):
        path = BASE / "dataset/valid" / f"{tile['tile_id']}.png"
        assert path.is_symlink() and sha(path) == hashes[tile["tile_id"]]
        with Image.open(path) as im:
            assert im.size == (1024, 1024) and im.mode == "RGB"
            ds = model.predict(im.convert("RGB"), threshold=0.25)
        raw[tile["tile_id"]] = []
        for b, score, cid in zip(ds.xyxy, ds.confidence, ds.class_id):
            cid = int(cid)
            if cid == 28:
                # The installed builder creates args.num_classes + 1 sigmoid output slots.
                # Roboflow COCO remapping supervises IDs 0..27; slot 28 has no target class.
                invalid_outputs.append(
                    {
                        "tile_id": tile["tile_id"],
                        "class_id": cid,
                        "score": float(score),
                        "box": list(map(float, b)),
                    }
                )
                continue
            if not 0 <= cid < 28:
                raise ValueError(f"Unexpected output class ID: {cid}")
            raw[tile["tile_id"]].append(
                {"box": list(map(float, b)), "score": float(score), "class_id": cid}
            )
        if index % 100 == 0:
            print(
                json.dumps({"validation_images_done": index + 1, "total": len(tiles)}), flush=True
            )
    write(
        out / "unused_output_slot_audit.json",
        {
            "unused_slot": 28,
            "target_ids": list(range(28)),
            "excluded_predictions": invalid_outputs,
            "count": len(invalid_outputs),
            "reason": "Installed model has 29 sigmoid channels but training labels remap to only IDs 0..27. Slot 28 is unassigned, not a biological class; never remapped to a target class.",
        },
    )
    with gzip.open(out / "raw_predictions.json.gz", "xt", compresslevel=6) as f:
        json.dump(raw, f)
    if a.smoke:
        write(
            out / "summary.json",
            {
                "status": "completed",
                "images": len(tiles),
                "checkpoint_sha256": status["checkpoint_sha256"],
                "elapsed_seconds": time.time() - started,
                "test_used": False,
            },
        )
        return
    summaries = []
    for threshold in (0.25, 0.5, 0.75):
        for pos in (False, True):
            summary, matches, preds = summarize(raw, plans, cats, threshold, pos)
            summary.update(
                status="completed",
                checkpoint_sha256=status["checkpoint_sha256"],
                experiment=a.experiment,
                unused_output_slot_excluded=28,
                unused_output_predictions_excluded=sum(
                    d["score"] >= threshold for d in invalid_outputs
                ),
            )
            tag = f"{'positive' if pos else 'full'}_confidence_{threshold:.2f}"
            write(out / f"{tag}_summary.json", summary)
            write(out / f"{tag}_matches.json", matches)
            if threshold == 0.5 and not pos:
                with gzip.open(out / "predictions.json.gz", "xt", compresslevel=6) as f:
                    json.dump(preds, f)
                write(out / "summary.json", summary)
            summaries.append(summary)
    write(out / "all_summaries.json", summaries)
    write(
        out / "status.json",
        {
            "status": "completed",
            "elapsed_seconds": time.time() - started,
            "images": 1432,
            "test_used": False,
        },
    )
    print(
        json.dumps(
            [
                {
                    "scope": s["scope"],
                    "threshold": s["confidence_threshold"],
                    "detected": s["detected"],
                    "correct": s["end_to_end_correct"],
                }
                for s in summaries
            ],
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

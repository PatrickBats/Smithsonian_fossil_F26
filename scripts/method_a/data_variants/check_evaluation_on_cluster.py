"""Regression: known-reference matching, overlap dedup, sparse unmatched predictions and subset scope."""

from evaluate import summarize
from common import ROOT, write


def main():
    cats = {"0": "A", "1": "B"}
    tiles = []
    raw = {}
    for index in range(274):
        left = index * 2048
        box = [700, 100, 800, 200] if index == 0 else [100, 100, 200, 200]
        tiles.append(
            {
                "tile_id": str(index),
                "left": left,
                "top": 0,
                "objects": [
                    {
                        "record_id": str(index),
                        "box_slide": [box[0] + left, box[1], box[2] + left, box[3]],
                        "broad_category": cats[str(index % 2)],
                    }
                ],
            }
        )
        raw[str(index)] = [{"box": box, "score": 0.8, "class_id": index % 2}]
    # The same known target in an overlapping tile must count only once.
    tiles.append({"tile_id": "duplicate", "left": 512, "top": 0, "objects": tiles[0]["objects"]})
    raw["duplicate"] = [{"box": [188, 100, 288, 200], "score": 0.85, "class_id": 0}]
    # A prediction in an annotation-empty tile remains unreviewed.
    tiles.append({"tile_id": "unknown", "left": 274 * 2048, "top": 0, "objects": []})
    raw["unknown"] = [{"box": [100, 100, 200, 200], "score": 0.95, "class_id": 0}]
    plans = [{"source_image": "synthetic", "tiles": tiles}]
    s, _, _ = summarize(raw, plans, cats, 0.5, False)
    assert (
        s["detected"] == 274
        and s["end_to_end_correct"] == 274
        and s["unmatched_prediction_count"] == 1
    )
    p, _, _ = summarize(raw, plans, cats, 0.5, True)
    assert (
        p["detected"] == 274
        and p["end_to_end_correct"] == 274
        and p["unmatched_prediction_count"] == 0
    )
    raw["1"][0]["class_id"] = 0
    s, _, _ = summarize(raw, plans, cats, 0.5, False)
    assert s["detected"] == 274 and s["end_to_end_correct"] == 273
    s, _, _ = summarize(raw, plans, cats, 0.9, False)
    assert (
        s["detected"] == 0
        and s["unmatched_prediction_count"] == 1
        and s["classification_accuracy_on_matched"] is None
    )
    write(
        ROOT / "audit/evaluation_regression.json",
        {
            "status": "passed",
            "checks": [
                "274 known matches",
                "overlapping tile deduplication",
                "unreviewed prediction count",
                "positive-tile subset",
                "classification error with correct location",
                "threshold filtering and empty matches",
            ],
        },
    )
    print("Evaluation regression passed", flush=True)


if __name__ == "__main__":
    main()

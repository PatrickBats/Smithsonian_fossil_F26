"""Publish a compact comparison only after all evaluations and input-integrity checks pass."""

import json
from pathlib import Path
from common import EXPERIMENTS, RESULTS, ROOT, load, sha, variant_id, write
from focus_helpers import crc32_file

rows = []
for name in EXPERIMENTS:
    ds = load(ROOT / "datasets" / name / "dataset_summary.json")
    st = load(ROOT / "run_artifacts" / name / "training/status.json")
    vs = load(RESULTS / name / "validation/status.json")
    ev = load(RESULTS / name / "validation/summary.json")
    assert st["status"] == vs["status"] == "completed" and st["optimizer_steps"] == 2400
    assert (
        sha(ROOT / "run_artifacts" / name / "training/checkpoint_final_ema.pth")
        == st["checkpoint_sha256"]
        == ev["checkpoint_sha256"]
    )
    rows.append(
        {
            "method": "A",
            "variant": variant_id(name),
            "experiment": name,
            "training_tiles": ds["train_images"],
            "training_known_records": ds["train_known_records"],
            "optimizer_steps": st["optimizer_steps"],
            "detected": ev["detected"],
            "end_to_end_correct": ev["end_to_end_correct"],
            "known_recall": ev["known_specimen_recall_iou50"],
            "end_to_end_success": ev["end_to_end_known_specimen_success"],
            "unmatched_predictions": ev["unmatched_prediction_count"],
            "checkpoint_sha256": st["checkpoint_sha256"],
        }
    )
# Confirm training sources and protected annotations retain their original stat/CRC.
for slide in load(ROOT / "audit/train_source_geometry.json"):
    stat = Path(slide["source"]).stat()
    assert [stat.st_size, stat.st_mtime_ns, stat.st_ino] == slide["source_stat"]
    assert crc32_file(Path(slide["annotation"])) == slide["annotation_crc32"]
checked = set()
for name in EXPERIMENTS:
    snap = load(ROOT / "audit" / f"external_inputs_before_{name}.json")
    for image in snap["used_images"]:
        p = Path(image["path"])
        st = p.stat()
        assert (st.st_uid, st.st_size, st.st_mtime_ns, st.st_ino) == (
            image["uid"],
            image["size"],
            image["mtime_ns"],
            image["inode"],
        )
        checked.add(str(p))
    for item in snap["external_files"]:
        p = Path(item["path"])
        assert sha(p) == item["sha256"] and p.stat().st_uid == item["uid"]
write(
    ROOT / "audit/external_inputs_after.json",
    {
        "status": "verified",
        "source_image_files": 47,
        "baseline_image_metadata_checked": len(checked),
        "annotations_crc32_unchanged": True,
        "external_label_and_pretrained_hashes_unchanged": True,
        "test_used": False,
    },
)
result = {
    "method": "A",
    "status": "completed",
    "validation_known_references": 274,
    "validation_tiles": 1432,
    "primary_confidence": 0.5,
    "experiments": rows,
    "baseline": {
        "training_tiles": 5152,
        "detected": 24,
        "end_to_end_correct": 20,
        "known_recall": 24 / 274,
        "end_to_end_success": 20 / 274,
        "warning": "Historical baseline differs in schedule, augmentation and checkpoint selection; comparisons are not a pure tile-selection ablation.",
    },
    "limits": [
        "Sparse annotations: full-scene precision/AP and total pollen recall are unknown.",
        "Matched-anchor crop dataset includes 2 incidentally supervised previously uncovered records.",
        "Padding changes training image context; all new runs use the same native object scale.",
    ],
    "test_used": False,
}
write(RESULTS / "comparison.json", result)
lines = [
    "# Method A: three training-data variants",
    "",
    "Primary evaluation: the unchanged 1,432-tile validation grid, 274 known references, confidence 0.50 and IoU 0.50. Test unused.",
    "",
    "| Experiment | Train tiles | Known train targets | Detected / 274 | Correct end-to-end / 274 |",
    "|---|---:|---:|---:|---:|",
]
for r in rows:
    lines.append(
        f"| Method A–{r['variant']} ({r['experiment']}) | {r['training_tiles']} | {r['training_known_records']} | {r['detected']} | {r['end_to_end_correct']} |"
    )
lines += [
    "",
    "Historical baseline: detected 24/274 and correct end-to-end 20/274. It used different training duration, augmentation and AP-based model selection; this is not a clean causal baseline.",
    "",
    "Unmatched predictions are unreviewed. No full-scene precision or AP is claimed. All three new runs share a fixed 2,400-step budget and final EMA selection. See comparison.json and each experiment directory for threshold and per-class diagnostics.",
]
p = RESULTS / "COMPARISON.md"
with p.open("x") as f:
    f.write("\n".join(lines) + "\n")
print(json.dumps(result, indent=2), flush=True)

"""Frozen specimen/crop provenance and pipeline configuration validation."""
import collections
import hashlib
import io
import json
import math
from pathlib import Path
from PIL import Image
from method_b.utils.file_io import digest, read_csv, rows, sha

EXPECTED_SPLIT_SHA = "da2062a127cf6e14945e50fff097e0db102d7f8203250b47daed6b6bb166478d"

def verify_inputs(root, assignments, category_map):
    """Validate frozen split, crop bytes, geometry, label order and source isolation.

    Args:
        root: Root directory containing the prepared crop dataset.
        assignments: CSV path containing the frozen specimen split assignments.
        category_map: CSV path containing the ordered 32-category vocabulary.

    Returns:
        tuple: Verified crop records, ordered labels, and integrity audit.
    """
    if digest(assignments) != EXPECTED_SPLIT_SHA:
        raise ValueError("Split differs from the adopted assignment")
    source = read_csv(assignments)
    crops = read_csv(root / "crop_manifest.csv")
    classes = read_csv(category_map)
    if [int(c["classifier_class_id"]) for c in classes] != list(range(32)):
        raise ValueError("Expected 32 ordered class IDs")
    labels = [c["sponsor_category"] for c in classes]
    if len(set(labels)) != 32 or any(c["priority"] != "YES" for c in classes):
        raise ValueError("Invalid class vocabulary")
    by_id = {r["record_id"]: r for r in source}
    if len(source) != 2283 or len(by_id) != 2283 or len(crops) != 2283:
        raise ValueError("Unexpected record count")
    if len({r["record_id"] for r in crops}) != 2283 or {r["record_id"] for r in crops} != set(
        by_id
    ):
        raise ValueError("Missing/duplicated crop IDs")
    groups = collections.defaultdict(set)
    images = collections.defaultdict(set)
    for row in crops:
        for key, value in by_id[row["record_id"]].items():
            if row.get(key) != value:
                raise ValueError(f"Crop source field changed: {key}")
        if row["sponsor_category"] not in labels or int(row["source_level"]) != 0:
            raise ValueError("Unknown category or source level")
        groups[row["accession_group_id"]].add(row["split"])
        images[row["image_nots_path"]].add(row["split"])
        expected = (
            row["split"] + "/" + hashlib.sha256(row["record_id"].encode()).hexdigest() + ".png"
        )
        if row["image_relpath"] != expected:
            raise ValueError("Unexpected crop path")
        path = root / expected
        if path.is_symlink():
            raise ValueError("Symlinked crop")
        data = path.read_bytes()
        if (
            len(data) != int(row["png_bytes"])
            or hashlib.sha256(data).hexdigest() != row["png_sha256"]
        ):
            raise ValueError("Crop bytes do not match export manifest")
        with Image.open(io.BytesIO(data)) as image:
            side = int(row["crop_side_px"])
            if image.format != "PNG" or image.mode != "RGB" or image.size != (side, side):
                raise ValueError("Invalid crop format")
            image.verify()
        # Circle must remain wholly inside the exported image.
        for axis, origin in [("x", "left"), ("y", "top")]:
            center = float(row[f"center_{axis}_px"]) - float(row[f"crop_{origin}_px"])
            radius = float(row[f"radius_{axis}_px"])
            if not radius > 0 or center - radius < -1e-6 or center + radius > side + 1e-6:
                raise ValueError("Circle clipped by crop")
    counts = dict(collections.Counter(r["split"] for r in crops))
    if counts != {"train": 1605, "val": 347, "test": 331}:
        raise ValueError("Wrong partition counts")
    if len(groups) != 57 or any(len(s) != 1 for s in list(groups.values()) + list(images.values())):
        raise ValueError("Source leakage across partitions")
    representation = verify_representation(root, crops)
    return (
        crops,
        labels,
        {
            "representation": representation,
            "verified_records": len(crops),
            "split_counts": counts,
            "groups": len(groups),
            "split_sha256": digest(assignments),
            "crop_manifest_sha256": digest(root / "crop_manifest.csv"),
            "category_map_sha256": digest(category_map),
            "test_inference": False,
        },
    )


def verify_representation(root, crops):
    """Validate zero-plane or Tenengrad crop provenance against frozen exports.

    Args:
        root: Root directory containing the prepared crop dataset.
        crops: Verified crop manifest records.

    Returns:
        dict: Accepted representation metadata; invalid provenance raises ValueError.
    """
    baseline_sha = "b4d803ca764f9941de38014bc5a67eb797f400a595033118c32512f5701e1373"
    if digest(root / "crop_manifest.csv") == baseline_sha:
        return {"name": "baseline_zero_plane", "crop_manifest_sha256": baseline_sha}
    metadata = json.loads((root / "representation.json").read_text())
    if (
        metadata["representation"] != "crop_wide_tenengrad_best_plane"
        or metadata["baseline_manifest_sha256"] != baseline_sha
    ):
        raise ValueError("Unrecognized image representation")
    if metadata["crop_manifest_sha256"] != digest(root / "crop_manifest.csv") or metadata[
        "focus_scores_sha256"
    ] != digest(root / "focus_scores.json"):
        raise ValueError("Focus provenance fingerprint mismatch")
    if (
        metadata["binding_sha256"] != digest(root.parent / "binding.json")
        or metadata["test_inference"] is not False
    ):
        raise ValueError("Invalid focus run binding")
    baseline_path = root.parent / "baseline_crop_manifest.csv"
    if digest(baseline_path) != baseline_sha:
        raise ValueError("Focus baseline changed")
    baseline = read_csv(baseline_path)
    scores = json.loads((root / "focus_scores.json").read_text())["records"]
    if len(scores) != len(crops) or [r["record_id"] for r in baseline] != [
        r["record_id"] for r in crops
    ]:
        raise ValueError("Focus records or order differ")
    if [r["record_id"] for r in scores] != [r["record_id"] for r in crops]:
        raise ValueError("Score order differs")
    mutable = {"png_bytes", "png_sha256", "rgb_channel_std_mean"}
    for row, old, score in zip(crops, baseline, scores):
        if any(row.get(k) != v for k, v in old.items() if k not in mutable):
            raise ValueError("Focus crop geometry/source changed")
        if (
            row["baseline_png_sha256"] != old["png_sha256"]
            or score["zero_plane_matches_baseline"] is not True
        ):
            raise ValueError("Zero-plane reference mismatch")
        planes = score["planes"]
        if not planes or any(
            not math.isfinite(p["tenengrad"]) or p["tenengrad"] < 0 for p in planes
        ):
            raise ValueError("Invalid focus score")
        best = max(planes, key=lambda p: (p["tenengrad"], -abs(p["z_offset"]), -p["index"]))
        if (
            int(row["selected_plane_index"]) != best["index"]
            or int(row["selected_z_offset"]) != best["z_offset"]
        ):
            raise ValueError("Selected plane is not the fixed-method maximum")
        if score["selected_sha256"] != row["png_sha256"] or score["selected_bytes"] != int(
            row["png_bytes"]
        ):
            raise ValueError("Selected image mismatch")
    return metadata


def validate_inputs(config):
    """Verify the configured frozen split, category map and Swin checkpoint.

    Args:
        config: Path to the pipeline JSON configuration.

    Returns:
        tuple: Configuration, assignment records and fine-to-broad mapping.
    """
    c = json.loads(Path(config).read_text())
    if c.get("test_inference") is not False:
        raise ValueError("This pipeline is restricted to train/validation")
    r = rows(c["assignments"])
    cats = rows(c["fine_to_broad"])
    assert len(r) == 2283 and len({x["record_id"] for x in r}) == 2283
    assert sha(c["assignments"]) == c["assignments_sha256"]
    assert sha(c["fine_to_broad"]) == c["fine_to_broad_sha256"]
    assert len(cats) == 32 and len({x["broad_category"] for x in cats}) == 28
    mapping = {x["fine_category"]: x["broad_category"] for x in cats}
    group = {}
    slide = {}
    for x in r:
        assert x["sponsor_classify"] == "YES" and x["sponsor_category"] in mapping
        assert x["split"] in ("train", "val", "test")
        group.setdefault(x["accession_group_id"], set()).add(x["split"])
        slide.setdefault(x["image_nots_path"], set()).add(x["split"])
    assert all(len(v) == 1 for v in group.values()) and all(len(v) == 1 for v in slide.values())
    assert sha(c["swin_checkpoint"]) == c["swin_checkpoint_sha256"]
    return c, r, mapping

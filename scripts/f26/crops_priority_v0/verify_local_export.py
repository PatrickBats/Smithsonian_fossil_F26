"""Independently verify the completed local F26 image split."""

import collections
import csv
import hashlib
import io
import json
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE / "local_images"
INPUT = HERE / "inputs" / "record_assignments.csv"
EXPECTED_COUNTS = {"train": 1605, "val": 347, "test": 331}


def main():
    with INPUT.open(newline="", encoding="utf-8") as file:
        source = {r["record_id"]: r for r in csv.DictReader(file)}
    with (ROOT / "crop_manifest.csv").open(newline="", encoding="utf-8") as file:
        crops = list(csv.DictReader(file))
    summary = json.loads((ROOT / "export_summary.json").read_text(encoding="utf-8"))
    if len(source) != 2283 or len(crops) != 2283:
        raise ValueError("Incorrect record count")
    if {r["record_id"] for r in crops} != set(source):
        raise ValueError("Image manifest does not match the split assignment")
    if collections.Counter(r["split"] for r in crops) != EXPECTED_COUNTS:
        raise ValueError("Incorrect partition counts")
    if summary["source_split_manifest_sha256"] != hashlib.sha256(INPUT.read_bytes()).hexdigest():
        raise ValueError("Wrong source split manifest checksum")
    if summary["crop_count"] != 2283 or summary["split_counts"] != EXPECTED_COUNTS:
        raise ValueError("Incorrect export summary")
    expected_paths = set()
    byte_count = 0
    for crop in crops:
        record = source[crop["record_id"]]
        for field in ("split", "sponsor_category", "image_nots_path", "annotation_nots_path"):
            if crop[field] != record[field]:
                raise ValueError(f"Provenance mismatch: {crop['record_id']} {field}")
        name = hashlib.sha256(crop["record_id"].encode()).hexdigest() + ".png"
        relative = Path(crop["image_relpath"])
        if relative.parts != (crop["split"], name):
            raise ValueError("Wrong image path")
        expected_paths.add(relative)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing or symlinked image: {relative}")
        data = path.read_bytes()
        if len(data) != int(crop["png_bytes"]):
            raise ValueError(f"Wrong image byte count: {relative}")
        if hashlib.sha256(data).hexdigest() != crop["png_sha256"]:
            raise ValueError(f"Wrong image checksum: {relative}")
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            side = int(crop["crop_side_px"])
            if image.format != "PNG" or image.mode != "RGB" or image.size != (side, side):
                raise ValueError(f"Invalid PNG: {relative}")
        byte_count += len(data)
    actual_paths = {path.relative_to(ROOT) for split in EXPECTED_COUNTS for path in (ROOT / split).glob("*.png")}
    if actual_paths != expected_paths:
        raise ValueError("Image file inventory differs from manifest")
    if byte_count != summary["verified_png_bytes"]:
        raise ValueError("Verified PNG byte total differs from summary")
    print(json.dumps({"verified_crops": len(crops), "split_counts": EXPECTED_COUNTS,
                      "verified_png_bytes": byte_count}, indent=2))


if __name__ == "__main__":
    main()

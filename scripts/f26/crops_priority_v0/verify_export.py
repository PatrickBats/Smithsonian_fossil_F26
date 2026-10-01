"""Verify a completed F26 crop export without changing source data."""

import argparse
import collections
import csv
import json
from pathlib import Path

from PIL import Image

from export_crops import (
    EXPECTED_RECORDS, EXPECTED_SPLIT_COUNTS, OUTPUT_ROOT,
    read_manifest, sha256_file,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("pilot", "full"), required=True)
    args = parser.parse_args()
    folder = OUTPUT_ROOT / ("pilot" if args.mode == "pilot" else "images")
    with (folder / "crop_manifest.csv").open(newline="", encoding="utf-8") as file:
        exported = list(csv.DictReader(file))
    summary = json.loads((folder / "export_summary.json").read_text(encoding="utf-8"))
    expected = {r["record_id"]: r for r in read_manifest()}
    if args.mode == "full":
        assert len(exported) == EXPECTED_RECORDS
        assert collections.Counter(r["split"] for r in exported) == EXPECTED_SPLIT_COUNTS
        assert {r["record_id"] for r in exported} == set(expected)
    else:
        assert len(exported) == 9
        assert collections.Counter(r["split"] for r in exported) == {
            "train": 3, "val": 3, "test": 3,
        }
    assert len({r["record_id"] for r in exported}) == len(exported)
    assert len({r["image_relpath"] for r in exported}) == len(exported)
    assert summary["crop_count"] == len(exported)
    assert summary["source_level"] == 0
    verified_bytes = 0
    for row in exported:
        source = expected[row["record_id"]]
        assert row["split"] == source["split"]
        assert row["sponsor_category"] == source["sponsor_category"]
        assert row["image_nots_path"] == source["image_nots_path"]
        relative = Path(row["image_relpath"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert relative.parts[0] == row["split"]
        path = folder / relative
        assert path.is_file() and not path.is_symlink()
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            assert image.format == "PNG"
            assert image.mode == "RGB"
            side = int(row["crop_side_px"])
            assert image.size == (side, side)
        assert path.stat().st_size == int(row["png_bytes"])
        assert sha256_file(path) == row["png_sha256"]
        verified_bytes += path.stat().st_size
    print(json.dumps({
        "mode": args.mode,
        "verified_crops": len(exported),
        "verified_png_bytes": verified_bytes,
        "split_counts": dict(collections.Counter(r["split"] for r in exported)),
    }, indent=2))


if __name__ == "__main__":
    main()

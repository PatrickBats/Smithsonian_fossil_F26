"""Read-only F26 NDPI crop export into a new NOTS experiment-output directory.

Run on NOTS with /projects/dsci435/smithsonian_sp26/conda-env/bin/python -B.
Only the explicit OUTPUT_ROOT tree is writable; source NDPI/NDPA paths are read.
"""

import argparse
import collections
import csv
import hashlib
import json
import math
import os
from pathlib import Path

import openslide
from PIL import Image, ImageDraw, ImageStat


OUTPUT_ROOT = Path("/projects/dsci435/Smithsonian_F26/crops/priority_v0")
SPLIT_MANIFEST = OUTPUT_ROOT / "inputs" / "record_assignments.csv"
SOURCE_LEVEL = 0
CONTEXT_FACTOR = 1.35
MIN_SIDE_PX = 256
SIDE_MULTIPLE = 16
EXPECTED_RECORDS = 2283
EXPECTED_SPLIT_COUNTS = {"train": 1605, "val": 347, "test": 331}


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_manifest():
    with SPLIT_MANIFEST.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if len(rows) != EXPECTED_RECORDS:
        raise ValueError("Unexpected split-manifest record count")
    if collections.Counter(r["split"] for r in rows) != EXPECTED_SPLIT_COUNTS:
        raise ValueError("Unexpected split-manifest partition counts")
    if len({r["record_id"] for r in rows}) != EXPECTED_RECORDS:
        raise ValueError("Duplicate record IDs in split manifest")
    return rows


def geometry(slide, record):
    props = slide.properties
    xnm_per_px = float(props["openslide.mpp-x"]) * 1000
    ynm_per_px = float(props["openslide.mpp-y"]) * 1000
    xoffset = float(props["hamamatsu.XOffsetFromSlideCentre"])
    yoffset = float(props["hamamatsu.YOffsetFromSlideCentre"])
    width, height = slide.dimensions
    x = width / 2 + (int(record["x_nm"]) - xoffset) / xnm_per_px
    y = height / 2 + (int(record["y_nm"]) - yoffset) / ynm_per_px
    radius_x = int(record["radius_nm"]) / xnm_per_px
    radius_y = int(record["radius_nm"]) / ynm_per_px
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError(f"Circle center outside source image: {record['record_id']}")
    if (x - radius_x < 0 or x + radius_x > width
            or y - radius_y < 0 or y + radius_y > height):
        raise ValueError(f"Circle boundary outside source image: {record['record_id']}")
    requested = 2 * max(radius_x, radius_y) * CONTEXT_FACTOR
    side = max(MIN_SIDE_PX, SIDE_MULTIPLE * math.ceil(requested / SIDE_MULTIPLE))
    if side > width or side > height:
        raise ValueError(f"Crop larger than source image: {record['record_id']}")
    left = min(max(round(x - side / 2), 0), width - side)
    top = min(max(round(y - side / 2), 0), height - side)
    if (x - radius_x < left or x + radius_x > left + side
            or y - radius_y < top or y + radius_y > top + side):
        raise ValueError(f"Circle would be clipped: {record['record_id']}")
    return {
        "center_x_px": x,
        "center_y_px": y,
        "radius_x_px": radius_x,
        "radius_y_px": radius_y,
        "crop_left_px": left,
        "crop_top_px": top,
        "crop_side_px": side,
        "mpp_x_um": xnm_per_px / 1000,
        "mpp_y_um": ynm_per_px / 1000,
        "source_width_px": width,
        "source_height_px": height,
    }


def crop_one(slide, record, output_directory):
    geom = geometry(slide, record)
    name = hashlib.sha256(record["record_id"].encode()).hexdigest() + ".png"
    split = record["split"]
    path = output_directory / split / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        # Resume only our own staged output. A corrupt staged file is an error,
        # never silently overwritten or substituted.
        with Image.open(path) as existing:
            existing.verify()
        with Image.open(path) as existing:
            if existing.size != (geom["crop_side_px"], geom["crop_side_px"]):
                raise ValueError(f"Existing staged crop has wrong size: {path}")
    else:
        side = geom["crop_side_px"]
        rgba = slide.read_region(
            (geom["crop_left_px"], geom["crop_top_px"]),
            SOURCE_LEVEL,
            (side, side),
        )
        white = Image.new("RGBA", (side, side), (255, 255, 255, 255))
        white.alpha_composite(rgba)
        rgb = white.convert("RGB")
        temporary = path.with_suffix(".png.part")
        try:
            with temporary.open("wb") as file:
                rgb.save(file, format="PNG", compress_level=3)
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
    with Image.open(path) as image:
        image.load()
        std = ImageStat.Stat(image).stddev
        grayscale_std = round(sum(std) / 3, 3)
    return {
        **record,
        "image_relpath": str(Path(split) / name),
        "source_level": SOURCE_LEVEL,
        **geom,
        "rgb_channel_std_mean": grayscale_std,
        "png_bytes": path.stat().st_size,
        "png_sha256": sha256_file(path),
    }


def pilot_records(rows):
    selected = []
    for split in ("train", "val", "test"):
        members = sorted(
            (r for r in rows if r["split"] == split),
            key=lambda r: (int(r["radius_nm"]), r["record_id"]),
        )
        for fraction in (0.0, 0.5, 1.0):
            selected.append(members[round((len(members) - 1) * fraction)])
    assert len({r["record_id"] for r in selected}) == 9
    return selected


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def create_pilot_contact_sheet(rows, image_directory, path):
    canvas = Image.new("RGB", (3 * 340, 3 * 372), "white")
    draw = ImageDraw.Draw(canvas)
    for i, record in enumerate(rows):
        x0 = (i % 3) * 340
        y0 = (i // 3) * 372
        with Image.open(image_directory / record["image_relpath"]) as image:
            thumb = image.resize((320, 320), Image.Resampling.LANCZOS)
        canvas.paste(thumb, (x0 + 10, y0 + 35))
        scale = 320 / record["crop_side_px"]
        cx = x0 + 10 + (record["center_x_px"] - record["crop_left_px"]) * scale
        cy = y0 + 35 + (record["center_y_px"] - record["crop_top_px"]) * scale
        rx = record["radius_x_px"] * scale
        ry = record["radius_y_px"] * scale
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline="red", width=2)
        draw.text((x0 + 9, y0 + 4), f"{record['split']} · {record['sponsor_category'][:30]}", fill="black")
        draw.text((x0 + 9, y0 + 356), record["record_id"][-42:], fill="black")
    canvas.save(path, format="JPEG", quality=92)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("pilot", "full"), required=True)
    args = parser.parse_args()
    if not OUTPUT_ROOT.is_dir() or OUTPUT_ROOT.is_symlink():
        raise ValueError("Expected new, real output root directory is missing")
    os.umask(0o002)
    rows = read_manifest()
    input_sha = sha256_file(SPLIT_MANIFEST)
    if args.mode == "pilot":
        rows = pilot_records(rows)
        stage = OUTPUT_ROOT / "pilot_staging"
        final = OUTPUT_ROOT / "pilot"
    else:
        stage = OUTPUT_ROOT / "image_staging"
        final = OUTPUT_ROOT / "images"
    if final.exists() or final.is_symlink():
        raise FileExistsError(f"Refusing to overwrite completed output: {final}")
    stage.mkdir(exist_ok=True)
    if stage.is_symlink():
        raise ValueError("Refusing symlinked staging directory")
    staging_config = {
        "mode": args.mode,
        "source_split_manifest_sha256": input_sha,
        "source_level": SOURCE_LEVEL,
        "context_factor": CONTEXT_FACTOR,
        "minimum_side_px": MIN_SIDE_PX,
        "side_multiple_px": SIDE_MULTIPLE,
    }
    staging_config_path = stage / "staging_config.json"
    if staging_config_path.exists():
        if json.loads(staging_config_path.read_text(encoding="utf-8")) != staging_config:
            raise ValueError("Existing staging directory uses different inputs or crop settings")
    else:
        staging_config_path.write_text(
            json.dumps(staging_config, indent=2) + "\n", encoding="utf-8"
        )
    image_stage = stage

    by_source = collections.defaultdict(list)
    for record in rows:
        by_source[record["image_nots_path"]].append(record)
    output = []
    for index, (source, source_records) in enumerate(sorted(by_source.items()), 1):
        print(f"source {index}/{len(by_source)}: {Path(source).name} ({len(source_records)} records)", flush=True)
        before = Path(source).stat()
        slide = openslide.OpenSlide(source)
        try:
            for record in sorted(source_records, key=lambda r: r["record_id"]):
                output.append(crop_one(slide, record, image_stage))
        finally:
            slide.close()
        after = Path(source).stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size, after.st_mtime_ns, after.st_ino
        ):
            raise RuntimeError(f"Source image changed during read: {source}")

    output.sort(key=lambda r: r["record_id"])
    if len(output) != len(rows):
        raise ValueError("Crop count does not match selected records")
    if {r["record_id"] for r in output} != {r["record_id"] for r in rows}:
        raise ValueError("Crop record IDs do not match selected records")
    if len({r["image_relpath"] for r in output}) != len(output):
        raise ValueError("Crop filename collision")
    write_csv(stage / "crop_manifest.csv", output)
    summary = {
        "mode": args.mode,
        "source_split_manifest": str(SPLIT_MANIFEST),
        "source_split_manifest_sha256": input_sha,
        "source_level": SOURCE_LEVEL,
        "context_factor": CONTEXT_FACTOR,
        "minimum_side_px": MIN_SIDE_PX,
        "side_multiple_px": SIDE_MULTIPLE,
        "crop_count": len(output),
        "split_counts": dict(collections.Counter(r["split"] for r in output)),
        "source_image_files": len(by_source),
        "crop_side_min_px": min(r["crop_side_px"] for r in output),
        "crop_side_max_px": max(r["crop_side_px"] for r in output),
        "low_contrast_crops_std_below_2": sum(r["rgb_channel_std_mean"] < 2 for r in output),
    }
    (stage / "export_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    if args.mode == "pilot":
        create_pilot_contact_sheet(output, image_stage, stage / "pilot_contact_sheet.jpg")
    stage.rename(final)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()

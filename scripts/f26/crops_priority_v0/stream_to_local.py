"""Resume-safe local receiver for NOTS read-only crop streams.

Run with local Python/Pillow. Remote work runs through Slurm and streams tar to
this process. Only local_export_staging/local_images in this directory are
written. Nothing is written to NOTS by this script or its remote companion.
"""

import collections
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile

from PIL import Image


HERE = Path(__file__).resolve().parent
INPUT = HERE / "inputs" / "record_assignments.csv"
REMOTE_SCRIPT = HERE / "remote_stream_batch.py"
STAGE = HERE / "local_export_staging"
FINAL = HERE / "local_images"
REMOTE_ROOT = os.environ.get("F26_REMOTE_ROOT")
REMOTE_PYTHON = os.environ.get(
    "F26_REMOTE_PYTHON", "/projects/dsci435/smithsonian_sp26/conda-env/bin/python"
)
EXPECTED_SPLITS = {"train": 1605, "val": 347, "test": 331}
BATCH_SIZE = 8


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_input():
    with INPUT.open(newline="", encoding="utf-8") as file:
        records = list(csv.DictReader(file))
    if len(records) != 2283:
        raise ValueError("Wrong input record count")
    if collections.Counter(row["split"] for row in records) != EXPECTED_SPLITS:
        raise ValueError("Wrong input split counts")
    if len({row["record_id"] for row in records}) != len(records):
        raise ValueError("Duplicate record ID")
    return records


def expected_for_batch(records, sources):
    return {row["record_id"]: row for row in records if row["image_nots_path"] in sources}


def validate_batch_rows(rows, expected):
    if len(rows) != len(expected) or {r["record_id"] for r in rows} != set(expected):
        raise ValueError("Batch manifest does not cover its expected records")
    for row in rows:
        source = expected[row["record_id"]]
        for field in ("split", "sponsor_category", "image_nots_path", "annotation_nots_path"):
            if row[field] != source[field]:
                raise ValueError(f"Batch provenance mismatch: {row['record_id']} {field}")
        filename = sha256(row["record_id"].encode()) + ".png"
        if row["image_relpath"] != str(Path(row["split"]) / filename):
            raise ValueError("Unexpected image path")
        if int(row["source_level"]) != 0:
            raise ValueError("Unexpected image level")


def verify_png(path, row):
    data = path.read_bytes()
    if len(data) != int(row["png_bytes"]) or sha256(data) != row["png_sha256"]:
        raise ValueError(f"PNG checksum mismatch: {path}")
    with Image.open(io.BytesIO(data)) as image:
        image.verify()
    with Image.open(io.BytesIO(data)) as image:
        if image.format != "PNG" or image.mode != "RGB":
            raise ValueError(f"Invalid PNG format: {path}")
        side = int(row["crop_side_px"])
        if image.size != (side, side):
            raise ValueError(f"Invalid PNG size: {path}")


def run_batch(start, end, expected):
    batch_path = STAGE / "batch_manifests" / f"{start:03d}_{end:03d}.csv"
    if batch_path.exists():
        with batch_path.open(newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
        validate_batch_rows(rows, expected)
        for row in rows:
            verify_png(STAGE / row["image_relpath"], row)
        print(f"batch {start}:{end} already verified ({len(rows)} crops)", flush=True)
        return rows

    remote = (
        f"F26_BATCH_START={start} F26_BATCH_END={end} "
        f"F26_CROP_ROOT={shlex.quote(REMOTE_ROOT)} "
        "srun --ntasks=1 --quiet --partition=commons --time=01:00:00 "
        "--cpus-per-task=1 --mem=8G --job-name=f26-crop-stream "
        f"--chdir={shlex.quote(REMOTE_ROOT)} "
        f"{shlex.quote(REMOTE_PYTHON)} -B -"
    )
    host = os.environ.get("F26_SSH_HOST")
    if not host:
        raise ValueError("Set F26_SSH_HOST to your own NOTS login")
    command = ["ssh", "-o", "BatchMode=yes"]
    control_path = os.environ.get("F26_SSH_CONTROL_PATH")
    if control_path:
        command.extend(["-S", control_path])
    command.extend([host, remote])
    script = REMOTE_SCRIPT.read_bytes()
    error_path = STAGE / "batch_manifests" / f"{start:03d}_{end:03d}.stderr.log"
    received = set()
    manifest_bytes = None
    with error_path.open("wb") as error_file:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=error_file)
        process.stdin.write(script)
        process.stdin.close()
        try:
            with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
                for member in archive:
                    if not member.isfile():
                        raise ValueError("Unexpected tar member type")
                    source = archive.extractfile(member)
                    if source is None:
                        raise ValueError("Missing tar member payload")
                    data = source.read()
                    if member.name == "batch_manifest.csv":
                        if manifest_bytes is not None:
                            raise ValueError("Duplicate batch manifest")
                        manifest_bytes = data
                        continue
                    if member.name not in {
                        str(Path(r["split"]) / (sha256(r["record_id"].encode()) + ".png"))
                        for r in expected.values()
                    }:
                        raise ValueError(f"Unexpected tar image path: {member.name}")
                    if member.name in received:
                        raise ValueError("Duplicate tar image")
                    received.add(member.name)
                    destination = STAGE / member.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if destination.exists():
                        if sha256(destination.read_bytes()) != sha256(data):
                            raise ValueError(f"Conflicting partial crop: {destination}")
                    else:
                        temporary = destination.with_suffix(".png.part")
                        try:
                            temporary.write_bytes(data)
                            os.replace(temporary, destination)
                        finally:
                            temporary.unlink(missing_ok=True)
        finally:
            process.stdout.close()
            returncode = process.wait()

    if returncode != 0:
        raise RuntimeError(f"Remote batch {start}:{end} failed; see {error_path}")
    if manifest_bytes is None or len(received) != len(expected):
        raise ValueError("Incomplete tar batch")
    rows = list(csv.DictReader(io.StringIO(manifest_bytes.decode("utf-8"))))
    validate_batch_rows(rows, expected)
    for row in rows:
        verify_png(STAGE / row["image_relpath"], row)
    temporary = batch_path.with_suffix(".csv.part")
    temporary.write_bytes(manifest_bytes)
    os.replace(temporary, batch_path)
    print(f"batch {start}:{end} verified ({len(rows)} crops)", flush=True)
    return rows


def main():
    if not REMOTE_ROOT:
        raise ValueError("Set F26_REMOTE_ROOT to the authorized RHF input root")
    if FINAL.exists() or FINAL.is_symlink():
        raise FileExistsError("Refusing to overwrite completed local export")
    if STAGE.is_symlink():
        raise ValueError("Refusing symlinked stage")
    records = load_input()
    STAGE.mkdir(exist_ok=True)
    (STAGE / "batch_manifests").mkdir(exist_ok=True)
    source_list = sorted({row["image_nots_path"] for row in records})
    if len(source_list) != 75:
        raise ValueError("Wrong source image count")
    all_rows = []
    for start in range(0, len(source_list), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(source_list))
        expected = expected_for_batch(records, set(source_list[start:end]))
        print(f"requesting batch {start}:{end} ({len(expected)} crops)", flush=True)
        all_rows.extend(run_batch(start, end, expected))

    all_rows.sort(key=lambda row: row["record_id"])
    validate_batch_rows(all_rows, {r["record_id"]: r for r in records})
    if collections.Counter(row["split"] for row in all_rows) != EXPECTED_SPLITS:
        raise ValueError("Completed local split counts differ")
    for row in all_rows:
        verify_png(STAGE / row["image_relpath"], row)
    with (STAGE / "crop_manifest.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(all_rows[0]))
        writer.writeheader()
        writer.writerows(all_rows)
    summary = {
        "mode": "local_stream_full",
        "source_split_manifest_sha256": sha256(INPUT.read_bytes()),
        "source_level": 0,
        "crop_count": len(all_rows),
        "split_counts": dict(collections.Counter(row["split"] for row in all_rows)),
        "source_image_files": len(source_list),
        "verified_png_bytes": sum(int(row["png_bytes"]) for row in all_rows),
        "crop_side_min_px": min(int(row["crop_side_px"]) for row in all_rows),
        "crop_side_max_px": max(int(row["crop_side_px"]) for row in all_rows),
        "low_contrast_crops_std_below_2": sum(float(row["rgb_channel_std_mean"]) < 2 for row in all_rows),
    }
    (STAGE / "export_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    STAGE.rename(FINAL)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()

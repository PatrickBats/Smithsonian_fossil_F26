"""Stream three read-only NDPI multifocal object crops as in-memory HDF5.

Run through Slurm with Python -B. Output is a tar stream on stdout; source
NDPI and assignment files are opened read only. No NOTS file is created.
"""

import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile

import h5py
import numpy as np
import tifffile
import zarr


ROOT = Path(os.environ["F26_INPUT_ROOT"])
STEMS = (
    "D1555_RAS_60_2023_04_20_15_40_35",
    "C_418058_W_Nassichuk_R_2025_01_21_14_59_16_Alaska",
    "D5825_L_2024_02_06_10_36_15_Utah",
)


def add(archive, name, data):
    member = tarfile.TarInfo(name)
    member.size = len(data)
    member.mode = 0o644
    member.mtime = 0
    archive.addfile(member, io.BytesIO(data))


def make_stack(record, geometry):
    path = Path(record["image_nots_path"])
    before = path.stat()
    left = int(geometry["crop_left_px"])
    top = int(geometry["crop_top_px"])
    side = int(geometry["crop_side_px"])
    with tifffile.TiffFile(path) as tif:
        series = tif.series[0]
        if series.axes != "ZYXS":
            raise ValueError("Unexpected NDPI series axes")
        z_offsets = [int(page.tags[65424].value) for page in series.pages]
        with series.aszarr() as store:
            array = zarr.open(store, mode="r")
            if isinstance(array, zarr.Group):
                array = array["0"]
            rgb = np.stack([
                np.asarray(array[i, top:top + side, left:left + side, :])
                for i in range(len(z_offsets))
            ])
    if rgb.shape != (len(z_offsets), side, side, 3) or rgb.dtype != np.uint8:
        raise ValueError("Incomplete focal crop")
    with h5py.File("f26_pilot", "w", driver="core", backing_store=False) as h5:
        h5.create_dataset("rgb", data=rgb, chunks=(1, side, side, 3),
                          compression="gzip", compression_opts=3)
        h5.create_dataset("z_offset", data=np.asarray(z_offsets, dtype=np.int64))
        h5.attrs["record_id"] = record["record_id"]
        h5.attrs["sponsor_category"] = record["sponsor_category"]
        h5.attrs["split"] = record["split"]
        h5.attrs["image_nots_path"] = str(path)
        h5.attrs["crop_left_px"] = left
        h5.attrs["crop_top_px"] = top
        h5.attrs["crop_side_px"] = side
        h5.flush()
        payload = h5.id.get_file_image()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
        after.st_size, after.st_mtime_ns, after.st_ino
    ):
        raise RuntimeError("Source image changed during read")
    return payload, z_offsets


def main():
    with (ROOT / "inputs/record_assignments.csv").open(newline="", encoding="utf-8") as file:
        records = list(csv.DictReader(file))
    with (ROOT / "preflight_records.csv").open(newline="", encoding="utf-8") as file:
        geometries = {r["record_id"]: r for r in csv.DictReader(file)}
    output = []
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|", format=tarfile.PAX_FORMAT) as archive:
        for stem in STEMS:
            record = next(r for r in records if Path(r["image_nots_path"]).stem == stem)
            payload, z_offsets = make_stack(record, geometries[record["record_id"]])
            name = hashlib.sha256(record["record_id"].encode()).hexdigest() + ".h5"
            add(archive, name, payload)
            output.append({"slide": stem, "record_id": record["record_id"],
                           "filename": name, "z_offset": z_offsets,
                           "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
            print(f"completed {stem}: {len(z_offsets)} planes", file=sys.stderr, flush=True)
        add(archive, "pilot_manifest.json", (json.dumps(output, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()

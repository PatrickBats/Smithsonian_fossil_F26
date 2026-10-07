"""Read-only random-access focal-plane probe on two source NDPI slides.

Run through Slurm and emit JSON. No output files are created on NOTS.
"""

import csv
import json
import os
from pathlib import Path
import time

import numpy as np
import openslide
import tifffile
import zarr


ROOT = Path(os.environ["F26_INPUT_ROOT"])
STEMS = (
    "D1555_RAS_60_2023_04_20_15_40_35",
    "C_418058_W_Nassichuk_R_2025_01_21_14_59_16_Alaska",
)


def main():
    with (ROOT / "inputs/record_assignments.csv").open(newline="", encoding="utf-8") as file:
        records = list(csv.DictReader(file))
    with (ROOT / "preflight_records.csv").open(newline="", encoding="utf-8") as file:
        geom = {r["record_id"]: r for r in csv.DictReader(file)}
    report = []
    for stem in STEMS:
        record = next(r for r in records if Path(r["image_nots_path"]).stem == stem)
        path = Path(record["image_nots_path"])
        g = geom[record["record_id"]]
        side = 256
        x = round(float(g["center_x_px"]) - side / 2)
        y = round(float(g["center_y_px"]) - side / 2)
        with tifffile.TiffFile(path) as tif:
            series = tif.series[0]
            if series.axes != "ZYXS":
                raise ValueError(f"Unexpected axes for {stem}: {series.axes}")
            z_values = [int(p.tags[65424].value) for p in series.pages]
            indices = sorted({0, len(z_values) // 2, len(z_values) - 1, z_values.index(0)})
            store = series.aszarr()
            try:
                array = zarr.open(store, mode="r")
                if isinstance(array, zarr.Group):
                    array = array["0"]
                samples = []
                for index in indices:
                    start = time.monotonic()
                    pixels = np.asarray(array[index, y:y + side, x:x + side, :])
                    samples.append({"index": index, "z_offset": z_values[index],
                                    "shape": list(pixels.shape), "mean_rgb": pixels.mean(axis=(0, 1)).round(2).tolist(),
                                    "read_seconds": round(time.monotonic() - start, 3),
                                    "_pixels": pixels})
            finally:
                store.close()
        with openslide.OpenSlide(path) as slide:
            rgba = slide.read_region((x, y), 0, (side, side))
            opener = np.asarray(rgba.convert("RGB"))
        for sample in samples:
            difference = np.abs(sample.pop("_pixels").astype(np.int16) - opener.astype(np.int16))
            sample["mean_abs_diff_from_openslide"] = round(float(difference.mean()), 3)
            sample["exact_pixel_fraction"] = round(float(np.mean(np.all(difference == 0, axis=2))), 4)
        report.append({"slide": stem, "source": str(path), "roi": [x, y, side],
                       "z_offsets": z_values, "samples": samples})
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

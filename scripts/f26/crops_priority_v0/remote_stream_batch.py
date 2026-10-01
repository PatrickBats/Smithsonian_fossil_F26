"""Stream one source-image batch as a tar archive; write nothing on NOTS.

This file is sent over SSH on stdin to ``srun ... python -B -``. Its stdout is
the tar stream. All source NDPI files and the split CSV are opened read only.
"""

import collections
import csv
import hashlib
import io
import os
from pathlib import Path
import sys
import tarfile

import openslide
from PIL import Image, ImageStat

from export_crops import SOURCE_LEVEL, geometry, read_manifest


def add_bytes(archive, name, data):
    member = tarfile.TarInfo(name)
    member.size = len(data)
    member.mode = 0o644
    member.mtime = 0
    archive.addfile(member, io.BytesIO(data))


def main():
    start = int(os.environ["F26_BATCH_START"])
    end = int(os.environ["F26_BATCH_END"])
    by_source = collections.defaultdict(list)
    for record in read_manifest():
        by_source[record["image_nots_path"]].append(record)
    sources = sorted(by_source)
    if not (0 <= start < end <= len(sources)):
        raise ValueError("Invalid source batch")

    output = []
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|", format=tarfile.PAX_FORMAT) as archive:
        for source in sources[start:end]:
            before = Path(source).stat()
            slide = openslide.OpenSlide(source)
            try:
                for record in sorted(by_source[source], key=lambda row: row["record_id"]):
                    geom = geometry(slide, record)
                    side = geom["crop_side_px"]
                    rgba = slide.read_region(
                        (geom["crop_left_px"], geom["crop_top_px"]),
                        SOURCE_LEVEL,
                        (side, side),
                    )
                    white = Image.new("RGBA", (side, side), (255, 255, 255, 255))
                    white.alpha_composite(rgba)
                    rgb = white.convert("RGB")
                    payload = io.BytesIO()
                    rgb.save(payload, format="PNG", compress_level=3)
                    data = payload.getvalue()
                    name = hashlib.sha256(record["record_id"].encode()).hexdigest() + ".png"
                    relative = str(Path(record["split"]) / name)
                    add_bytes(archive, relative, data)
                    output.append({
                        **record,
                        "image_relpath": relative,
                        "source_level": SOURCE_LEVEL,
                        **geom,
                        "rgb_channel_std_mean": round(sum(ImageStat.Stat(rgb).stddev) / 3, 3),
                        "png_bytes": len(data),
                        "png_sha256": hashlib.sha256(data).hexdigest(),
                    })
            finally:
                slide.close()
            after = Path(source).stat()
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (
                after.st_size, after.st_mtime_ns, after.st_ino
            ):
                raise RuntimeError(f"Source image changed during read: {source}")

        output.sort(key=lambda row: row["record_id"])
        text = io.StringIO(newline="")
        writer = csv.DictWriter(text, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
        add_bytes(archive, "batch_manifest.csv", text.getvalue().encode("utf-8"))


if __name__ == "__main__":
    main()

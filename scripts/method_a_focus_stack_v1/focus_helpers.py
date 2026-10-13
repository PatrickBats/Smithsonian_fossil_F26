"""Read-only source geometry and file-integrity helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
import zlib

import openslide


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def crc32_file(path: Path) -> str:
    crc = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            crc = zlib.crc32(block, crc)
    return f"{crc & 0xffffffff:08x}"


def geometry(slide: openslide.OpenSlide, record: dict) -> tuple[float, float, float, float]:
    props = slide.properties
    xnm = float(props["openslide.mpp-x"]) * 1000
    ynm = float(props["openslide.mpp-y"]) * 1000
    xoff = float(props["hamamatsu.XOffsetFromSlideCentre"])
    yoff = float(props["hamamatsu.YOffsetFromSlideCentre"])
    width, height = slide.dimensions
    x = width / 2 + (int(record["x_nm"]) - xoff) / xnm
    y = height / 2 + (int(record["y_nm"]) - yoff) / ynm
    rx = int(record["radius_nm"]) / xnm
    ry = int(record["radius_nm"]) / ynm
    return x, y, rx, ry

"""Read-only source geometry and Spring 2026 LoG focal-plane fusion."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import zlib

import cv2
import numpy as np
import openslide
from PIL import Image


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


def fused_tile(planes, expected_side: int, zero_index: int, zero_reference: np.ndarray):
    """Select each RGB pixel from the plane with maximal absolute LoG response.

    This is equivalent to Sp26 postprocess_tiles.focus_stack(k=5):
    GaussianBlur(gray, (5,5), 0), then Laplacian(CV_64F, ksize=5), with
    np.argmax over source plane order. Streaming keeps memory bounded.
    """
    best_response = np.full((expected_side, expected_side), -1.0, dtype=np.float64)
    fused = np.empty((expected_side, expected_side, 3), dtype=np.uint8)
    winning_plane = np.zeros((expected_side, expected_side), dtype=np.uint8)
    scores = []
    for index, pixels in enumerate(planes):
        if pixels.shape != (expected_side, expected_side, 3) or pixels.dtype != np.uint8:
            raise ValueError("Unexpected source focal tile shape or dtype")
        if index == zero_index and not np.array_equal(pixels, zero_reference):
            raise ValueError("Source plane zero differs from OpenSlide")
        gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        response = np.abs(cv2.Laplacian(blurred, cv2.CV_64F, ksize=5))
        scores.append(float(response.mean()))
        better = response > best_response
        fused[better] = pixels[better]
        winning_plane[better] = index
        best_response[better] = response[better]
    return fused, scores, np.bincount(winning_plane.ravel(), minlength=len(scores)).tolist()


def save_png_no_replace(path: Path, rgb: np.ndarray) -> None:
    if path.exists():
        raise FileExistsError(path)
    temporary = path.with_name(f".{path.stem}.{os.getpid()}.tmp")
    try:
        Image.fromarray(rgb, mode="RGB").save(temporary, format="PNG", compress_level=3)
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

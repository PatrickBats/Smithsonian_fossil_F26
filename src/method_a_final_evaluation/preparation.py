"""Combine both deliveries and export source-preserving focal context crops."""

import collections
import csv
import hashlib
import json
import math
import random
from pathlib import Path

from .protocol import digest, partition, read, write_new


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def overlap(box, left, top, side):
    return max(0, min(box[2], left + side) - max(box[0], left)) * max(
        0, min(box[3], top + side) - max(box[1], top)
    )


def plan_crops(plan, seed):
    """Retain the preceding native-pixel A3 context and LoG preparation rule.

    Every source record remains an anchor. Adjacent windows may repeat its box;
    evaluation later merges predictions and scores source records once.
    """
    objects, width, height = plan["objects"], plan["width"], plan["height"]
    crops = []
    for anchor in sorted(objects, key=lambda o: o["record_id"]):
        box = anchor["box_slide"]
        side = next(
            (
                s
                for s in (512, 640, 768, 896, 1024)
                if max(box[2] - box[0], box[3] - box[1]) + 64 <= s
            ),
            None,
        )
        if side is None:
            raise ValueError(
                f"Target exceeds available context sizes: {anchor['record_id']}"
            )
        existing = next(
            (
                c
                for c in crops
                if c["left"] + 16 <= box[0]
                and c["top"] + 16 <= box[1]
                and c["left"] + c["side"] - 16 >= box[2]
                and c["top"] + c["side"] - 16 >= box[3]
            ),
            None,
        )
        if existing:
            existing["anchor_record_ids"].append(anchor["record_id"])
            continue
        lx, hx = max(0, math.ceil(box[2] + 32 - side)), min(
            width - side, math.floor(box[0] - 32)
        )
        ly, hy = max(0, math.ceil(box[3] + 32 - side)), min(
            height - side, math.floor(box[1] - 32)
        )
        if lx > hx or ly > hy:
            raise ValueError(
                f"Target too close to image boundary: {anchor['record_id']}"
            )
        rng = random.Random(f"{seed}:{anchor['record_id']}")
        candidates = []
        for attempt in range(128):
            left, top = rng.randint(lx, hx), rng.randint(ly, hy)
            partial = sum(
                0
                < overlap(o["box_slide"], left, top, side)
                < (o["box_slide"][2] - o["box_slide"][0])
                * (o["box_slide"][3] - o["box_slide"][1])
                - 1e-6
                for o in objects
            )
            candidates.append((partial, attempt, left, top))
        partial, _, left, top = min(candidates)
        px, py = rng.randint(0, 1024 - side), rng.randint(0, 1024 - side)
        crop = {
            "tile_id": digest(
                [plan["source"], left, top, side, px, py, "mixed-final-log5"]
            )[:24],
            "source": plan["source"],
            "left": left,
            "top": top,
            "side": side,
            "pad_left": px,
            "pad_top": py,
            "anchor_record_ids": [anchor["record_id"]],
            "known_partial_boxes": partial,
            "objects": [],
        }
        for obj in objects:
            b = obj["box_slide"]
            area = overlap(b, left, top, side)
            if area:
                x0, y0 = max(b[0], left) - left + px, max(b[1], top) - top + py
                x1, y1 = (
                    min(b[2], left + side) - left + px,
                    min(b[3], top + side) - top + py,
                )
                crop["objects"].append(
                    {
                        **obj,
                        "bbox": [x0, y0, x1 - x0, y1 - y0],
                        "visible_fraction": area / ((b[2] - b[0]) * (b[3] - b[1])),
                    }
                )
        crops.append(crop)
    for crop in crops:
        for rid in crop["anchor_record_ids"]:
            if not any(
                o["record_id"] == rid and abs(o["visible_fraction"] - 1) < 1e-8
                for o in crop["objects"]
            ):
                raise ValueError("A known anchor was clipped")
    return crops


def prepare(old_manifest, new_plan_root, maps, root, seed=20261120):
    """Freeze all old/new source identities and independent test membership."""
    import numpy as np
    import openslide
    from method_a_new_delivery.focus_helpers import crc32_file, geometry

    root, maps = Path(root), Path(maps)
    if root.exists():
        raise FileExistsError(root)
    broad = read(maps / "broad_category_map.json")
    names = {int(k) + 1: v for k, v in broad.items()}
    with (maps / "fine_to_broad.csv").open(newline="") as f:
        mapping = {
            r["fine_category"]: (int(r["broad_class_id"]) + 1, r["broad_category"])
            for r in csv.DictReader(f)
        }
    with Path(old_manifest).open(newline="") as f:
        rows = [
            r
            for r in csv.DictReader(f)
            if r["sponsor_classify"] == "YES" and r["annotation_type"] == "circle"
        ]
    if len(rows) != 2290:
        raise ValueError(
            f"Full original inventory must retain 2290 records, got {len(rows)}"
        )
    grouped = collections.defaultdict(list)
    for row in rows:
        grouped[row["image_nots_path"]].append(row)
    plans = []
    for source, records in sorted(grouped.items()):
        path = Path(source)
        with openslide.OpenSlide(source) as slide:
            width, height = slide.dimensions
            objects = []
            for r in records:
                x, y, rx, ry = geometry(slide, r)
                cid, category = mapping[r["sponsor_category"]]
                objects.append(
                    {
                        "record_id": "old:" + r["record_id"],
                        "box_slide": [x - rx, y - ry, x + rx, y + ry],
                        "category_id": cid,
                        "category": category,
                    }
                )
        annotation = records[0]["annotation_nots_path"]
        crc = crc32_file(Path(annotation))
        if any(r["annotation_crc32"] != crc for r in records):
            raise ValueError(f"Original annotation provenance changed: {annotation}")
        stat = path.stat()
        plans.append(
            {
                "source": source,
                "annotation": annotation,
                "annotation_crc32": crc,
                "source_stat": [stat.st_size, stat.st_mtime_ns, stat.st_ino],
                "width": width,
                "height": height,
                "origin": "old",
                "group_id": "old:" + records[0]["split_group_id"],
                "objects": objects,
            }
        )
    for path in sorted(Path(new_plan_root).glob("*.json")):
        old = read(path)
        plans.append(
            {
                **{
                    k: old[k]
                    for k in (
                        "source",
                        "annotation",
                        "annotation_crc32",
                        "source_stat",
                        "width",
                        "height",
                    )
                },
                "origin": "new",
                "group_id": "new:" + old["source"],
                "objects": [
                    {**o, "record_id": "new:" + o["record_id"]} for o in old["objects"]
                ],
            }
        )
    if sum(len(p["objects"]) for p in plans if p["origin"] == "new") != 540:
        raise ValueError("New delivery inventory must retain 540 known records")
    # Thumbnail matches conservatively join identities; records are not merged.
    # This catches renamed equal scans without interpreting accession/L/R names.
    parent = {p["group_id"]: p["group_id"] for p in plans}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    fingerprints, identity_joins = {}, []
    for p in plans:
        with openslide.OpenSlide(p["source"]) as slide:
            pixels = np.asarray(slide.get_thumbnail((512, 512)).convert("RGB"))
            if pixels.std() < 1:
                raise ValueError(f"Uninformative identity thumbnail: {p['source']}")
            fingerprint = digest(
                [
                    p["width"],
                    p["height"],
                    list(pixels.shape),
                    hashlib.sha256(pixels.tobytes()).hexdigest(),
                ]
            )
        p["thumbnail_sha256"] = fingerprint
        if fingerprint in fingerprints:
            other = fingerprints[fingerprint]
            a, b = find(p["group_id"]), find(other["group_id"])
            parent[max(a, b)] = min(a, b)
            identity_joins.append([p["source"], other["source"]])
        else:
            fingerprints[fingerprint] = p
    for i, p in enumerate(sorted(plans, key=lambda p: p["source"])):
        p["index"] = i
        p["group_id"] = find(p["group_id"])
        if any(
            not (
                0 <= o["box_slide"][0] < o["box_slide"][2] <= p["width"]
                and 0 <= o["box_slide"][1] < o["box_slide"][3] <= p["height"]
            )
            for o in p["objects"]
        ):
            raise ValueError(f"Source box out of bounds: {p['source']}")
        p["crops"] = plan_crops(p, seed)
    plans.sort(key=lambda p: p["source"])
    assignment = partition(plans, seed=seed)
    for p in plans:
        write_new(root / "plans" / f"{p['index']:03d}.json", p)
    write_new(root / "assignment.json", assignment)
    write_new(root / "categories.json", names)
    summary = {
        "seed": seed,
        "scan_count": len(plans),
        "known_records": sum(len(p["objects"]) for p in plans),
        "crop_count": sum(len(p["crops"]) for p in plans),
        "plans_digest": digest(plans),
        "assignment_digest": digest(assignment),
        "old_inventory_sha256": file_sha(old_manifest),
        "identity_joins": identity_joins,
        "identity_limit": "Source paths, evidenced alias groups and matching whole-scan thumbnails; full NDPI byte equality not claimed.",
        "partitions": {},
    }
    for split in ("development", "test"):
        selected = [p for p in plans if assignment[p["source"]]["split"] == split]
        summary["partitions"][split] = {
            "scans": len(selected),
            "known": sum(len(p["objects"]) for p in selected),
            "by_origin": {
                o: {
                    "scans": sum(p["origin"] == o for p in selected),
                    "known": sum(
                        len(p["objects"]) for p in selected if p["origin"] == o
                    ),
                }
                for o in ("old", "new")
            },
            "class_support": dict(
                collections.Counter(
                    o["category"] for p in selected for o in p["objects"]
                )
            ),
        }
    write_new(root / "protocol.json", summary)
    return summary


def export(root, index, limit=None):
    """Export focal crops; require source metadata and plane-zero agreement."""
    import numpy as np
    import cv2
    import os
    import openslide
    import tifffile
    import zarr
    from PIL import Image
    from method_a_new_delivery.focus_helpers import (
        crc32_file,
        fused_tile,
        save_png_no_replace,
    )

    root = Path(root)
    cv2.setNumThreads(int(os.environ.get("SLURM_CPUS_PER_TASK", "1")))
    p = read(root / "plans" / f"{index:03d}.json")
    source = Path(p["source"])
    st = source.stat()
    if [st.st_size, st.st_mtime_ns, st.st_ino] != p["source_stat"] or crc32_file(
        Path(p["annotation"])
    ) != p["annotation_crc32"]:
        raise ValueError("Source provenance changed")
    output = root / "images"
    output.mkdir(parents=True, exist_ok=True)
    completed = []
    with openslide.OpenSlide(str(source)) as slide, tifffile.TiffFile(source) as tif:
        series = tif.series[0]
        if series.axes != "ZYXS":
            raise ValueError(f"Unexpected focal series: {series.axes}")
        offsets = [int(page.tags[65424].value) for page in series.pages]
        with series.aszarr() as store:
            array = zarr.open(store, mode="r")
            if isinstance(array, zarr.Group):
                array = array["0"]
            for c in p["crops"][:limit]:
                path = output / (c["tile_id"] + ".png")
                metadata = path.with_suffix(".json")
                if metadata.exists():
                    m = read(metadata)
                    if m["crop_digest"] != digest(c) or m["sha256"] != file_sha(path):
                        raise ValueError(
                            "Existing crop does not match its recorded content"
                        )
                    completed.append(c["tile_id"])
                    continue
                left, top, side = c["left"], c["top"], c["side"]
                reference = np.asarray(
                    slide.read_region((left, top), 0, (side, side)).convert("RGB")
                )
                pixels, scores, hist = fused_tile(
                    (
                        np.asarray(array[i, top : top + side, left : left + side, :])
                        for i in range(len(offsets))
                    ),
                    side,
                    offsets.index(0),
                    reference,
                )
                edges = np.concatenate(
                    (pixels[0], pixels[-1], pixels[:, 0], pixels[:, -1])
                )
                canvas = np.empty((1024, 1024, 3), dtype=np.uint8)
                canvas[:] = np.median(edges, axis=0).astype(np.uint8)
                canvas[
                    c["pad_top"] : c["pad_top"] + side,
                    c["pad_left"] : c["pad_left"] + side,
                ] = pixels
                if path.exists():
                    with Image.open(path) as im:
                        if not np.array_equal(np.asarray(im), canvas):
                            raise ValueError("Interrupted crop export differs")
                else:
                    save_png_no_replace(path, canvas)
                write_new(
                    metadata,
                    {
                        "crop_digest": digest(c),
                        "sha256": file_sha(path),
                        "focal_offsets": offsets,
                        "plane_scores": scores,
                        "plane_pixel_counts": hist,
                        "zero_plane_matches_openslide": True,
                    },
                )
                completed.append(c["tile_id"])
                print(
                    json.dumps(
                        {
                            "source_index": index,
                            "completed": len(completed),
                            "total": len(p["crops"]),
                        }
                    ),
                    flush=True,
                )
    status = root / "export_status" / f"{index:03d}.json"
    if not limit and not status.exists():
        write_new(status, {"status": "completed", "crop_ids": completed})
    return {"completed": len(completed)}

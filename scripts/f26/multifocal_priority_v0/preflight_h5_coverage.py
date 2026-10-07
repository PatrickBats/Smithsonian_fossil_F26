"""Read-only audit of existing HDF5 focal stacks against F26 priority crops.

Run on NOTS through Slurm with Python -B. Emits JSON on stdout and writes no
remote files. It checks metadata and geometry, not pixel equivalence.
"""

import collections
import csv
import json
import os
from pathlib import Path

import h5py


ROOT = Path(os.environ["F26_INPUT_ROOT"])
H5_ROOT = Path("/rhf/allocations/dsci435/smithsonian_full_sp26/processed/tiles")


def covered_by_union(crop, tiles):
    left, top, right, bottom = crop
    relevant = []
    x_edges = {left, right}
    for x, y, w, h in tiles:
        x0, x1 = max(left, x), min(right, x + w)
        y0, y1 = max(top, y), min(bottom, y + h)
        if x0 < x1 and y0 < y1:
            relevant.append((x0, y0, x1, y1))
            x_edges.update((x0, x1))
    edges = sorted(x_edges)
    for x0, x1 in zip(edges, edges[1:]):
        intervals = sorted((y0, y1) for ax0, y0, ax1, y1 in relevant if ax0 <= x0 and ax1 >= x1)
        frontier = top
        for y0, y1 in intervals:
            if y0 > frontier:
                break
            frontier = max(frontier, y1)
            if frontier >= bottom:
                break
        if frontier < bottom:
            return False
    return True


def main():
    with (ROOT / "inputs/record_assignments.csv").open(newline="", encoding="utf-8") as file:
        assignments = {r["record_id"]: r for r in csv.DictReader(file)}
    with (ROOT / "preflight_records.csv").open(newline="", encoding="utf-8") as file:
        geometry = {r["record_id"]: r for r in csv.DictReader(file)}
    if len(assignments) != 2283 or set(assignments) != set(geometry):
        raise ValueError("Unexpected input coverage")
    by_slide = collections.defaultdict(list)
    for record_id, row in assignments.items():
        by_slide[Path(row["image_nots_path"]).stem].append((row, geometry[record_id]))

    output = []
    for stem, records in sorted(by_slide.items()):
        path = H5_ROOT / (stem + ".h5")
        if not path.is_file():
            output.append({"slide": stem, "h5_exists": False, "records": len(records),
                           "center_covered": 0, "one_tile_covered": 0, "union_covered": 0})
            continue
        with h5py.File(path, "r") as h5:
            width = int(h5.attrs["image_width"])
            height = int(h5.attrs["image_height"])
            planes = int(h5.attrs["num_focal_planes"])
            tiles = []
            for group in h5.values():
                tiles.append(tuple(int(group.attrs[k]) for k in ("x", "y", "w", "h")))
            dims_match = all(
                int(g["source_width_px"]) == width and int(g["source_height_px"]) == height
                for _, g in records
            )
            counts = collections.Counter()
            for _, g in records:
                left, top, side = int(g["crop_left_px"]), int(g["crop_top_px"]), int(g["crop_side_px"])
                x, y = float(g["center_x_px"]), float(g["center_y_px"])
                crop = (left, top, left + side, top + side)
                if any(tx <= x < tx + tw and ty <= y < ty + th for tx, ty, tw, th in tiles):
                    counts["center"] += 1
                if any(tx <= left and ty <= top and tx + tw >= left + side and ty + th >= top + side
                       for tx, ty, tw, th in tiles):
                    counts["one_tile"] += 1
                if covered_by_union(crop, tiles):
                    counts["union"] += 1
            output.append({"slide": stem, "h5_exists": True, "records": len(records),
                           "focal_planes": planes, "tile_count": len(tiles),
                           "source_dimensions_match": dims_match,
                           "center_covered": counts["center"],
                           "one_tile_covered": counts["one_tile"],
                           "union_covered": counts["union"]})
    summary = {"slide_count": len(output), "h5_slide_count": sum(r["h5_exists"] for r in output),
               "record_count": sum(r["records"] for r in output),
               "center_covered": sum(r["center_covered"] for r in output),
               "one_tile_covered": sum(r["one_tile_covered"] for r in output),
               "union_covered": sum(r["union_covered"] for r in output)}
    print(json.dumps({"summary": summary, "slides": output}, indent=2))


if __name__ == "__main__":
    main()

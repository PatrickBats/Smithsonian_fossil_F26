"""Inspect only training image metadata and build deterministic candidate crops."""

import collections, csv, json, math, random, sys
import numpy as np
import openslide
from pathlib import Path
from common import BASE, ROOT, load, write

# Reuse only reviewed, read-only source geometry.
from focus_helpers import geometry, crc32_file


def main():
    rows = list(csv.DictReader((BASE / "inputs/priority_records.csv").open()))
    groups = collections.defaultdict(list)
    for r in rows:
        if r["method_a_split"] == "train":
            groups[r["image_nots_path"]].append(r)
    assert len(groups) == 47 and sum(map(len, groups.values())) == 1605
    covered = set()
    for p in (BASE / "plan").glob("*.json"):
        plan = load(p)
        if plan["split"] == "train":
            covered.update(plan["covered_record_ids"])
    assert len(covered) == 1061
    plans = []
    diameters = []
    all_boxes = []
    for index, (source, rs) in enumerate(sorted(groups.items())):
        ap = Path(rs[0]["annotation_nots_path"])
        assert crc32_file(ap) == rs[0]["annotation_crc32"]
        stat = Path(source).stat()
        with openslide.OpenSlide(source) as slide:
            w, h = slide.dimensions
            objs = []
            for r in rs:
                x, y, rx, ry = geometry(slide, r)
                box = [x - rx, y - ry, x + rx, y + ry]
                diameters.append(max(2 * rx, 2 * ry))
                objs.append(
                    {
                        "record_id": r["record_id"],
                        "box_slide": box,
                        "category_id": int(r["broad_class_id"]) + 1,
                        "category": r["broad_category"],
                        "old_grid_covered": r["record_id"] in covered,
                    }
                )
            plans.append(
                {
                    "index": index,
                    "source": source,
                    "annotation": str(ap),
                    "annotation_crc32": rs[0]["annotation_crc32"],
                    "source_stat": [stat.st_size, stat.st_mtime_ns, stat.st_ino],
                    "width": w,
                    "height": h,
                    "objects": objs,
                }
            )
        all_boxes.extend(objs)
    report = {
        "source_files": len(plans),
        "train_records": len(all_boxes),
        "old_grid_covered": len(covered),
        "box_max_dimension_percentiles": dict(
            zip(
                ["min", "p25", "p50", "p75", "p90", "p95", "p99", "max"],
                map(float, np.percentile(diameters, [0, 25, 50, 75, 90, 95, 99, 100])),
            )
        ),
        "fit_512_with_32px_margin": sum(v + 64 <= 512 for v in diameters),
        "fit_768_with_32px_margin": sum(v + 64 <= 768 for v in diameters),
        "test_images_opened": False,
    }
    write(ROOT / "audit/train_geometry.json", report)
    write(ROOT / "audit/train_source_geometry.json", plans)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

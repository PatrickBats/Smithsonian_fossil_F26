"""Read-only image metadata/geometry check before F26 crop export."""

import collections
import csv
import json
import statistics
from pathlib import Path

import openslide

from export_crops import OUTPUT_ROOT, SPLIT_MANIFEST, geometry, read_manifest, sha256_file


def main():
    if not OUTPUT_ROOT.is_dir() or OUTPUT_ROOT.is_symlink():
        raise ValueError("Expected new output root directory is missing")
    report_path = OUTPUT_ROOT / "preflight_records.csv"
    summary_path = OUTPUT_ROOT / "preflight_summary.json"
    if report_path.exists() or summary_path.exists():
        raise FileExistsError("Refusing to overwrite prior preflight output")

    rows = read_manifest()
    by_source = collections.defaultdict(list)
    for row in rows:
        by_source[row["image_nots_path"]].append(row)
    report = []
    open_errors = []
    for index, (source, records) in enumerate(sorted(by_source.items()), 1):
        print(f"source {index}/{len(by_source)}: {Path(source).name}", flush=True)
        try:
            before = Path(source).stat()
            slide = openslide.OpenSlide(source)
        except Exception as error:
            open_errors.append({"source": source, "error": str(error)[:500]})
            for record in records:
                report.append({"record_id": record["record_id"], "split": record["split"],
                               "source": source, "status": "open_error", "error": str(error)[:500]})
            continue
        try:
            for record in records:
                try:
                    details = geometry(slide, record)
                    report.append({"record_id": record["record_id"], "split": record["split"],
                                   "source": source, "status": "ok", "error": "", **details})
                except Exception as error:
                    report.append({"record_id": record["record_id"], "split": record["split"],
                                   "source": source, "status": "geometry_error",
                                   "error": str(error)[:500]})
        finally:
            slide.close()
        after = Path(source).stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size, after.st_mtime_ns, after.st_ino
        ):
            raise RuntimeError(f"Source image changed during read: {source}")

    fields = ["record_id", "split", "source", "status", "error", "center_x_px", "center_y_px",
              "radius_x_px", "radius_y_px", "crop_left_px", "crop_top_px", "crop_side_px",
              "mpp_x_um", "mpp_y_um", "source_width_px", "source_height_px"]
    with report_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report)
    valid = [r for r in report if r["status"] == "ok"]
    summary = {
        "source_split_manifest_sha256": sha256_file(SPLIT_MANIFEST),
        "source_image_files": len(by_source),
        "expected_records": len(rows),
        "checked_records": len(report),
        "valid_records": len(valid),
        "open_error_files": len(open_errors),
        "invalid_records": len(report) - len(valid),
        "crop_side_min_px": min((r["crop_side_px"] for r in valid), default=None),
        "crop_side_median_px": statistics.median(
            (r["crop_side_px"] for r in valid)
        ) if valid else None,
        "crop_side_max_px": max((r["crop_side_px"] for r in valid), default=None),
        "open_errors": open_errors,
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    if summary["invalid_records"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

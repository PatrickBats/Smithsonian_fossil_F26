"""Read focal NDPI data without changing sources; write only this experiment's RHF tree."""

import argparse, os
import numpy as np
import openslide, tifffile, zarr
from PIL import Image
import json
from pathlib import Path
from common import ROOT, load, sha, write
from focus_helpers import fused_tile, save_png_no_replace, crc32_file


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--slide-index", type=int, required=True)
    p.add_argument("--limit", type=int)
    a = p.parse_args()
    plan = load(ROOT / "plan" / f"{a.slide_index:02d}.json")
    source = Path(plan["source"])
    st = source.stat()
    assert [st.st_size, st.st_mtime_ns, st.st_ino] == plan["source_stat"]
    assert crc32_file(Path(plan["annotation"])) == plan["annotation_crc32"]
    out = ROOT / "images/crops"
    out.mkdir(parents=True, exist_ok=True)
    done = []
    with openslide.OpenSlide(str(source)) as slide, tifffile.TiffFile(source) as tif:
        series = tif.series[0]
        assert series.axes == "ZYXS" and tuple(series.shape[1:]) == (
            slide.dimensions[1],
            slide.dimensions[0],
            3,
        )
        offsets = [int(page.tags[65424].value) for page in series.pages]
        assert len(offsets) == len(set(offsets)) and 0 in offsets
        with series.aszarr() as store:
            array = zarr.open(store, mode="r")
            if isinstance(array, zarr.Group):
                array = array["0"]
            assert tuple(array.shape) == tuple(series.shape)
            for c in plan["crops"][: a.limit]:
                png = out / f"{c['tile_id']}.png"
                meta = png.with_suffix(".json")
                if meta.exists():
                    old = load(meta)
                    assert png.is_file() and old["sha256"] == sha(png) and old["crop"] == c
                    done.append(c["tile_id"])
                    continue
                if png.exists():
                    # A prior interruption after writing PNG is recovered by verifying regenerated pixels.
                    assert png.lstat().st_uid == os.getuid() and not png.is_symlink()
                l, t, s = c["left"], c["top"], c["side"]
                reference = np.asarray(slide.read_region((l, t), 0, (s, s)).convert("RGB"))
                fused, scores, hist = fused_tile(
                    (np.asarray(array[i, t : t + s, l : l + s, :]) for i in range(len(offsets))),
                    s,
                    offsets.index(0),
                    reference,
                )
                edges = np.concatenate((fused[0], fused[-1], fused[:, 0], fused[:, -1]), axis=0)
                color = np.median(edges, axis=0).astype(np.uint8)
                canvas = np.empty((1024, 1024, 3), dtype=np.uint8)
                canvas[:] = color
                px, py = c["pad_left"], c["pad_top"]
                canvas[py : py + s, px : px + s] = fused
                if png.exists():
                    with Image.open(png) as im:
                        assert np.array_equal(np.asarray(im), canvas)
                else:
                    save_png_no_replace(png, canvas)
                for o in c["objects"]:
                    x, y, w, h = o["bbox"]
                    assert (
                        min(x, y) >= 0
                        and min(w, h) > 0
                        and x + w <= 1024
                        and y + h <= 1024
                        and 1 <= o["category_id"] <= 28
                    )
                for rid in c["anchor_record_ids"]:
                    assert any(
                        o["record_id"] == rid and abs(o["visible_fraction"] - 1) < 1e-8
                        for o in c["objects"]
                    )
                write(
                    meta,
                    {
                        "status": "verified",
                        "crop": c,
                        "sha256": sha(png),
                        "focal_offsets": offsets,
                        "plane_scores": scores,
                        "plane_pixel_counts": hist,
                        "padding_rgb": list(map(int, color)),
                        "zero_plane_matches_openslide": True,
                    },
                )
                done.append(c["tile_id"])
                print(
                    json.dumps(
                        {
                            "slide": a.slide_index,
                            "done": len(done),
                            "total": len(plan["crops"]),
                            "side": s,
                        }
                    ),
                    flush=True,
                )
    after = source.stat()
    assert [after.st_size, after.st_mtime_ns, after.st_ino] == plan["source_stat"]
    write(
        ROOT / "export_status" / f"{a.slide_index:02d}.json",
        {
            "status": "pilot_completed" if a.limit else "completed",
            "tiles": done,
            "source_metadata_unchanged": True,
        },
    )


if __name__ == "__main__":
    main()

"""Tile slides whose annotations are box lists (OMERO CSV or NDPA without ROIs) into H5.

Same H5 schema as model_A/code/src/preprocessing/generate_tiles.py + postprocess_tiles.py
(focus_stacked, focal_plane_ranking_*, bboxes, uncropped_bboxes, labels, same attrs), but:
  * tiles = 1024px grid cells that contain an annotation centre (no ROI rectangles in this data),
    plus random empty cells on slides listed in DENSE (likely exhaustively annotated);
  * the raw z-stack is NOT stored (disk); best_plane_tenengrad is stored instead.
So export_coco.py --mode focus_stack works unchanged; best_plane/top_k modes do not.

Usage: python tile_boxes.py --row <index into split_v2_manifest.csv> [--limit N]
"""
import argparse, os, sys, time, json
import numpy as np, pandas as pd, h5py

CODE = "/rhf/allocations/dsci435/Smithsonian_F26/model_A/code"
sys.path.insert(0, CODE)
from src.data.ndpi_reader import NDPIData
from src.data.ndpa_reader import NDPAData
from src.data.util import bounds_to_pixels
from src.preprocessing.postprocess_tiles import focus_stack, tenengrad_ranking, vol_ranking

MANIFEST = "/rhf/allocations/dsci435/Smithsonian_F26/splits/split_v2_manifest.csv"
OUT = "/rhf/allocations/dsci435/Smithsonian_F26/processed/detector_v2_tiles"
TILE, MAG, SEED = 1024, 40, 435
DENSE = {"5406", "5412", "5418", "3746", "3749", "5769", "5853"}   # folders; from 2026-11-11 audit
EMPTY_FRAC = 0.25
MIN_SIDE, MAX_SIDE, DEDUP_IOU = 20, 1500, 0.5


def load_boxes(row, ndpi):
    md = ndpi.metadata
    if row.ann_format == "omero_csv":
        a = pd.read_csv(row.annotations, encoding="utf-8-sig", low_memory=False)
        a = a[a.shape_type != "Point"]
        b = a[["bbox_x_min", "bbox_y_min", "bbox_x_max", "bbox_y_max"]].to_numpy(float)
    else:
        b = []
        for p in NDPAData(row.annotations).palynomorphs:
            x, y, w, h = bounds_to_pixels(p.bounds, MAG, md)
            b.append([x, y, x + w, y + h])
        b = np.array(b, float).reshape(-1, 4)
    n_raw = len(b)
    W, H = md.full_width, md.full_height
    b[:, [0, 2]] = b[:, [0, 2]].clip(0, W)
    b[:, [1, 3]] = b[:, [1, 3]].clip(0, H)
    w, h = b[:, 2] - b[:, 0], b[:, 3] - b[:, 1]
    b = b[(w >= MIN_SIDE) & (h >= MIN_SIDE) & (w <= MAX_SIDE) & (h <= MAX_SIDE)]
    area = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    keep = []
    for i in range(len(b)):
        if keep:
            k = np.array(keep)
            ix = np.clip(np.minimum(b[k, 2], b[i, 2]) - np.maximum(b[k, 0], b[i, 0]), 0, None)
            iy = np.clip(np.minimum(b[k, 3], b[i, 3]) - np.maximum(b[k, 1], b[i, 1]), 0, None)
            inter = ix * iy
            if (inter / (area[k] + area[i] - inter) > DEDUP_IOU).any():
                continue
        keep.append(i)
    return b[keep], n_raw


def tile_origins(boxes, W, H, dense):
    cx = ((boxes[:, 0] + boxes[:, 2]) / 2 // TILE).astype(int)
    cy = ((boxes[:, 1] + boxes[:, 3]) / 2 // TILE).astype(int)
    pos = sorted(set(zip(cx.tolist(), cy.tolist())))
    empty = []
    if dense and len(pos):
        occ = set()
        for x0, y0, x1, y1 in boxes:   # any cell a box touches is not "empty"
            for gx in range(int(x0 // TILE), int(x1 // TILE) + 1):
                for gy in range(int(y0 // TILE), int(y1 // TILE) + 1):
                    occ.add((gx, gy))
        gx0, gx1, gy0, gy1 = min(cx), max(cx), min(cy), max(cy)
        cand = [(gx, gy) for gx in range(gx0, gx1 + 1) for gy in range(gy0, gy1 + 1) if (gx, gy) not in occ]
        rng = np.random.default_rng(SEED)
        n = min(len(cand), int(round(EMPTY_FRAC * len(pos))))
        empty = [cand[i] for i in rng.choice(len(cand), n, replace=False)] if n else []
    out = []
    for gx, gy in pos + empty:
        out.append((min(gx * TILE, W - TILE), min(gy * TILE, H - TILE)))
    return sorted(set(out)), len(pos), len(empty)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", type=int, required=True)
    ap.add_argument("--limit", type=int, default=0, help="debug: only first N tiles")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    args = ap.parse_args()
    M = pd.read_csv(MANIFEST, dtype={"folder": str})
    row = M.iloc[args.row]
    folder = str(row.folder).replace(".0", "") if isinstance(row.folder, str) or pd.notna(row.folder) else ""
    os.makedirs(args.out, exist_ok=True)
    final = os.path.join(args.out, f"{row.slide}.h5")
    if args.nshards > 1:
        if os.path.exists(final):
            print("merged file exists, skipping", final); return
        final = os.path.join(args.out, "parts", f"{row.slide}.part{args.shard:02d}of{args.nshards:02d}.h5")
        os.makedirs(os.path.dirname(final), exist_ok=True)
    if os.path.exists(final) and not args.limit:
        print("exists, skipping", final); return
    t0 = time.time()
    nd = NDPIData(row.ndpi)
    W, H = nd.metadata.full_width, nd.metadata.full_height
    boxes, n_raw = load_boxes(row, nd)
    origins, n_pos, n_empty = tile_origins(boxes, W, H, folder in DENSE)
    origins = origins[args.shard::args.nshards]
    if args.limit:
        origins = origins[: args.limit]
    print(f"{row.slide}: {n_raw} raw -> {len(boxes)} clean boxes; {n_pos} positive + {n_empty} empty tiles; z={len(nd.get_z_offsets())}", flush=True)
    tmp = final + (".debug" if args.limit else ".tmp")
    n_ann = 0
    with h5py.File(tmp, "w") as h5f:
        for i, (x0, y0) in enumerate(origins):
            x1, y1 = x0 + TILE, y0 + TILE
            sel = ~((boxes[:, 2] <= x0) | (boxes[:, 0] >= x1) | (boxes[:, 3] <= y0) | (boxes[:, 1] >= y1))
            bb, ub = [], []
            for ax0, ay0, ax1, ay1 in boxes[sel]:
                rx, ry, aw, ah = ax0 - x0, ay0 - y0, ax1 - ax0, ay1 - ay0
                cx0, cy0 = max(0, rx), max(0, ry)
                cw, ch = min(rx + aw, TILE) - cx0, min(ry + ah, TILE) - cy0
                if cw > 0 and ch > 0:
                    bb.append([cx0, cy0, cw, ch]); ub.append([rx, ry, aw, ah])
            data = nd.get_tile(int(x0), int(y0), TILE, TILE, magnification=MAG)   # (h, w, 3, z)
            stacked, avg_logs = focus_stack(data)
            ten = tenengrad_ranking(data)
            g = h5f.create_group(f"tile_{int(x0)}_{int(y0)}")
            g.create_dataset("focus_stacked", data=stacked, compression="gzip")
            g.create_dataset("best_plane_tenengrad", data=data[..., ten[0]], compression="gzip")
            g.create_dataset("focal_plane_ranking_LoG", data=np.argsort(avg_logs)[::-1])
            g.create_dataset("focal_plane_ranking_tenengrad", data=ten)
            g.create_dataset("focal_plane_ranking_VoL", data=vol_ranking(data))
            g.create_dataset("bboxes", data=np.array(bb, np.float32).reshape(-1, 4), compression="gzip")
            g.create_dataset("uncropped_bboxes", data=np.array(ub, np.float32).reshape(-1, 4), compression="gzip")
            g.create_dataset("labels", data=np.zeros(len(bb), np.int32), compression="gzip")
            g.attrs.update(dict(x=int(x0), y=int(y0), w=TILE, h=TILE, num_annotations=len(bb)))
            n_ann += len(bb)
            if i % 50 == 0:
                el = time.time() - t0
                print(f"  {i+1}/{len(origins)} tiles  {el/60:.1f} min  ({el/(i+1):.2f} s/tile)", flush=True)
        h5f.attrs.update(dict(source_image=row.ndpi, source_annotations=row.annotations, ann_format=row.ann_format,
                              num_tiles=len(origins), num_positive_tiles=n_pos, num_empty_tiles=n_empty,
                              num_focal_planes=len(nd.get_z_offsets()), image_width=W, image_height=H,
                              tile_size=TILE, overlap=0.0, magnification=MAG, raw_zstack_stored=False,
                              n_boxes_raw=n_raw, n_boxes_clean=len(boxes)))
        h5f.attrs["rois"] = np.zeros((0, 4), np.float32)
    if not args.limit:
        os.replace(tmp, final)
    print(f"done {row.slide}: {len(origins)} tiles, {n_ann} box instances, {(time.time()-t0)/60:.1f} min, {os.path.getsize(final if not args.limit else tmp)/1e9:.2f} GB", flush=True)


if __name__ == "__main__":
    main()

"""Merge shard H5 parts of one slide into the final <slide>.h5 (same schema as an unsharded run)."""
import argparse, glob, os, sys
import h5py, pandas as pd
sys.argv += [] ; import tile_boxes as T
ap = argparse.ArgumentParser(); ap.add_argument("--row", type=int, required=True); ap.add_argument("--nshards", type=int, required=True)
a = ap.parse_args()
slide = pd.read_csv(T.MANIFEST, dtype={"folder": str}).iloc[a.row].slide
final = os.path.join(T.OUT, f"{slide}.h5")
if os.path.exists(final):
    print("exists", final); sys.exit(0)
parts = [os.path.join(T.OUT, "parts", f"{slide}.part{i:02d}of{a.nshards:02d}.h5") for i in range(a.nshards)]
missing = [p for p in parts if not os.path.exists(p)]
if missing:
    print("MISSING", missing); sys.exit(1)
tmp = final + ".tmp"; n = 0
with h5py.File(tmp, "w") as out:
    for p in parts:
        with h5py.File(p, "r") as src:
            if p == parts[0]:
                for k, v in src.attrs.items(): out.attrs[k] = v
            for g in src:
                src.copy(src[g], out, name=g); n += 1
    out.attrs["num_tiles"] = n
    out.attrs["merged_from_shards"] = a.nshards
os.replace(tmp, final)
for p in parts: os.remove(p)
print(f"merged {slide}: {n} tiles from {a.nshards} shards")

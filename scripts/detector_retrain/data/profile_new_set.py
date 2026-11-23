"""First look at the November delivery on NOTS: per-slide ROI counts, shapes, box sizes, duplicates, sites."""
import glob, os, collections
import pandas as pd

ROOT = "/rhf/allocations/dsci435/smithsonian_full_sp26/new files/New_train_set_detection_model_rice"
rows = []
dfs = []
for d in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, d)
    if not os.path.isdir(p):
        continue
    csvs = glob.glob(os.path.join(p, "*rois.csv"))
    ndpis = glob.glob(os.path.join(p, "*.ndpi"))
    meta = glob.glob(os.path.join(p, "*metadata.txt"))
    m = {}
    if meta:
        for line in open(meta[0], errors="ignore"):
            if "=" in line:
                k, v = line.strip().split("=", 1)
                m[k] = v
    df = pd.read_csv(csvs[0], encoding="utf-8-sig", low_memory=False)
    df["folder"] = d
    dfs.append(df)
    W, H = float(m.get("ImageWidth", "nan")), float(m.get("ImageLength", "nan"))
    oob = ((df.bbox_x_min < 0) | (df.bbox_y_min < 0) | (df.bbox_x_max > W) | (df.bbox_y_max > H)).sum()
    rows.append(dict(
        folder=d, slide=os.path.basename(ndpis[0]) if ndpis else None,
        ndpi_GB=round(os.path.getsize(ndpis[0]) / 1e9, 1) if ndpis else None,
        n_rois=len(df), n_unique_roi=df.roi_id.nunique(),
        shapes=dict(collections.Counter(df.shape_type)),
        W=W, H=H, obj=m.get("Objective.Lens.Magnificant"), mag=m.get("Magnification"),
        px_um=round(df.pixel_size_x_um.iloc[0], 4) if len(df) else None,
        z_vals=sorted(df.z.dropna().unique().tolist())[:10],
        labeled=int(df[["roi_name", "roi_description", "text"]].notna().any(axis=1).sum()),
        oob=int(oob),
        med_w=round(df.width.median(), 1), med_h=round(df.height.median(), 1),
    ))

S = pd.DataFrame(rows)
A = pd.concat(dfs, ignore_index=True)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200); pd.set_option("display.max_colwidth", 60)
print("## per-slide summary")
print(S.drop(columns=["slide"]).to_string())
print("\n## totals: slides", len(S), "| rois", len(A), "| ndpi TB", round(S.ndpi_GB.sum() / 1000, 2))
print("shape types:", dict(collections.Counter(A.shape_type)))
for c in ["roi_name", "roi_description", "text", "c", "t", "z"]:
    vc = A[c].value_counts(dropna=False).head(15)
    print(f"\n## {c} values\n{vc.to_string()}")
print("\n## box size (px, level0)\n", A[["width", "height", "area_um2"]].describe(percentiles=[.01, .05, .5, .95, .99]).round(1).to_string())
print("\n## tiny (<40px either side):", int(((A.width < 40) | (A.height < 40)).sum()),
      " huge (>1000px):", int(((A.width > 1000) | (A.height > 1000)).sum()))
print("## exact duplicate boxes:", int(A.duplicated(subset=["folder", "bbox_x_min", "bbox_y_min", "bbox_x_max", "bbox_y_max"]).sum()))
print("## distinct (W,H,px) combos:", S.groupby(["obj", "mag", "px_um"]).size().to_dict())


def site(s):
    """Site / collection from the file name (for leakage-safe splits)."""
    s = s or ""
    for k in ["TADP1", "TADP-1A", "TOTA", "Carimagua", "Ladriges", "GT-17A", "Chucal", "2CDST", "Une-", "Pislipampa", "Contamana", "360300", "L440", "L860", "55365", "55370", "55372", "55378"]:
        if k in s:
            return k
    return "other"


S["site"] = S.slide.map(site)
print("\n## slides & rois by site")
print(S.groupby("site").agg(slides=("folder", "count"), rois=("n_rois", "sum")).sort_values("rois", ascending=False).to_string())
S.to_csv(os.path.expanduser("~/new_set_slide_summary.csv"), index=False)

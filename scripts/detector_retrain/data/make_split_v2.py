"""Build split_v2: old splits frozen + new Nov-2026 data split by sample, with held-out collections.
Run: python make_split_v2.py   (writes split_v2_20261118.json + split_v2_manifest.csv next to this file)
"""
import glob, json, os, random, re, collections
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = "/rhf/allocations/dsci435/smithsonian_full_sp26/processed/train_val_test.json"
NEW = "/rhf/allocations/dsci435/smithsonian_full_sp26/new files/New_train_set_detection_model_rice"
SEED, VAL_FRAC = 435, 0.15

# Hand-chosen from the 2026-11-11 audit (see README):
TEST_NEW = {"3746", "3749", "5853"}            # dense, look exhaustively annotated -> full mAP
TEST_NEW_RECALL = {"3776", "9000", "9009"}     # rest of held-out collections (2CDST, Pislipampa); likely sparse -> recall only
HELDOUT_SITES = {"2CDST", "Pislipampa"}

def stem(p): return os.path.basename(p)[: -len(".ndpi")]

def sample_id(s):
    s = re.sub(r"[ _]-?[ _]?\d{4}[-_]\d{2}[-_]\d{2}[ _]\d{2}[._]\d{2}[._]\d{2}.*$", "", s)  # drop scan timestamp
    s = re.sub(r"_(L|R)(?=_|$)", "", s)                                                     # drop slide side
    return s.rstrip("_- ")

def group_id(s):
    # stricter than sample: slides sharing a locality lot (e.g. 48371_L860033_L / 46427_L860033_R) stay together.
    # Carimagua lots are spelled both L470047 and L4770047, so group that site as a whole.
    if "Carimagua" in s: return "Carimagua"
    m = re.search(r"(?:^|_)(L\d{6})(?=_|$)", sample_id(s))
    return m.group(1) if m else sample_id(s)

def site(s):
    for k in ["Pislipampa", "2CDST", "Ladriges", "Carimagua", "Contamana", "Chucal", "TOTA", "GT-17A",
              "TADP", "Une-", "360300", "L440", "L860", "Nassichuk", "D1555", "CP_2012", "DG92", "Lake_Kemp"]:
        if k in s: return k.rstrip("-")
    m = re.match(r"(\d{3})\d{2}_[LR]?", s)
    return (m.group(1) + "xx") if m else "other"

rows = []
for d in sorted(glob.glob(NEW + "/*/")):
    nd = glob.glob(d + "*.ndpi")[0]; csv = glob.glob(d + "*rois.csv")[0]
    a = pd.read_csv(csv, encoding="utf-8-sig", low_memory=False)
    w, h = a.bbox_x_max - a.bbox_x_min, a.bbox_y_max - a.bbox_y_min
    n = int(((a.shape_type != "Point") & (w >= 20) & (h >= 20) & (w <= 1500) & (h <= 1500)).sum())
    rows.append(dict(slide=stem(nd), folder=os.path.basename(d.rstrip("/")), ndpi=nd, annotations=csv, ann_format="omero_csv", n_boxes=n))
for nd in sorted(glob.glob(NEW + "/*.ndpi")):
    ndpa = nd + ".ndpa"
    n = open(ndpa, errors="ignore").read().count('type="circle"') if os.path.exists(ndpa) else 0
    rows.append(dict(slide=stem(nd), folder="", ndpi=nd, annotations=ndpa, ann_format="ndpa", n_boxes=n))
M = pd.DataFrame(rows)
M["sample"] = M.slide.map(sample_id); M["group"] = M.slide.map(group_id); M["site"] = M.slide.map(site); M["split"] = None

M.loc[M.folder.isin(TEST_NEW), "split"] = "test_new"
M.loc[M.folder.isin(TEST_NEW_RECALL), "split"] = "test_new_recall"
assert set(M[M.site.isin(HELDOUT_SITES)].split) <= {"test_new", "test_new_recall"}, "held-out site leaked"
M.loc[M.ann_format == "ndpa", "split"] = "train"   # loose slides: 2 are old-raw copies (C_418058_L: its R side is old train; D1555: unused), 3 new

# Val: whole samples, one per site first for diversity, skip giant samples, until ~15% of new boxes
pool = M[M.split.isna()].groupby("group").agg(n=("n_boxes", "sum"), site=("site", "first")).reset_index()
target = VAL_FRAC * M[M.ann_format == "omero_csv"].n_boxes.sum()
rng = random.Random(SEED); order = pool.sample(frac=1, random_state=SEED).to_dict("records")
val, tot, used_sites = [], 0, set()
for pass_ in (0, 1):
    for g in order:
        if tot >= target or g["group"] in val or g["n"] > 2500: continue
        if pass_ == 0 and g["site"] in used_sites: continue
        val.append(g["group"]); tot += g["n"]; used_sites.add(g["site"])
M.loc[M["group"].isin(val), "split"] = "val"
M.loc[M.split.isna(), "split"] = "train"

# leakage checks
per = M.groupby("group").split.nunique(); assert (per == 1).all(), per[per > 1]
old = json.load(open(OLD)); old_all = {x for v in old.values() for x in v}
assert not ({sample_id(s) for s in old_all} & set(M[M.ann_format == "omero_csv"]["sample"])), "overlap with old"

out = {
    "version": "v2_20261118",
    "notes": "train/val = old + new; test = OLD test, frozen (compare to last semester); test_new = new exhaustive slides (full mAP); "
             "test_new_recall = held-out collections w/ likely-sparse labels (recall only). Slide ids for new data map to paths in split_v2_manifest.csv.",
    "train": sorted(old["train"]) + sorted(M[M.split == "train"].slide),
    "val": sorted(old["val"]) + sorted(M[M.split == "val"].slide),
    "test": sorted(old["test"]),
    "test_new": sorted(M[M.split == "test_new"].slide),
    "test_new_recall": sorted(M[M.split == "test_new_recall"].slide),
    "heldout_sites": sorted(HELDOUT_SITES), "seed": SEED,
}
json.dump(out, open(os.path.join(HERE, "split_v2_20261118.json"), "w"), indent=1)
M.drop(columns=[]).to_csv(os.path.join(HERE, "split_v2_manifest.csv"), index=False)

pd.set_option("display.width", 200)
S = M.groupby("split").agg(slides=("slide", "count"), groups=("group", "nunique"), boxes=("n_boxes", "sum"), sites=("site", lambda s: ",".join(sorted(set(s)))))
S["box_%"] = (100 * S.boxes / S.boxes.sum()).round(1)
print(S.to_string()); print("\nold kept:", {k: len(old[k]) for k in old})
print("final slide counts:", {k: len(v) for k, v in out.items() if isinstance(v, list) and k != "heldout_sites"})
print("\nval samples:", val)

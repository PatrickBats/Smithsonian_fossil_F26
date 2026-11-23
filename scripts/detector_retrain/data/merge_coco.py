"""Build detector_v2 COCO sets in export_coco layout (images/<split>/ + annotations/instances_<split>.json).
combined/      train = old sp26 train + new train (+ Contamana), val = old val + new val, test = OLD sp26 test (frozen)
test_new/      test  = new exhaustive-looking slides (3746, 3749, 5853)
test_new_recall/ test = held-out sparse slides (3776, 9000, 9009)
Images are symlinked (tar -h when copying). Single category id 0 'palynomorph'.
"""
import json, os, shutil
OLD = "/rhf/allocations/dsci435/smithsonian_full_sp26/processed/coco/coco_focus_stack"
NEW = "/rhf/allocations/dsci435/Smithsonian_F26/processed/coco_detector_v2"
CAT = [{"id": 0, "name": "palynomorph", "supercategory": "palynomorph"}]

def load(root, split):
    p = f"{root}/annotations/instances_{split}.json"
    return (json.load(open(p)), f"{root}/images/{split}") if os.path.exists(p) else (None, None)

def build(out_root, split, sources):
    img_dir = f"{out_root}/images/{split}"; os.makedirs(img_dir, exist_ok=True); os.makedirs(f"{out_root}/annotations", exist_ok=True)
    images, anns, seen = [], [], set()
    for root, s in sources:
        d, src = load(root, s)
        if d is None:
            print("  (missing, skipped)", root, s); continue
        assert all(c["id"] == 0 for c in d["categories"]), (root, d["categories"])
        idmap = {}
        for im in d["images"]:
            assert im["file_name"] not in seen, ("duplicate file", im["file_name"]); seen.add(im["file_name"])
            nid = len(images); idmap[im["id"]] = nid
            images.append({**im, "id": nid})
            dst = f"{img_dir}/{im['file_name']}"
            if not os.path.lexists(dst): os.symlink(f"{src}/{im['file_name']}", dst)
        for a in d["annotations"]:
            anns.append({**a, "id": len(anns), "image_id": idmap[a["image_id"]], "category_id": 0})
        print(f"  + {root.split('/')[-1]}:{s} {len(d['images'])} imgs {len(d['annotations'])} anns")
    json.dump({"images": images, "annotations": anns, "categories": CAT}, open(f"{out_root}/annotations/instances_{split}.json", "w"))
    print(f"{out_root.split('/')[-1]}/{split}: {len(images)} images, {len(anns)} annotations")

for d in ["combined", "test_new", "test_new_recall"]:
    if os.path.exists(f"{NEW}/{d}"): shutil.rmtree(f"{NEW}/{d}")
build(f"{NEW}/combined", "train", [(OLD, "train"), (f"{NEW}/new_main", "train"), (f"{NEW}/new_main_contamana", "train")])
build(f"{NEW}/combined", "val",   [(OLD, "val"), (f"{NEW}/new_main", "val")])
build(f"{NEW}/combined", "test",  [(OLD, "test")])
build(f"{NEW}/test_new", "test",  [(f"{NEW}/new_main", "test")])
build(f"{NEW}/test_new_recall", "test", [(f"{NEW}/new_recall", "test")])

# Annotations for the detector splits

COCO JSON, gzip-compressed, single category `palynomorph` (id 0). Boxes are in pixels on 1024 px focus-stacked tiles.
File names are `<slide>_tile_<x>_<y>.jpeg`.

| File | Tiles | Boxes | Use |
|---|---|---|---|
| `train.coco.json.gz` | 35,149 | 50,524 | training (old + new) |
| `val.coco.json.gz` | 8,837 | 9,689 | validation (old + new) |
| `old_test.coco.json.gz` | 986 | 1,594 | last semester's test set, unchanged |
| `test_new.coco.json.gz` | 7,663 | 7,826 | densely labeled new slides; 1,532 empty tiles |
| `test_new_recall.coco.json.gz` | 838 | 1,137 | sparsely labeled new slides; recall only |
| `retrain2_train_with_ignore_boxes.coco.json.gz` | 44,719 entries | 68,342 + 28,440 ignore | retrain 2 training set: old tiles listed 3x, category 1 = `__ignore__` |
| `retrain2_val_balanced.coco.json.gz` | 2,825 | 3,122 | retrain 2 validation; image id >= 1,000,000 = new collection |

## Where the tile images are

The images are too large for Git (about 18 GB). They are on NOTS:

```
/rhf/allocations/dsci435/Smithsonian_F26/processed/coco_detector_v2/
    combined/images/{train,val,test}/      # test = old_test
    test_new/images/test/
    test_new_recall/images/test/
```

Each folder also has `annotations/instances_<split>.json`, identical to the files here. The retrain 2 files use the
same images as `combined/`. Group read permission on these folders has not been checked since they were written;
tell Alan if you cannot read them.

## Scoring a detector on the test sets

`scripts/detector_retrain/eval/eval_detectors.py` scores any one-class RF-DETR checkpoint on the three test sets
(edit `CKPTS` and the root path `H` at the top). It needs rfdetr 1.6.4 and rfdetr-plus 1.0.2.

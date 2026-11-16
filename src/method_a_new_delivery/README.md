# Method A new-delivery implementation

This package holds the processing and evaluation functions behind the thin [command entry points](../../scripts/method_a_new_delivery/README.md). The modules are grouped by stage:

- `label_audit.py`, `label_geometry.py`, `label_unify.py`, and `label_map.py`: source inventory, NDPA nanometer-to-pixel conversion, unified pixel boxes, and sponsor-priority selection.
- `crop_plan.py`, `focus_helpers.py`, `crop_export.py`, `common.py`, `dataset.py`, and `dataset_verify.py`: native context crops, LoG k=5 focal fusion, merged COCO, and data checks. `focus_helpers.py` and the crop export algorithm retain the completed A3 implementation used for this run, sourced from `/projects/dsci435/Smithsonian_F26/method_a/experiments/sparse_labels_20261017/` on NOTS.
- `ignore_regions.py` and `training.py`: one-class pseudo ignore boxes and the final 28-class RF-DETR training protocol. The training implementation is based on the A4 source commit `8174c47939430d873a4f42b023f35fe7516aa168`.
- `cv.py`, `cv_evaluate.py`, `cv_aggregate.py`, `confusion.py`, and `plot_confusion.py`: whole-scan folds, known-target scoring, threshold selection, full aggregate counts, and figure rendering.
- `paths.py`: documented NOTS defaults and optional fresh-run output-root overrides.

Imports do not parse arguments or read/write project data. Output-producing work starts in a command `main()` function. The recorded path defaults identify the completed run; use fresh output roots to run again. Raw NDPI/NDPA images, row-level manifests, predictions, and model weights remain on NOTS.

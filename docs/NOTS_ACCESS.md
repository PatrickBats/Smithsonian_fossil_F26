# NOTS access, data locations, and viewing evidence

Observed September 14, 2026 through authenticated SSH as `pb52`. This is a bounded access and preview inspection, not a complete data audit or a validated Fall 2026 training manifest. Original cluster files were not changed and no training jobs were launched.

## Access and storage roles

SSH login to `nots.rice.edu` succeeded, with the account in the `dsci435` group. The configured `rice-nots` shortcut works in the environment used for this handoff; it is not automatically installed on teammates' machines. Each teammate uses their own NOTS account and private SSH setup. Keys and passwords are not stored in this repository.

The user supplied faculty storage guidance: persistent data belongs in `/rhf/allocations/dsci435/`, which is shared with the class, and other uses of that allocation require consultation with the faculty member. Experiment data/results belong in the team directory `/projects/dsci435/Smithsonian_F26/`. That experiment directory was absent at inspection time. No team directory was created during this documentation update.

| Remote location | Observation |
| --- | --- |
| `/rhf/allocations/dsci435/smithsonian_full_sp26/raw/Images_with_annotations_for_CNN_training/` | 82 NDPI files and 82 NDPA files; every image has a matching `image.ndpi.ndpa` filename |
| `/rhf/allocations/dsci435/smithsonian_full_sp26/raw/` | Direct children include 110 NDPI and 46 NDPA files, in addition to the training subdirectory |
| `/rhf/allocations/dsci435/smithsonian_full_sp26/processed/` | Existing `tiles/`, `coco/`, and `train_val_test.json`; COCO folders include focus-stacked and Tenengrad-plane variants |
| `/projects/dsci435/smithsonian_sp26/` | Prior environment, a small HDF5 inspection script, exploration outputs, and an annotator-output directory with RF-DETR/YOLO subdirectories |
| `/rhf/allocations/dsci435/smithsonian_cruft/` | Directory exists; contents were not audited |

The raw-directory counts do not establish unique slides across folders or whether every file is readable. Small reads succeeded for sample NDPI and NDPA files in both raw locations. Filename pairing does not establish valid classification labels, current annotation versions, or complete annotation coverage.

## Actual preview inspection

The sample basename was `C_418058_W_Nassichuk_R_2025_01_21_14_59_16_Alaska`, with its NDPI in the training directory above and its corresponding HDF5 file in `processed/tiles/`.

| Property | Observation |
| --- | --- |
| NDPI file size | 28,488,707,119 bytes, approximately 28.49 GB |
| Full-resolution dimensions | 88,320 × 89,856 pixels |
| Reader-reported resolution | Approximately 0.22886 micrometers/pixel in each axis; reported objective power 40× |
| TIFF structure | 164 pages including multiple magnifications/focal planes; initial full-resolution page reported focal offset −13,000 in NDPI tag 65424 |
| Existing HDF5 metadata | 27 focal planes, 56 tiles, tile size 1,024, zero overlap; one recorded ROI |
| Examined tile | `tile_63624_42509`; recorded position x=63,624, y=42,509, width/height 1,024 |
| Tile stack shape | `(1024, 1024, 3, 27)` |

A small PNG montage was generated outside the repository. The overview was decoded from a low-resolution NDPI page whose focal tag was zero. The detailed panel used the existing HDF5 `focus_stacked` dataset; the three additional panels used stored stack indices 0, 13, and 26 from the same tile. Those indices were not independently calibrated to physical focus offsets. The montage was visually inspected and showed the overview, the selected region, and focus changes.

This confirms that small previews can be produced without transferring the entire NDPI. It does not validate historical focus stacking, all tile coordinates, annotation-to-category mappings, or compatibility with the updated classification set. The prior `scripts/view_h5.py` lists HDF5 structure; it is not a graphical viewer. Libraries from the prior shared environment were used for read-only inspection, not installed or modified.

## Planned integration

The [pipeline roadmap](PIPELINE_PLAN.md) calls for registering remote file locations, running code in a NOTS checkout, and using Slurm for training/inference. A repository inventory is a reference to existing data, not a data download or network mount. Keep large images and run artifacts on NOTS; return small previews and reports for local review.

For interactive inspection, [Rice's NOTS OnDemand](https://kb.rice.edu/155161) provides JupyterLab and desktop applications on cluster resources. The project still needs an appropriate specimen/image viewer in that environment. [Rice's getting-started guide](https://kb.rice.edu/147970) links scheduler and storage instructions. These pages were consulted September 14, 2026; job settings must use the team's actual allocations.

OpenSlide's [Hamamatsu format documentation](https://openslide.org/formats/hamamatsu/) states that its NDPI reader ignores other focal planes and reads plane 0. Successful overview viewing therefore does not prove full-stack support. The planned extraction/viewer must verify focal-plane access explicitly.

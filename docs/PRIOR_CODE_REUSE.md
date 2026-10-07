# Spring 2026 code reuse — September 24, 2026

Repository access now succeeds: [RiceD2KLab/Smithsonian_fossil_Sp26](https://github.com/RiceD2KLab/Smithsonian_fossil_Sp26). Inspected commit: `1b62b68a0d95178e6275ef55c38ee4765317b334`. A separate local checkout was created; no upstream code was modified or merged into this project. Earlier 404 observations are historical.

## Useful components

- `src/data/ndpi_reader.py`: slide metadata, focal-plane indexing and region reads.
- `src/data/ndpa_reader.py`, `util.py`, `ndpa_writer.py`: annotation parsing, coordinate conversion and NDPA output.
- `src/preprocessing/`: tiling, focus stacking, focus ranking, slide splitting and COCO export.
- `src/models/`: YOLO26 and RF-DETR training, prediction and tuning.
- `src/annotator/`: configurable whole-slide detection/annotation pipeline.
- `scripts/`: Slurm launch examples; `tests/`: focused existing tests.

All four [published Rice Box checkpoints](https://rice.box.com/s/tspzty026aheeoj4z8fr399fs8iwegzu) were downloaded September 24: RF-DETR 2XL best-plane and focus-stack (1,515,934,018 bytes each), YOLO26 L focus-stack (53,056,677 bytes), and YOLO26 L best-plane (53,057,701 bytes). Total: 3,137,982,414 bytes. They are stored outside Git in `/home/pb52/MADness/smithsonian/smithsonian_prior_artifacts/weights/`; code is in `/home/pb52/MADness/smithsonian/Smithsonian_fossil_Sp26`. A verified Git bundle preserves the source history. See [artifact manifest](PRIOR_ARTIFACTS.json).

Sizes match the published file metadata; ZIP CRC checks passed and SHA-256 hashes were recorded. Download integrity is verified. The two YOLO checkpoints subsequently completed the [Fall detection pilot](DETECTION_PILOT.md); RF-DETR loading remains untested. No training was run.

## Required adaptation before reuse

1. **Annotation paths:** generate_tiles currently pairs an NDPI with an adjacent `.ndpa`. Our verified Fall annotation paths span annotations_F26 and unchanged raw files. Use our explicit cluster_source_paths.csv instead.
2. **Coverage:** generate_tiles constructs its grid from rectangle ROIs only. It must account for Fall specimen annotations outside those rectangles.
3. **Labels:** build_label_maps expects `Specimen_name` and `Category`, rather than our `Annotation title` and `Category`. Use the reconciled Fall mapping and retain fine labels while defining broad groups.
4. **Class IDs:** static inspection found generate_tiles creates zero-based IDs, whereas the multiclass export path subtracts one assuming one-based IDs. This is a potential incompatibility requiring an end-to-end label test before using multiclass exports; it is not a reproduced runtime failure.
5. **Provenance and splits:** extend the outputs to retain specimen/source identity, and use the new grouped evaluation protocol rather than blindly inheriting old splits. Single-class export intentionally collapses labels and is inappropriate for a multiclass task.

Recommended sequence: verify the existing reader/conversion on a small Fall specimen batch; adapt manifest-driven extraction; audit and load the prior checkpoint; compare a separate crop classifier with a multiclass detector only after labels, coverage and evaluation are defined. This is a reuse review, not an implementation or scientific-protocol change.

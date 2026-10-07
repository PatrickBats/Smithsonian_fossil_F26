# Under-five-minute speaker guide

Two standalone slides. Planned delivery: 80 seconds. Spoken script: 156 words. At 125 words/minute this is approximately 1.2 minutes before pauses. Rehearse once; timing is a target, not a guarantee. Source notes are not spoken.

## Slide 1 — Sources to specimen inventory (40 seconds)

We begin with two linked sources: the large microscope images and the separate expert annotation files. Each annotation is connected to its source slide, location, original identification, and mapped category. The existing inventory covers eighty-three image and annotation pairs, with two thousand two hundred ninety records in the initial target categories. We then check geometry, duplicate candidates, missing labels, and coverage across slides. The output is a traceable specimen inventory; it is not yet a quality-checked training dataset.

Presenter reference: Current verified data inventory and report Sections III–IV. Completed: pairing and count reconciliation. Crop quality and duplicate review remain preparation tasks. NO and unmarked objects are not automatically background.

## Slide 2 — Inventory to model-ready inputs (40 seconds)

Before preparing the full model inputs, we define training, validation, and test groups by slide and investigate related samples that need to stay together. All focal planes and augmented views of a specimen follow its assigned group. We read small regions from the images, inspect alignment and image quality, and prepare focus-stacked detector tiles and specimen crops. Balancing and augmentation apply only to training. Saved identifiers and settings let us trace each input back to its original annotation.

Presenter reference: Report Sections IV–V. Diagram describes the planned main experiment, not a completed split or extraction run. Small quality-inspection samples may precede the final split. Tile merging and model inference belong to the architecture slides.
# Under-five-minute speaker guide

Ten slides. Planned delivery: 4:15 (255 seconds). Spoken script: 505 words. At 125 words/minute this is approximately 4.0 minutes before pauses. Rehearse once; timing is a target, not a guarantee. Source notes are not spoken.

## Slide 1 — Opening (20 seconds)

Our project uses machine learning to help identify fossil pollen in Smithsonian microscope images. These tiny fossils form a large scientific record, but examining them requires substantial expert time. We are developing a workflow that connects specimen detection with category identification.

Presenter reference: Uploaded report, Introduction. Real focus-stacked Bombacacidites crop; expert annotation category.

## Slide 2 — Scientific motivation (20 seconds)

Pollen can survive in sediments long after the plants that produced it disappear. Identifying those fossils helps researchers reconstruct vegetation. Here, the scientific motivation is understanding North American plant communities around fifty million years ago and their relationship to past warm climates.

Presenter reference: Uploaded report, Introduction. Image: expert-labeled Platycarya platycarioides; not a model prediction.

## Slide 3 — Problem definition (20 seconds)

There are two distinct tasks. Detection locates a specimen in an image. Classification identifies its category from its appearance. Previous project work provides a detection foundation. Our main question is whether identification works better inside the detector or in a separate classifier.

Presenter reference: Uploaded report, Objectives and Proposed Models.

## Slide 4 — Dataset (25 seconds)

The working dataset contains eighty-three annotated slides. Our initial target inventory has two thousand two hundred ninety annotations across thirty-two candidate categories, within a larger set of eleven thousand two hundred seventy-five named annotations. The final category grouping remains to be fixed. Images contain multiple focal depths, so we read small regions on Rice’s cluster.

Presenter reference: Uploaded report, Data. Counts precede quality review, duplicate checks, category regrouping and sampling.

## Slide 5 — Imbalance (25 seconds)

Examples are unevenly distributed. Bisaccate has three hundred sixteen annotations, while the smallest target category has twenty-seven. Slide coverage matters too: many examples from one slide do not provide the same diversity as examples across several slides. We will consider training-only balancing strategies and evaluate performance separately for each category.

Presenter reference: Uploaded report, Class balance. Bars use a common linear scale. Candidate strategies: undersampling, balanced sampling and weighted loss.

## Slide 6 — Joint approach (30 seconds)

The first approach uses multiclass RF-DETR, a transformer-based detector. It receives image tiles and predicts both specimen locations and categories. Predictions from overlapping tiles are then merged in slide coordinates. The attraction is a unified model, but learning rare or visually similar categories alongside localization may be difficult. This is a proposed experiment.

Presenter reference: Uploaded report, Model 1. Simplified diagram; focus stacking, coordinate mapping and duplicate merging remain part of the pipeline.

## Slide 7 — Two-stage approach (30 seconds)

The second approach uses RF-DETR to find specimens, then passes individual crops to a Swin-Tiny image classifier. This lets us examine classification separately. However, missed specimens and poor crops can affect the final result. We will test the classifier on both expert-defined crops and detector-generated crops to identify where errors arise. This approach is also still proposed.

Presenter reference: Uploaded report, Model 2. Same input preprocessing and split as Model 1; detector boxes mapped and merged before crop classification.

## Slide 8 — Pilot evidence (30 seconds)

We tested two existing YOLO detector checkpoints on sixty-four known targets from twenty-nine slides. The best-plane model recovered fifty-four targets, and the focus-stacked model recovered fifty-one under the same confidence and box-overlap rule. These results demonstrate feasibility. They are not classification accuracy or independent generalization: crops were centered on known targets, and many slides appear in historical training records.

Presenter reference: Uploaded report, Preliminary Detector Assessment. Confidence >=0.50, IoU >=0.50. Different checkpoint weights; cannot isolate preprocessing. No RF-DETR/Swin classification training reported.

## Slide 9 — Fair testing (30 seconds)

Both approaches will use the same category definitions, preprocessing, and evaluation groups. We will separate slides and investigate related samples to reduce leakage. Category-level metrics will reveal weaknesses hidden by overall accuracy. End-to-end evaluation must count missed specimens as well as wrong labels. Measuring detection precision also requires reviewed regions with sufficiently complete annotations.

Presenter reference: Uploaded report, Partitioning and Evaluation. Metrics include macro-F1, balanced accuracy, per-class recall, and end-to-end detection measures where labels support them.

## Slide 10 — Close (25 seconds)

Next, we will inspect crops, define the category groups, and freeze the evaluation split. Then we can compare the two baselines and use their errors to guide development. Our intended deliverable is a simple interface linking each specimen image and location to proposed labels and uncertainty, so researchers can review results efficiently.

Presenter reference: Uploaded report, Next Steps and Objectives. No completed viewer or trained classifier is claimed.
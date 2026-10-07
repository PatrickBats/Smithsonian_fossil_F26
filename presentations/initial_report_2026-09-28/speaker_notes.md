# Under-five-minute speaker guide

Ten slides. Planned delivery: 4:20 (260 seconds). Spoken script: 542 words. At 125 words/minute this is approximately 4.3 minutes before pauses. Rehearse once; timing is a target, not a guarantee. Source notes are not spoken.

## Slide 1 — Project and objective (20 seconds)

Our project asks whether fossil specimens are better located and identified by one joint model, or by a detector followed by a separate classifier. We are building on existing Smithsonian and Rice work to support expert review of fossil pollen and other palynomorphs.

Presenter reference: Report pp. 3–4, objectives. Palynomorphs include pollen and spores. Image: expert-labeled Bombacacidites focus-stacked crop.

## Slide 2 — Motivation and scale (25 seconds)

Fossil pollen provides evidence about past vegetation and warm climates around fifty million years ago. The report describes a broader Smithsonian collection of roughly seventy thousand slides, far larger than our working dataset. Locating and identifying specimens manually is time-consuming. Automation could help scientists review more material while retaining access to the original images.

Presenter reference: Report p. 3, Introduction; collection estimate attributed there to Romero et al., report reference [2]. This collection estimate is distinct from the 83-slide working dataset.

## Slide 3 — Why recognition is difficult (25 seconds)

Identification depends on features such as shape, apertures, and surface structure. Different structures may be sharp at different focal depths, while staining and surrounding debris change the appearance. These real examples illustrate that variation. Focus stacking produces a usable two-dimensional image, but we must check whether it preserves the details needed for classification.

Presenter reference: Report pp. 3–5, multifocal imaging and data quality; p. 7 specimen examples. These are different specimens with different source field widths, not a focal-plane sequence or a controlled stain comparison.

## Slide 4 — Prior research and rationale (30 seconds)

Prior work gives us two foundations. Shaikh and colleagues developed whole-slide detection with image tiling and focal compression. Studies by Punyasena and Martinsen provide precedents for detecting specimens and classifying crops separately. Those studies use different images and categories, so their results do not establish performance here. Our contribution is to compare joint and two-stage identification on the same fossil dataset.

Presenter reference: Report pp. 3–4, related work, references [4], [5], [7]. No claim that earlier studies used Swin or establish its superiority. Swin rationale: hierarchical local-window image features, report reference [9].

## Slide 5 — Data and imbalance (30 seconds)

The working dataset contains eighty-three annotated slides and eleven thousand two hundred seventy-five named annotations. Our initial target inventory uses two thousand two hundred ninety annotations across thirty-two candidate categories. Counts range from twenty-seven to three hundred sixteen per target category. We will assess both category frequency and independent slide coverage, and consider training-only balancing rather than changing the evaluation data.

Presenter reference: Report pp. 4–5, data inventory and imbalance. These are records before quality review, duplicate checking, regrouping and sampling. The two bars show the range on a common scale.

## Slide 6 — Shared pipeline (25 seconds)

Both approaches share the same preparation and source groups. We will check annotation geometry, focus, and specimen quality, and keep related slides and all views of a specimen together when defining splits. Images are processed as overlapping, focus-stacked tiles. Every derived specimen retains its source coordinates and labels, so predictions can be traced back and inspected.

Presenter reference: Report p. 5, Pipeline. Source groups assigned before tiling, augmentation or balancing; split proportions and exact settings remain to be specified.

## Slide 7 — Multiclass RF-DETR (25 seconds)

The first approach adapts RF-DETR to predict specimen locations and categories together. It processes image tiles, and overlapping predictions are merged in whole-slide coordinates. This gives a unified detection-and-identification model. The question is whether its joint objective can learn uncommon or visually similar categories well enough.

Presenter reference: Report pp. 6 and 8, Model 1. Architecture restored from report and recolored to match this deck. Model internals and output marks are conceptual, not measured predictions; thumbnails are real images.

## Slide 8 — RF-DETR plus Swin-Tiny (25 seconds)

The second approach first uses RF-DETR to find specimens, then applies Swin-Tiny to their crops. This separates identification from localization and makes classifier errors easier to examine. However, missed detections or poor crops can reduce overall performance. Comparing expert-defined crops with detected crops will help identify that bottleneck.

Presenter reference: Report pp. 7–8, Model 2. Same source split and preprocessing; detector and classifier scores retained separately. Proposed model, not completed classifier training.

## Slide 9 — Evaluation and preliminary evidence (35 seconds)

We will evaluate detection, classification, and the combined workflow on separate source groups, with per-category metrics so common categories do not dominate. Detection precision requires sufficiently complete annotations. As preliminary evidence, existing YOLO checkpoints recovered fifty-four and fifty-one of sixty-four known targets. These were centered crops with possible prior training exposure, so the results establish feasibility rather than independent generalization. The proposed RF-DETR and Swin comparison remains to be run.

Presenter reference: Report pp. 8–9. Pilot: best-plane 54/64; focus-stack 51/64, confidence and IoU each >=0.50. Different checkpoints mean preprocessing is not isolated. Macro-F1 averages category-level F1; balanced accuracy averages recall.

## Slide 10 — Next steps and deliverable (20 seconds)

Next we will finalize categories, inspect crops, and freeze the evaluation protocol before training the baselines. The selected approach will support a simple interface linking specimen images and locations to proposed labels and uncertainty. The goal is useful scientific review, with clear evidence about where automated identification succeeds or fails.

Presenter reference: Report p. 10, next steps and limitations. No promise of a finalized grouping, trained classifier, or completed viewer.
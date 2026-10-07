# Sponsor update — speaker notes

Three slides · approximately two minutes. Source context is not spoken.

## Slide 1 — 40 seconds

This week, much of our effort went into preparing and presenting our initial class slides and report. That helped us clarify the scope and how we want to evaluate the models. We also made progress with data preparation. The latest team update reports 2,283 single-plane specimen crops and a draft split that we’re reviewing. We haven’t completed a full evaluation or trained the category classifiers yet.

## Slide 2 — 45 seconds

Our preliminary check used two frozen detectors from the previous work on 64 annotated targets across 29 slides. The best-plane checkpoint recovered 54 targets, and the focus-stack checkpoint recovered 51. This is an encouraging sign that we can reuse the detection work. However, these were small regions centered on known specimens, so the numbers are not whole-slide accuracy or classification accuracy. The checkpoints have different weights, so this also doesn’t isolate which image-preparation method is better.

## Slide 3 — 35 seconds

Our next priority is to finalize the training, validation, and test sets. We’ll review crop quality and label issues, keep related microscope slides together, and check that the category coverage supports a useful evaluation. Once that protocol is agreed, we can train the first classification baseline. We also need to resolve shared storage before completing the multifocal crop export.

# Sponsor update speaker notes

Prepared content: approximately 3:40. RF-DETR slide is an unfilled placeholder; allow about 60 seconds for that team’s update to target 4:40 total. No meeting date assumed.

## 1. Two approaches to identifying fossil pollen — 25 seconds

We’ve organized this update into two parts. First is the RF-DETR method, which aims to locate specimens and identify their categories together. Then we’ll cover the classifier backbones, which identify categories from prepared specimen crops. That classification experiment uses 2,283 specimens across 32 priority categories. The images here are real examples with expert labels.

## 2. RF-DETR: detection and category identification — 0 seconds

PLACEHOLDER — not a spoken script. RF-DETR team to add its method, progress and results. Allow approximately 60 seconds if the full presentation should stay near five minutes. No RF-DETR results are supplied or implied here.

## 3. A clearer view helps the model identify pollen — 45 seconds

The microscope scans show each specimen at several focal depths. On the left is the original view; on the right is a sharper view of the same specimen. We used a sharpness score to choose one plane for each crop. With the same Swin training settings, validation accuracy on unfamiliar slides increased from about 32 to 38 percent. This example illustrates the focus change; it doesn’t mean this particular specimen caused that improvement. We’d also like to know when identification requires features visible across several depths, rather than just one sharp image.

## 4. Two questions, two ways to check performance — 50 seconds

We checked performance in two situations. In the unseen-slide experiment, all specimens from a slide stay together, so the model is checked on slides it hasn’t learned from. In the shared-slide experiment, it learns from some grains and is checked on other grains from the same slides. We never reuse the exact same specimen in both sets. Shared slides can have familiar staining and imaging conditions, so that is an easier situation. Both experiments have the same number of training and validation examples, but the actual examples differ. A separate final test set remains unused.

## 5. Adapting DINO gives our strongest results so far — 55 seconds

Here are the classification results. Swin reached 38 percent on unseen slides and 66 percent with shared slides. DINO initially did worse when we kept its image-processing backbone fixed and trained only a small classifier. We then allowed the final part of DINO to adapt to our specimens. That reached about 44 percent on unseen slides and 70 percent with shared slides. Its category-averaged F1 score also improved. These are promising initial results, but they are single-run validation comparisons, not final test results. They measure identification of prepared crops, rather than the complete process of finding and classifying everything on a slide.

## 6. Where identification still struggles — 45 seconds

This shows the categories the adapted DINO model struggled with most on unfamiliar slides. Momipites wyomingensis was the clearest problem: none of its 21 validation specimens were identified correctly, and 18 were called Momipites instead. Polyatriopollenites, Bombacacidites, Ulmipollenites, Psilatricolpites and Arecipites also had low recovery. The counts on the right show how many examples each result is based on. We’ve limited this ranking to categories with at least five examples, since a result based on one or two specimens would be especially unreliable. These are the main categories to investigate next.
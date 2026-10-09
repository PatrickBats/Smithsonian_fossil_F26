# Sponsor update speaker notes

Prepared content: approximately 3:40. RF-DETR slide is an unfilled placeholder; allow about 60 seconds for that team’s update to target 4:40 total. No meeting date assumed.

## 1. Two approaches to identifying fossil pollen — 25 seconds

We’ve organized this update into two parts. First is the RF-DETR method, which aims to locate specimens and identify their categories together. Then we’ll cover the classifier backbones, which identify categories from prepared specimen crops. We kept the same 2,283 specimens and grouped the original 32 labels into 28 broader categories. Four Momipites labels now form one group, and two Caryapollenites labels form another. The images here are real examples with expert labels.

## 2. RF-DETR: detection and category identification — 0 seconds

PLACEHOLDER — not a spoken script. RF-DETR team to add its method, progress and results. Allow approximately 60 seconds if the full presentation should stay near five minutes. No RF-DETR results are supplied or implied here.

## 3. A clearer view helps the model identify pollen — 45 seconds

The microscope scans show each specimen at several focal depths. On the left is the original view; on the right is a sharper view of the same specimen. We used a sharpness score to choose one plane for each crop. In our earlier 32-category experiment, with the same Swin training settings, validation accuracy on unfamiliar slides increased from about 32 to 38 percent. This example illustrates the focus change; it doesn’t mean this particular specimen caused that improvement. We’d also like to know when identification requires features visible across several depths, rather than just one sharp image.

## 4. Two questions, two ways to check performance — 50 seconds

We checked performance in two situations. In the unseen-slide experiment, all specimens from a slide stay together, so the model is checked on slides it hasn’t learned from. In the shared-slide experiment, it learns from some grains and is checked on other grains from the same slides. We never reuse the exact same specimen in both sets. Shared slides can have familiar staining and imaging conditions, so that is an easier situation. Both experiments have the same number of training and validation examples, but the actual examples differ. A separate final test set remains unused.

## 5. DINO leads the broad-category comparison — 55 seconds

We trained both models again using the 28 broader categories. Swin reached about 43 percent on unseen slides and 71 percent with shared slides. DINO reached 50 percent and 74 percent, so it still leads both comparisons. But grouping categories makes the task easier. If we simply regroup our earlier DINO predictions, we already get about 50 and 74 percent. So retraining on the broader labels has added very little accuracy so far. These are validation results for prepared crops; we have not evaluated the final test set.

## 6. Three categories still need closer review — 45 seconds

These three categories remain difficult in both settings: Bombacacidites, Polyatriopollenites, and Psilatricolpites. The counts show how many examples were identified correctly. They have relatively few labeled examples, which may contribute, but some other small categories perform well. We haven’t established the main cause. We’ll inspect which categories they get confused with and whether focus or crop quality is hiding useful details. The shared-slide results use only seven or eight examples per category, so the percentages are uncertain. The merged Momipites group now gets about 80 percent correct in both settings and is no longer a main weakness.
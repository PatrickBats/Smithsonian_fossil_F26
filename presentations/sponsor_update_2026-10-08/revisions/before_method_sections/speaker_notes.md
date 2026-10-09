# Sponsor update speaker notes

Target: approximately 4:40 speaking, plus transitions. No meeting date assumed.

## 1. From pollen images to category predictions — 40 seconds

Since our last update, we’ve moved from preparing the data to training initial classifiers. We now have 2,283 labeled specimens across 32 priority categories in this experiment. These are real examples from the collection, with the expert category labels. We prepared focused images, compared two model families, and saved their predictions for review. Our goal is still to help researchers identify specimens more efficiently. Today, we’ll show what improved, where the models still struggle, and where your input would be most useful.

## 2. A clearer view helps the model identify pollen — 45 seconds

The microscope scans show each specimen at several focal depths. On the left is the original view; on the right is a sharper view of the same specimen. We used a sharpness score to choose one plane for each crop. With the same Swin training settings, validation accuracy on unfamiliar slides increased from about 32 to 38 percent. This example illustrates the focus change; it doesn’t mean this particular specimen caused that improvement. We’d also like to know when identification requires features visible across several depths, rather than just one sharp image.

## 3. Two questions, two ways to check performance — 50 seconds

We checked performance in two situations. In the unseen-slide experiment, all specimens from a slide stay together, so the model is checked on slides it hasn’t learned from. In the shared-slide experiment, it learns from some grains and is checked on other grains from the same slides. We never reuse the exact same specimen in both sets. Shared slides can have familiar staining and imaging conditions, so that is an easier situation. Both experiments have the same number of training and validation examples, but the actual examples differ. A separate final test set remains unused.

## 4. Adapting DINO gives our strongest results so far — 55 seconds

Here are the classification results. Swin reached 38 percent on unseen slides and 66 percent with shared slides. DINO initially did worse when we kept its image-processing backbone fixed and trained only a small classifier. We then allowed the final part of DINO to adapt to our specimens. That reached about 44 percent on unseen slides and 70 percent with shared slides. Its category-averaged F1 score also improved. These are promising initial results, but they are single-run validation comparisons, not final test results. They measure identification of prepared crops, rather than the complete process of finding and classifying everything on a slide.

## 5. Which differences matter to an expert? — 50 seconds

These are actual mistakes from the adapted DINO model on unseen-slide validation specimens. The expert labels are shown above the model’s predictions. We selected examples from recurring confusions, rather than treating them as representative of every error. We don’t yet know whether these mistakes reflect subtle biological differences, image quality, nearby material, or the model relying on the wrong features. Your interpretation would help us decide what to improve. We would especially value guidance on which visible characteristics distinguish these categories, and whether another focal view would make the distinction clearer.

## 6. Help us prioritize the next improvements — 40 seconds

The main takeaway is that we now have a working classifier and a way to compare improvements. Adapting DINO helped, but unfamiliar slides remain challenging. We’d like your help deciding which confusions have the greatest scientific consequences, which categories deserve priority, and when multiple focal views are essential. Our next step is to review a manageable set of errors with you, make targeted improvements, and then evaluate the selected approach on the reserved test slides. We want the next experiments to address useful scientific distinctions, not simply produce a higher overall score.
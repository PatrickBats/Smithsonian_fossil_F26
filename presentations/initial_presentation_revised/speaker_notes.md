# Speaker notes

Target: 4:40 speaking, with up to 20 seconds for transitions. The rubric specifies exactly five minutes; rehearse to approach five minutes without running over.

Presenter blocks: 1 → slides 1–2; 2 → slides 3–4; 3 → slides 5–6; 4 → slides 7–8; 5 → slides 9–10. Assign names within the team.

## Slide 1: Welcome — 10 seconds

Hi everyone. We’re the Rice D2K Smithsonian team. Our project is about helping researchers identify fossil pollen using machine learning.

## Slide 2: Background — 30 seconds

Fossil pollen gives us clues about which plants lived in the past. Smithsonian researchers use it to understand North American vegetation about fifty million years ago. The challenge is that identifying these tiny specimens takes expert time. The previous Rice team developed a detector that finds specimens. We want to build on that by identifying their categories.

## Slide 3: The problem — 25 seconds

This shows the difference between finding a specimen and identifying it. On the left, the box marks one pollen grain in a crowded microscope image. On the right, we can inspect its shape and surface details. Detection asks, where is it? Classification asks, what kind is it? Our project connects those two tasks.

## Slide 4: Previous approaches — 25 seconds

These studies give us two foundations. Punyasena and Martinsen locate specimens and then classify individual crops. Abbas Shaikh and colleagues developed a pipeline for detecting specimens across large, multifocal slides. We want to build on that detection work and add category identification, comparing separate and combined approaches.

## Slide 5: Microscopy data — 20 seconds

The images also capture different focal depths. Here, the same specimen appears across twenty-five focal planes, and this example’s full scan is about thirty gigabytes. We’ll work with smaller image regions and use the focal views to make the specimen’s details easier to see.

## Slide 6: Annotation inventory — 30 seconds

Our collection has eighty-three microscope images paired with expert annotations. We’re starting with thirty-two priority categories containing two thousand two hundred ninety annotations. The chart shows that some categories have many more examples than others. That matters because categories with fewer examples can be harder to learn. We’ll account for that when training and evaluating the models.

## Slide 7: Organizing the data — 30 seconds

First, we organize the examples. Each microscope image is matched with its annotation file, which gives us specimen locations and expert labels. We connect those labels to the categories we want to recognize. Then we check that the marks point to the right specimens and look for missing labels or duplicates. This keeps each example linked to its source.

## Slide 8: Preparing examples — 35 seconds

Next, we separate the data for training, validation, and testing. Examples from the same microscope slide stay together, so the test checks performance on unfamiliar slides. We then extract smaller regions and check their position and focus. Larger regions help the detector find specimens, while individual crops help the classifier identify them. Any extra image variations or category balancing are applied only to training examples.

## Slide 9: Proposed methods — 50 seconds

We’ll compare two approaches. The first uses RF-DETR to find each specimen and predict its category at the same time. The second uses RF-DETR just to find specimens. We then crop each specimen and pass it to Swin-Tiny, a separate classifier. This comparison helps us see whether identifying specimens separately works better than doing both tasks together. We’ll check whether the models find the right locations and assign the right categories, including categories with fewer examples. These are our proposed approaches; training and evaluation are the next steps.

## Slide 10: Conclusion — 25 seconds

The main idea is to move from finding pollen to identifying it. Next, we’ll prepare the specimen images, train the initial models, and look closely at their mistakes. The goal is to give experts a useful starting point for identification, so they can study past vegetation more efficiently. Thank you.

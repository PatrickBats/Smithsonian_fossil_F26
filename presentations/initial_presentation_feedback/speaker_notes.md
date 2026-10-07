# Speaker notes

Target: 4:30 speaking, with up to 30 seconds for transitions. The rubric specifies exactly five minutes; rehearse to approach five minutes without running over.

Presenter blocks: 1 → slides 1–2; 2 → slides 3–4; 3 → slides 5–6; 4 → slides 7–8; 5 → slides 9–10. Assign names within the team.

## Slide 1: Welcome — 10 seconds

Hi everyone. We’re the Rice D2K Smithsonian team. We’re using machine learning to help researchers identify fossil pollen.

## Slide 2: Background — 30 seconds

Our scientific question is: what grew in North America when the climate was warmer, about fifty million years ago? Fossil pollen gives researchers clues about the plants that lived there. But identifying thousands of tiny specimens by hand takes expert time. We want to help with that identification step so researchers can study more of the collection.

## Slide 3: The problem — 25 seconds

This image shows the gap we’re addressing. The previous team developed a detector to find specimens, like the one inside this box. But a location alone doesn’t tell researchers what kind of pollen it is. Our goal is to add that category identification, using details of the specimen’s shape and surface.

## Slide 4: Previous approaches — 25 seconds

These three studies give us our starting point. Punyasena and Martinsen locate specimens and then classify individual crops. Abbas Shaikh and colleagues developed a pipeline for detecting specimens across large, multifocal slides. We’ll build on whole-slide detection and compare two ways to add category identification.

## Slide 5: Microscopy data — 20 seconds

Each scan captures different focal depths, so different details become clear in different views. This example has twenty-five focal planes, and the full scan is about thirty gigabytes. We’ll extract smaller regions so we can work with individual specimens.

## Slide 6: Annotation inventory — 25 seconds

We have eighty-three image and annotation pairs. Our starting selection includes thirty-two priority categories and two thousand two hundred ninety annotations. These four categories illustrate the imbalance: some have hundreds of examples, while others have only a few dozen. That can make the less common categories harder to learn.

## Slide 7: Organizing the data — 30 seconds

Here’s how we turn the annotations into learning examples. First, we locate the marked specimen in the image. We read its expert label and use the supplied mapping to connect it to a target category. Then we extract a small image around it and check that it’s clear and properly positioned. The result is a specimen image paired with its category.

## Slide 8: Preparing examples — 30 seconds

Next, we mix up the microscope slides and divide them into training, validation, and testing groups. The model learns from training examples, validation helps us make adjustments, and testing checks how well it works on new slides. All examples from one slide stay together. We can also balance the training examples so the most common categories don’t dominate.

## Slide 9: Proposed methods — 50 seconds

We’ll compare two ways to do the job. In the first, one model finds each specimen and identifies its category at the same time. In the second, a detector finds the specimens, and a separate classifier identifies each crop. The question is whether giving identification its own model improves the results. We don’t know yet which will work better. We’ll compare them on the same held-out slides, checking both the locations and the categories, including less common categories.

## Slide 10: Conclusion — 25 seconds

Our intended result is a set of located, labeled specimens that experts can review. The aim is to reduce repetitive identification work and help researchers study past vegetation. Next, we’ll prepare the crops, train both approaches, and compare their mistakes. Thank you.

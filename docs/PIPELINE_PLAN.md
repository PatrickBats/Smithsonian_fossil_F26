# Project plan

For the October 1 priority data audit and October 7 storage correction, see [the dated update](F26_DATA_PROGRESS_2026-10-01.md).

Immediate work: [next steps after the September 18 meeting](NEXT_STEPS.md), using the corrected Fall_2026 dataset.

Build a pollen-classification pipeline and a simple results viewer.

1. **Use the verified Fall_2026 data:** the supplied archive reconciles with all sponsor counts (2,290 YES annotations across 32 categories). Verify that extraction uses these updated NDPA files and matching image versions on NOTS. The 933-record snapshot is superseded.
2. **Define broad categories first:** follow the September 18 agreement, preserving original names and finer categories for later experiments. The exact broad mapping remains to be defined; the original 32 YES / 5 MAYBE priorities are source guidance.
3. **Extract specimens:** read small image regions and focal planes, including annotations outside the old training rectangles. Check boxes against the images.
4. **Train and evaluate:** define a reproducible split that keeps related specimens/slides together. Compare a baseline using sharpest-plane and focus-stacked inputs.
5. **Run inference:** classify detected specimens and export predictions and annotations without overwriting the originals.
6. **Build the viewer:** browse specimens, switch focus planes, and inspect classifications.

Run training and inference on NOTS. Record configurations, data versions, metrics, and model checkpoints so results can be reproduced.

## Dates

| Date | Milestone |
| --- | --- |
| Sept. 28/30 | Five-minute project introduction and initial report |
| Oct. 19/21 | Software review |
| Oct. 26/28 | Midterm presentation and report |
| Nov. 2/4 | Midterm software |
| Nov. 30 / Dec. 2 | Final presentation |
| Week of Dec. 7 | Showcase |
| Dec. 13 | Final report and software |

Class day is still unassigned. Use the earlier date for planning.

## Decision log

Latest decisions: [September 21 context](CURRENT_CONTEXT.md). Start broad before finer distinctions; prioritize Platycarya platycarioides, Bombacacidites and Arecipites. September 18 guidance requests 50 random training grains for classes above 100, superseding the earlier approximately-60 request.

Still to confirm: cluster installation/image-version verification, broad-category mapping, tentative classes, sampling relative to groups and evaluation splits, performance targets, and input/export format. Multiclass YOLO/RF-DETR and a separate classifier are candidate approaches, not selected architectures. The detailed grading rubric has not been provided.

[Data access](NOTS_ACCESS.md) · [Category list](CATEGORIES.md) · [Detailed planning notes](background/PIPELINE_PLAN_FULL.md)

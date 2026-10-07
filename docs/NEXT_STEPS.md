# Next steps after the September 18 meeting

Updated September 21, 2026. This plan turns the [meeting decisions](../meeting%20transcriptions/2026-09-18_smithsonian_sponsor_meeting_summary.md) into proposed work. It does not launch training or settle the remaining scientific choices.

## Starting point

The annotation-count mismatch is resolved: the correct Fall_2026 files reproduce all 185 title rows and all 65 category totals. The initial YES inventory has **2,290 annotations in 32 supplied categories**, rather than the old 933-record snapshot. All 32 YES categories now have examples on multiple slides (at least three per category). This improves the prospects for evaluation; it does not establish sufficient variation, independent specimens, or an acceptable split for every class.

The sponsors' three named scientific priorities have the following verified coverage:

| Priority category | Annotations | Slides |
| --- | ---: | ---: |
| Arecipites sp. (palm pollen) | 81 | 20 |
| Bombacacidites sp. | 40 | 17 |
| Platycarya platycarioides | 56 | 6 |

Source: [current category inventory](../data/current/category_summary.csv). These are annotation records before crop quality checks or sampling. Fine-grained coverage and broad-category coverage must be reported separately.

## Work in order

| Step | Concrete work | Ready when |
| --- | --- | --- |
| 1. Fix the source paths | Use the verified Fall_2026 NDPA version and corresponding NDPI image for each slide. Preserve source hashes and a source manifest. Do not scan only annotations_F26: updated and unchanged files are stored separately on NOTS. | Every selected record resolves to the correct annotation bytes and readable image. |
| 2. Define the broad first task | Draft a table mapping supplied categories to broader training groups, retaining original title and fine category. Start from YES records; keep MAYBE, NO and untitled entries separate. | The team and sponsors agree on an explicit grouping, including which ecologically important distinctions remain separate. |
| 3. Extract and inspect specimens | Begin with a small inspection batch spanning priority classes, multiple slides, focal planes, boundaries and annotations outside historical rectangles. Check coordinate overlays, crop margins, focus, preservation and duplicate specimens. Then extract the accepted set. | The inspection examples locate the intended objects; every accepted crop has source coordinates and identity. Failures and exclusions have reasons. |
| 4. Freeze a fair evaluation | Review counts by broad group and slide; investigate shared sample/locality/preparation links. Keep all focal planes and augmented views of a specimen together. Reserve test data before tuning. Apply balancing to training only after recording the agreed policy. | A versioned list assigns each specimen to one split, with no prohibited overlap, recorded seed and a documented coverage report. |
| 5. Run a first baseline | Proposed first experiment: classify verified specimen crops with a transfer-learning baseline to assess the broad labels. Compare focus representations on the same split. Multiclass YOLO/RF-DETR remains a candidate alternative discussed at the meeting. | A reproducible run reports held-out validation results, class-level errors and examples for sponsor review. Choose subsequent experiments from that evidence. |
| 6. Make the results usable | Show the image, candidate labels/scores and uncertain cases in a simple interface. Agree on an export example and preserve original annotations. Integrate existing detector outputs after validating the crop classifier, or follow the agreed multiclass approach. | Sponsors can inspect a small end-to-end example without writing code; outputs retain the source specimen identity and coordinates. |

Steps 2 and a small extraction inspection can proceed alongside each other. Final sampling, class selection and full training depend on both being settled. A crop classifier is a recommendation for isolating classification quality, not an architecture already approved by the sponsors. A multiclass detector still predicts locations; incompletely annotated slide regions cannot automatically be treated as negative training examples.

## Decisions to settle before full training

- **Broad groups:** the meeting agreed to start broad and then investigate finer distinctions (00:19:54–00:20:08). Draft same-genus grouping candidates such as Momipites and Caryapollenites, but do not silently merge all similar-looking names or erase fine labels. The exact hierarchy was not specified. Keep the sponsors' named ecological priorities visible.
- **Balancing:** Ingrid requested 50 randomly selected training grains for categories above 100 (00:05:31–00:06:18), updating the earlier email's approximately 60. Clarify whether the threshold refers to source-category totals or training-pool counts after broad regrouping. Record the selected IDs and seed; never thin or resample evaluation data to improve performance. Do not cap every class at 50 by assumption.
- **Split:** choose proportions or grouped folds after the class-by-slide audit. Slide grouping is the minimum; related samples may require larger groups. No arbitrary split or minimum accuracy target is fixed by this plan.
- **Uncertainty and output:** candidate labels/scores are requested (00:23:10–00:24:02); thresholds, calibration, crop versus NDPI input and export format remain open. Do not describe raw model scores as guaranteed probabilities.
- **Baseline:** decide between the proposed crop classifier and the students' multiclass YOLO/RF-DETR proposal. Previous code is now accessible; see the [September 24 reuse review](PRIOR_CODE_REUSE.md). All four published trained checkpoints have been downloaded and passed file integrity checks; loading and runtime compatibility remain untested. Runtime compatibility and an appropriate label/negative-region audit are prerequisites for reuse.

## Evaluation and experiment records

Use macro-F1, balanced accuracy, per-class precision/recall and a confusion matrix. Report the three scientific priority categories explicitly, alongside all other included categories. Inspect errors for staining, preservation, orientation, focus and slide-specific patterns. Count unique specimens rather than augmented views. Use validation for model selection and retain the final test set for the final evaluation. Finishing an initial run does not establish scientific success; set numeric targets with sponsors once the baseline and available data have been assessed.

Run training and substantial preprocessing through Slurm on NOTS. Keep original data unchanged. Put derived crops, checkpoints, predictions and logs in separate team-readable runs under `/projects/dsci435/Smithsonian_F26/`. Track source versions, code commit, environment, mapping, split, seed, configuration, Slurm job ID, metrics, failures and compute usage. No GPU runtime budget is imposed. Git holds small inventories, code and reports, not raw slides or checkpoints.

## Next meeting and class deliverable

Suggested work through the next check-in: provide the reconciled inventory, a draft broad-category map, a small panel of verified specimen crops, and a proposed grouped evaluation/sampling policy. Assign owners within the team rather than treating the old introduction deck as a final task allocation.

For the September 28/30 initial class presentation, show the scientific question, corrected data, pipeline, risks and next experiment. Do not promise a trained result as a prerequisite for that presentation. The full course milestones remain in the [pipeline plan](PIPELINE_PLAN.md).

Ask the sponsors to review: the broad groups, good/difficult examples of the three priority types, handling of uncertain original identifications, the 50-grain policy, and an example desired output. Retrieve the two reference links shared in meeting chat; their URLs are absent from the transcript.

## What remains unbuilt

The complete specimen crop dataset, broad-group mapping, final split, model training and usable viewer remain to be implemented. Previous presentations are historical records. Follow [current context](CURRENT_CONTEXT.md) and [current data](../data/current/README.md) for the authoritative version.

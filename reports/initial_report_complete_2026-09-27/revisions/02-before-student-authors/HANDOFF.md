# Before submission

The report is complete as an initial proposal, with the following scientific decisions explicitly left open. They are not missing writing or claims of completed work.

1. Confirm the broad-category mapping with the sponsors. The source inventory has 32 YES categories, but the final model class count is not established. Keep the three named priority categories visible.
2. Confirm the 50-grain training-sampling request: whether the >100 threshold is applied before or after regrouping and before or after the evaluation split.
3. Agree on uncertain/out-of-scope labels and on exhaustively reviewed detector-training/evaluation regions. Sponsor NO labels and unannotated regions are not automatically background.
4. Review sample/preparation links between slides, historical checkpoint training exposure, and class coverage before freezing split proportions or grouped folds.
5. Inspect extraction, focal compression, and circle-to-box conventions. Confirm tile size, overlap, crop margin, image resolution, detector variant/checkpoint and training settings before running the main comparison.
6. Agree on numeric performance goals, unfamiliar-specimen handling, prediction score/ranking rules, and viewer input/export formats. The report does not promise a calibrated confidence threshold.
7. Confirm the team's Monday/Wednesday course schedule and any syllabus changes. Dates are copied from the supplied syllabus, not a live course calendar.
8. The title page retains Patrick Batsell from the supplied draft. Confirm the final team author list before submission; an existing team introduction is not assumed to establish report authorship.
9. Check whether any later sponsor decisions supersede the September 18 meeting and September 21 inventory. The supplied draft is treated as the proposed two-model comparison; it does not establish sponsor approval of a final architecture.

## Editorial choices

- Title-page mentors updated from Patrick's September 27 instruction: faculty mentor Dr. Arko Barman and PhD mentor Nhi Le. Sponsors are Ingrid Romero and Scott Wing; Scott's surname is confirmed in the supplied project proposal and team records. The pre-edit report is preserved in `revisions/01-before-mentor-names/`.
- The model comparison, separate expert-crop evaluation, and original 224×224 crop proposal are retained. Repetition was reduced, tense was corrected, and incomplete-label/checkpoint-leakage caveats were integrated where they affect validity.
- The previous detection paper is cited as **Shaikh et al.**, correcting the given-name citation “Abbas et al.”
- The 64-target YOLO pilot is presented as a completed diagnostic, not a new RF-DETR result, a classification experiment, or an independent generalization estimate.
- The report uses 83 verified Fall image/annotation pairs; the prior paper's 82 annotated slides and 847-image collection are explicitly historical. The proposal's larger collection estimates are not reported as the verified working dataset.
- No unverified claim of species-level labels, complete-slide annotations, accepted specimen crops, or completed classification training is made.
- Original input PDFs, historical notes and experiment records remain unchanged. An exact copy of the supplied draft and rubric is in `inputs/`.

## Reference verification

Checked September 27, 2026. Technical summaries use primary publications; general architecture results are not treated as fossil-specific evidence.

| Reference | Evidence inspected |
| --- | --- |
| Shaikh et al., 2026 | Supplied manuscript; author/title/version verified at [arXiv](https://arxiv.org/abs/2609.05323). Historical metrics are attributed to that study. |
| Romero et al., 2020 | [Original article in PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7668113/), including abstract and model descriptions; bibliographic metadata cross-checked through Europe PMC. |
| Punyasena et al., 2022 | [Publisher full text](https://besjournals.onlinelibrary.wiley.com/doi/10.1111/2041-210X.13917), abstract and methods, including two-stage workflow and uneven taxon counts. |
| Robinson et al., 2026 | [Authors' RF-DETR paper record](https://arxiv.org/abs/2511.09554), version 2; author list, title, abstract and ICLR status. |
| Liu et al., 2021 | [Authors' Swin paper record](https://arxiv.org/abs/2103.14030), abstract and metadata; the supplied draft also identifies the ICCV citation. |
| Internal sources | Proposal, September 18 meeting, verified current inventories, September 24 pilot records, and supplied syllabus. Paths and hashes are in the manifests. |

The literature section is a focused background review for this initial report, not a claim to be an exhaustive survey.

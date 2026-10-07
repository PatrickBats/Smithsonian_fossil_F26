# Current project context — September 21, 2026

## October 7 storage clarification

Yunfan relayed Dr. Barman's reply: “projects is not for data storage, rhf is for data storage.” Raw and processed image datasets and row-level split/annotation manifests should be stored under `/rhf/allocations/dsci435/`, not `/projects/dsci435/Smithsonian_F26/`. The exact new project-specific RHF subdirectory was not specified in the quoted reply, and the group allocation was last observed at its hard limit. See the [priority data update](F26_DATA_PROGRESS_2026-10-01.md) for the misplaced earlier outputs and current code guards. This does not change the model results below.

## October 7 specimen-split diagnostic

Patrick authorized a [random specimen-level training/validation diagnostic](../reports/swin_specimen_split_2026-10-07/README.md), preserving the original test set. The new run starts from ImageNet weights and permits shared training/validation slides; it does not replace the grouped baseline. The 40-epoch diagnostic completed in 490 seconds; selected epoch 29 achieved 66.28% validation accuracy, macro-F1 0.6114 and balanced accuracy 60.71%. The test set remains reserved. Longer training was discussed but not combined with this experiment because the existing curves already indicate overfitting.

## October 7 baseline category decision

A subsequent [Tenengrad pilot](../reports/tenengrad_pilot_2026-10-07/README.md) completed on eight training specimens across four slides: four selected nonzero planes and looked visibly sharper, four retained plane zero. All zero-plane images matched the baseline. Patrick subsequently authorized the [full Tenengrad export and matched Swin comparison](../reports/tenengrad_full_2026-10-07/README.md). All 2,283 best-plane crops passed verification and the matched 40-epoch classifier run completed. Selected epoch 32 achieved validation accuracy 38.04%, macro-F1 0.3392, and balanced accuracy 41.74%. No test inference is enabled.

The first ordinary-sampling Swin-Tiny baseline [completed 40 epochs](../reports/swin_baseline_2026-10-07/README.md). Epoch 18 was selected by validation macro-F1: 0.2332, with 31.99% validation accuracy and 29.34% balanced accuracy. Test inference remains disabled. The run succeeded technically, but identification quality is limited; late-epoch behavior is consistent with overfitting. Balanced sampling has not run. The alternate-focus comparison has completed, improving the selected validation macro-F1 from 0.2332 to 0.3392 in a single-seed comparison.

Patrick confirmed using the 32 sponsor YES categories unchanged for the first baseline. The [category map and proposed split protocol](BASELINE_DATA_PROTOCOL.md) record the shared vocabulary, audited draft 1,605/347/331 split, and sparse-category limitations. Patrick subsequently approved this split and ordinary sampling for the first Swin-Tiny baseline. See [training workflow](../scripts/classification/README.md); keep test inference disabled. The initial run uses a user-owned workstation GPU because of the NOTS output-storage quota, with source slides retained on NOTS.

## October 2 meeting added October 7

See the [meeting summary](../meeting%20transcriptions/2026-10-02_smithsonian_sponsor_meeting_summary.md). Sponsors emphasized inspecting localization, crop/image quality, and category mistakes separately for both proposed models; specimen crop export matters for museum use. The meeting does not finalize the experimental protocol or assign named owners to the two model groups. Patrick subsequently confirmed model ownership on October 7: Patrick, Yun-Ying, and Alan will work on Swin-Tiny classification (the classifier side of Model 2); Yeonju and Bob will work on the direct multiclass RF-DETR approach (Model 1). Ownership of the single-class detector integration for Model 2 was not separately specified. Both groups should use the same agreed data split and category mapping. The earlier dated status below is historical and does not incorporate the October 1 crop-preparation PR.

**Correct dataset: Fall_2026.zip, supplied by Patrick on September 21.** Use [data/current](../data/current/README.md) and the [updated source annotations](sources/data/Fall_2026/). Earlier 933-record and provisional-alias inventories are archived and must not drive new training data preparation.

## Dataset mismatch resolved for the supplied package

The archive contains 83 NDPA files and one NDPI image. All **11,275 named annotations**, **185 annotation-title counts**, and **65 category totals** match Ingrid’s tables exactly after trimming three trailing spaces. All **32 YES categories** are represented, with **2,290 YES records**. No inferred biological aliases are needed. There are also 114 MAYBE and 8,871 NO records plus 227 untitled annotations excluded from category counts.

The prior low counts and apparently absent classes came from the older/incomplete annotation set we audited, not a shortage established in the intended Fall dataset. Reassess category coverage using the new by-slide inventory rather than carrying forward old conclusions.

**NOTS verified:** all 83 source NDPA files match the uploaded archive byte-for-byte. There are 48 updated files in `annotations_F26` and 35 unchanged exact matches in `raw`. Use [cluster_source_paths.csv](../data/current/cluster_source_paths.csv) instead of scanning only the update folder. All 83 corresponding images passed header and 32×32 center-region read checks. This is not a full-slide/focal-stack corruption check or a validation of specimen crops. See [verification details](../data/current/cluster_verification.json). No shared files were modified.

## September 18 direction

- **Start broad, then go finer.** Create an explicit broad-category mapping after reviewing the updated inventory; preserve original titles and the supplied finer categories. The exact grouping is not finalized.
- **Scientific priorities:** Platycarya platycarioides, Bombacacidites and Arecipites. Do not discard these solely because the old inventory appeared sparse.
- **Initial balancing request:** randomly select 50 training grains for categories above 100. This updates the earlier approximately-60 email request; decide how it applies after broad grouping and reserve evaluation data separately.
- **Outputs:** alternative labels/scores and uncertain cases for expert review through a simple interface requiring no coding. Input/export format, thresholds and score calibration remain open.
- Multiclass YOLO/RF-DETR and a detector plus separate classifier were discussed as alternatives. No architecture, numeric success target, split or trained model is finalized.

## Next work

Follow the [ordered next-step plan](NEXT_STEPS.md) for deliverables, acceptance checks and decisions before training.

Use the correct updated NDPA version with the corresponding images, inspect crops and focal planes including annotations outside old rectangles, review class-by-slide coverage, define the broad mapping and grouped experimental protocol, then train. This older next-work section is superseded by the October 7 baseline protocol and execution records above: the zero-plane crop export and adopted split are verified, the first classifier run is complete, and a best-plane comparison is in progress.

Evidence: [September 18 meeting summary](../meeting%20transcriptions/2026-09-18_smithsonian_sponsor_meeting_summary.md), [audit manifest](../data/current/audit_manifest.json), [title reconciliation](../data/current/title_reconciliation.csv), [category summary](../data/current/category_summary.csv). The two external references mentioned in meeting chat remain unavailable. See the [pipeline plan](PIPELINE_PLAN.md).

## Previous code now accessible — September 24

The Spring 2026 repository has been cloned and inspected at commit `1b62b68a0d95178e6275ef55c38ee4765317b334`. See [reuse review](PRIOR_CODE_REUSE.md). All four published detector checkpoints have now been downloaded and their sizes/ZIP integrity verified; see [artifact manifest](PRIOR_ARTIFACTS.json). The two YOLO checkpoints now pass inference on a 64-target Fall pilot; RF-DETR runtime compatibility remains untested. The old rectangle coverage, adjacent-annotation assumption, CSV schema and class-ID handling need attention before reuse.

## Detection-first execution — September 24

The user authorized validating the existing detector before classification. A fixed 64-target, 32-category diagnostic using both frozen YOLO checkpoints completed on NOTS as Slurm array job 1612309: best-plane recovered 54/64 and focus-stack 51/64 at the fixed confidence/overlap thresholds. See [protocol and run status](DETECTION_PILOT.md). It is annotation-centered detection recovery, not independent whole-slide generalization or classifier training.

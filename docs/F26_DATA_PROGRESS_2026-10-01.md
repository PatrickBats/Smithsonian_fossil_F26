# Fall 2026 priority data work: status on October 1, 2026

This is a dated update to the [September 14 pipeline plan](PIPELINE_PLAN.md), which remains a record of what was known then. The work below used sponsor-provided `Fall_2026.zip`, read-only checks of NOTS source files, and local validation scripts. It concerns **priority (`YES`) pollen classification only**. No model training or augmentation has started, and no whole-slide detection ground truth is claimed.

## Source and annotation audit

| Finding | Result and limitation |
| --- | --- |
| Sponsor archive | `Fall_2026.zip` contains 83 `.ndpi.ndpa` files and one `.ndpi` image. The ZIP manifest was compared with NOTS on September 30; these files were present there. The 83 F26 annotations are split between `annotations_F26/` (48) and `raw/Images_with_annotations_for_CNN_training/` (35). Historical same-name NDPA copies can differ from F26 copies, so filename alone is insufficient to select an annotation version. |
| Annotation inventory | The 83 sponsor NDPA files contain 11,502 XML view states. Titles/categories reconcile to the sponsor's supplied tables. All view-state `z` values are zero; the files provide specimen x/y position and circle radius, not separate contours for each focal plane. The expert category applies to the specimen across its corresponding focal images. |
| Priority filter | 2,290 raw priority circles become **2,283 temporary candidates** in all 32 `YES` categories. Five copies of same-category, same-geometry alias records are excluded; both records at one geometry with conflicting priority categories are excluded. These seven exclusions are reversible and retain source IDs in the private working manifests. Priority-versus-nonpriority overlaps are outside the current scope. |
| Image pairing | A sampled overlay check found no gross image/annotation offset in the examined examples. It cannot certify every pairing or the experts' taxonomy. Punctuation-only filename aliases are treated as the same image group for counting; L/R scans remain distinct images but share a conservative split group where their accession matches. |

The exact row-level manifests, source images, annotations, and image crops remain outside this public repository. The audit and selection code is in [`scripts/f26/`](../scripts/f26/). It requires the sponsor files and a verified NOTS file-location manifest supplied separately on the authorized project storage.

## Review-draft split and extraction

The current split is a **review draft**, not a frozen evaluation protocol. Conservative accession grouping keeps possible related scans together: 57 groups total, with train **40 groups / 1,605 records**, validation **9 / 347**, and test **8 / 331**. Every priority category appears in test, but `Retipollenites sp.` has only two test records and none in validation. Seven categories have fewer than three validation records and five have fewer than three test records. Per-class held-out estimates need an explicit support policy before reporting.

The crop exporter produced a verified **2D, focal-plane-0** local baseline: 2,283 RGB PNGs at native resolution, train 1,605 / validation 347 / test 331. Each crop is centered on its NDPA circle, at least 1.35 times the diameter with a 256-pixel minimum, and contains no augmentation or overlay. All 2,283 PNGs, paths, dimensions, provenance fields, and SHA-256 hashes passed the independent local verifier. The complete crop payload is about 299 MB. This is **not a complete multifocal dataset**.

The first NOTS export stopped at 619 staged PNGs after `Disk quota exceeded`; all 619 were later checked against the completed local copy and matched by SHA-256. The remote `image_staging/` is incomplete; there is **no finished team-accessible NOTS image split**. Do not use that staging directory as a dataset.

## Multifocal findings and limits

- Historical Spring 2026 HDF5 tiles fully cover only **1,331 of 2,283** F26 priority crop regions. The other **952** lack full tile coverage, so direct source-NDPI reads are needed for complete F26 object-crop extraction. The additional D1555 slide has no matching historical HDF5.
- Direct NDPI reads produced three **sample** full focal stacks for annotated priority objects: 21, 27, and 25 focal planes on three different slides. Their zero-offset plane matched the corresponding verified 2D crop pixel for pixel; nonzero planes contain different pixels. A contact sheet showed the same specimen in the selected focal views. This checks a method and sampled alignment, not all 2,283 crops or expert-label correctness.
- A separate automated 64×64-pixel read completed on 25 of the 75 priority source slides; all 25 read and their zero-offset samples matched OpenSlide. The remaining per-slide diagnostic run was stopped because it was unnecessary before batch extraction. **No full multifocal export exists.**
- “Complete focal planes” still needs a precise output definition: all focal planes for every priority-object crop, or full-frame planes for every entire slide. The pilot implements the object-crop interpretation. Source NDPI files already contain the original whole-slide stacks.

## NOTS storage blocker and handling

Professor Barman's instructions put the complete persistent dataset under `/rhf/allocations/dsci435/`, ask the team to consult him before placing other material there, and put experimental outputs under `/projects/dsci435/Smithsonian_F26/`. They identify `/rhf/allocations/dsci435/smithsonian_full_sp26/annotations_F26/` for the supplied F26 annotations. They do **not** designate a separate F26 NDPI image folder or a derived multifocal-output subdirectory. Do not overwrite historical NDPI/NDPA files.

On October 1, the shared `dsci435` group quota check reported `/projects` at **100,000 MB used / 100,000 MB limit** and `/rhf/allocations` at **16,384 GB used / 16,384 GB hard limit**. The filesystem's overall free capacity does not remove these group limits. Thus the complete multifocal output has **not** been written to either NOTS storage area. Existing split metadata and partial 2D staging are experiment outputs in the professor-designated `/projects/dsci435/Smithsonian_F26/` tree; no previously created file was identified as misplaced or deleted. The original source NDPI/NDPA and all other NOTS directories were left untouched.

**Before a shared multifocal export:** resolve the crop-versus-full-frame scope, restore group storage capacity, and confirm the destination with Professor Barman if new material is to enter the persistent allocation. Keep the split draft and its rare-class evaluation limitations under review. Do not treat the three pilots, the 25-slide diagnostic, or the local 2D baseline as completion of that export.

## Reproduction and provenance

[`scripts/f26/README.md`](../scripts/f26/README.md) lists the exact private inputs, script sequence, dependencies, and output guards. The local audit retained SHA-256 of the 2,283-row priority candidate manifest (`16db803da0e9c2e780e52d0565f2194f7600f93b49591f25ff55f10179312bf9`) and the seven-row exclusion manifest (`7c34557ad6f515a52ad2e90f5685a21b258891ec9622c43669097e38896f25ab`). The verified 2D crop manifest SHA-256 is `b4d803ca764f9941de38014bc5a67eb797f400a595033118c32512f5701e1373`. These identify the checked local working artifacts; their row-level contents are not included in this PR.

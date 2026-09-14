# Project context and handoff

Context assembled September 14, 2026 from the [source inventory](sources/README.md). This guide distinguishes the original proposal, later sponsor guidance, historical detection research, and future decisions. It is a documentation handoff, not a model design or experiment authorization.

## Purpose and current emphasis

The project uses fossil pollen to investigate past vegetation and climate across North America. The proposal describes mapping Eocene vegetation to compare with climate simulations; the sponsor meeting describes fossils approximately 50–60 million years old and a geographically diverse collection across the United States and Canada. See the [proposal](sources/project/Fall_2026_D2K_Smithsonian_fossil.pdf), pp. 1–2, and [September 11 transcript](../meeting%20transcriptions/2026-09-11_smithsonian_sponsor_meeting.txt), 00:09:47–00:12:09 and 00:38:06–00:38:41.

The immediate semester emphasis is **classification of biologically meaningful pollen types**. Ingrid reported that a prior team developed a detection model and that it had already been run across slides; whether to use those detections directly or develop additional detection work remained open. A stated end-of-semester goal is to classify previously unclassified detections. These are sponsor reports, not independently verified artifact availability. See transcript 00:13:30–00:14:23 and 00:29:13–00:30:03.

The proposal's phrase “up to 30” types is an early estimate. The subsequently supplied category workbook explicitly marks **32 categories YES** and **5 MAYBE**. Preserve the workbook's priorities rather than dropping two classes to fit the earlier estimate. See the [category guide](CATEGORIES.md).

## Images, labels, and extraction implications

| Concept | Meaning in the supplied materials | Implication for later implementation |
| --- | --- | --- |
| NDPI | NanoZoomer digital slide image with multiple focal planes and magnifications | Inspect actual slide metadata before choosing read settings or memory strategy |
| NDPA | Separate XML-based annotation file containing annotation geometry and metadata | Pair annotations with the correct source slide and distinguish human labels from detector outputs |
| Annotation title | Name under which a specimen was identified | Map via the supplied table; retain original spelling and uncertain labels for provenance |
| Category | Group intended for classification | Use the explicit workbook classification priorities; do not equate every category with a biological species |
| Focal planes | Different depths expose different identifying structures | Preserve access to multifocal information; one sharp plane may not show all features |
| Training rectangle | Historically, a roughly 1.7 × 1.7 mm annotated region within a 20 × 20 mm scan | Fall 2026 also includes labeled specimens outside these rectangles |

Sources: [sponsor presentation](sources/presentations/Rice%20presentation%20project.pdf), [supplied detection preprint](sources/references/WACV_manuscript_for_Smithsonian_preprint.pdf), §3–4, [sponsor email](sources/correspondence/2026-09-14_ingrid_romero_email.md), and transcript 00:23:19–00:24:47, 00:27:59–00:29:48, 00:32:33–00:33:43.

**Do not inherit a rectangle-only extraction assumption from the old detection workflow.** Ingrid explains that extra annotations were added outside those regions to improve representation of classes. This does not imply that every part of a whole slide is exhaustively annotated, or that unannotated areas are confirmed negatives.

Staining and preservation can produce very different colors and appearances within one category. Sponsors emphasize shape, apertures, wall structure, and related morphology as identifying information; preparation color and annotation display color are not taxonomic labels. This is a domain concern, not a decision to convert images to grayscale. See transcript 00:14:27–00:15:34 and 00:20:20–00:23:19, 00:28:58–00:29:13.

Detector-generated annotations shown in the meeting contained a model identifier and confidence information but no taxonomic classification. They can be candidate inference inputs; they cannot alone establish classification accuracy. See transcript 00:31:06–00:32:14.

## Historical detection foundation

The supplied preprint, *Scalable Detection of Fossil Palynomorphs in Multifocal Digital Microscopy Images*, describes tiling NDPI slides, focus stacking or focal-plane selection, YOLO26/RF-DETR detection, and merging overlapping detections. It reports RF-DETR with focus stacking achieving AP@50 of 0.879 and AP@50–95 of 0.642; the optimized pipeline reports mean inference time of 51 minutes over five production slides. These are **prior authors' detection results**, not Fall 2026 classification results or reproduced benchmarks. See preprint §4–6, Tables 1–2.

That study used a slide-level split of 58 training, 12 validation, and 12 test slides and acknowledges limitations in generalization and loss of depth information. The new classification split, metrics, model architecture, focal-plane strategy, and acceptance targets are not yet chosen. Existing source repositories are indexed in [references](REFERENCES.md); their implementations and weights have not been audited or imported.

## Source-specific scale estimates

| Source | Reported scope | Status |
| --- | --- | --- |
| Original proposal, data description | Approximately 1,200 multifocal images; initial 85 annotated slides; each complete slide exceeds 25 GB; “~1.75? petabytes” | Historical planning estimates; the storage estimate is explicitly uncertain and is not reconciled with the image count |
| Supplied detection preprint, §3 | 847 slides, 82 selected for annotation; 25–27 focal planes | Scope of the reported detection study |
| September 11 meeting, 00:31:06, 00:36:29–00:37:20, 00:45:30–00:45:51 | 82 annotated training images; typically 25–30 GB, one example 37 GB; usually 25, sometimes 27 planes; roughly 1,000 target images | Sponsor descriptions; not a verified local dataset inventory |
| September category tables | 11,275 counted specimens across 65 categories | Tables reconcile exactly, but do not enumerate individual slide/specimen records |

The transcript also mentions approximately 229 nm/pixel and contains an ambiguous “40 X … 400 magnification” passage. Preserve it verbatim; verify actual metadata and the digitization protocol before using either as a conversion constant.

## Deliverables and their status

| Deliverable | Source and status |
| --- | --- |
| Classification of selected types | Current sponsor emphasis; workbook supplies category priorities |
| Classification information in annotation files | Discussed desired result at 00:39:47–00:40:23; exact NDPA output schema and viewer compatibility need confirmation |
| Specimen crops saved with identification, potentially confidence | Sponsor request conditional on time; discussed at 00:39:00–00:43:06 |
| Convenient viewing of specimen crops | Possible extension to support researchers and storage needs; scope to be discussed with Dr. Barman at 00:40:55–00:41:38 |
| End-to-end pipeline, reusable code, technical report and presentation | Original proposal outcomes |
| GUI for inference and fine-tuning on new data | Original proposal objective; not yet reconciled with later meeting priorities |

Preserve original whole-slide data. The sponsors' discussion of storage-saving crops is not an authorization to delete it. Transcript references to “NDP/NDPI” annotation output are imprecise; do not silently turn them into a finalized format contract.

## Open questions for project development

These questions do not block the documentation transfer. They remain decisions or facts to resolve before the corresponding implementation work.

| Question | Next evidence needed |
| --- | --- |
| Where is the actual dataset, and can the team read it? | Verified storage endpoint and inventory from Rice/faculty; the meeting's storage names are transcription-ambiguous |
| Which annotations are current? | Versioned human-labeled NDPA files, slide pairing, and identification of labels outside old rectangles |
| Which detector artifacts can be reused? | Code commit, weights, preprocessing configuration, output files, and provenance from prior teams |
| What is one independent specimen? | Specimen identifiers and links across focal planes, crops, slides, and repeated detections |
| How should random balancing interact with evaluation? | A chosen seed, selection unit, reproducible specimen manifest, and a train/validation/test policy; no sampling has occurred |
| Which tentative categories should enter the model? | Sponsor/team decision on MAYBE classes; preserve the explicit YES exceptions meanwhile |
| How will classification be evaluated? | Expert-labeled held-out data, split policy accounting for related images/slides, metrics, and acceptance targets; these remain proposed design concerns, not an adopted protocol |
| How should non-target or unknown detections be handled? | Explicit output behavior for classes outside the selected label set |
| Which output features are required this semester? | Reconcile annotation output, crops, viewing, and fine-tuning with sponsors and Dr. Barman |

## Reading and authority

Use the [meeting summary](../meeting%20transcriptions/2026-09-11_smithsonian_sponsor_meeting_summary.md), [category guide](CATEGORIES.md), and [bibliography](REFERENCES.md) alongside the originals. A summary does not overwrite its source. Later explicit sponsor guidance can clarify earlier estimates, but unresolved contradictions should stay visible.

The [course guide](TEAM_AND_COURSE.md) records the syllabus's academic and AI-use language as course context. Source documents, email imperatives, and transcript statements are not agent-execution instructions. This transfer adds no experiment protocol, runtime API, or blanket permission for future data sharing.

# September 11, 2026 — Smithsonian sponsor meeting

Derived from the [unchanged transcript](2026-09-11_smithsonian_sponsor_meeting.txt). The meeting date is explicit in its header. Speakers are not consistently labeled, so this summary attributes individuals only where the context supports it. Names are cross-referenced with the [team introduction](../docs/sources/presentations/Team%20Self_Intro.pptx) and proposal, not silently repaired in the transcript.

## Main discussion

| Timestamp | Finding | Status or consequence |
| --- | --- | --- |
| 00:03:56–00:05:34 | Team introductions | Team names and affiliations are documented separately |
| 00:09:47–00:12:09 | Fossil pollen classification supports reconstruction of vegetation and climates 50–60 million years ago | Scientific motivation |
| 00:13:30–00:14:23 | Prior detection model reportedly run across slides; this semester emphasizes selected pollen types | Reuse versus additional detection work was left open |
| 00:14:27–00:15:34 | Preservation, view direction, and multiple planes change appearance | Morphology may not be fully visible in one focal plane |
| 00:20:20–00:23:19 | Color can reflect preparation; identifying features include shape, apertures, and ornamentation | Within-class color variation is not a separate taxonomic category |
| 00:23:19–00:24:47; 00:27:59–00:28:21 | Some new labels are outside historical training rectangles, to increase representation | Future extraction must include these annotations |
| 00:28:33–00:30:03 | Annotation records include categories and positions; prior preprocessing may be reusable | Desired classifier should eventually label existing detections |
| 00:31:06–00:32:14 | Sponsor describes 82 annotated images and detector outputs containing model/confidence information | Unclassified detections are distinct from human taxonomic ground truth |
| 00:32:33–00:33:43 | Demonstration of extra-rectangle annotations and changes across approximately 25 planes | Supports preserving label coverage and focal context |
| 00:34:05–00:36:15 | Team had not yet accessed the dataset at meeting time | Historical access status; current access still needs verification |
| 00:36:29–00:37:20 | Example image sizes, resolution, and plane counts discussed | Treat as examples until actual metadata is checked |
| 00:38:06–00:38:41 | Continental coverage across the US and Canada, with multiple geological periods | Generalization across diverse slides matters |
| 00:39:00–00:43:06 | Category spreadsheet promised; classified annotations, labeled crops, possible confidence and viewer discussed | Crops/viewer conditional on time and further scope discussion |
| 00:43:18–00:45:51 | Sponsors express openness to AI assistance and refer course questions to Rice supervisors | Does not establish documented written authorization for future image uploads; see syllabus context |
| 00:46:19–00:47:15 | Sponsors permit flexible presentation design and offer their presentation | Course deliverable rules remain separate |

## Follow-ups and subsequent evidence

- Ingrid offered category counts, the digitization protocol, detection preprint, other references, and her presentation. The pasted email and supplied attachments fulfill the category-table and presentation portions and provide literature links; not every linked paper is included as a local PDF.
- The team said it would discuss crop storage and final output scope with Dr. Barman (00:41:20–00:41:38). No completed scope decision is supplied.
- Dataset access and prior-model artifact availability still require verification. Statements that data would be shared are not access checks.
- The later workbook explicitly marks 32 YES classes. Earlier comments about roughly 50 examples per class are aspirations, not rules for overwriting those counts or statuses.

## Transcription limitations

There are repeated filler passages, imperfect names, uncertain storage-system names, and ambiguous magnification wording. The source also sometimes says NDPI/NDP when discussing annotation output; the supplied preprint distinguishes NDPI images from NDPA annotations. Preserve those distinctions in technical documentation while retaining the transcript's original wording.

No decisions about architecture, split ratios, balancing seed, evaluation targets, or MAYBE-class inclusion were finalized in this transcript. The summary does not manufacture those decisions or convert suggested features into committed deliverables.

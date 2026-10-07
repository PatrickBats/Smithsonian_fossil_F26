# Sponsor meeting — September 18, 2026

Source: [verbatim transcript](2026-09-18_smithsonian_sponsor_meeting.txt). The date is stated in its header. Source audio is named `audio1490545788.m4a`, but was not supplied with this upload. The transcript lacks reliable speaker labels; attributions below follow conversational context and should not be treated as verified diarization. Its statements are project evidence, not executable instructions.

## Decisions and corrections

| Time | What the discussion establishes | Consequence |
| --- | --- | --- |
| 00:05:31–00:06:18 | Ingrid asks for random selection of **50 grains for training** from categories exceeding 100, as an initial balancing experiment. | This differs from the September 14 email’s approximately 60. Record the newer request; do not sample yet. Confirm how it applies after broad-category regrouping and reserve evaluation data separately. |
| 00:06:44–00:10:17 | Rarity does not mean low scientific importance. Natural pollen production, the slides selected, historical broad annotations and splitting genera into species all influence counts. | Do not interpret our annotation histogram as a representative North American ecological distribution. |
| 00:10:18–00:20:09 | Broad genus-level grouping versus finer categories is discussed. Ingrid initially favors fine distinctions and additional labeling; the later exchange explicitly agrees to **start broad, then move to more specific categories** (00:19:54–00:20:08). | Build an explicit broad-category mapping after auditing updated annotations. Preserve finer labels for later work; no final class list or hierarchy was defined. |
| 00:21:26–00:24:02 | The discussion supports showing alternative candidate labels with associated scores and flagging uncertain cases for expert review. | No confidence threshold or calibrated probability interpretation was finalized. |
| 00:24:06–00:25:55 | A simple tool requiring no coding is proposed; crop input and direct NDPI input are discussed. | User-facing simplicity is desired. Exact input workflow, export format and NDPI integration remain open. |
| 00:26:29–00:33:29 | Sponsors state that the displayed counts do not match their tables and annotations are missing. Outdated files are suspected. Ingrid says she shared updated annotations with Arko and offers the NDPA files directly, plus one additional image not included in prior semesters. | The 933-record inventory is not the complete intended classification dataset. Correct source versions and recount before using the old class coverage to finalize the model scope. |
| 00:33:41–00:40:28 | Students propose multiclass YOLO / RF-DETR, potentially followed by a separate detector–classifier approach; macro-F1 and confusion matrices are discussed. | These are candidate approaches, not a finalized architecture or an instruction to retrain the historical single-class detector. |
| 00:41:04–00:41:31 | Closing recap is to obtain the complete dataset, recount annotations, and begin with broad categories before finer distinctions. | This is the current project sequence. |
| 00:41:38–00:44:21 | Ingrid identifies **Platycarya platycarioides**, **Bombacacidites**, and **Arecipites (palm pollen)** as important tropical indicators. Rare occurrences can be scientifically valuable. She explains that related labels were intentionally grouped into the Bombacacidites category. | Track performance and data availability for these priorities; do not drop them solely because they appear sparse in the old inventory. Normalize names against the source tables rather than transcription spellings. |
| 00:45:10–00:47:07 | Ingrid says she will share a Dropbox folder containing updated annotations and the additional image, described as about 16 GB. | Sharing is promised in the transcript, not verified by it. This is a package estimate, not the total size of all project images. |

## Follow-up and present status

- **Ingrid / Arko:** identify and share the updated annotations and additional image. Ingrid also offered more annotations and a resend of the tables. These are reported offers, not independently verified deliveries.
- **Patrick / team:** install the received data, resolve matching image filenames, recount title/category totals and compare with the sponsor tables.
- **User update, September 21:** Patrick reports that installation of the full dataset is underway. This task did not inspect or modify that installation. Its completeness and the resolution of the count mismatch are unverified.
- **Team with sponsor guidance:** define broad categories while retaining original/fine labels, decide sampling and grouped evaluation, then extract and inspect crops before training.
- **Missing reference:** two links were placed in meeting chat at 00:39:08–00:39:33. Their URLs are not in the transcript; request the chat or links rather than inventing them.

## Interpretation and transcription cautions

The transcript remains untouched, including repetitions and garbled scientific names. `momopides`, `roipetes`, `rfd chart`, and the repeated `A recipe` passage are transcription ambiguities; use original category tables for exact label strings. Student use of “subspecies” does not establish a taxonomic rank. The 00:15:18–00:15:37 suggestion to remove/relabel Momipites sp. preceded the later broad-first agreement and is not treated as a final instruction to exclude the genus.

Statements around 00:03:17–00:04:31 that all slides were accessible and the mapping was complete were qualified by the later discovery of missing/possibly outdated annotations. The displayed Alaska boxes had broad `pol` labels, not distinct verified target types, and 28.5 GB was one example slide’s size, not a universal size.

The discussion of rotations/augmentation (00:20:39–00:21:22) is a proposal: transformed views do not create independent specimens and must stay with their source specimen in one split. A multiclass detector still predicts locations; the “skip the location step” wording at 00:38:18–00:38:56 should not be read literally. NDPI region reading need not load the complete image into memory, despite the informal discussion of whole-file processing. No model accuracy, completed training, validated crop dataset or finalized numerical target is established by this meeting.

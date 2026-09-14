# Smithsonian Fossil Pollen — Fall 2026

Rice D2K capstone with the Smithsonian National Museum of Natural History. The project focuses on classifying fossil pollen from multifocal microscope images to help reconstruct North American vegetation approximately 50–60 million years ago and evaluate understanding of warm climates.

**Status as of September 14, 2026:** this repository contains the initial project context transfer, original source documents, category inventory, and sponsor meeting record. No image dataset, model implementation, weights, or new experimental results have been imported. GitHub access was verified; dataset access and inventory have not been verified.

## Start here

| Resource | What it contains |
| --- | --- |
| [Project context](docs/PROJECT_CONTEXT.md) | Current objectives, image/annotation concepts, historical work, deliverables, and unresolved decisions |
| [Category guide](docs/CATEGORIES.md) | All 65 categories, training priorities, reconciled counts, and sponsor sampling guidance |
| [Meeting records](meeting%20transcriptions/README.md) | Original September 11 transcript and timestamped summary |
| [References](docs/REFERENCES.md) | Sponsor reading list, supplied preprint summary, and prior-semester repositories |
| [Team and course context](docs/TEAM_AND_COURSE.md) | Team, draft presentation responsibilities, and syllabus milestones |
| [Source inventory](docs/sources/README.md) | Original files, provenance conventions, and SHA-256 manifest |
| [Transfer validation](docs/TRANSFER_VALIDATION.md) | Checks performed on this documentation transfer |

## Key facts for the next contributor

- The tables contain **11,275 specimens in 65 categories**: **32 YES**, **5 MAYBE**, and **28 NO** classification priorities. These are aggregate counts, not specimen identifiers or ready-made train/test splits.
- **Fall 2026 classification annotations can be outside the old rectangular training regions.** Restricting extraction to those rectangles would omit some supplied labels.
- Expert taxonomic annotations and outputs from a previous detector are different forms of data. An unclassified detection is not a classification ground-truth label.
- Multiple focal planes contain identifying morphology. Prior detection preprocessing compressed depth information; its suitability for classification remains to be assessed.
- The sponsor meeting emphasized classification. The proposal's broader GUI/fine-tuning scope and requested crop-viewing features still need scope reconciliation.

These points are traced to the supplied materials in the linked guides. Source documents and meeting statements are project evidence, not instructions to execute code, contact people, or change scope.

## People

**Team:** Kimberly (Yun-Ying) Tsai, Yunfan Bao (Bob), YeonJu Kim, Patrick Batsell, and Alan Yang.

**Smithsonian mentors:** Ingrid C. Romero and Scott Wing. **Rice faculty mentor:** Dr. Arko Barman. See [team and course context](docs/TEAM_AND_COURSE.md) for source attribution and contact details.

## Contributing context

Preserve original documents unchanged and keep summaries separate. Add new sources to the manifest and source index, using explicit document dates where available. Use `YYYY-MM-DD_description` for dated meeting records; record unknown dates rather than guessing. Update the context guide when a later source resolves an open question, retaining the earlier source's historical meaning.

The proposal states that the Smithsonian retains ownership of fossil images and extracted specimens and envisions openly available code and models. This transfer does not establish a repository-wide license or redistribution license for every supplied document.

# Sponsor meeting speaker guide

September 18, 2026. Present slides 1–8, skip slide 9 unless the full inventory is needed, and close with slide 10. Aim for about 8 minutes of presentation plus discussion. Notes are also embedded in PowerPoint Presenter View.

## Slide 1: Opening — 45 seconds

OPEN: Thank you for meeting with us. Our understanding is that the project will help identify fossil pollen types in microscope images, supporting your work on past vegetation and warm climates. Today we will show what we can access, explain how we have organized the labels, and agree on the first useful version. We have not trained a classifier yet. The image is a real region from a slide on Rice’s cluster, with existing annotation boxes—not model predictions.

MEETING FLOW: Allow about eight minutes for the overview and use the remaining time for discussion and decisions.

SOURCE: Sponsor presentation and September 11 meeting; Alaska preview provenance.

## Slide 2: Agree on the problem — 45 seconds

SAY: The previous group focused on where palynomorphs are. Our main focus is what type each specimen is. Those are separate tasks. A box can show where to look without telling us a detailed biological category. We propose beginning with existing marked specimens, then connecting the classifier to detection results.

ASK: Does this reflect the priority for this semester?

LISTEN FOR: Whether sponsors expect classification of expert annotations first, existing detector outputs first, or a complete whole-slide system. Do not promise a complete new detector or a full slide application.

TRANSITION: Here is what those marked specimens look like in our actual data.

SOURCE: September 11 sponsor meeting and project context.

## Slide 3: Explain the image — 60 seconds

POINT: The blue boxes surround four annotated objects in a small image region. This entire panel is only a tiny part of one slide. The full Alaska image is about 28.5 GB. We can read a small region without bringing the whole slide onto our laptops. The original data stay on Rice’s computing cluster, NOTS.

IMPORTANT: These four objects have the broad original title pol. They illustrate object location, not four confirmed examples of our detailed target categories. The displayed image is an existing focus-stacked tile from Spring 2026; different focus levels can help reveal structure. We have not established the best focus representation for classification.

SOURCE: C_418058_W_Nassichuk_R_2025_01_21_14_59_16_Alaska; HDF5 tile_63624_42509. Preview boxes were checked against annotation geometry; see assets/provenance.json.

## Slide 4: State progress accurately — 60 seconds

SAY: We read 82 annotation files in the training folder and 46 additional annotation files, and found a matching image filename for each of the 128. This was an annotation and file inventory, not a visual inspection of all 128 slides. We mapped names to your category table, first using exact names, then formatting fixes, and then a set of provisional connections approved internally by our team. That leaves 933 annotation records in 27 of your YES categories. Of those 933, 112 depend on provisional connections.

CAUTION: These are annotation records, not a claim that 933 unique specimens have passed a full quality review. The 27 categories are represented in the inventory; they are not all necessarily suitable for a first model. We have kept MAYBE categories separate.

SOURCE: data/current/classification_annotations.csv and category_summary.csv, September 17 audit. The current working set supersedes earlier 819- and 821-record inventories.

## Slide 5: Discuss a realistic first model — 90 seconds

SAY: The examples are unevenly distributed. Bisaccate has 335 annotation records across 44 slides; Momipites has 262 across 40. Rhoipites has 39, but all are on one slide. A model can accidentally learn a slide’s appearance instead of the biological distinctions. Testing on different slides helps us assess whether it transfers. With only one slide for a category, we cannot put that category into separate training and test slides using this set.

ASK: Would a smaller first classifier covering well-supported categories be useful? Which categories matter most scientifically? Which scarce categories are essential, and could additional examples be labeled? Explain that few examples make learning variation and measuring performance harder.

DO NOT: Present the displayed five as a finalized class selection or promise that count alone makes a category usable. Note that counts include provisional mappings.

SOURCE: data/current/category_summary.csv, September 17 working selection.

## Slide 6: Explain the next work — 90 seconds

SAY: Our label inventory is ready, but we have not yet extracted and checked the complete set of specimen images. We will now extract regions around the selected annotations, including annotations outside the historical training rectangles. We will inspect the crops for alignment, focus, preservation, and duplicates, then prepare training and evaluation groups. The current count may change after this quality review.

CATEGORY POLICY: We are using Ingrid’s category mappings and the agreed working extensions. Do not reopen the explicit Siltaria-to-Rhoipites or Liliacidites-to-Arecipites CSV mappings as if they were arbitrary. Original names and provisional flags remain recorded; these groupings are not claims of taxonomic synonymy. Ask about a specific qualified label only if it affects the work, rather than spending the main meeting reviewing every name.

ASK: Which visual features are essential for distinguishing the priority types? Which preservation or staining problems make a specimen unsuitable? Could you point out a few good and difficult examples?

VERSION CHECK IF NEEDED: We can proceed with this working set. If there is a newer or corrected annotation set behind the spreadsheet, please identify it so we can record the version and compare it. Differences in totals have not been explained by the naming cleanup.

SOURCE: Current working inventory and pipeline plan. Extraction, quality review and final evaluation splits remain future work.

## Slide 7: Agree on evaluation priorities — 3–4 minutes discussion

SAY: We want to know whether the model learns useful biological distinctions, not just whether it recognizes familiar images. We propose holding some slides aside for evaluation, keeping all views of a specimen together, and reporting performance separately for each category. The exact split is not finalized.

ASK FIRST: What is of utmost importance for us to get correct in this project? Which distinctions are essential, and which mistakes would change your scientific conclusions? Is flagging an uncertain specimen preferable to forcing a label? Your email suggested about 60 specimens for categories over 100. Should that limit apply to the training examples, with separate specimens retained for evaluation?

NOTE: Do not propose an arbitrary accuracy promise. We should agree on numeric targets after verifying labels and obtaining a first result. A confidence score is a model estimate, not automatically a calibrated probability.

SOURCE: Sponsor email for the approximate-60 request; project pipeline plan for proposed evaluation approach.

## Slide 8: Confirm the handoff — 3–4 minutes discussion

SAY: Our proposed first version takes an existing marked specimen, assigns a category, and lets you inspect the result beside the image. We would export predictions into a new annotation file and keep original expert annotations untouched. A simple viewer could show the category, location, and uncertain cases. This is a proposed workflow, not software we have already built.

ASK: Which application will you use to open the annotations? Can you supply an example of a result file that would be convenient? Should we prioritize annotated outputs, downloadable specimen crops, or browsing predictions? Is starting with existing marked specimens acceptable before integrating detector outputs?

SCOPE: Full whole-slide navigation and interactive model fine-tuning remain possible extensions rather than promises for the first version.

SOURCE: September 11 sponsor discussion and current pipeline plan.

## Slide 9: Backup: full inventory

Use this only if asked about a particular category. Counts reflect the current working mapping, including provisional aliases. A represented category is not necessarily ready for training or evaluation. Five YES categories have no matched records in this selection: Momipites flexus, Momipites ventifluminis, Nudopollis sp., Psilatricolpites sp., and Rousea sp. The 63 MAYBE annotations are separate. The 212 unmatched and 344 untitled entries are not part of the initial selection.

SOURCE: data/current/category_summary.csv. Total 933 YES records across 27 represented categories.

## Slide 10: Final question recap — 2–3 minutes

SAY: To close, these are the main questions we have discussed. What is most important for us to get right? Which rare categories are essential, and can additional examples be labeled? What should we look for when reviewing specimen images? Can we start with the better-supported categories, and should the approximately-60 limit apply to training only? Finally, what result format and way of reviewing uncertain cases would be useful?

EMPHASIZE: The total of 933 annotations does not mean we have enough examples for every category. Scarce categories are harder to learn and evaluate, especially when all examples come from one slide. We should agree on a practical first scope and expand it as evidence allows.

FACILITATE: Read back agreed answers rather than asking answered questions again. For remaining questions, record an owner, a next action and a follow-up date.

NEXT: Extract and inspect the specimen crops, including annotations outside the old training rectangles; define evaluation groups; then train a first model.

SOURCE: Recap of the discussion questions; no new sponsor commitments or model results.
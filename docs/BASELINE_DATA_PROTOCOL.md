# Initial classification categories and split

Prepared October 7, 2026. Patrick confirmed keeping the sponsor's 32 YES categories unchanged for the first baseline. Patrick subsequently approved the proposed first baseline: the existing grouped split and ordinary sampling are adopted for this exploratory run. The assignment file is frozen by hash; sparse-category and biological-grouping limitations remain. This is not a claim of final scientific adequacy.

## Categories

Use [baseline_category_map.csv](../data/current/baseline_category_map.csv): alphabetical, zero-based classifier IDs 0–31 with exact sponsor category strings. Preserve original annotation titles as provenance. These classifier IDs are not automatically a detector framework's category IDs; validate the conversion in each model's dataset adapter.

Keep all 32 YES categories separate, including the named scientific priorities Arecipites sp., Bombacacidites sp., and Platycarya platycarioides. MAYBE, NO, and untitled records are excluded from this first closed-set classification experiment. Do not treat them as an automatically approved background or unknown class. Detector training requires a separate review of unlabeled and excluded objects within tiles.

This first experiment uses 2,283 candidate records after the existing seven duplicate/conflict exclusions. Choosing the unchanged categories is a new baseline decision; it does not establish a sponsor-approved broader taxonomy or supersede the usefulness of later broad-category experiments.

## Adopted exploratory split

| Set | Records | Accession groups |
| --- | ---: | ---: |
| Training | 1,605 | 40 |
| Validation | 347 | 9 |
| Test | 331 | 8 |

Keep the current accession-group assignments rather than randomly splitting individual crops. Group identities are conservative filename-derived proxies; biological sample relationships still need confirmation. All focal planes, derived focus representations, augmentations, and overlapping image regions from each source group must remain in its assigned partition. Both model teams should use this same assignment for this baseline.

The October 7 read-only audit of the deployed private record_assignments.csv verified 2,283 unique IDs, exact agreement with the previously reconstructed candidate fields, and no accession group crossing partitions. SHA-256 of the audited assignment file: `da2062a127cf6e14945e50fff097e0db102d7f8203250b47daed6b6bb166478d`. This is a metadata audit, not a verification of every exported crop. Row-level review inputs remain outside the public checkout.

See [per-category coverage](../data/current/baseline_split_coverage.csv). Retipollenites sp. has 73 training, zero validation, and two test examples. Seven categories have fewer than three validation examples; five have fewer than three test examples. Three is a reporting flag, not a threshold establishing reliable evaluation. Explicitly list categories represented in each metric; do not claim validation measures all 32 categories. Retain all 32 classifier outputs and report support with per-class results.

A separate feasibility check removed the old forced-dominant-group and exact group-count constraints. Under the current 57 groups, training size 65–75%, validation and test each 10–20%, every category in both held-out sets, and at least five training examples per category, the integer solver reported infeasible. Requiring 40% of each category in training was also infeasible. This result is conditional on those constraints and the current grouping; it does not prove that every possible split design is impossible. The existing split is practical, not established as statistically optimal.

## Evaluation and remaining choices

Use training and validation for development; leave test predictions and scores untouched until the final protocol is fixed. Report sparse-class results descriptively with their counts and source-group support. More independent labeled material is needed for convincing category-specific estimates where support is tiny. Grouped cross-validation may assess sensitivity but cannot create independent examples.

Keep all eligible training records in the split manifest. A training sampler can later implement a cap, weighting, or balanced sampling without changing membership. For this baseline, Patrick approved ordinary sampling of all training records and conservative training augmentation. This deliberately differs from the sponsor's earlier 50-grain cap; compare alternative sampling policies separately without changing the split. Never thin validation or test data to improve scores.

The first run adopts conservative accession grouping. Before launch, verify crop quality/export provenance and output storage. Training uses the recorded configuration in [the classifier workflow](../scripts/classification/README.md). Record checkpoint provenance; a held-out slide may have been seen by a reused Spring detector. No training, test evaluation, Git push, or shared-file mutation was performed for this decision review.

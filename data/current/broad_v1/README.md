# Broad category map — draft v1

First name-based grouping of the 32 sponsor YES categories, requested October 8. It defines 28 operational groups and preserves all 2,283 eligible specimens, their original fine labels, and both existing split assignments. The two merged groups are draft scientific groupings for sponsor review; this is not a uniform genus-, family-, or morphology-level taxonomy.

## Proposed merges

| Broad group | Preserved fine labels | Eligible specimens |
| --- | --- | ---: |
| Momipites | Momipites sp; Momipites flexus; Momipites ventifluminis; Momipites wyomingensis | 334 |
| Caryapollenites | Caryapollenites sp.; Caryapollenites veripites | 150 |

The Momipites proposal follows Patrick’s report that wyomingensis belongs within Momipites and the explicit shared name of the other labels. Caryapollenites is a second shared-name proposal. These are not synonym declarations. The original “sp” labels remain unspecified source categories; do not infer a species for those specimens. All other 26 source categories remain separate and retain their exact names.

## Complete map and current grouped-split counts

| Broad ID | Broad category | Fine categories | Train | Validation | Test |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0 | Alnipollenites verus | 1 | 62 | 23 | 7 |
| 1 | Arecipites sp. | 1 | 65 | 11 | 5 |
| 2 | Betulaceae | 1 | 54 | 13 | 11 |
| 3 | Bisaccate | 1 | 160 | 32 | 121 |
| 4 | Bombacacidites sp. | 1 | 20 | 17 | 3 |
| 5 | Caryapollenites | 2 | 122 | 22 | 6 |
| 6 | Cicatricosisporites sp. | 1 | 42 | 1 | 9 |
| 7 | Cupuliferoipollenites sp. | 1 | 15 | 3 | 9 |
| 8 | Ericipites sp. | 1 | 47 | 3 | 4 |
| 9 | Illexpollenites sp. | 1 | 25 | 3 | 4 |
| 10 | Inaperturopollenites sp. | 1 | 30 | 7 | 6 |
| 11 | Laevigatosporites sp. | 1 | 21 | 3 | 14 |
| 12 | Momipites | 4 | 257 | 50 | 27 |
| 13 | Monocolpites sp. | 1 | 51 | 25 | 4 |
| 14 | Nudopollis sp. | 1 | 85 | 3 | 1 |
| 15 | Pistillipollenites sp. | 1 | 61 | 1 | 2 |
| 16 | Platycarya platycarioides | 1 | 52 | 1 | 3 |
| 17 | Platycaryapollenites swasticoidus | 1 | 77 | 2 | 2 |
| 18 | Polyatriopollenites type | 1 | 28 | 9 | 6 |
| 19 | Psilatricolpites sp. | 1 | 26 | 18 | 17 |
| 20 | Psilatriletes sp. | 1 | 27 | 6 | 15 |
| 21 | Quercus sp. | 1 | 38 | 3 | 3 |
| 22 | Retipollenites sp. | 1 | 73 | 0 | 2 |
| 23 | Rhoipites sp. | 1 | 41 | 6 | 18 |
| 24 | Rousea sp. | 1 | 34 | 12 | 6 |
| 25 | Taxodium sp. | 1 | 25 | 33 | 3 |
| 26 | Tetracolporopollenites sp. | 1 | 40 | 8 | 19 |
| 27 | Ulmipollenites sp. | 1 | 27 | 32 | 4 |

## Files and use

- [fine_to_broad.csv](fine_to_broad.csv): all 32 exact sponsor strings and original class IDs mapped to 28 broad IDs, with basis and review status.
- [groups.csv](groups.csv): group membership and counts before and after the existing duplicate/conflict exclusions.
- [split_coverage.csv](split_coverage.csv): counts and unique source-slide/accession-group coverage for both existing splits. Group counts are recomputed as unions, not added across child categories.
- [manifest.json](manifest.json): input/output hashes and scope checks.
- [Builder](../../../scripts/classification/build_broad_map.py): deterministic generation from the original category map and frozen private assignments; requires a new output directory.

Broad IDs are a separate namespace. Do not replace the original 32-category map or reinterpret an existing checkpoint’s output indices. Join by exact fine category and retain both fields. Unknown labels should fail mapping rather than being guessed. No MAYBE, NO, or untitled records are added.

No specimens are removed by this map: the difference between 2,290 sponsor YES annotation records and 2,283 eligible specimens is the seven previously recorded exclusions. Original train/validation/test sizes remain 1,605/347/331. Retipollenites still has no grouped-validation support; this first grouping does not fix every sparse category.

For a later hierarchical model, train broad identification first, then assess fine identification within a broad group using the preserved labels and existing memberships. Do not treat unspecified source labels as confirmed named species. A stage-two classifier needs its own coverage assessment.

If evaluating existing predictions at the broad level later, distinguish mapping the fine argmax label from summing all fine-class probabilities within each broad group; they can give different answers. This draft does not recalculate historical metrics, run a new model, or evaluate the test set. Any later broad results must be labeled as a new, coarser task.

## Connections deliberately left unresolved

- Platycarya platycarioides and Platycaryapollenites swasticoidus remain separate; a similar-looking name is not enough evidence to merge.
- Betulaceae, Bisaccate and other operational categories are not expanded into inferred biological families or morphology groups.
- Bombacacidites/Rousea, Monocolpites/Arecipites and other model confusions are not evidence of shared biological identity.
- A substantially smaller map requires sponsor guidance on which distinctions can be discarded. Select further groups by scientific purpose, not by which changes raise validation scores.

The generation manifest records the map-only preparation step. Patrick subsequently authorized a [separate training experiment](../../../reports/broad_classification_2026-10-08/README.md) for Swin and adapted DINO. The original fine-category results and map remain preserved; no Git push is included.

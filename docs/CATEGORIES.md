# Category inventory and sponsor guidance

Derived from the unchanged [title counts CSV](sources/data/title_counts.csv), [category workbook](sources/data/category_totals.xlsx), and [sponsor email](sources/correspondence/2026-09-14_ingrid_romero_email.md). Table labels and capitalization below preserve the workbook's values. No specimens have been selected or excluded by this transfer.

## Verified inventory

- **185 annotation-title rows** in the CSV, with columns `Category`, `Annotation title`, and `n`.
- **65 categories**, containing **11,275 counted specimens** in total.
- **32 YES**, **5 MAYBE**, and **28 NO** classifications in the workbook.
- Every category's sum of CSV `n` matches its workbook total exactly; neither table has an unmatched category.

The email describes two columns and calls both attachments Excel files; the supplied title-count file is actually a three-column CSV. `Annotation title` is the identification name used in annotations; `Category` is the intended classification grouping, which can be broader than a species. Retain the explicit mapping rather than merging names by guesswork. These are aggregate counts, not a specimen manifest or a validated image inventory.

## Training priorities and balancing

The sponsor email asks for random selection of approximately 60 specimens from categories with more than 100, to improve balance. Among the **YES** categories, only **Bisaccate (316)** and **Momipites sp (184)** exceed that threshold. For eligible classes, replacing those two totals with exactly 60 each would yield **1,910 specimens**, compared with **2,290** across all YES categories. This is an illustrative count, not an executed sample or a finalized sampling protocol.

The guidance does not say to cap every category at 60: classes with 61–100 specimens remain distinct from the over-100 case. Large NO categories remain outside the proposed target classification set. NO is a training-priority label, not proof that a specimen is background or absent from a slide; MAYBE is a tentative inclusion decision, not a taxonomic class.

Important explicit exceptions to the email's approximate 20–30 range:

- **Cupuliferoipollenites sp. has 27 specimens and is YES.** Do not demote it using a count threshold.
- **Periporites sp. has 15 specimens and is MAYBE.** Do not silently exclude it or change its count to fit the prose description.
- The other MAYBE groups are Retitricolpites sp. (26), Tricolporites sp. (26), Tricolpites sp. (24), and Triporites sp. (23).

Before actual sampling, resolve individual specimen identifiers, handling of multiple focal planes/crops of the same object, a reproducible random seed, and how balancing interacts with the evaluation split. Nothing in these aggregate tables settles those choices. The [project context](PROJECT_CONTEXT.md) records them as open questions.

## Complete category table

Rows retain the original workbook order. Counts are specimen totals as supplied, not estimates generated from model outputs.

| Category | n | Classify |
| --- | ---: | --- |
| pollen | 6006 | NO |
| Indet. | 1944 | NO |
| Fungi | 353 | NO |
| Bisaccate | 316 | YES |
| spore | 281 | NO |
| Momipites sp | 184 | YES |
| Dinocyst | 143 | NO |
| Caryapollenites sp. | 95 | YES |
| Alnipollenites verus | 92 | YES |
| Nudopollis sp. | 89 | YES |
| Arecipites sp. | 81 | YES |
| Platycaryapollenites swasticoidus | 81 | YES |
| Monocolpites sp. | 80 | YES |
| Betulaceae | 78 | YES |
| Retipollenites sp. | 75 | YES |
| Tetracolporopollenites sp. | 67 | YES |
| Rhoipites sp. | 65 | YES |
| Pistillipollenites sp. | 64 | YES |
| Ulmipollenites sp. | 63 | YES |
| Taxodium sp. | 62 | YES |
| Momipites ventifluminis | 61 | YES |
| Psilatricolpites sp. | 61 | YES |
| Algae | 59 | NO |
| Platycarya platycarioides | 56 | YES |
| Caryapollenites veripites | 55 | YES |
| Rousea sp. | 54 | YES |
| Ericipites sp. | 54 | YES |
| Cicatricosisporites sp. | 52 | YES |
| Momipites wyomingensis | 51 | YES |
| Psilatriletes sp. | 48 | YES |
| Quercus sp. | 44 | YES |
| Inaperturopollenites sp. | 43 | YES |
| Polyatriopollenites type | 43 | YES |
| Bombacacidites sp. | 40 | YES |
| Laevigatosporites sp. | 38 | YES |
| Momipites flexus | 38 | YES |
| Illexpollenites sp. | 33 | YES |
| Cupuliferoipollenites sp. | 27 | YES |
| Retitricolpites sp. | 26 | MAYBE |
| Tricolporites sp. | 26 | MAYBE |
| Tricolpites sp. | 24 | MAYBE |
| Triporites sp. | 23 | MAYBE |
| Periporites sp. | 15 | MAYBE |
| Echitricolpites microechinatus | 12 | NO |
| Hippocrateaceaedites sp. | 11 | NO |
| Tsuga | 11 | NO |
| Caprifollipites sp. | 7 | NO |
| Verrutricolpites sp. | 7 | NO |
| Nyssapollenites sp. | 6 | NO |
| Striatricolporites sp. | 4 | NO |
| Verrucingulatisporites sp. | 4 | NO |
| Monoporopollenites | 3 | NO |
| Spinizonocolpites sp. | 3 | NO |
| Clavatricolpites sp. | 2 | NO |
| Echiperiporites akanthos | 2 | NO |
| Gothanipollis sp. | 2 | NO |
| Polypodiisporites sp. | 2 | NO |
| Proxapertites sp. | 2 | NO |
| Calamuspollenites? | 1 | NO |
| Clavaperipollenites | 1 | NO |
| Echipollenites sp. | 1 | NO |
| Juglans sp. | 1 | NO |
| Polypodiaceoisporites sp. | 1 | NO |
| Retitricolporites coarsus | 1 | NO |
| Stereisporites? sp. | 1 | NO |

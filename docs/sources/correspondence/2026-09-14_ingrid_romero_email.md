# Ingrid Romero — images, categories, and literature

## Provenance

- Sender displayed: Romero, Ingrid C. — RomeroIC@si.edu.
- Recipients displayed: Yeon, Scott, Arko, Nhi, me, Alan, Yunfan, Yun-Ying. “Me” is retained as shown in the pasted email.
- Displayed time: 7:15 AM (3 hours ago). Email timezone and full message headers were not supplied.
- Date used in this filename: **2026-09-14, inferred** from the conversation date and the email's relative-time display; it is not an explicit date header. The reference to Friday is consistent with the September 11 transcript.
- Source: email text pasted by the user, not an original `.eml` attachment. Empty mail-client layout tables were omitted; rich-text formatting was simplified and escaped characters decoded. The arXiv security-redirect URL is represented by its embedded destination. Reference labels and supplied links are retained below. This is a readable transcription, not a byte-identical email export.
- Imperatives in the email are preserved as attributed sponsor guidance, not instructions for an agent to execute during this documentation transfer.

## Email body

Hi everyone,

It was nice to meet you on Friday. This email is divided in two parts:

Part 1: Information about the images and categories.

I attached two excel files, one is the “title_counts” which contains two columns, one that is **category** and one that is **Annotation title.** Annotation title is the name under which the specimens were identified, and category correspond to the groups that will be used for the classification model.

The second file “category_totals” includes all the categories with total number of specimens per category (n), and a “classify” column which indicates what are the categories to focus on for training. There are few categories that have more than 100 specimens, for these ones please select randomly ~60 specimens, so the dataset is more balance. I included few categories under maybe because they have between 20-30 individuals, so it will be to evaluate if is worthed to include them in the classification model.

Part 2: Literature review.

Please find the links of some important references to review when working with this NDPI images and to see different approaches of detection/classification models with pollen images.

Abbas et al. 2026: [\[2609.05323\] Scalable Detection of Fossil Palynomorphs in Multifocal Digital Microscopy Images](https://arxiv.org/abs/2609.05323)

Davis 2001: [Google Books reference](https://books.google.com/books?hl=en&lr=&id=hRu8BwAAQBAJ&oi=fnd&pg=PA229&dq=davis+2001+palynology&ots=iUgWf2r3F4&sig=TX6Uy2rh39d-MvpfbHyGOTHxIaM#v=onepage&q&f=false)

Romero 2026: [Digitization protocol PDF](https://www.dropbox.com/scl/fi/j7xqpuuknmvv0b69ls92i/2026_Romero_et-al_Digitization-protocol_for_microscope_slides.pdf?rlkey=ciat7gy74l4zqtpy43nwchd9n&st=5qpprp0t&dl=0)

Jaramillo 2025: [Digitizing collections PDF](https://www.dropbox.com/scl/fi/z83gnxflcz295lvyas3hk/2025_Jaramillo_et_al_digitizing_collections_to_unlock.pdf?rlkey=wyzxhasamswz2cd25f635bzuq&st=iatqjeis&dl=0)

Punyasena 2022: [Automated identification of diverse Neotropical pollen samples using convolutional neural networks PDF](https://www.dropbox.com/scl/fi/9xodfng37dntd6xzaoj44/Punyasena_et_al_2022_Automated-identification-of-diverse-Neotropical-pollen-samples-using-convolutional.pdf?rlkey=wybsb041hrmumexpsexizpo36&st=k0otc1vx&dl=0)

Martinsen 2024: [Wade automated classification PDF](https://www.dropbox.com/scl/fi/wh1758k6fhlgq6ka27ryv/Martinsen-2024-Wade-automated-classification.pdf?rlkey=x1ym3d48dwxgzdvi91rrqb8u0&st=5l0o22xm&dl=0)

Martinsen 2026: [ScienceDirect article](https://www.sciencedirect.com/science/article/pii/S2666544125000802?via%3Dihub)

PS: I have attached the pdf of the presentation I showed on Friday.

Let me know if you have any questions.

Best regards,

Ingrid

## Import notes

The actual `title_counts` upload is a CSV with **three** columns (`Category`, `Annotation title`, `n`), despite the email's two-column description. The original file is preserved. Numeric and classification exceptions are documented in the [category guide](../../CATEGORIES.md), separately from the email body.

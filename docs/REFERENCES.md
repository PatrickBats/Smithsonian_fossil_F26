# References and previous project work

This is an index of references **supplied by the sponsors**, not a completed literature review or a fresh recommendation list. Only the locally supplied detection preprint is summarized substantively here. Linked papers and prior repositories have not been retrieved or audited during this transfer, and their availability or current publication metadata has not been independently verified.

## Sponsor email reading list

The [preserved email](sources/correspondence/2026-09-14_ingrid_romero_email.md) retains all seven supplied references and their original destination links, including Dropbox links.

| Supplied label | Reference and context | Review status |
| --- | --- | --- |
| Abbas et al. 2026 | [Scalable Detection of Fossil Palynomorphs in Multifocal Digital Microscopy Images](https://arxiv.org/abs/2609.05323); first author in the supplied PDF is Abbas Shaikh | Local [preprint](sources/references/WACV_manuscript_for_Smithsonian_preprint.pdf) reviewed; linked arXiv version not compared |
| Davis 2001 | [Google Books selection](https://books.google.com/books?hl=en&lr=&id=hRu8BwAAQBAJ&oi=fnd&pg=PA229&dq=davis+2001+palynology&ots=iUgWf2r3F4&sig=TX6Uy2rh39d-MvpfbHyGOTHxIaM#v=onepage&q&f=false) | Not read; exact chapter/title and metadata unresolved |
| Romero 2026 | Digitization protocol; preprint reference [21] names *Digitizing microscope slide-based natural history collections: A protocol using slide scanner technology* | Link in email; full paper not read |
| Jaramillo 2025 | Digitizing collections; preprint reference [9] names *Digitizing collections to unlock the full potential of palynology: A case study with the Smithsonian palynology collection* | Link in email; full paper not read; email/file says 2025, preprint bibliography says 2026 |
| Punyasena 2022 | *Automated identification of diverse Neotropical pollen samples using convolutional neural networks*; [DOI from Resources.docx](https://doi.org/10.1111/2041-210X.13917) | Full paper not read |
| Martinsen 2024 | Preprint reference [15] names *The 3-billion fossil question: How to automate classification of microfossils* | Link in email; full paper not read |
| Martinsen 2026 | [ScienceDirect link](https://www.sciencedirect.com/science/article/pii/S2666544125000802?via%3Dihub); preprint reference [16] names *The Fossil Frontier: An answer to the 3-billion fossil question* | Full paper not read; title association drawn from supplied bibliography, not verified at the link |

The title associations above come from the uploaded preprint's reference list and supplied filenames. Year differences remain visible rather than being silently resolved.

## Supplied detection preprint

The [local manuscript](sources/references/WACV_manuscript_for_Smithsonian_preprint.pdf) describes a whole-slide detection workflow:

1. Read slide regions as overlapping tiles and map physical annotation coordinates onto pixels.
2. Compress focal information using either focus stacking or focal-plane selection.
3. Detect palynomorphs with YOLO26 or RF-DETR.
4. Merge overlapping detections and optimize image reads to make whole-slide inference practical.

Its study contains 847 slides, 82 of which were selected for annotation. It reports slide-level training/validation/test partitions of 58/12/12. The strongest reported configuration is RF-DETR-2XL with focus stacking: AP@50 0.879 and AP@50–95 0.642. Optimized whole-slide inference averages 51 minutes over five production slides on the reported hardware. Sources: §3–5 and Tables 1–2.

For Fall 2026, this supplies historical detection context and possible reusable preprocessing. It does **not** establish classification performance, validate the new label set, or settle how to retain focal information for taxonomy. Section 6 identifies limited annotated-slide coverage, generalization differences, and loss of volumetric information as limitations. No results were reproduced during this transfer.

## Faculty resource collection

The original [Resources.docx](sources/references/Resources.docx) is preserved intact, including hyperlinks. It groups general deep learning and machine vision courses, RCNN/YOLO/transformer detectors, RetinaNet, pollen recognition papers, software repositories, and a larger paper collection. Labels such as “latest” are historical source wording, not current claims made by this handoff.

Selected navigation links from that document, all unreviewed here:

- [MIT introduction to deep learning](https://ocw.mit.edu/courses/6-s191-introduction-to-deep-learning-january-iap-2020/) and [machine vision](https://ocw.mit.edu/courses/6-801-machine-vision-fall-2020/).
- [Fossil pollen taxonomy with CNNs and superresolution microscopy](https://doi.org/10.1073/pnas.2007324117).
- [Pollen detection/classification code](https://github.com/aimerykong/pollenDetClsSystem/), [Detectron2](https://github.com/facebookresearch/detectron2), and [MMDetection](https://github.com/open-mmlab/mmdetection).
- [Computational pathology resource collection](https://github.com/open-pathology/awesome-pathology).

## Prior-semester repositories

| Repository supplied in Resources.docx | Status in this transfer |
| --- | --- |
| [Spring 2025](https://github.com/RiceD2KLab/Smithsonian_fossil_Sp25) | Indexed only; access, code, and artifacts not inspected |
| [Fall 2025](https://github.com/RiceD2KLab/Smithsonian_fossil_F25) | Indexed only; access, code, and artifacts not inspected |
| [Spring 2026](https://github.com/RiceD2KLab/Smithsonian_fossil_Sp26) | Indexed only; access, code, and artifacts not inspected |

Before future reuse, identify exact commits, weights, label assumptions, licenses, and dependencies. The current transfer imports neither their code nor their model choices.

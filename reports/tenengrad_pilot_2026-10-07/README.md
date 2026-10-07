# Tenengrad focal selection pilot

An eight-specimen pilot across four training slides selected visibly sharper views for four blurred plane-zero crops. It retained plane zero for the other four. This supports testing focal selection as a preprocessing change; no improvement in classification accuracy has been measured.

## Method and integrity

The first two training records in manifest order from each of four sources were selected before scoring: D1555, C_418058, C_418080, and D1911. They provide 21, 27, 27, and 25 planes respectively, for 200 focal views total. Pilot crop sides were 256–304 pixels. This is a small purposive sample, not an estimate of the fraction of the full dataset needing refocusing.

[Pilot code](../../scripts/classification/tenengrad_pilot.py) reads the original NDPI regions through tifffile/zarr, one focal view at a time. It converts RGB to grayscale and computes mean squared horizontal/vertical 3x3 Sobel gradients using OpenCV defaults. It selects the highest score, breaking exact ties by proximity to zero offset and then index. The paper describes a sum; the earlier team's code uses a mean. Equal-size views of the same crop have the same ranking under either aggregation.

The scoring region is the individual specimen crop, rather than the larger detection tile used in the paper. All context within the crop contributes, so sharp neighboring specimens or debris can influence selection. No masking or noise correction was added. This crop-level adaptation remains distinct from a reproduction of the paper's tile-level experiment.

Every zero-offset crop matched the existing verified baseline PNG checksum exactly. All selected output hashes, dimensions, training-only membership, and maximal-score choices passed checks. Source files were read only and checked for unchanged metadata during processing. No test data or model inference was used. A synthetic Sobel check confirmed a sharp square scores above its blurred version, while a blank image scores zero.

## Measurements

| Measurement | Observed |
| --- | ---: |
| Specimens / slides / focal views | 8 / 4 / 200 |
| Remote processing elapsed time, excluding queue/import startup | 57.66 seconds |
| Focal crop read time | 21.58 seconds |
| Tenengrad score computation | 0.24 seconds |
| Process CPU time | 7.38 seconds |
| Peak process memory | 3,790 MiB |
| Selected PNG payload | 713,592 bytes |
| Selected nonzero focal planes | 4 of 8 |

Slurm job 2034574 ran on NOTS with two requested CPUs and 16 GB memory, streaming only selected PNGs and score metadata to workstation storage. No remote dataset outputs were written. The original plane-zero dataset is preserved. Local artifacts reside outside Git in `tenengrad_pilot_2026-10-07`: request, script snapshot, Slurm log, returned archive, verified report, per-plane scores, selected images, and comparison figures.

## Interpretation and next experiment

Processing 2,283 specimens across 75 slides projects to approximately two hours on one worker if pilot per-crop time holds and slide-opening overhead is amortized across all specimens on each slide. Naively scaling the entire eight-crop pilot instead gives about 4.6 hours because it repeats that overhead too often. Neither estimate is a benchmark of the complete export: larger crops (up to 880 pixels), cache behavior, and shared I/O may change it substantially. Reading pixels and opening slides dominate; Tenengrad arithmetic is inexpensive.

A full comparison would preserve specimen IDs, categories, crop geometry, grouped split, and Swin training settings while changing only the selected plane. Score validation/test inputs with the fixed image-only selection rule without consulting classification outcomes; reserve test-model evaluation as before. This pilot did not launch the full export or retrain a classifier. No files were pushed.

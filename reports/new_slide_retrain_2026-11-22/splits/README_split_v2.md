# split_v2 (2026-11-18) -- ACTIVE (team chose slide-level split for old slides, 2026-11-18). split_v3 = sample-grouped alternative, not used.

Files: `split_v2_20261118.json` (slide lists), `split_v2_manifest.csv` (new slides -> ndpi path, annotation path, format, box count, group, site), `make_split_v2.py` (regenerates both; seed 435).

| key | contents | how to score |
|---|---|---|
| train | old train (58) + new train (45) | - |
| val | old val (12) + new val (16) | checkpoint selection; log old/new parts separately |
| test | OLD test (12), unchanged | full mAP; compare directly to the previous semester model |
| test_new | 3746, 3749 (2CDST 1808.9 L/R), 5853 (TADP1 223Q-1-42.5): dense, look exhaustively annotated | full mAP |
| test_new_recall | 3776 (2CDST 617.65), 9000/9009 (Pislipampa L/R): rest of held-out collections, likely sparse labels | recall only (unboxed grains would count as FPs) |

Rules:
- New data is split by group = locality lot (e.g. L860033) when present, else sample (slide name minus side/timestamp). L/R slides of a sample never cross splits. Carimagua is grouped whole (lot is spelled two ways).
- 2CDST and Pislipampa are held out entirely (unseen-collection test). Carimagua and Chucal (L440139) ended up val-only.
- No new slide overlaps old splits. The 5 loose top-level ndpi+ndpa slides are all train (C_418058_L: its R side is old train; D1555: unused before).
- Box counts exclude Points and boxes under 20 px or over 1500 px per side; the COCO converter should still dedupe IoU>0.5 and clip to image bounds.

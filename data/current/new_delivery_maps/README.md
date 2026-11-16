# New-delivery label maps

These versioned tables are the inputs used for the November Method A preparation. `sponsor_title_map.csv` maps delivered annotation titles to sponsor category and YES/NO/MAYBE classification. `fine_to_broad.csv` maps the 32 sponsor categories to the 28 merged model classes. `broad_category_map.json` gives the exact merged class IDs used by the preparation audit. The preparation scripts read these copies from this directory and write specimen-level manifests only to RHF.

The source copies are in `/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_new_delivery/`. Source SHA-256 values are `9c8ad03118f4211de11e206c7f614834733086052e9516bb93b9d15a1294378c` for `broad_category_map.json`, `1ae955ac10ed46959b2dea9766978bc1682d140590c29eda1c68ae2db7ebe863` for `sponsor_title_map.csv`, and `a2f8da0b40cf9a1a89ea7fffe360770b2b9eae56f9fdd307bbf1b286bd9f793d` for `fine_to_broad.csv`. The CSV copies here use LF line endings, and `fine_to_broad.csv` retains only the three fields read by the code; mapping values are unchanged.

The original NDPI, NDPA, and ROI CSV files are under `/rhf/allocations/dsci435/smithsonian_full_sp26/new files/New_train_set_detection_model_rice/` on NOTS. They are not stored in Git.

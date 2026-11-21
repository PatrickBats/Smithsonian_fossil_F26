# Final mixed-delivery joint detection and classification

The completed final model recovers **157/442 targets (35.5%) with both the
correct location and category** on the reserved test scans. This is the final
single-model test result for this experiment. The five-fold development results
are selection evidence, not the final test score.

## What was completed

- Combined all 2,290 original priority-label records with 540 additional
  records, retaining all 28 mapped output categories and all source annotations.
- Rebuilt scan-group partitions from the complete pooled inventory, independently
  of historical membership. The 75 development scans contain 2,388 targets;
  the 20 test scans contain 442 targets. Both deliveries occur in each partition.
  Two evidenced alias pairs remain within indivisible groups.
- Retained native-context crops, LoG k=5 focal fusion and ignore-region loss.
  Newly fitted proposal detectors use only the corresponding training scans;
  the generic initializer has no fossil-target training. Historical fossil
  models were not trained, evaluated or used for initialization in this run.
- Completed five-fold cross-validation, comparing EMA snapshots at 1,200 and
  2,400 optimizer steps and five predefined confidence cutoffs. The predefined
  mean scan-level recovery rule selected 2,400 steps and confidence 0.25.
- Trained one final joint model on all development scans with those settings,
  then evaluated that checkpoint once on the fixed test. The test did not
  enter training, proposal generation or model selection.

The final training dataset has 2,188 crops and 2,604 known box instances.
Box instances can repeat a source annotation across overlapping context crops;
the scientific inventory and test denominator count unique source records.

## Final results and interpretation

| Measure | Final mixed-delivery test |
| --- | ---: |
| Location and category both correct | 157/442 (35.5%) |
| Location matched at IoU >= 0.50 | 414/442 (93.7%) |
| Located but wrong category | 257 |
| Missed targets | 28 |
| Mean scan-level joint recovery | 34.8% |
| Original-delivery targets, both correct | 122/365 (33.4%) |
| Additional-delivery targets, both correct | 35/77 (45.5%) |

Classification is the main observed error source: 257 of the 285 unsuccessful
targets were located but assigned a different category. Bisaccate remains
strong (38/41), followed by Laevigatosporites (29/42) and Momipites (25/42).
Monocolpites has 0/39 correct, including 15 predictions as Laevigatosporites;
Tetracolporopollenites has 1/17 correct, including five as Rhoipites. Seven
of the 28 categories have no correct test target; some have very small support.

The selected development result is 971/2,388 (40.7%) pooled joint recovery and
48.3% mean scan-level recovery. This comes from five separate held-out fold
models and must not be substituted for the final-model result above.

This experiment uses a newly reserved mixed-delivery test and a generic model
initializer. Historical scores on other partitions or with other initialization
are not a controlled before/after comparison. These results do not by themselves
establish a performance improvement over historical experiments.

The task is recovery of known annotated targets in annotation-guided context
crops. Sparse labels do not establish whole-slide search performance, AP or
full-scene precision. The 71 unmatched predictions remain unreviewed, rather
than being counted as verified false positives. Original overlapping or
conflicting source records remain intact. Scan identity safeguards use source
paths, evidenced aliases and matching thumbnails; full NDPI byte equality is
not claimed.

## Evidence and reproduction

- [Final counts and per-category support](final_summary.json)
- [Confusion matrix](confusion_matrix.png), [PDF](confusion_matrix.pdf),
  [exact matrix counts](confusion_counts.csv), [category analysis](per_class.csv)
- [All selection candidates and selected settings](selection.json)
- [Data summary](data_summary.json), [final training contract](training_contract.json)
- [Artifact hashes and sealed test boundary](artifact_provenance.json)
- [Submission ledger](provenance/jobs.json), [source/runtime inventory](provenance/source_version.json)
- [Runnable workflow, settings and NOTS paths](../../scripts/method_a_final_evaluation/README.md)

The aggregate files are copied from the completed remote publication directory.
Raw source records, membership manifests, crops and checkpoints remain outside
Git under the documented NOTS roots. Predictions and logs remain under
`/projects/dsci435/Smithsonian_F26/method_a/mixed_final_20261120/`.
The source inventory also includes inert macOS metadata sidecar hashes; only
ordinary Python modules are executable workflow source.

The final model SHA-256 is
`126001e423a1a71faac4163922f1125ef3342ce5a8e8eae53ae4141a37da0700`.
The submission ledger records every initial submission, queue replacement and
resumed chunk. Resumption preserves optimizer, scheduler and EMA state; a
partially consumed epoch may revisit its initial batches. No checkpoint or
threshold was selected using final test results.

Verification reconciled all 442 matrix entries, 157 diagonal entries, 28 misses,
class/origin totals, the selected settings, sealed test hashes and executed
Python source hashes against this branch. Unit tests and repository checks ran
on macOS; CUDA smoke checks, all training and all inference ran on NOTS Linux
with NVIDIA L40S GPUs. Native Windows execution was not tested.

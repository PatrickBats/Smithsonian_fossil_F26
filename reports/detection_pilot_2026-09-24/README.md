# Detection pilot — September 24, 2026

Both frozen Spring YOLO checkpoints successfully processed 64 Fall targets on 29 slides, covering all 32 YES categories. This establishes runtime compatibility and initial target recovery, not whole-slide accuracy or classification performance.

| Image preparation | Recovered at confidence ≥0.5 | Outside old rectangles | Inside old rectangles | Diagnostic confidence ≥0.25 |
| --- | --- | --- | --- | --- |
| Best focal plane | 54/64 (84.4%) | 27/32 | 27/32 | 57/64 |
| Focus stack | 51/64 (79.7%) | 26/32 | 25/32 | 59/64 |

Both thresholds require box intersection-over-union ≥0.5. The lower confidence threshold was predeclared and does not replace the primary result. These models also use different weights; the comparison does not isolate preprocessing alone.

For the sponsor priorities, focus-stack recovered both examples of Arecipites, Bombacacidites, and Platycarya platycarioides. Best-plane recovered both Arecipites and Platycarya examples and one of two Bombacacidites examples. Two examples per category cannot establish reliable category performance or justify choosing a model.

## Interpretation and visual checks

Three focus-stack overlays were inspected: shard 0 target 000 (Bisaccate), 005 (Nudopollis), and 027 (Bombacacidites). Annotation boxes align with visible specimens in these examples. Bisaccate and Bombacacidites pass the preset matching rule. The Nudopollis example has a tighter predicted box around the central specimen than the square derived from its annotation circle; it fails the IoU rule despite a visible detection. Treat this as a candidate annotation-versus-box convention issue, not a reason to silently lower the threshold. Full expert review of failures remains needed. Saved previews are illustrative, not a completed audit of all crops.

These are specimen-centered crops rather than blind tiles. Fifty targets are on slides listed in the historical training split, nine on historical test slides, and five have unresolved exact-name membership. That split file is not verified checkpoint training provenance. Accordingly, neither new-slide generalization nor precision/AP can be inferred. Surrounding objects are incompletely labeled, so unmatched predictions are not automatically false positives.

## Records and execution

- [Protocol](../../docs/DETECTION_PILOT.md), [configuration](config.json), and [fixed selection](pilot_targets.json).
- [Per-target results](results.csv), [unmatched target/model pairs](unmatched_targets.csv), and [stratified summary](summary.json).
- [Run record](run.json), [scheduler accounting](scheduler_accounting.txt), and provenance/completion JSON files for both shards.
- Slurm 1612309: both tasks COMPLETED with exit 0. Allocated one L40S GPU each for 448 and 441 seconds: 889 total GPU-allocation seconds, including setup/I/O rather than pure inference time.
- A few TIFF metadata tags produced ASCII-decoding warnings; reading and all shape, finite-value, coordinate-bound, source-hash and checkpoint-hash checks completed successfully. Logs are preserved with the run.
- Full tiles, overlays, raw predictions, source snapshot and logs remain at `/projects/dsci435/Smithsonian_F26/runs/detection_pilot_20260924T183555Z/`. A local metadata/preview copy is outside Git under `smithsonian_prior_artifacts/runs/`.

## Next step

Review unmatched cases against original focal stacks and agree how expert circles should be compared with tight detector boxes. Then evaluate fixed-grid regions, including tile boundaries and independently held-out slides after checkpoint provenance is resolved. Keep the current pilot results unchanged. A classifier can later be developed from expert-labeled crops without discarding specimens just because this detector missed them; assess the combined detection-plus-classification workflow separately.

No detector retraining, classifier training, threshold revision, full-slide scan or GitHub push was performed.

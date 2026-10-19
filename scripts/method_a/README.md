# Method A: direct multiclass pollen detection

Method A uses one RF-DETR model to locate pollen and predict its identification
class. Method B's detector-plus-classifier pipeline is a separate architecture.

The [three training-data variants](data_variants/README.md) below all use the
**same Method A RF-DETR 2XL architecture and new-run training protocol**:

- **A1 — positive ROI tiles:** retain original training tiles with a YES box.
- **A2 — context crops, original coverage:** recrop around the targets covered by
  the original training grid.
- **A3 — context crops, full training coverage:** extend the crop pool to all
  targets already assigned to training.

See the [completed comparison](../../reports/method_a_data_variants_2026-10-18/README.md)
for results, run provenance and interpretation limits. The older full-grid Method A
baseline is documented separately in [PR #5](https://github.com/PatrickBats/Smithsonian_fossil_F26/pull/5).

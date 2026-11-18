# Attribution
DINOv2 ViT-B/14 is provided by Meta: https://github.com/facebookresearch/dinov2 . Source is not vendored here. Recorded revision: 7764ea0f912e53c92e82eb78a2a1631e92725fc8. Preserve upstream license terms when obtaining source or weights.
Image transforms and the optional Swin helper use PyTorch/torchvision. The Swin helper is retained because the recorded trainer snapshots it for provenance; this workflow does not train Swin.
This package reuses the Fall2026 Method B classifier audit, split, broad-label mapping and training utilities. Frozen RF-DETR crop replay uses the team's existing RGB-corrected Abbas best-plane pipeline; the detector is not retrained or modified by this change.

"""Strict frozen Swin-Tiny / DINOv2 model loading in checkpoint label order."""
# Source implementations: torchvision Swin-Tiny and Meta DINOv2.
# Smithsonian_Fossil_Sp26 algorithm attribution and pinned revisions: root NOTICE.md.
import torch
from torch import nn
from torchvision.models import swin_t

def load_classifier(kind, path, dino_source, device):
    """Restore a frozen broad28 classifier and its checkpoint-ordered labels.

    Args:
        kind: Classifier architecture: swin or dino.
        path: Trusted trained checkpoint path.
        dino_source: Local checkout of the pinned official DINOv2 source.
        device: PyTorch device or device string for inference.

    Returns:
        tuple: Evaluation-mode model on the requested device and ordered class names.
    """
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    labels = ckpt["categories"]
    if len(labels) != 28 or len(set(labels)) != 28:
        raise ValueError("Expected unique broad28 checkpoint labels")
    if kind == "swin":
        model = swin_t(weights=None)
        model.head = nn.Linear(model.head.in_features, len(labels))
    else:

        class Dino(nn.Module):
            def __init__(self):
                """Initialize the classifier model or crop dataset with the recorded configuration.

                Returns:
                    None: Initializes this instance.
                """
                super().__init__()
                self.backbone = torch.hub.load(
                    str(dino_source), "dinov2_vitb14", source="local", pretrained=False
                )
                self.head = nn.Linear(1536, len(labels))

            def forward(self, x):
                """Classify the concatenated DINO CLS and mean patch-token representation.

                Args:
                    x: Normalized RGB tensor with shape (batch, 3, 224, 224).

                Returns:
                    torch.Tensor: Class logits with shape (batch, number_of_classes).
                """
                f = self.backbone.forward_features(x)
                return self.head(
                    torch.cat([f["x_norm_clstoken"], f["x_norm_patchtokens"].mean(1)], dim=1)
                )

        model = Dino()
    model.load_state_dict(ckpt["model"], strict=True)
    model.requires_grad_(False)
    model.eval().to(device)
    return model, labels

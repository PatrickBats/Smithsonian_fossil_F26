"""Private, verified pretrained copy prevents library recovery paths writing shared weights."""

import shutil
from common import ROOT, WEIGHTS, WEIGHT_SHA, sha, write

assert sha(WEIGHTS) == WEIGHT_SHA
p = ROOT / "inputs/rf-detr-xxlarge.pth"
p.parent.mkdir(parents=True, exist_ok=True)
with WEIGHTS.open("rb") as src, p.open("xb") as dst:
    shutil.copyfileobj(src, dst)
assert sha(p) == WEIGHT_SHA
write(
    ROOT / "inputs/pretrained_provenance.json",
    {"source": str(WEIGHTS), "sha256": WEIGHT_SHA, "copy": str(p), "source_modified": False},
)

import torch
from torch import nn
from unittest.mock import patch
import method_b.classification.train_dinov2 as t
class Fake(nn.Module):
 def __init__(self):
  super().__init__();self.blocks=nn.ModuleList([nn.Linear(4,4) for _ in range(12)]);self.norm=nn.LayerNorm(4)
for n in (2,4):
 t.TRAIN_BLOCKS=tuple(range(12-n,12))
 with patch.object(torch.hub,'load',return_value=Fake()):model=t.DinoClassifier(28)
 assert all(p.requires_grad==name.startswith('head.') for name,p in model.named_parameters())
 model.configure(False);model.train()
 trainable=[name for name,p in model.named_parameters() if p.requires_grad]
 for i in range(12):
  assert model.backbone.blocks[i].training==(i>=12-n)
  assert all(p.requires_grad==(i>=12-n) for p in model.backbone.blocks[i].parameters())
 assert all(p.requires_grad for p in model.head.parameters())
 assert all(p.requires_grad for p in model.backbone.norm.parameters())
 before=t.frozen_digest(model)
 with torch.no_grad():
  for p in model.parameters():
   if p.requires_grad:p.add_(.01)
 assert before==t.frozen_digest(model)
 print('Verified head-only, last',n,'blocks, train mode and frozen digest')

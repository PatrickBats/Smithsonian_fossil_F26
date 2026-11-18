import csv,json,random,sys
from pathlib import Path
import torch
from PIL import Image,ImageOps,ImageDraw
from method_b.classification.crop_dataset import strong_transform
torch.set_num_threads(2);random.seed(20261007)
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=True,parents=True)
policy=sys.argv[3]
rows=[r for r in csv.DictReader((root/'crop_manifest.csv').open()) if r['split']=='train']
assert len(rows)==1605
checks=0;fallback=0;tiles=[]
for idx,r in enumerate(rows):
 im=Image.open(root/r['image_relpath']).convert('RGB');im=ImageOps.pad(im,(max(im.size),)*2,color='white').resize((224,224),Image.Resampling.BICUBIC)
 for j in range(3):
  aug,m=strong_transform(im,r,stronger_geometry=policy=="geometry");b=m['bounds'];assert min(b[:2])>=-1e-5 and max(b[2:])<=224+1e-5,(r['record_id'],m)
  fallback+=m['fallback'];checks+=1
  if idx % 67==0 and j==0:
   tile=Image.new('RGB',(448,250),'white');tile.paste(im,(0,0));tile.paste(aug,(224,0));d=ImageDraw.Draw(tile);d.rectangle([b[0]+224,b[1],b[2]+224,b[3]],outline='red',width=2);d.text((5,228),f"Original / strong | angle={m['angle']:.0f} scale={m['scale']:.2f}",fill='black');tiles.append(tile)
sheet=Image.new('RGB',(448*4,250*6),'white')
for k,t in enumerate(tiles[:24]):sheet.paste(t,((k%4)*448,(k//4)*250))
sheet.save(out/'augmentation_preview.png')
(out/'qa_summary.json').write_text(json.dumps(dict(training_images=len(rows),transforms_checked=checks,annotation_clipping=0,fallbacks=fallback,seed=20261007,limitation='Checks annotated object bounds, not unannotated material or structures already outside source crops'),indent=2));print((out/'qa_summary.json').read_text())

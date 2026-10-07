"""Reproducible vector workflow diagrams and authentic annotation-centered examples."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
P=Path(__file__).resolve().parent;F=P/'figures'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42})
TEAL='#147D80';INK='#183640';MUTED='#536873';BG='#EDF5F4'
def workflow(name,title,subtitle,steps):
 n=len(steps);fig,ax=plt.subplots(figsize=(3.5,0.83*n+0.85));ax.set_xlim(0,3.5);ax.set_ylim(0,n+.95);ax.axis('off')
 ax.text(.09,n+.67,title,color=INK,weight='bold',fontsize=12)
 ax.text(.09,n+.37,subtitle,color=MUTED,fontsize=8)
 for i,(head,body,model) in enumerate(steps):
  y=n-i-1+.13
  ax.add_patch(FancyBboxPatch((.07,y),3.36,.77,boxstyle='round,pad=0.015,rounding_size=0.065',facecolor=TEAL if model else BG,edgecolor='none'))
  color='white' if model else INK
  ax.text(.22,y+.49,f'{i+1:02}',fontsize=9,color=color,weight='bold')
  ax.text(.65,y+.49,head,fontsize=9.1,color=color,weight='bold')
  ax.text(.65,y+.17,body,fontsize=7.3,color='white' if model else MUTED,linespacing=1.3)
  if i<n-1:ax.add_patch(FancyArrowPatch((1.75,y-.025),(1.75,y-.20),arrowstyle='-|>',mutation_scale=11,color=TEAL,lw=1.3))
 fig.subplots_adjust(left=.01,right=.99,top=.99,bottom=.01)
 fig.savefig(F/(name+'.pdf'));fig.savefig(F/(name+'.png'),dpi=240);plt.close(fig)
workflow('workflow_direct','A  Detect and identify together','PROPOSED • MULTICLASS RF-DETR',[
 ('Prepare slide regions','Multifocal image → focus stack\nRead overlapping tiles',False),
 ('Multiclass RF-DETR','Predict a box, category and score\nfor each target specimen',True),
 ('Combine tile predictions','Map boxes to slide coordinates\nMerge duplicate detections',False),
 ('Inspect labeled specimens','Location + category + score\nRetain source identity for review',False)])
workflow('workflow_two_stage','B  Detect, then classify','PROPOSED • RF-DETR + SWIN-TINY',[
 ('Prepare slide regions','Multifocal image → focus stack\nRead overlapping tiles',False),
 ('Single-class RF-DETR','Locate eligible specimens\nRetain detection scores',True),
 ('Combine and crop','Map and merge tile detections\nExtract one crop per specimen',False),
 ('Swin-Tiny classifier','Assign a category to each crop\nRetain classification scores',True),
 ('Inspect labeled specimens','Location + category + both scores\nRetain source identity for review',False)])
order=['Arecipites sp.','Bombacacidites sp.','Platycarya platycarioides','Bisaccate','Momipites sp','Cicatricosisporites sp.']
items={}
for p in (F/'specimen_sources').glob('*.json'):
 d=json.loads(p.read_text());items[d['summary']['category']]=(p,d)
fig,axes=plt.subplots(2,3,figsize=(7.16,5.3));manifest=[]
for i,(ax,c) in enumerate(zip(axes.flat,order)):
 p,d=items[c];im=Image.open(p.with_suffix('.png'));b=d['target_box_xyxy'];cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
 side=int(np.ceil(max(b[2]-b[0],b[3]-b[1])*1.35));x=max(0,min(im.width-side,int(cx-side/2)));y=max(0,min(im.height-side,int(cy-side/2)));box=[x,y,x+side,y+side]
 crop=im.crop(box);crop.save(F/'specimen_sources'/(p.stem+'_crop.png'))
 ax.imshow(crop);ax.set_xticks([]);ax.set_yticks([])
 for sp in ax.spines.values():sp.set_color('#D6E2E2')
 label=c.replace('Platycarya platycarioides','Platycarya\nplatycarioides')
 ax.set_title(chr(65+i)+'  '+label,loc='left',fontsize=9,color=INK,pad=7)
 ax.set_xlabel(f'Field width: {side} source pixels',fontsize=7,color=MUTED)
 manifest.append({'panel':chr(65+i),'category':c,'record_id':d['target']['record_id'],'slide':d['target']['slide'],'image_file':d['target']['image_file'],'original_title':d['target'].get('original_title'),'representation':'focus stack; original pilot kernel 5','source_tile':p.with_suffix('.png').name,'source_tile_sha256':hashlib.sha256(p.with_suffix('.png').read_bytes()).hexdigest(),'crop_xyxy_in_tile':box,'source_metadata':p.name,'processing':'Annotation-centered crop only; no color correction, retouching or generated imagery.'})
fig.subplots_adjust(left=.02,right=.98,bottom=.06,top=.91,wspace=.13,hspace=.38)
fig.savefig(F/'specimen_examples.pdf',dpi=250);fig.savefig(F/'specimen_examples.png',dpi=240);plt.close(fig)
(F/'specimen_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Built two vector workflow diagrams and six authentic specimen panels.')

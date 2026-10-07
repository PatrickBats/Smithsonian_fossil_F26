"""Opening scientific figure using an authentic image region and expert annotation."""
from pathlib import Path
import json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,ConnectionPatch
from PIL import Image
P=Path(__file__).resolve().parent;F=P/'figures';src=F/'specimen_sources/shard_0_target_027.png';meta=F/'specimen_sources/shard_0_target_027.json'
d=json.loads(meta.read_text());im=Image.open(src);b=d['target_box_xyxy'];pad=20
box=[int(b[0])-pad,int(b[1])-pad,int(b[2])+pad,int(b[3])+pad];crop=im.crop(box)
plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42})
fig=plt.figure(figsize=(7.16,3.85),facecolor='white');navy='#202D48';copper='#93451F'
left=fig.add_axes([.015,.17,.49,.76]);left.imshow(im);left.set_xticks([]);left.set_yticks([])
for spine in left.spines.values():spine.set_visible(False)
left.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor='white',linewidth=3.5))
left.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor='#087F83',linewidth=1.5))
left.set_title('A  A crowded microscope image',loc='left',fontsize=11,color=navy,pad=9)
right=fig.add_axes([.64,.39,.30,.52]);right.imshow(crop);right.set_xticks([]);right.set_yticks([])
for spine in right.spines.values():spine.set_color('#D6D9DE')
right.set_title('B  Inspect the specimen',loc='left',fontsize=11,color=navy,pad=9)
fig.add_artist(ConnectionPatch(xyA=(b[2],(b[1]+b[3])/2),coordsA=left.transData,xyB=(0,.5),coordsB=right.transAxes,arrowstyle='-|>',mutation_scale=16,color=copper,linewidth=1.3,shrinkA=5,shrinkB=9))
fig.text(.65,.32,'Example expert label',fontsize=9,color='#596477')
fig.text(.65,.25,'Bombacacidites sp.',fontsize=12,fontweight='bold',color=navy)
fig.text(.045,.055,'DETECTION',fontsize=10,fontweight='bold',color=copper)
fig.text(.205,.055,'Where is the specimen?',fontsize=10,color=navy)
fig.text(.58,.055,'CLASSIFICATION',fontsize=10,fontweight='bold',color=copper)
fig.text(.805,.055,'What type is it?',fontsize=10,color=navy)
fig.savefig(F/'problem_overview.pdf',dpi=300);fig.savefig(F/'problem_overview.png',dpi=250);plt.close(fig)
(F/'problem_overview_provenance.json').write_text(json.dumps({'image_source':str(src.relative_to(P)),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'record_id':d['target']['record_id'],'slide':d['target']['slide'],'expert_category':d['summary']['category'],'annotation_box':b,'crop_xyxy':box,'representation':'focus-stacked pilot input tile','image_processing':'Region crop and display scaling only; no color correction or retouching. Box derived from expert annotation, not model prediction.'},indent=2)+'\n')

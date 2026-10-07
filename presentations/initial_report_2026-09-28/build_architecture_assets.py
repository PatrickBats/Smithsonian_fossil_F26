"""Publication diagrams: conceptual modules, authentic image thumbnails, no invented predictions."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch,Rectangle
from PIL import Image
P=Path(__file__).resolve().parent;F=P/'assets';F.mkdir(exist_ok=True)
SOURCE=P.parents[1]/'reports/initial_report_complete_2026-09-27/figures'
plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42})
INK='#202D48';TEAL='#93451F';GOLD='#B87B28';MUTED='#596477';PALE='#EEE3D6';WHITE='#FFFFFF'
source=SOURCE/'specimen_sources/shard_0_target_027.png'
crop=SOURCE/'specimen_sources/shard_0_target_027_crop.png'
def rect(ax,x,y,w,h,fill,edge='none',lw=1,r=.1):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f'round,pad=0,rounding_size={r}',facecolor=fill,edgecolor=edge,linewidth=lw,zorder=2))
def txt(ax,x,y,t,size=13,color=INK,bold=False,ha='left'):
 ax.text(x,y,t,fontsize=size,color=color,fontweight='bold' if bold else 'normal',ha=ha,va='center',zorder=8,linespacing=1.4)
def arrow(ax,x1,y1,x2,y2,c=TEAL):
 ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=17,color=c,lw=1.6,zorder=7))
def photo(ax,path,x,y,w):
 ax.imshow(Image.open(path),extent=(x,x+w,y,y+w),zorder=4)
 ax.add_patch(Rectangle((x,y),w,w,fill=False,ec='#C5D9D8',lw=.8,zorder=5))
def render(two):
 fig,ax=plt.subplots(figsize=(14.4,5.15));ax.set_xlim(0,14.4);ax.set_ylim(0,5.15);ax.axis('off')
 tag='B' if two else 'A';title='Locate first. Identify second.' if two else 'Locate and identify in one model.'
 rect(ax,.13,4.42,.48,.48,TEAL)
 txt(ax,.37,4.66,tag,19,WHITE,True,'center')
 txt(ax,.80,4.71,title,25,INK,True)
 txt(ax,.80,4.23,'PROPOSED ARCHITECTURE  /  RF-DETR + SWIN-TINY' if two else 'PROPOSED ARCHITECTURE  /  MULTICLASS RF-DETR',12,MUTED)
 names=['Prepare images','RF-DETR detector','Merge + extract','Swin-Tiny','Expert review'] if two else ['Prepare images','Multiclass RF-DETR','Merge predictions','Expert review']
 widths=[2.65,2.65,2.65,2.65,2.65] if two else [3.4,3.4,3.4,3.4]
 gap=.18;xs=[];x=.16
 for w in widths:xs.append(x);x+=w+gap
 for i,(x,w,name) in enumerate(zip(xs,widths,names)):
  model=(i==1 or(two and i==3));fill=INK if model else '#F5EFE7'
  rect(ax,x+.035,.915,w,2.94,'#DFD8CF',r=.13)
  rect(ax,x,.96,w,2.94,fill,r=.13)
  txt(ax,x+.17,3.62,f'{i+1:02}',11,'#EAC5A8' if model else TEAL,True)
  txt(ax,x+.58,3.62,name,14,WHITE if model else INK,True)
  if i<len(xs)-1:arrow(ax,x+w+.008,2.43,x+w+gap-.005,2.43)
 # shared preprocessing: depth-stack schematic then actual tile
 x=xs[0];w=widths[0]
 for k in [2,1,0]:
  rect(ax,x+.22+k*.10,2.29+k*.10,.83,.74,'#E2EFEE',TEAL,.7,r=.025)
  ax.add_patch(Rectangle((x+.41+k*.10,2.49+k*.10),.32,.26,fill=False,ec=TEAL,lw=.7,zorder=3))
 arrow(ax,x+1.23,2.66,x+1.49,2.66)
 photo(ax,source,x+1.55,2.20,.86)
 for a in [1,2]:
  ax.plot([x+1.55+a*.86/3]*2,[2.20,3.06],color=WHITE,lw=.8,zorder=6)
  ax.plot([x+1.55,x+2.41],[2.20+a*.86/3]*2,color=WHITE,lw=.8,zorder=6)
 txt(ax,x+.20,1.79,'Focus stack → tiles',14)
 txt(ax,x+.20,1.30,'Read small regions',14,MUTED)
 # detector conceptual nodes
 x=xs[1];w=widths[1]
 for j,label in enumerate(['Visual features','Object queries','Boxes + scores' if two else 'Boxes + categories + scores']):
  yy=2.78-j*.51
  rect(ax,x+.20,yy,w-.40,.36,'#344560',r=.06)
  txt(ax,x+w/2,yy+.18,label,13,WHITE,False,'center')
  if j<2:arrow(ax,x+w/2,yy-.025,x+w/2,yy-.12,'#EAC5A8')
 txt(ax,x+.20,1.29,'One detection class' if two else 'Joint localization + identification',13,'#EAC5A8')
 # merge visual tileboxes
 x=xs[2];w=widths[2]
 for xx,yy in [(x+.35,2.38),(x+.65,2.60)]:
  rect(ax,xx,yy,.95,.55,'#FFFFFF','#B7A89A',.9,.04)
  ax.add_patch(Rectangle((xx+.3,yy+.14),.27,.26,fill=False,edgecolor=TEAL,lw=1.3,zorder=5))
 arrow(ax,x+1.75,2.66,x+2.03,2.66)
 if two:photo(ax,crop,x+2.10,2.47,.37)
 else:rect(ax,x+2.19,2.47,.50,.44,TEAL,r=.05);txt(ax,x+2.44,2.69,'1',16,WHITE,True,'center')
 txt(ax,x+.20,1.80,'Use slide coordinates',14)
 txt(ax,x+.20,1.30,'Merge boxes; crop' if two else 'Merge duplicate boxes',14,MUTED)
 if two:
  x=xs[3];w=widths[3]
  # shifted-window motif: conceptual attention regions, not literal layer diagram
  for j in range(4):
   for k in range(4):
    rect(ax,x+.50+k*.35,2.12+j*.24,.30,.19,'#D8AC86' if (k+j)%3 else '#F0DCCA',r=.025)
  ax.add_patch(Rectangle((x+.79,2.29),.73,.51,fill=False,edgecolor='#F1BE65',lw=1.8,zorder=6))
  txt(ax,x+.20,1.80,'Learn crop features',14,WHITE)
  txt(ax,x+.20,1.30,'Category + score',14,'#EAC5A8')
 # output example, no fake model labels
 x=xs[-1];w=widths[-1];photo(ax,crop,x+.24,2.13,.93)
 rect(ax,x+1.30,2.72,w-1.53,.13,TEAL,r=.02)
 rect(ax,x+1.30,2.46,(w-1.53)*.79,.10,'#CBA88B',r=.02)
 rect(ax,x+1.30,2.23,(w-1.53)*.57,.10,'#E1CAB5',r=.02)
 txt(ax,x+.20,1.80,'Labeled specimen',14)
 txt(ax,x+.20,1.30,'Location + both scores' if two else 'Location + score',14,MUTED)
 rect(ax,.16,.15,14.04,.49,PALE,r=.07)
 txt(ax,.36,.395,'FAIR COMPARISON',11,TEAL,True)
 txt(ax,2.41,.395,'Same category map • same grouped split • same preprocessing • held-out evaluation',12,INK)
 fig.subplots_adjust(left=0,right=1,bottom=0,top=1)
 stem='workflow_two_stage' if two else 'workflow_direct'
 fig.savefig(F/(stem+'.pdf'));fig.savefig(F/(stem+'.png'),dpi=200);plt.close(fig)
render(False);render(True)

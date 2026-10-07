from pathlib import Path
from io import BytesIO
import hashlib,json,re
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
OUT=Path(__file__).resolve().parent
SRC=Path('/home/pb52/.codex/attachments/6eb22bcf-a1da-4d6a-91f4-d22aa2fd0363/Initial Presentation.pptx')
p=Presentation(SRC)
C={'bg':'F8F5EF','ink':'202D48','accent':'93451F','light':'EEE3D6','muted':'596477','white':'FFFFFF'}
def text(s,x,y,w,h,t,size=16,color='ink',bold=False):
 sh=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=sh.text_frame;tf.word_wrap=True
 tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0
 for i,line in enumerate(t.split('\n')):
  q=tf.paragraphs[0] if i==0 else tf.add_paragraph();q.text=line;q.font.name='Lato';q.font.size=Pt(size);q.font.bold=bold;q.font.color.rgb=RGBColor.from_string(C[color]);q.space_after=Pt(5)
 return sh
def rect(s,x,y,w,h,c):
 sh=s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h));sh.fill.solid();sh.fill.fore_color.rgb=RGBColor.from_string(C[c]);sh.line.fill.background();return sh
def walk(ss):
 for sh in ss:
  if sh.shape_type==6: yield from walk(sh.shapes)
  else: yield sh
def settext(sh,t,size=None):
 from copy import deepcopy
 tf=sh.text_frame
 q=tf.paragraphs[0]
 rp=deepcopy(q.runs[0]._r.rPr) if q.runs and q.runs[0]._r.rPr is not None else None
 pp=deepcopy(q._p.pPr) if q._p.pPr is not None else None
 tf.clear()
 for i,line in enumerate(t.split('\n')):
  q=tf.paragraphs[0] if i==0 else tf.add_paragraph()
  if pp is not None:
   if q._p.pPr is not None:q._p.remove(q._p.pPr)
   q._p.insert(0,deepcopy(pp))
  r=q.add_run();r.text=line
  if rp is not None:r._r.insert(0,deepcopy(rp))
  if size:r.font.size=Pt(size)
 tf.word_wrap=True
 return sh
def byid(s,n):return next(sh for sh in walk(s.shapes) if sh.shape_id==n)
def change(s,n,t,size=None):return settext(byid(s,n),t,size)
def clean(s):
 for sh in list(s.shapes):sh._element.getparent().remove(sh._element)
def frame(s,num,section,title):
 rect(s,0,0,10,5.625,'bg');rect(s,.38,.29,.26,.04,'accent')
 text(s,.76,.20,8.85,.2,f'{num:02d} / {section}',8,'accent',True)
 if title:text(s,.38,.59,9.25,.6,title,24,bold=True)
 rect(s,.38,5.26,9.25,.009,'light');text(s,.38,5.36,8.65,.18,'SMITHSONIAN × RICE D2K',7,'muted');text(s,9.35,5.34,.3,.2,str(num),8,'muted')
# Existing background: keep its three-card layout, simplify claims and acronyms.
s=p.slides[0]
change(s,92,'Why fossil pollen matters',24)
change(s,97,'Pollen survives in sediment.\nIt records ancient plant life.\nWe study vegetation about 50 million years ago.',14)
change(s,101,'The challenge',17)
change(s,102,'Microscope images contain many specimens and debris.\nIdentifying each specimen takes expert time.',14)
change(s,106,'Our starting point',17)
change(s,107,'The previous Rice team developed a detector.\nOur next step is identifying the category of each specimen.',14)
# Three related-work cards; the third paper supplies whole-slide detection.
s=p.slides[2];clean(s);frame(s,4,'PRIOR WORK','What earlier studies suggest')
for x,num,author,body in [(.4,'01','Punyasena et al.','Locate pollen\n↓\nCrop specimens\n↓\nIdentify categories'),(3.55,'02','Martinsen et al.','Locate specimens\n↓\nCrop specimens\n↓\nIdentify categories'),(6.7,'03','Abbas Shaikh et al.','Multifocal slides\n↓\nImage tiles\n↓\nDetect specimens')]:
 rect(s,x,1.42,2.9,2.98,'white')
 text(s,x+.18,1.64,2.54,.25,num,12,'accent',True)
 text(s,x+.18,2.03,2.54,.37,author,17,bold=True)
 box=text(s,x+.18,2.64,2.54,1.65,body,15,'muted')
 for para in box.text_frame.paragraphs:para.alignment=PP_ALIGN.CENTER;para.space_after=Pt(1)
text(s,.4,4.75,9.2,.32,'Build on whole-slide detection; add category identification.',16,'accent',True)
# Example-specific microscopy details.
s=p.slides[3];change(s,154,'One specimen, multiple focal views',24)
old=byid(s,157);old._element.getparent().remove(old._element)
text(s,6.37,1.29,2.85,.65,'This example: 25 focal planes\nAbout 30 GB for the full scan',12,'muted')
# Dataset metrics: improve scannability without changing the original chart.
s=p.slides[4]
old=byid(s,170);old._element.getparent().remove(old._element)
for y,value,label in [(1.43,'83','image–annotation pairs'),(2.39,'32','priority categories'),(3.35,'2,290','annotations')]:
 text(s,.4,y,2.5,.48,value,28,'ink',True)
 text(s,.4,y+.5,2.65,.27,label,12,'muted')
text(s,.4,4.52,2.7,.47,'Some categories have\nfar fewer examples.',12,'accent',True)
# Simplify data preparation language.
s=p.slides[5];change(s,180,'Connect images, locations, and expert labels',24)
change(s,186,'Match the files',18);change(s,194,'Check the examples',18)
change(s,195,'Check positions, missing\nlabels, and duplicates.',14)
change(s,199,'Each specimen linked to its image, location, and category',14)
s=p.slides[6];change(s,208,'Prepare examples for a fair test',24)
change(s,219,'Extract small image regions;\ncheck position and focus.',14)
change(s,223,'Regions for detection;\nspecimen crops for\nclassification.',14)
change(s,227,'Vary training examples and balance categories.',14)
# Rebuild only the crowded methods slide; preserve its source images in the file.
s=p.slides[7]
method_images=[sh.image.blob for sh in s.shapes if sh.shape_type==13]
clean(s);frame(s,9,'PROPOSED METHODS','Two ways to identify specimens')
text(s,.4,1.32,9,.3,'1   FIND AND IDENTIFY TOGETHER',13,'accent',True)
rect(s,.4,1.85,4.1,.8,'white');text(s,.6,2.02,3.7,.45,'RF-DETR',20,bold=True)
text(s,4.65,2.02,.5,.4,'→',23,'accent')
rect(s,5.25,1.85,4.35,.8,'light');text(s,5.45,2.04,3.95,.45,'Location + category',19,bold=True)
text(s,.4,3.0,9,.3,'2   FIND FIRST, IDENTIFY SECOND',13,'accent',True)
for x,w,head,body in [(.4,2.65,'RF-DETR','Find specimens'),(3.65,2.65,'Specimen crops','Isolate each example'),(6.9,2.7,'Swin-Tiny','Identify its category')]:
 rect(s,x,3.52,w,.97,'white');text(s,x+.16,3.65,w-.32,.3,head,18,bold=True);text(s,x+.16,4.05,w-.32,.28,body,12,'muted')
for x in [3.15,6.4]:text(s,x,3.82,.4,.4,'→',23,'accent')
text(s,.4,4.78,9.2,.3,'Compare location accuracy and category identification.',15,'accent',True)
# Welcome and conclusion as editable slides.
w=p.slides.add_slide(p.slide_layouts[6]);frame(w,1,'WELCOME','')
rect(w,.4,1.35,.055,2.3,'accent')
text(w,.68,1.37,6.2,1.65,'Identifying Fossil Pollen\nwith Machine Learning',30,bold=True)
text(w,.7,3.15,5.7,.65,'Help researchers identify fossil pollen\ncategories more efficiently.',17,'muted')
fig=OUT.parents[1]/'reports/initial_report_complete_2026-09-27/figures/specimen_sources/shard_0_target_027_crop.png'
w.shapes.add_picture(str(fig),Inches(7.05),Inches(1.53),width=Inches(2.45),height=Inches(2.45))
text(w,.7,4.48,8.7,.4,'Patrick Batsell · Yun Ying Tsai · Yeonju Kim · Yunfan Bao · Alan Yang',12,'muted')
ids=p.slides._sldIdLst;el=ids[-1];ids.remove(el);ids.insert(0,el)
s=p.slides.add_slide(p.slide_layouts[6]);frame(s,10,'CONCLUSION','From finding pollen to identifying it')
text(s,.45,1.52,8.9,.6,'Compare two approaches to automated identification.',23,bold=True)
for x,n,title in [(.45,'01','Prepare specimen images'),(3.6,'02','Train initial models'),(6.75,'03','Evaluate mistakes')]:
 rect(s,x,2.55,2.8,1.28,'white');text(s,x+.18,2.73,2.45,.25,n,12,'accent',True);text(s,x+.18,3.12,2.43,.55,title,17,bold=True)
text(s,.45,4.35,9,.55,'Help experts study past vegetation more efficiently.',21,'accent',True)
# Standardize all retained slide headers and footers.
sections=['WELCOME','BACKGROUND','THE PROBLEM','PRIOR WORK','MICROSCOPY DATA','ANNOTATION INVENTORY','DATA PIPELINE','DATA PIPELINE','PROPOSED METHODS','CONCLUSION']
for i,s in enumerate(p.slides):
 if i in [0,8,9]:continue
 for sh in s.shapes:
  if not sh.has_text_frame:continue
  if sh.top<Inches(.45) and ' / ' in sh.text:settext(sh,f'{i+1:02d} / {sections[i]}')
  elif sh.top>Inches(5.3):
   if 'SMITHSONIAN' in sh.text:settext(sh,'SMITHSONIAN × RICE D2K')
   elif sh.text.strip().isdigit():settext(sh,str(i+1))
# Visual revision responding to mentor feedback. Retain the original microscopy assets.
F=OUT.parents[1]/'reports/initial_report_complete_2026-09-27/figures'
def pic(s,name,x,y,w,h=None):
 from PIL import Image
 path=F/name
 with Image.open(path) as im:iw,ih=im.size
 if h is None:h=w*ih/iw
 scale=min(w/iw,h/ih);ww=iw*scale;hh=ih*scale
 return s.shapes.add_picture(str(path),Inches(x+(w-ww)/2),Inches(y+(h-hh)/2),width=Inches(ww),height=Inches(hh))
def arrow(s,x,y):text(s,x,y,.45,.4,'→',24,'accent',True)
def outline(s,x,y,w,h):
 sh=rect(s,x,y,w,h,'white');sh.fill.background();sh.line.color.rgb=RGBColor.from_string(C['accent']);sh.line.width=Pt(2)
def tree(s,x,y,scale=1):
 rect(s,x+.35*scale,y+.68*scale,.12*scale,.65*scale,'accent')
 for dx,dy,r in [(0,.2,.7),(.4,.25,.65),(.2,0,.7)]:
  sh=s.shapes.add_shape(MSO_SHAPE.OVAL,Inches(x+dx*scale),Inches(y+dy*scale),Inches(r*scale),Inches(r*scale));sh.fill.solid();sh.fill.fore_color.rgb=RGBColor.from_string(C['muted']);sh.line.fill.background()
def tile(s,x,y,w):
 pic(s,'specimen_sources/shard_0_target_027.png',x,y,w,w)
 box=json.loads((F/'specimen_sources/shard_0_target_027.json').read_text())['target_box_xyxy']
 outline(s,x+w*box[0]/1024,y+w*box[1]/1024,w*(box[2]-box[0])/1024,w*(box[3]-box[1])/1024)
# Scientific motivation, with an explicitly schematic vegetation illustration.
s=p.slides[1];clean(s);frame(s,2,'WHY IT MATTERS','What grew in North America during a warmer past?')
text(s,.4,1.19,9.1,.38,'Fossil pollen preserves clues from about 50 million years ago.',17,'muted')
pic(s,'specimen_sources/shard_0_target_027_crop.png',.7,1.95,1.95,1.95)
arrow(s,3.02,2.6)
for x,y,n in [(3.85,2.15,'008'),(4.73,2.15,'016'),(4.29,3.01,'027')]:
 pic(s,f'specimen_sources/shard_0_target_{n}_crop.png',x,y,.8,.8)
arrow(s,6.0,2.6)
for x,y,z in [(7.12,2.5,.85),(7.9,2.04,1.2),(8.81,2.61,.78)]:tree(s,x,y,z)
for x,w,t in [(.45,2.6,'Fossil pollen'),(3.5,2.5,'Identify plant groups'),(6.95,2.6,'Reconstruct vegetation')]:text(s,x,4.1,w,.42,t,16,bold=True)
text(s,.45,4.8,9.1,.3,'The bottleneck: identifying thousands of specimens by hand.',17,'accent',True)
# Problem: keep the photographic detection-to-identification example.
s=p.slides[2]
for sh in s.shapes:
 if sh.has_text_frame and sh.top>Inches(.5) and sh.top<Inches(1):settext(sh,'Finding pollen is only the first step',24)
text(s,.42,4.99,9,.24,'Our goal: assign a category to each detected specimen.',14,'accent',True)
# Inventory: large counts and four representative categories, not a dense table.
s=p.slides[5];clean(s);frame(s,6,'OUR DATA','Some categories have far fewer examples')
for x,val,label in [(.45,'83','image–annotation pairs'),(3.6,'32','priority categories'),(6.75,'2,290','priority annotations')]:
 text(s,x,1.32,2.8,.5,val,30,bold=True);text(s,x,1.87,2.8,.32,label,13,'muted')
import csv
rows=list(csv.DictReader((OUT.parents[1]/'data/current/category_summary.csv').open()))
counts={r['category']:int(r['annotation_records']) for r in rows}
chosen=['Bisaccate','Arecipites sp.','Bombacacidites sp.','Cupuliferoipollenites sp.']
text(s,.45,2.43,8,.25,'LABELED EXAMPLES · FOUR SELECTED CATEGORIES',10,'muted',True)
for i,key in enumerate(chosen):
 y=2.92+i*.42;n=counts[key]
 text(s,.45,y,3,.32,key,14)
 rect(s,3.65,y+.025,4.8*n/316,.23,'accent' if i==0 else 'muted')
 text(s,3.8+4.8*n/316,y-.01,.8,.33,str(n),14,bold=True)
text(s,.45,4.83,9.1,.32,'Fewer examples can make a category harder to learn.',17,'accent',True)
# Dataset preparation with an actual image, actual annotation title, and mapped crop.
s=p.slides[6];clean(s);frame(s,7,'PREPARE LABELED EXAMPLES','Turn expert annotations into learning examples')
text(s,.45,1.28,2.75,.4,'1  Locate the specimen',16,bold=True)
text(s,3.7,1.28,2.55,.4,'2  Read its expert label',16,bold=True)
text(s,6.95,1.28,2.65,.4,'3  Extract a labeled crop',16,bold=True)
tile(s,.6,1.97,2.55);arrow(s,3.22,2.8)
rect(s,3.8,2.09,2.4,2.21,'white')
text(s,3.96,2.3,2.05,.29,'ANNOTATION TITLE',10,'muted',True)
text(s,3.96,2.71,2.05,.68,'Tiliapollenites sp.',17,bold=True)
text(s,3.96,3.6,2.05,.45,'Expert category map',12,'muted')
arrow(s,6.45,2.8);pic(s,'specimen_sources/shard_0_target_027_crop.png',7.2,1.97,2.15,2.15)
text(s,6.99,4.26,2.7,.4,'Bombacacidites sp.',15,bold=True)
text(s,.45,4.89,9.1,.28,'Check that the crop is clear and contains the marked specimen.',15,'accent',True)
# Grouped split schematic. No arbitrary percentages or counts are implied.
s=p.slides[7];clean(s);frame(s,8,'TRAINING AND TESTING','Learn from some slides; test on unseen slides')
text(s,.45,1.26,9,.34,'Mix up the microscope slides, then separate them into three groups.',16,'muted')
for x,title,desc in [(.45,'Training','Learn from examples'),(3.6,'Validation','Make adjustments'),(6.75,'Testing','Check new slides')]:
 rect(s,x,1.94,2.8,2.42,'white');text(s,x+.17,2.12,2.46,.36,title,20,bold=True)
 if title=='Training':
  # Real specimen examples, with short label bars beneath them.
  for j,num in enumerate(['008','016','027']):
   xx=x+.23+j*.8
   pic(s,f'specimen_sources/shard_0_target_{num}_crop.png',xx,2.82,.69,.69)
   rect(s,xx+.07,3.59,.55,.055,'accent')
 elif title=='Validation':
  # Three adjustable controls communicate model tuning.
  for j,offset in enumerate([.55,1.54,.99]):
   yy=2.86+j*.32
   rect(s,x+.35,yy,2.1,.045,'light')
   rect(s,x+.35,yy,offset-.35,.045,'accent')
   sh=s.shapes.add_shape(MSO_SHAPE.OVAL,Inches(x+offset-.105),Inches(yy-.083),Inches(.21),Inches(.21))
   sh.fill.solid();sh.fill.fore_color.rgb=RGBColor.from_string(C['accent']);sh.line.fill.background()
 else:
  # A held-out evaluation sheet with visible checks.
  rect(s,x+.69,2.66,1.39,1.0,'light');outline(s,x+.69,2.66,1.39,1.0)
  for j in range(3):
   yy=2.81+j*.25
   text(s,x+.81,yy-.05,.28,.27,'✓',17,'accent',True)
   rect(s,x+1.15,yy+.065,.7,.045,'muted')
 text(s,x+.17,3.84,2.48,.34,desc,15,'muted')
text(s,.45,4.78,9.1,.34,'All examples from one microscope slide stay in the same group.',16,'accent',True)
# Methods foreground the job performed, with model names secondary.
s=p.slides[8];clean(s);frame(s,9,'OUR COMPARISON','Does a dedicated classifier improve identification?')
text(s,.45,1.29,9,.3,'A  ONE MODEL DOES BOTH JOBS',12,'accent',True)
rect(s,.45,1.82,3.16,.91,'white');text(s,.64,1.95,2.8,.35,'Find + identify',20,bold=True);text(s,.64,2.39,2.8,.22,'RF-DETR',10,'muted')
arrow(s,3.82,2.08);text(s,4.47,2.08,4.8,.45,'Specimen locations + categories',18,bold=True)
text(s,.45,3.04,9,.3,'B  TWO MODELS SHARE THE WORK',12,'accent',True)
rect(s,.45,3.54,2.65,.94,'white');text(s,.64,3.69,2.3,.32,'Find specimens',19,bold=True);text(s,.64,4.13,2.3,.22,'Detector · RF-DETR',10,'muted')
arrow(s,3.28,3.79);pic(s,'specimen_sources/shard_0_target_027_crop.png',4.16,3.47,1.03,1.03)
arrow(s,5.67,3.79)
rect(s,6.35,3.54,3.2,.94,'white');text(s,6.54,3.69,2.82,.32,'Identify each crop',19,bold=True);text(s,6.54,4.13,2.82,.22,'Classifier · Swin-Tiny',10,'muted')
text(s,.45,4.87,9.1,.26,'Compare correct locations and labels on the same held-out slides.',15,'accent',True)
# Intended output is explicitly illustrative; no fabricated prediction confidence.
s=p.slides[9];clean(s);frame(s,10,'TAKE-HOME MESSAGE','Make fossil pollen collections easier to study')
text(s,.45,1.29,9,.33,'INTENDED OUTPUT: LOCATED, LABELED SPECIMENS FOR EXPERT REVIEW',12,'accent',True)
tile(s,.58,1.98,2.35);arrow(s,3.14,2.74)
pic(s,'specimen_sources/shard_0_target_027_crop.png',3.86,2.05,1.82,1.82)
text(s,6.12,2.12,3.45,.74,'A suggested category\nfor the expert to review',21,bold=True)
text(s,6.12,3.26,3.4,.55,'Example: Bombacacidites sp.',15,'muted')
text(s,3.83,4.02,5.7,.24,'Illustration uses an expert label, not a model prediction.',10,'muted')
text(s,.45,4.6,9.1,.37,'Less manual identification. More evidence about past vegetation.',17,'accent',True)
text(s,.45,5.01,9.1,.2,'NEXT: prepare crops → train both approaches → compare their errors',11,'muted')

notes=['Hi everyone. We’re the Rice D2K Smithsonian team. We’re using machine learning to help researchers identify fossil pollen.', 'Our scientific question is: what grew in North America when the climate was warmer, about fifty million years ago? Fossil pollen gives researchers clues about the plants that lived there. But identifying thousands of tiny specimens by hand takes expert time. We want to help with that identification step so researchers can study more of the collection.', 'This image shows the gap we’re addressing. The previous team developed a detector to find specimens, like the one inside this box. But a location alone doesn’t tell researchers what kind of pollen it is. Our goal is to add that category identification, using details of the specimen’s shape and surface.', 'These three studies give us our starting point. Punyasena and Martinsen locate specimens and then classify individual crops. Abbas Shaikh and colleagues developed a pipeline for detecting specimens across large, multifocal slides. We’ll build on whole-slide detection and compare two ways to add category identification.', 'Each scan captures different focal depths, so different details become clear in different views. This example has twenty-five focal planes, and the full scan is about thirty gigabytes. We’ll extract smaller regions so we can work with individual specimens.', 'We have eighty-three image and annotation pairs. Our starting selection includes thirty-two priority categories and two thousand two hundred ninety annotations. These four categories illustrate the imbalance: some have hundreds of examples, while others have only a few dozen. That can make the less common categories harder to learn.', 'Here’s how we turn the annotations into learning examples. First, we locate the marked specimen in the image. We read its expert label and use the supplied mapping to connect it to a target category. Then we extract a small image around it and check that it’s clear and properly positioned. The result is a specimen image paired with its category.', 'Next, we mix up the microscope slides and divide them into training, validation, and testing groups. The model learns from training examples, validation helps us make adjustments, and testing checks how well it works on new slides. All examples from one slide stay together. We can also balance the training examples so the most common categories don’t dominate.', 'We’ll compare two ways to do the job. In the first, one model finds each specimen and identifies its category at the same time. In the second, a detector finds the specimens, and a separate classifier identifies each crop. The question is whether giving identification its own model improves the results. We don’t know yet which will work better. We’ll compare them on the same held-out slides, checking both the locations and the categories, including less common categories.', 'Our intended result is a set of located, labeled specimens that experts can review. The aim is to reduce repetitive identification work and help researchers study past vegetation. Next, we’ll prepare the crops, train both approaches, and compare their mistakes. Thank you.']
times=[10,30,25,25,20,25,30,30,50,25]
titles=['Welcome','Background','The problem','Previous approaches','Microscopy data','Annotation inventory','Organizing the data','Preparing examples','Proposed methods','Conclusion']
assert len(p.slides)==10
manifest=[];md=['# Speaker notes\n','Target: 4:30 speaking, with up to 30 seconds for transitions. The rubric specifies exactly five minutes; rehearse to approach five minutes without running over.\n','Presenter blocks: 1 → slides 1–2; 2 → slides 3–4; 3 → slides 5–6; 4 → slides 7–8; 5 → slides 9–10. Assign names within the team.\n']
for i,(s,n,t,title) in enumerate(zip(p.slides,notes,times,titles)):
 count=len(n.split());s.notes_slide.notes_text_frame.text=f'TARGET: {t} seconds | PRESENTER {i//2+1}\n\nSAY:\n{n}'
 manifest.append({'slide':i+1,'title':title,'seconds':t,'words':count,'presenter':i//2+1})
 md.append(f'## Slide {i+1}: {title} — {t} seconds\n\n{n}\n')
assert 480<=sum(x['words'] for x in manifest)<=570,sum(x['words'] for x in manifest)
p.save(OUT/'Smithsonian_initial_presentation_feedback.pptx')
(OUT/'speaker_notes.md').write_text('\n'.join(md))
(OUT/'timing.json').write_text(json.dumps(manifest,indent=2)+'\n')
(OUT/'source_manifest.json').write_text(json.dumps({'source_filename':SRC.name,'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'slides':10,'spoken_words':sum(x['words'] for x in manifest),'planned_seconds':sum(times),'original_preserved':True},indent=2)+'\n')
print('WORDS',sum(x['words'] for x in manifest));print(manifest)

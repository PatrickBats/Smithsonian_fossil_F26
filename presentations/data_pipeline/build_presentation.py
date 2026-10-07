from pathlib import Path
import textwrap,json,hashlib,re
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
import fitz
P=Path(__file__).resolve().parent;R=P.parents[1];A=R/'reports/initial_report_complete_2026-09-27/figures/specimen_sources'
W,H=960,540
C={'bg':'F8F5EF','ink':'202D48','teal':'93451F','light':'EEE3D6','muted':'596477','white':'FFFFFF','gold':'B97832'}
for n,f in [('Lato','Lato-Regular.ttf'),('Lato-Bold','Lato-Bold.ttf')]:pdfmetrics.registerFont(TTFont(n,'/usr/share/fonts/truetype/lato/'+f))
prs=Presentation();prs.slide_width=Pt(W);prs.slide_height=Pt(H)
pdf=canvas.Canvas(str(P/'Smithsonian_data_pipeline.pdf'),pagesize=(W,H));notes=[];bounds=[]
def rect(x,y,w,h,c):
 c=C.get(c,c);sh=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Pt(x),Pt(y),Pt(w),Pt(h));sh.fill.solid();sh.fill.fore_color.rgb=RGBColor.from_string(c);sh.line.fill.background();pdf.setFillColor('#'+c);pdf.rect(x,H-y-h,w,h,stroke=0,fill=1)
def tx(t,x,y,w,size=20,c='ink',bold=False):
 font='Lato-Bold' if bold else 'Lato';lines=[]
 for para in t.split('\n'):
  line=''
  for word in para.split():
   cand=(line+' '+word).strip()
   if line and pdfmetrics.stringWidth(cand,font,size)>w:lines.append(line);line=word
   else:line=cand
  lines.append(line)
 height=len(lines)*size*1.2+4;bounds.append((len(prs.slides),t[:40],x,y,w,height))
 sh=s.shapes.add_textbox(Pt(x),Pt(y),Pt(w),Pt(height));tf=sh.text_frame;tf.clear();tf.word_wrap=False;tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0
 for i,line in enumerate(lines):
  p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line;p.font.name='Lato';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=RGBColor.from_string(C.get(c,c));p.line_spacing=Pt(size*1.2);p.space_after=Pt(0)
 pdf.setFont(font,size);pdf.setFillColor('#'+C.get(c,c))
 for i,line in enumerate(lines):pdf.drawString(x,H-y-size-i*size*1.2,line)
def pic(path,x,y,w,h):
 iw,ih=Image.open(path).size;scale=min(w/iw,h/ih);ww=iw*scale;hh=ih*scale;x+=(w-ww)/2;y+=(h-hh)/2
 s.shapes.add_picture(str(path),Pt(x),Pt(y),width=Pt(ww),height=Pt(hh));pdf.drawImage(str(path),x,H-y-hh,ww,hh)
def new(k,title):
 global s
 s=prs.slides.add_slide(prs.slide_layouts[6]);rect(0,0,W,H,'bg');rect(36,28,25,4,'teal');tx(k,73,20,850,11,'teal',True);tx(title,36,57,888,32,bold=True)
 rect(36,505,888,1,'light');tx('SMITHSONIAN × RICE D2K  /  DATA PIPELINE',36,516,830,9,'muted');tx(str(len(prs.slides)),900,514,24,11,'teal',True)
def end(title,seconds,spoken,source):
 n=f'TARGET: {seconds} seconds\n\nSAY:\n{spoken}\n\nSOURCE / PRESENTER CONTEXT (not spoken):\n{source}'
 s.notes_slide.notes_text_frame.text=n;notes.append(dict(slide=len(prs.slides),title=title,seconds=seconds,script=spoken,source=source));pdf.showPage()
def banner(t):rect(36,444,888,43,'light');tx(t,50,454,860,18,'teal',True)
new('01 / DATA PIPELINE','Connect each specimen to its image and expert label')
for x,n,h,b in [(36,'01','Register the sources','Pair each microscope image with its annotation file.'),(338,'02','Map expert labels','Link original annotation titles to the target categories.'),(640,'03','Audit the inventory','Check geometry, missing labels, duplicates, and slide coverage.')]:
 rect(x,141,284,232,'white');tx(n,x+18,159,247,18,'teal',True);tx(h,x+18,201,247,25,bold=True);tx(b,x+18,282,247,19,'muted')
for x in [319,621]:tx('→',x,238,20,18,'teal',True)
tx('OUTPUT',36,394,105,13,'teal',True);tx('Specimen ID + slide + coordinates + original label + mapped category',151,388,773,20,bold=True)
end('Sources to specimen inventory',40,'We begin with two linked sources: the large microscope images and the separate expert annotation files. Each annotation is connected to its source slide, location, original identification, and mapped category. The existing inventory covers eighty-three image and annotation pairs, with two thousand two hundred ninety records in the initial target categories. We then check geometry, duplicate candidates, missing labels, and coverage across slides. The output is a traceable specimen inventory; it is not yet a quality-checked training dataset.', 'Current verified data inventory and report Sections III–IV. Completed: pairing and count reconciliation. Crop quality and duplicate review remain preparation tasks. NO and unmarked objects are not automatically background.')
new('02 / DATA PIPELINE','Prepare model inputs without mixing training and testing')
for x,n,h,b in [(36,'01','Group and split','Keep related slides and every view of a specimen together.'),(338,'02','Extract and inspect','Read local focal stacks; check alignment, focus, and crop margins.'),(640,'03','Build model inputs','Focus-stacked tiles for detection; specimen crops for classification.')]:
 rect(x,141,284,232,'white');tx(n,x+18,159,247,18,'teal',True);tx(h,x+18,201,247,25,bold=True);tx(b,x+18,275,247,19,'muted')
for x in [319,621]:tx('→',x,238,20,18,'teal',True)
tx('TRAINING ONLY',36,396,170,13,'teal',True);tx('Augmentation and class balancing; keep evaluation sets fixed.',223,389,700,20,bold=True)
end('Inventory to model-ready inputs',40,'Before preparing the full model inputs, we define training, validation, and test groups by slide and investigate related samples that need to stay together. All focal planes and augmented views of a specimen follow its assigned group. We read small regions from the images, inspect alignment and image quality, and prepare focus-stacked detector tiles and specimen crops. Balancing and augmentation apply only to training. Saved identifiers and settings let us trace each input back to its original annotation.', 'Report Sections IV–V. Diagram describes the planned main experiment, not a completed split or extraction run. Small quality-inspection samples may precede the final split. Tile merging and model inference belong to the architecture slides.')
for page,t,x,y,w,h in bounds:assert x>=0 and y>=0 and x+w<=W+1 and y+h<=H+1,(page,t,y,h)
prs.save(P/'Smithsonian_data_pipeline.pptx');pdf.save()
count=sum(len(re.findall(r"\b[\w’-]+\b",n['script'])) for n in notes)
(P/'speaker_notes.md').write_text('# Under-five-minute speaker guide\n\nTwo standalone slides. Planned delivery: 80 seconds. Spoken script: '+str(count)+' words. At 125 words/minute this is approximately '+str(round(count/125,1))+' minutes before pauses. Rehearse once; timing is a target, not a guarantee. Source notes are not spoken.\n\n'+'\n\n'.join(f"## Slide {n['slide']} — {n['title']} ({n['seconds']} seconds)\n\n{n['script']}\n\nPresenter reference: {n['source']}" for n in notes))
(P/'timing.json').write_text(json.dumps({'slides':2,'target_seconds':sum(n['seconds'] for n in notes),'spoken_words':count,'slides_timing':notes},indent=2))
doc=fitz.open(P/'Smithsonian_data_pipeline.pdf');thumbs=[]
for i,page in enumerate(doc):
 path=P/f'slide_{i+1:02}.png';page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(path);thumbs.append(Image.open(path).resize((640,360)))
sheet=Image.new('RGB',(1280,360),'white')
for i,im in enumerate(thumbs):sheet.paste(im,((i%2)*640,(i//2)*360))
sheet.save(P/'slide_overview.png')
print('Slides:',len(prs.slides),'Spoken words:',count,'Target seconds:',sum(n['seconds'] for n in notes))

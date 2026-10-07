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
pdf=canvas.Canvas(str(P/'Smithsonian_background.pdf'),pagesize=(W,H));notes=[];bounds=[]
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
 rect(36,505,888,1,'light');tx('SMITHSONIAN × RICE D2K  /  PROJECT BACKGROUND',36,516,830,9,'muted');tx(str(len(prs.slides)),900,514,24,11,'teal',True)
def end(title,seconds,spoken,source):
 n=f'TARGET: {seconds} seconds\n\nSAY:\n{spoken}\n\nSOURCE / PRESENTER CONTEXT (not spoken):\n{source}'
 s.notes_slide.notes_text_frame.text=n;notes.append(dict(slide=len(prs.slides),title=title,seconds=seconds,script=spoken,source=source));pdf.showPage()
def banner(t):rect(36,444,888,43,'light');tx(t,50,454,860,18,'teal',True)
new('BACKGROUND','Tiny fossils help us understand ancient environments')
tx('Pollen preserves a record\nof past plant life.',36,145,472,31,bold=True)
tx('Smithsonian researchers study North American vegetation from about 50 million years ago.',36,255,460,23,'muted')
tx('Identifying thousands of specimens by hand takes expert time.',36,359,460,23,'ink',True)
pic(A/'shard_0_target_008_crop.png',570,139,315,285)
tx('Fossil pollen • expert-labeled specimen',553,434,370,14,'muted')
end('Background',30,'Pollen can survive as a fossil long after the plant itself is gone. By identifying it, researchers can work out what kinds of plants lived in an area and learn about past environments. Our project focuses on North American vegetation from about fifty million years ago. The challenge is that microscope slides contain lots of tiny specimens, and identifying them by hand takes expert time. We want to use machine learning to help with that process.', 'Scientific motivation from the supplied sponsor presentation and initial report. Image: expert-labeled Platycarya platycarioides focus-stacked crop from the project dataset; not a model prediction.')
for page,t,x,y,w,h in bounds:assert x>=0 and y>=0 and x+w<=W+1 and y+h<=H+1,(page,t,y,h)
prs.save(P/'Smithsonian_background.pptx');pdf.save()
count=sum(len(re.findall(r"\b[\w’-]+\b",n['script'])) for n in notes)
(P/'speaker_notes.md').write_text('# Under-five-minute speaker guide\n\nOne background slide. Planned delivery: 30 seconds. Spoken script: '+str(count)+' words. At 125 words/minute this is approximately '+str(round(count/125,1))+' minutes before pauses. Rehearse once; timing is a target, not a guarantee. Source notes are not spoken.\n\n'+'\n\n'.join(f"## Slide {n['slide']} — {n['title']} ({n['seconds']} seconds)\n\n{n['script']}\n\nPresenter reference: {n['source']}" for n in notes))
(P/'timing.json').write_text(json.dumps({'slides':1,'target_seconds':sum(n['seconds'] for n in notes),'spoken_words':count,'slides_timing':notes},indent=2))
doc=fitz.open(P/'Smithsonian_background.pdf');thumbs=[]
for i,page in enumerate(doc):
 path=P/f'slide_{i+1:02}.png';page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(path);thumbs.append(Image.open(path).resize((640,360)))
sheet=Image.new('RGB',(640,360),'white')
for i,im in enumerate(thumbs):sheet.paste(im,((i%2)*640,(i//2)*360))
sheet.save(P/'slide_overview.png')
print('Slides:',len(prs.slides),'Spoken words:',count,'Target seconds:',sum(n['seconds'] for n in notes))

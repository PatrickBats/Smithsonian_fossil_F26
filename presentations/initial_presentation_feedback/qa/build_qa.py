from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,KeepTogether,PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
OUT=Path(__file__).resolve().parent
for name,file in [('Lato','Regular'),('Lato-Bold','Bold'),('Lato-Italic','Italic')]:pdfmetrics.registerFont(TTFont(name,f'/usr/share/fonts/truetype/lato/Lato-{file}.ttf'))
pdfmetrics.registerFontFamily('Lato',normal='Lato',bold='Lato-Bold',italic='Lato-Italic',boldItalic='Lato-Bold')
sections=[('The questions to practice first',[
('What exactly is the project trying to do?','We want to locate fossil pollen in microscope images and identify its category. The previous team developed a detector to find specimens. We’re adding category identification so experts have labeled examples they can review.'),
('Why does fossil pollen matter?','Fossil pollen gives researchers evidence about which plants lived in an area. That helps them reconstruct ancient vegetation and understand past environments. Our project supports the identification step; the model itself is not predicting ancient climate.'),
('What have you completed so far?','We’ve accessed the data, reconciled annotation labels with the sponsor’s tables, generated previews, and run an initial check of existing detector checkpoints. Preparing the full training dataset and training the classifiers are still ahead.'),
('Why compare one model with two models?','One model can find and identify specimens together. A separate classifier can focus on each cropped specimen. We’re testing whether that separation improves identification. It adds another step, so two models are not automatically better.'),
('How accurate is the system right now?','We don’t have classification results yet. Our small detector check measured recovery of known, annotation-centered targets. It does not establish classification accuracy or performance across complete unseen slides.'),
('What will the final product look like?','The goal is to show experts specimen locations and suggested categories in a simple review interface. We’ll also report where the system works well and where it struggles. The predicted labels are intended to support expert review.')]),
('Data, labels, and a fair evaluation',[
('How much data do you have?','We have 83 microscope image–annotation pairs. The current collection contains 11,275 named annotations across 65 mapped categories. Our starting classification selection is 32 priority categories with 2,290 annotations. Those are label counts before the full crop-quality review.'),
('Is 2,290 examples enough for 32 categories?','It gives us a starting point, but we can’t promise reliable performance for every category. We plan to adapt pretrained models rather than learn everything from scratch. Performance will depend on image quality, category similarity, and how many independent slides represent each category.'),
('How will you handle categories with fewer examples?','We can give rare categories more emphasis during training, use balanced training batches, or reduce the dominance of abundant categories. We’ll assess those choices with validation data and discuss any category grouping with the experts. We won’t rebalance the test set just to improve scores.'),
('Who supplies the labels, and why does a name change on slide 7?','Experts provide specimen locations and identification titles. The sponsor’s table maps those titles to target categories. In the illustrated example, Tiliapollenites sp. maps to Bombacacidites sp. We are following that supplied grouping, not independently declaring the names taxonomically equivalent.'),
('Why keep examples from the same microscope slide together?','Specimens on one slide share staining, background, and imaging conditions. Mixing them across training and testing could make the test too easy. We mix up slides, not individual crops, and keep all views of a specimen together. We’ll also check relationships between slides.'),
('How will you decide whether a model works?','We’ll check whether it finds specimens and assigns the correct categories on held-out slides. We’ll inspect category-level errors, not just overall accuracy. For detection precision and average precision, evaluation regions need sufficiently complete annotations so genuine unlabeled specimens aren’t incorrectly counted as false alarms.')]),
('Models: DETR, RF-DETR, and Swin-Tiny',[
('What is a transformer in an image model?','It is a neural-network architecture that uses attention to combine information from image features. Attention lets the model learn which visual information matters together. For pollen, useful information might include shape and surface patterns, but we need experiments to establish what it actually learns.'),
('How does DETR detect objects?','DETR means Detection Transformer. It extracts image features and uses learned object queries—prediction slots—to propose objects. It predicts a bounding box and category for each object. During training, predictions are matched to expert annotations so the model can learn from location and category errors.'),
('Is RF-DETR the same as the original DETR?','RF-DETR is a newer detector in the DETR family, not the identical original architecture. It uses a vision-transformer backbone and a detection decoder. For our presentation, the important point is that it can predict both object locations and categories.'),
('How does Swin-Tiny work, and why use it?','Swin processes image patches using attention within local windows. The windows shift between layers so neighboring regions exchange information, and later stages combine features at larger scales. Tiny is a smaller Swin variant. We propose using it to classify specimen crops; its suitability still needs testing.'),
('What is the practical difference between RF-DETR and Swin-Tiny?','In our pipeline, RF-DETR receives a larger image region and predicts multiple specimen boxes. It can also predict their categories. Swin-Tiny receives an individual specimen crop and predicts its category. Both use transformers, but their assigned tasks and outputs differ. Swin can also be used in other vision systems.'),
('What happens if the detector misses a specimen or crops it badly?','A missed specimen never reaches the separate classifier, and a poor crop may hide identifying features. We’ll first evaluate classification on expert-defined crops, then on detector crops, to distinguish classification errors from detection errors. The full-pipeline evaluation must still count missed specimens.')]),
('Focal planes and the Abbas Shaikh paper',[
('What are focal planes? Are they separate specimens?','They are images of the same location captured at different focus depths, like turning a microscope’s focus knob. Different details become sharp in different views. The example has 25 planes, but those are 25 views of the same specimen—not 25 independent training examples.'),
('How did the Abbas paper process the large images?','It divided images into overlapping tiles, using 1024-by-1024-pixel tiles with 10% overlap in preprocessing. It converted each tile’s focal stack into one 2D image, ran a detector, and combined tile predictions while removing duplicates. The model did not receive the entire raw slide at once.'),
('What is the difference between focus stacking and selecting a plane?','Focus stacking chooses sharp information from different planes to build one composite image. The paper used a Laplacian-of-Gaussian focus measure at each pixel. Plane selection keeps one entire plane per tile, chosen using a Tenengrad sharpness score based on image gradients.'),
('Which focal method worked better in the paper?','RF-DETR-2XL achieved detection AP50 of 0.879 with focus stacking and 0.877 with plane selection—very similar results. YOLO26-L favored plane selection: 0.860 versus 0.826. The best reported pairing was RF-DETR with focus stacking. These are detection metrics, not category-classification accuracy.'),
('Why not automatically use focus stacking for our classifier?','Stacking can reveal details at different depths, but it can also introduce artificial edges and other artifacts. Selecting one plane avoids compositing artifacts but can leave useful details blurry. The best representation for finding specimens may differ from the best representation for identifying their categories.'),
('Did Abbas use Swin-Tiny or classify the pollen categories?','No. The supplied paper evaluated YOLO26-L and RF-DETR-2XL for single-class palynomorph detection. It did not use Swin-Tiny or distinguish our target categories. We can build on its image-processing and detection work, while testing classification as the next step.')])]
ink=colors.HexColor('#202D48');copper=colors.HexColor('#93451F');muted=colors.HexColor('#596477')
styles={
 'k':ParagraphStyle('k',fontName='Lato-Bold',fontSize=9,leading=12,textColor=copper,spaceAfter=9),
 't':ParagraphStyle('t',fontName='Lato-Bold',fontSize=23,leading=27,textColor=ink,spaceAfter=9),
 'sub':ParagraphStyle('sub',fontName='Lato',fontSize=10,leading=14,textColor=muted,spaceAfter=15),
 'q':ParagraphStyle('q',fontName='Lato-Bold',fontSize=11,leading=14,textColor=ink,spaceAfter=5),
 'a':ParagraphStyle('a',fontName='Lato',fontSize=10.2,leading=14,textColor=ink,spaceAfter=13),
 'src':ParagraphStyle('src',fontName='Lato',fontSize=8,leading=10,textColor=muted,spaceAfter=0)}
story=[];n=0
for i,(title,items) in enumerate(sections):
 if i:story.append(PageBreak())
 story += [Paragraph('SMITHSONIAN × RICE D2K / PRESENTATION Q&amp;A',styles['k']),Paragraph(title,styles['t']),Paragraph('Practice short answers. Describe proposed work as planned, and avoid promising results before evaluation.' if i==0 else 'Suggested spoken answers • use the detail only if the audience asks.',styles['sub'])]
 for q,a in items:
  n+=1;story.append(KeepTogether([Paragraph(f'{n:02d}  {escape(q)}',styles['q']),Paragraph(escape(a),styles['a'])]))
 if i==3:
  story.append(Paragraph('Sources: supplied Shaikh et al. preprint, Sections 4.2–4.3 and Table 1; current project inventory and presentation notes. Architecture references: <link href="https://arxiv.org/abs/2005.12872" color="#93451F">DETR</link>, <link href="https://arxiv.org/abs/2103.14030" color="#93451F">Swin</link>, <link href="https://github.com/roboflow/rf-detr" color="#93451F">RF-DETR</link>.',styles['src']))
def page(c,d):
 c.setFillColor(copper);c.rect(43,759,30,3,fill=1,stroke=0)
 c.setStrokeColor(colors.HexColor('#DDD6CA'));c.line(43,40,569,40)
 c.setFillColor(muted);c.setFont('Lato',8);c.drawString(43,25,'Initial presentation • team preparation');c.drawRightString(569,25,str(d.page))
file=OUT/'Smithsonian_presentation_QA.pdf'
SimpleDocTemplate(str(file),pagesize=(612,792),rightMargin=43,leftMargin=43,topMargin=48,bottomMargin=53,title='Smithsonian Presentation — Questions and Suggested Answers',author='Rice D2K Smithsonian Team').build(story,onFirstPage=page,onLaterPages=page)
print(file)

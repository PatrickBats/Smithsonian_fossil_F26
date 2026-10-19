"""Unmodified Spring inference plus a same-tile frozen Swin handoff.

Validation diagnostic only: the reused Spring model saw some validation slides.
Source NDPA files are copied before native inference can rewrite them.
"""
import os, sys, csv, json, math, shutil, hashlib, gc
from pathlib import Path
os.environ['NO_ALBUMENTATIONS_UPDATE']='1'
os.environ['PALYNET_NUM_WORKERS']='0'
HERE=Path(__file__).resolve().parent
sys.path.insert(0,os.environ.get('SPRING_SOURCE',str(HERE/'upstream')))
import torch
import numpy as np
from PIL import Image, ImageOps
from torchvision.models import swin_t
from torchvision.transforms import functional as TF
from torchvision.ops import box_iou
from src.annotator.config import AnnotatorConfig
from src.annotator.pipeline import NDPIAnnotator

BASE=Path(os.environ.get('SMITHSONIAN_ROOT','/rhf/allocations/dsci435/Smithsonian_F26'))
OLD=BASE/'model_B/runs/abbas_focus_stack_v1/separate_slides/ordinary_baseline'
OUT=BASE/'model_B/runs/abbas_best_plane_original_v1'
SWIN=BASE/'runs/broad_swin_2026-10-08/separate_slides/ordinary_baseline/best.pt'
WEIGHT=BASE/'weights/rfdetr(2xl)_best_plane.pth'
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2),encoding='utf-8');temp.chmod(0o640);temp.replace(path)
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
def crop_input(image,box):
    x0,y0,x1,y1=box;pad=.1*max(x1-x0,y1-y0)
    b=(math.floor(x0-pad),math.floor(y0-pad),math.ceil(x1+pad),math.ceil(y1+pad))
    canvas=Image.new('RGB',(b[2]-b[0],b[3]-b[1]),'white')
    clip=(max(0,b[0]),max(0,b[1]),min(image.width,b[2]),min(image.height,b[3]))
    if clip[2]>clip[0] and clip[3]>clip[1]:canvas.paste(image.crop(clip),(clip[0]-b[0],clip[1]-b[1]))
    side=max(canvas.size)
    return ImageOps.pad(canvas,(side,side),color='white').resize((224,224),Image.Resampling.BICUBIC)
def key(d):return (d.x1_px,d.y1_px,d.x2_px,d.y2_px,d.score)

class Handoff(NDPIAnnotator):
    def attach(self,swin,labels):
        self.swin=swin;self.labels=labels;self.origins={};self.results=[]
        grid=self._build_tile_grid()
        self.sequence=iter(t for band in self._group_into_bands(grid,8192) for t in band[4])
        self.call_count=0
        save(Path(self.config.output_dir)/'tile_grid.json',[vars(t) for t in grid])
        native_predict=self.detector.predict
        def capture(tile_image):
            spec=next(self.sequence);self.call_count+=1
            boxes,scores=native_predict(tile_image)
            if len(boxes):
                image=Image.fromarray(np.asarray(tile_image,dtype=np.uint8)).convert('RGB')
                for box,score in zip(boxes,scores):
                    k=tuple(float(offset+v) for offset,v in zip((spec.x,spec.y,spec.x,spec.y),box))+(float(score),)
                    self.origins.setdefault(k,(image,[float(v) for v in box],spec.x,spec.y))
            return boxes,scores
        self.detector.predict=capture
    def _write_crops(self,detections,*args,**kwargs):
        # Only the new crop-to-Swin bridge is overridden; native inference is intact.
        for start in range(0,len(detections),32):
            batch=detections[start:start+32];inputs=[]
            for d in batch:
                image,box,_,_=self.origins[key(d)]
                inputs.append(TF.normalize(TF.to_tensor(crop_input(image,box)),[.485,.456,.406],[.229,.224,.225]))
            with torch.inference_mode():probs=self.swin(torch.stack(inputs).cuda()).softmax(-1).cpu()
            for d,prob in zip(batch,probs):
                image,box,x,y=self.origins[key(d)];i=int(prob.argmax())
                self.results.append({'box_slide':list(key(d)[:4]),'score':d.score,'category':self.labels[i],'classification_score':float(prob[i]),'source':self.config.ndpi_path,'box_tile':box,'tile_origin':[x,y]})

def main():
    assert torch.cuda.is_available(),'GPU required'
    refs=[r for i in range(4) for r in json.loads((OLD/f'export_shard_{i}_references.json').read_text()) if r['split']=='val']
    assert len(refs)==274 and len({r['record_id'] for r in refs})==274
    assignment=BASE/'runs/broad_swin_2026-10-08/separate_slides/ordinary_baseline/record_assignments.csv'
    rows=list(csv.DictReader(assignment.open()))
    sources={r['image_nots_path']:r['annotation_nots_path'] for r in rows if r['split']=='val'}
    assert len(sources)==14
    assert sha(SWIN)=='14d6e2d2727563c077320a82f77163fcd1e25eefaea6a41e84f9b1e415c53e70'
    ckpt=torch.load(SWIN,map_location='cpu',weights_only=False);labels=ckpt['categories'];assert len(labels)==28
    swin=swin_t(weights=None);swin.head=torch.nn.Linear(swin.head.in_features,28);swin.load_state_dict(ckpt['model'],strict=True);swin.cuda().eval();del ckpt
    save(OUT/'configuration.json',{'upstream_commit':'1b62b68a0d95178e6275ef55c38ee4765317b334','overlap':.1,'tile_size':1000,'stride':900,'magnification':40,'compression':'best_focal_plane','tenengrad_ksize':3,'confidence_threshold':.5,'nms_iou_threshold':.5,'detector_checkpoint':str(WEIGHT),'detector_sha256':sha(WEIGHT),'swin_checkpoint':str(SWIN),'swin_sha256':sha(SWIN),'test_used':False,'caveat':'13/14 validation slides were seen in original Spring training; diagnostic comparison only','crop_margin':.1,'crop_size':224})
    predictions=[];matches=[]
    for number,(source,annotation) in enumerate(sorted(sources.items()),1):
        slide_dir=OUT/'slides'/Path(source).stem;slide_dir.mkdir(parents=True,exist_ok=True)
        snapshot=slide_dir/'source_annotation.ndpa';working=slide_dir/'predictions.ndpa'
        shutil.copyfile(annotation,snapshot);shutil.copyfile(snapshot,working)
        source_hash=sha(Path(annotation))
        config=AnnotatorConfig(ndpi_path=source,output_dir=str(slide_dir),model_name='rfdetr',checkpoint_path=str(WEIGHT),overlap=.1,magnification=40,compression_method='best_focal_plane',tenengrad_ksize=3,rfdetr_variant='2xlarge',export_crops=True,ndpa_path=str(working))
        annotator=Handoff(config);annotator.attach(swin,labels);native=annotator.run()
        candidates=annotator.results;assert len(candidates)==len(native)
        assert sha(Path(annotation))==source_hash,'Source annotation changed'
        truth=[r for r in refs if r['image']==source]
        overlaps=box_iou(torch.tensor([p['box_slide'] for p in candidates],dtype=torch.float32).reshape(-1,4),torch.tensor([r['box_slide'] for r in truth],dtype=torch.float32).reshape(-1,4))
        pairs=[(float(overlaps[i,j]),i,j) for i,j in torch.nonzero(overlaps>=.5).tolist()]
        usedp=set();usedt=set();assigned={}
        for iou,i,j in sorted(pairs,reverse=True):
            if i not in usedp and j not in usedt:usedp.add(i);usedt.add(j);assigned[j]=(i,iou)
        for j,r in enumerate(truth):
            p=candidates[assigned[j][0]] if j in assigned else None
            matches.append({'record_id':r['record_id'],'source':source,'true_category':r['broad_category'],'detected':p is not None,'predicted_category':p['category'] if p else None,'classification_correct':p is not None and p['category']==r['broad_category'],'iou':assigned[j][1] if p else None})
        for i,p in enumerate(candidates):p['matched_known_reference']=i in usedp
        predictions.extend(candidates)
        save(OUT/'predictions.json',predictions);save(OUT/'known_reference_results.json',matches)
        print(json.dumps({'slide':number,'of':14,'tiles':annotator.call_count,'known':len(truth),'predictions':len(candidates),'found':len(assigned)}),flush=True)
        del annotator,native;gc.collect();torch.cuda.empty_cache()
    found=sum(r['detected'] for r in matches);correct=sum(r['classification_correct'] for r in matches)
    summary={'status':'complete','known_specimens':274,'predictions':len(predictions),'found':found,'correct':correct,'known_specimen_recall_iou50':found/274,'classification_accuracy_on_matched':correct/found if found else None,'end_to_end_known_specimen_success':correct/274,'test_used':False,'unmatched_predictions':'unreviewed','caveat':'13/14 validation slides seen in original Spring training'}
    save(OUT/'summary.json',summary)
    old=json.loads((OLD/'pipeline_validation/summary.json').read_text())
    old03=json.loads((OLD/'pipeline_validation_conf030/summary.json').read_text())
    save(OUT/'comparison.json',{'old_focus_stack_conf050':old,'old_focus_stack_conf030':old03,'new_original_best_plane_conf050':summary})
    print(json.dumps(summary),flush=True)
if __name__=='__main__':main()

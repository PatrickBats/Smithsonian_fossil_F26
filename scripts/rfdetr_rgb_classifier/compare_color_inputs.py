"""Paired BGR-vs-RGB inference on identical native Tenengrad tiles; no training.

Original pipeline, shared NDPI sources, checkpoints and previous outputs stay
unchanged. A same-process BGR control is checked against the frozen prior run.
"""
import os,sys,json,shutil,gc,collections,hashlib
from pathlib import Path
os.environ['NO_ALBUMENTATIONS_UPDATE']='1'
os.environ['PALYNET_NUM_WORKERS']='0'
ORIGINAL=Path(os.environ.get('SPRING_ADAPTER_ROOT',str(Path(__file__).resolve().parent)))
sys.path.insert(0,str(ORIGINAL))
import compare_bestplane as prior
import torch,numpy as np
from PIL import Image
from torchvision.models import swin_t
from torchvision.ops import box_iou
from src.annotator.config import AnnotatorConfig
from src.annotator.types import Detection
from src.annotator.detectors import sanitize_boxes
from src.annotator.nms import deduplicate
from src.data.util import pixels_to_nm_bbox
ROOT=prior.BASE/'model_B/runs/abbas_rgb_input_check_v1'
BASELINE=prior.OUT
def save(p,value):
    prior.save(p,value);p.chmod(0o644)
def score(candidates,truth):
    a=torch.tensor([p['box_slide'] for p in candidates],dtype=torch.float32).reshape(-1,4)
    b=torch.tensor([r['box_slide'] for r in truth],dtype=torch.float32).reshape(-1,4)
    overlaps=box_iou(a,b)
    pairs=[(float(overlaps[i,j]),i,j) for i,j in torch.nonzero(overlaps>=.5).tolist()]
    usedp=set();usedt=set();assigned={}
    for overlap,i,j in sorted(pairs,reverse=True):
        if i not in usedp and j not in usedt:usedp.add(i);usedt.add(j);assigned[j]=(i,overlap)
    results=[]
    for j,r in enumerate(truth):
        p=candidates[assigned[j][0]] if j in assigned else None
        results.append({'record_id':r['record_id'],'source':r['image'],'true_category':r['broad_category'],'detected':p is not None,'predicted_category':p['category'] if p else None,'classification_correct':p is not None and p['category']==r['broad_category'],'iou':assigned[j][1] if p else None})
    for i,p in enumerate(candidates):p['matched_known_reference']=i in usedp
    return results
def summary(matches,predictions):
    found=sum(r['detected'] for r in matches);correct=sum(r['classification_correct'] for r in matches);n=len(matches)
    return {'known_specimens':n,'predictions':len(predictions),'found':found,'correct':correct,'known_specimen_recall_iou50':found/n,'classification_accuracy_on_matched':correct/found if found else None,'end_to_end_known_specimen_success':correct/n,'test_used':False,'training_performed':False,'unmatched_predictions':'unreviewed; not all assumed false positives','caveat':'13/14 validation slides seen during original detector training'}

def predict_rgb(detector,tile):
    """Match native RF-DETR adapter exactly except for the RGB-to-BGR swap."""
    detected=detector.model.predict(np.ascontiguousarray(tile),threshold=detector.confidence_threshold)
    boxes=getattr(detected,'xyxy',None);scores=getattr(detected,'confidence',None)
    if boxes is None or len(boxes)==0:return np.zeros((0,4),dtype=np.float32),np.array([],dtype=np.float32)
    boxes=np.asarray(boxes,dtype=np.float32)
    scores=np.ones(len(boxes),dtype=np.float32) if scores is None else np.asarray(scores,dtype=np.float32)
    return sanitize_boxes(boxes,scores,width=tile.shape[1],height=tile.shape[0])

class Paired(prior.Handoff):
    def attach_pair(self,swin,labels):
        grid=self._build_tile_grid()
        self.rgb_by_tile={};self.rgb_origins={};self.trace=[]
        sequence=iter(t for band in self._group_into_bands(grid,8192) for t in band[4])
        original_predict=self.detector.predict
        def paired_predict(tile):
            spec=next(sequence)
            # Original branch, including its existing RGB-to-BGR conversion.
            boxes,scores=original_predict(tile)
            # The only intervention: feed original RGB pixels to model.predict.
            model_input=np.ascontiguousarray(tile)
            rb,rs=predict_rgb(self.detector,tile)
            if len(rb):
                image=Image.fromarray(np.asarray(tile,dtype=np.uint8)).convert('RGB');items=[]
                for box,conf in zip(rb,rs):
                    gx=tuple(float(offset+v) for offset,v in zip((spec.x,spec.y,spec.x,spec.y),box))
                    nm=pixels_to_nm_bbox(*gx,self.config.magnification,self.ndpi.metadata)
                    det=Detection(*gx,float(conf),*nm);items.append(det)
                    self.rgb_origins.setdefault(prior.key(det),(image,[float(v) for v in box],spec.x,spec.y))
                self.rgb_by_tile[spec]=items
            self.trace.append({'x':spec.x,'y':spec.y,'rgb_tile_sha256':hashlib.sha256(model_input.tobytes()).hexdigest(),'bgr_input_sha256':hashlib.sha256(np.ascontiguousarray(tile[:,:,::-1]).tobytes()).hexdigest(),'original_candidates':len(boxes),'rgb_candidates':len(rb)})
            return boxes,scores
        self.detector.predict=paired_predict
        # Existing RGB crop handoff records the original control unchanged.
        self.attach(swin,labels)

def main():
    assert torch.cuda.is_available()
    contract=json.loads((BASELINE/'configuration.json').read_text())
    assert prior.sha(prior.WEIGHT)==contract['detector_sha256']
    assert prior.sha(prior.SWIN)==contract['swin_sha256']
    expected=json.loads((BASELINE/'summary.json').read_text())
    refpaths=[prior.OLD/f'export_shard_{i}_references.json' for i in range(4)]
    refs=[r for p in refpaths for r in json.loads(p.read_text()) if r['split']=='val']
    assert len(refs)==274 and len({r['record_id'] for r in refs})==274
    sources=sorted({r['image'] for r in refs});assert len(sources)==14
    cfg={**contract,'experiment':'paired original BGR vs RGB input','only_intervention':'remove RGB-to-BGR conversion before RF-DETR predict; classifier crops remain RGB in both arms','control_baseline':str(BASELINE),'input_references':{str(p):prior.sha(p) for p in refpaths},'environment':json.loads((ROOT/'environment/audit.json').read_text()),'training_performed':False,'test_used':False,'job_id':os.environ.get('SLURM_JOB_ID')}
    save(ROOT/'configuration.json',cfg)
    ckpt=torch.load(prior.SWIN,map_location='cpu',weights_only=False);labels=ckpt['categories'];assert len(labels)==28
    swin=swin_t(weights=None);swin.head=torch.nn.Linear(swin.head.in_features,28);swin.load_state_dict(ckpt['model'],strict=True);swin.cuda().eval();del ckpt
    predictions={'original_bgr':[],'rgb_corrected':[]};matches={'original_bgr':[],'rgb_corrected':[]}
    for number,source in enumerate(sources,1):
        output=ROOT/'slides'/Path(source).stem;output.mkdir(parents=True,exist_ok=True)
        snapshot=BASELINE/'slides'/Path(source).stem/'source_annotation.ndpa'
        source_hash=prior.sha(snapshot);working=output/'original_bgr.ndpa';shutil.copyfile(snapshot,working)
        config=AnnotatorConfig(ndpi_path=source,output_dir=str(output),model_name='rfdetr',checkpoint_path=str(prior.WEIGHT),overlap=.1,magnification=40,compression_method='best_focal_plane',tenengrad_ksize=3,rfdetr_variant='2xlarge',export_crops=True,ndpa_path=str(working))
        ann=Paired(config);ann.attach_pair(swin,labels)
        currentgrid=json.loads((output/'tile_grid.json').read_text());oldgrid=json.loads((snapshot.parent/'tile_grid.json').read_text());assert currentgrid==oldgrid,'Grid differs from prior run'
        original_detections=ann.run();control=ann.results
        assert len(control)==len(original_detections)
        rgb_detections=deduplicate(ann.rgb_by_tile,config.nms_iou_threshold)
        ann.origins=ann.rgb_origins;ann.results=[]
        ann._write_crops(rgb_detections);rgb=ann.results
        ann._write_csv(rgb_detections,str(output/'rgb_corrected.csv'))
        ann._write_ndpa(rgb_detections,str(output/'rgb_corrected.ndpa'))
        truth=[r for r in refs if r['image']==source]
        for arm,ps in [('original_bgr',control),('rgb_corrected',rgb)]:
            predictions[arm].extend(ps);matches[arm].extend(score(ps,truth))
            save(ROOT/arm/'predictions.json',predictions[arm]);save(ROOT/arm/'known_reference_results.json',matches[arm])
        save(output/'paired_tile_inputs.json',ann.trace)
        assert prior.sha(snapshot)==source_hash,'Original snapshot changed'
        print(json.dumps({'slide':number,'of':14,'tiles':ann.call_count,'known':len(truth),'original_bgr':summary(matches['original_bgr'],predictions['original_bgr']),'rgb_corrected':summary(matches['rgb_corrected'],predictions['rgb_corrected'])}),flush=True)
        ann.ndpi.close();del ann,original_detections,rgb_detections;gc.collect();torch.cuda.empty_cache()
    results={arm:summary(matches[arm],predictions[arm]) for arm in predictions}
    for arm in results:save(ROOT/arm/'summary.json',{'status':'complete',**results[arm]})
    old=json.loads((BASELINE/'known_reference_results.json').read_text());oldmap={r['record_id']:r for r in old};controlmap={r['record_id']:r for r in matches['original_bgr']}
    diffs=[ident for ident in oldmap if (oldmap[ident]['detected'],oldmap[ident]['predicted_category'])!=(controlmap[ident]['detected'],controlmap[ident]['predicted_category'])]
    control_matches=all(results['original_bgr'][k]==expected[k] for k in ['known_specimens','predictions','found','correct']) and not diffs
    before={r['record_id']:r for r in matches['original_bgr']};after={r['record_id']:r for r in matches['rgb_corrected']}
    pairs={}
    for name,condition in [('both_found',lambda a,b:a['detected'] and b['detected']),('rgb_only',lambda a,b:not a['detected'] and b['detected']),('bgr_only',lambda a,b:a['detected'] and not b['detected']),('neither',lambda a,b:not a['detected'] and not b['detected'])]:
        ids=[i for i in before if condition(before[i],after[i])]
        pairs[name]={'count':len(ids),'bgr_correct':sum(before[i]['classification_correct'] for i in ids),'rgb_correct':sum(after[i]['classification_correct'] for i in ids),'record_ids':ids}
    output={'status':'complete','training_performed':False,'test_used':False,'original_bgr':results['original_bgr'],'rgb_corrected':results['rgb_corrected'],'control_reproduced_previous_run':control_matches,'control_differing_record_ids':diffs,'paired_reference_groups':pairs,'caveat':'13/14 validation slides seen in original training; diagnostic only'}
    save(ROOT/'comparison.json',output);print(json.dumps(output),flush=True)
    for path in ROOT.rglob('*'):
        if path.is_file():path.chmod(path.stat().st_mode|0o444)
        elif path.is_dir():path.chmod(path.stat().st_mode|0o555)

if __name__=='__main__':main()

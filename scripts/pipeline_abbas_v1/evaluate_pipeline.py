"""Frozen-Swin validation handoff on complete Abbas ROI grids.

Missing known specimens count as end-to-end failures. Unmatched predictions
are unreviewed, not assumed false positives. Reserved test is not accessed.
"""
import argparse,collections,json,os
from pathlib import Path
import numpy as np
from PIL import Image
from pipeline_common import validate_inputs,sha,save,crop_input
from spring_types import Detection,TileSpec
from spring_nms import deduplicate

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--smoke',action='store_true');a=ap.parse_args()
    c,records,mapping=validate_inputs(a.config);root=Path(c['workspace']);output=root/('pipeline_smoke' if a.smoke else 'pipeline_validation');output.mkdir(parents=True,exist_ok=True)
    os.environ['HF_HOME']=str(root/'cache/hf');os.environ['TORCH_HOME']=str(root/'cache/torch')
    import torch
    from torchvision.models import swin_t
    from torchvision.transforms import functional as TF
    from torchvision.ops import box_iou
    from rfdetr_plus.models.detection import RFDETR2XLarge
    assert torch.cuda.is_available()
    checkpoint=root/('detector_smoke' if a.smoke else 'detector')/'checkpoint_best_total.pth'
    detector=RFDETR2XLarge(pretrain_weights=str(checkpoint),num_classes=1,resolution=c['detector_resolution'])
    ckpt=torch.load(c['swin_checkpoint'],map_location='cpu',weights_only=False)
    labels=ckpt['categories'];assert len(labels)==28 and set(labels)==set(mapping.values())
    swin=swin_t(weights=None);swin.head=torch.nn.Linear(swin.head.in_features,28);swin.load_state_dict(ckpt['model'],strict=True);swin.cuda().eval()
    grouped=collections.defaultdict(list)
    for p in sorted((root/'dataset/valid').glob('*.json')):
        if p.name!='_annotations.coco.json':
            meta=json.loads(p.read_text());meta['file']=str(p.with_suffix('.png'));grouped[meta['image']].append(meta)
    predictions=[];matches=[];known=0
    references=[r for shard in range(c['export_shards']) for r in json.loads((root/f'export_shard_{shard}_references.json').read_text()) if r['split']=='val']
    for source,tiles in sorted(grouped.items()):
        if a.smoke:tiles=tiles[:1]
        candidates=[];truth={r['record_id']:{'box':r['box_slide'],'category':r['broad_category']} for r in references if r['image']==source}
        by_tile={};origin={}
        for meta in tiles:
            assert sha(meta['file'])==meta['png_sha256']
            with Image.open(meta['file']) as im:
                image=im.convert('RGB');det=detector.predict(image,threshold=c['confidence_threshold'])
            spec=TileSpec(meta['left'],meta['top'],meta['size'],meta['size'],meta['left'],meta['top'])
            by_tile[spec]=[]
            for box,score in zip(det.xyxy,det.confidence):
                box=[float(v) for v in box]
                global_box=[box[0]+meta['left'],box[1]+meta['top'],box[2]+meta['left'],box[3]+meta['top']]
                detection=Detection(*global_box,float(score),0.,0.,0.,0.)
                by_tile[spec].append(detection)
                origin[id(detection)]={'box_slide':global_box,'box_tile':box,'tile':meta['file'],'score':float(score)}
        if a.smoke:
            visible={obj['record_id'] for meta in tiles for obj in meta['objects']}
            truth={k:v for k,v in truth.items() if k in visible}
        candidates=[origin[id(d)] for d in deduplicate(by_tile,c['merge_iou'])]
        known+=len(truth)
        if candidates:
            for start in range(0,len(candidates),32):
                batch=candidates[start:start+32];inputs=[]
                for p in batch:
                    with Image.open(p['tile']) as im:crop=crop_input(im.convert('RGB'),p['box_tile'],c['crop_margin'])
                    inputs.append(TF.normalize(TF.to_tensor(crop),[.485,.456,.406],[.229,.224,.225]))
                with torch.inference_mode():probs=swin(torch.stack(inputs).cuda()).softmax(-1).cpu()
                for p,prob in zip(batch,probs):
                    index=int(prob.argmax());p.update(category=labels[index],classification_score=float(prob[index]),source=source)
            ids=list(truth);overlap=box_iou(torch.tensor([p['box_slide'] for p in candidates]),torch.tensor([truth[i]['box'] for i in ids])) if ids else torch.empty((len(candidates),0))
            pairs=[]
            for i,j in torch.nonzero(overlap>=.5).tolist():pairs.append((float(overlap[i,j]),i,j))
            usedp=set();usedt=set();assigned={}
            for iou,i,j in sorted(pairs,reverse=True):
                if i not in usedp and j not in usedt:usedp.add(i);usedt.add(j);assigned[j]=(i,iou)
            for j,ident in enumerate(ids):
                p=candidates[assigned[j][0]] if j in assigned else None
                matches.append({'record_id':ident,'source':source,'true_category':truth[ident]['category'],'detected':p is not None,'predicted_category':p['category'] if p else None,'classification_correct':p is not None and p['category']==truth[ident]['category'],'iou':assigned[j][1] if p else None})
            for i,p in enumerate(candidates):p['matched_known_reference']=i in usedp
        else:
            matches.extend({'record_id':ident,'source':source,'true_category':t['category'],'detected':False,'predicted_category':None,'classification_correct':False,'iou':None} for ident,t in truth.items())
        predictions.extend(candidates)
        save(output/'predictions.json',predictions);save(output/'known_reference_results.json',matches)
        print(json.dumps({'source':source,'known':len(truth),'predictions':len(candidates)}),flush=True)
        if a.smoke:break
    found=sum(x['detected'] for x in matches);correct=sum(x['classification_correct'] for x in matches)
    summary={'status':'complete','scope':'complete fixed-grid annotated-ROI validation; specimen locations never select tiles; label completeness unconfirmed','known_specimens':known,'known_specimen_recall_iou50':found/known if known else None,'classification_accuracy_on_matched':correct/found if found else None,'end_to_end_known_specimen_success':correct/known if known else None,'unmatched_predictions':'unreviewed, not counted as false positives','test_used':False,'detector_checkpoint_sha256':sha(checkpoint),'swin_checkpoint_sha256':sha(c['swin_checkpoint']),'categories':labels,'job_id':os.environ.get('SLURM_JOB_ID'),'preprocessing_difference':'existing Swin trained on crop-wide best-plane; requested handoff uses Abbas LoG focus-stacked tile pixels with fixed 10% context; measured input shift','merge_method':'unchanged Spring boundary-aware union-find; threshold >0.5'}
    save(output/'summary.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':main()

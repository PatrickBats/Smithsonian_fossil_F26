"""Frozen-split Swin-Tiny baseline. Training/validation only; no test inference.

Outputs must be outside the repository. Each invocation creates a new run.
"""
import argparse
import collections
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import traceback

import numpy as np
from PIL import Image, ImageOps
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
import torchvision
from torchvision.models import swin_t, Swin_T_Weights
from torchvision.transforms import functional as TF

EXPECTED_SPLIT_SHA = 'da2062a127cf6e14945e50fff097e0db102d7f8203250b47daed6b6bb166478d'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with Path(path).open(newline='') as f:
        return list(csv.DictReader(f))


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')


def verify_inputs(root, assignments, category_map):
    if digest(assignments) != EXPECTED_SPLIT_SHA:
        raise ValueError('Split differs from the adopted assignment')
    source = read_csv(assignments)
    crops = read_csv(root/'crop_manifest.csv')
    classes = read_csv(category_map)
    if [int(c['classifier_class_id']) for c in classes] != list(range(32)):
        raise ValueError('Expected 32 ordered class IDs')
    labels = [c['sponsor_category'] for c in classes]
    if len(set(labels)) != 32 or any(c['priority'] != 'YES' for c in classes):
        raise ValueError('Invalid class vocabulary')
    by_id = {r['record_id']: r for r in source}
    if len(source) != 2283 or len(by_id) != 2283 or len(crops) != 2283:
        raise ValueError('Unexpected record count')
    if len({r['record_id'] for r in crops}) != 2283 or {r['record_id'] for r in crops} != set(by_id):
        raise ValueError('Missing/duplicated crop IDs')
    groups = collections.defaultdict(set)
    images = collections.defaultdict(set)
    for row in crops:
        for key, value in by_id[row['record_id']].items():
            if row.get(key) != value:
                raise ValueError(f'Crop source field changed: {key}')
        if row['sponsor_category'] not in labels or int(row['source_level']) != 0:
            raise ValueError('Unknown category or source level')
        groups[row['accession_group_id']].add(row['split'])
        images[row['image_nots_path']].add(row['split'])
        expected = row['split']+'/'+hashlib.sha256(row['record_id'].encode()).hexdigest()+'.png'
        if row['image_relpath'] != expected:
            raise ValueError('Unexpected crop path')
        path = root/expected
        if path.is_symlink():raise ValueError('Symlinked crop')
        data=path.read_bytes()
        if len(data) != int(row['png_bytes']) or hashlib.sha256(data).hexdigest() != row['png_sha256']:
            raise ValueError('Crop bytes do not match export manifest')
        with Image.open(io.BytesIO(data)) as image:
            side=int(row['crop_side_px'])
            if image.format != 'PNG' or image.mode != 'RGB' or image.size != (side,side):
                raise ValueError('Invalid crop format')
            image.verify()
        # Circle must remain wholly inside the exported image.
        for axis,origin in [('x','left'),('y','top')]:
            center=float(row[f'center_{axis}_px'])-float(row[f'crop_{origin}_px'])
            radius=float(row[f'radius_{axis}_px'])
            if not radius > 0 or center-radius < -1e-6 or center+radius > side+1e-6:
                raise ValueError('Circle clipped by crop')
    counts=dict(collections.Counter(r['split'] for r in crops))
    if counts != {'train':1605,'val':347,'test':331}:
        raise ValueError('Wrong partition counts')
    if len(groups)!=57 or any(len(s)!=1 for s in list(groups.values())+list(images.values())):
        raise ValueError('Source leakage across partitions')
    representation = verify_representation(root, crops)
    return crops, labels, {'representation':representation,'verified_records':len(crops),'split_counts':counts,'groups':len(groups),
                           'split_sha256':digest(assignments),'crop_manifest_sha256':digest(root/'crop_manifest.csv'),
                           'category_map_sha256':digest(category_map),'test_inference':False}


def verify_representation(root, crops):
    """Admit either the frozen zero-plane export or its verified focus replacement."""
    baseline_sha = 'b4d803ca764f9941de38014bc5a67eb797f400a595033118c32512f5701e1373'
    if digest(root/'crop_manifest.csv') == baseline_sha:
        return {'name':'baseline_zero_plane','crop_manifest_sha256':baseline_sha}
    metadata=json.loads((root/'representation.json').read_text())
    if metadata['representation']!='crop_wide_tenengrad_best_plane' or metadata['baseline_manifest_sha256']!=baseline_sha:
        raise ValueError('Unrecognized image representation')
    if metadata['crop_manifest_sha256']!=digest(root/'crop_manifest.csv') or metadata['focus_scores_sha256']!=digest(root/'focus_scores.json'):
        raise ValueError('Focus provenance fingerprint mismatch')
    if metadata['binding_sha256']!=digest(root.parent/'binding.json') or metadata['test_inference'] is not False:
        raise ValueError('Invalid focus run binding')
    baseline_path=root.parent/'baseline_crop_manifest.csv'
    if digest(baseline_path)!=baseline_sha:raise ValueError('Focus baseline changed')
    baseline=read_csv(baseline_path)
    scores=json.loads((root/'focus_scores.json').read_text())['records']
    if len(scores)!=len(crops) or [r['record_id'] for r in baseline]!=[r['record_id'] for r in crops]:
        raise ValueError('Focus records or order differ')
    if [r['record_id'] for r in scores]!=[r['record_id'] for r in crops]:raise ValueError('Score order differs')
    mutable={'png_bytes','png_sha256','rgb_channel_std_mean'}
    for row,old,score in zip(crops,baseline,scores):
        if any(row.get(k)!=v for k,v in old.items() if k not in mutable):raise ValueError('Focus crop geometry/source changed')
        if row['baseline_png_sha256']!=old['png_sha256'] or score['zero_plane_matches_baseline'] is not True:
            raise ValueError('Zero-plane reference mismatch')
        planes=score['planes']
        if not planes or any(not math.isfinite(p['tenengrad']) or p['tenengrad']<0 for p in planes):raise ValueError('Invalid focus score')
        best=max(planes,key=lambda p:(p['tenengrad'],-abs(p['z_offset']),-p['index']))
        if int(row['selected_plane_index'])!=best['index'] or int(row['selected_z_offset'])!=best['z_offset']:
            raise ValueError('Selected plane is not the fixed-method maximum')
        if score['selected_sha256']!=row['png_sha256'] or score['selected_bytes']!=int(row['png_bytes']):raise ValueError('Selected image mismatch')
    return metadata


class Crops(Dataset):
    def __init__(self, root, rows, labels, augment):
        self.rows=rows
        self.targets=[labels.index(r['sponsor_category']) for r in rows]
        self.augment=augment
        self.images=[]
        for row in rows:
            with Image.open(root/row['image_relpath']) as im:
                side=max(im.size)
                im=ImageOps.pad(im,(side,side),color='white')
                self.images.append(im.resize((224,224),Image.Resampling.BICUBIC).copy())

    def __len__(self):return len(self.rows)

    def __getitem__(self, index):
        im=self.images[index]
        if self.augment:
            # Quarter-turns and reflections retain the full square specimen crop.
            k=random.randrange(4)
            if k:im=im.transpose([Image.Transpose.ROTATE_90,Image.Transpose.ROTATE_180,Image.Transpose.ROTATE_270][k-1])
            if random.random()<.5:im=ImageOps.mirror(im)
        x=TF.normalize(TF.to_tensor(im),[.485,.456,.406],[.229,.224,.225])
        return x,self.targets[index],index


def metrics(truth, predictions, labels):
    cm=np.zeros((len(labels),len(labels)),dtype=np.int64)
    np.add.at(cm,(truth,predictions),1)
    support=cm.sum(1);predicted=cm.sum(0);tp=np.diag(cm)
    precision=np.divide(tp,predicted,out=np.zeros(len(labels),float),where=predicted>0)
    recall=np.divide(tp,support,out=np.zeros(len(labels),float),where=support>0)
    f1=np.divide(2*tp,support+predicted,out=np.zeros(len(labels),float),where=(support+predicted)>0)
    present=support>0
    return {'accuracy':float(tp.sum()/support.sum()),'macro_f1_present':float(f1[present].mean()),
            'balanced_accuracy_present':float(recall[present].mean()),
            'evaluated_categories':[labels[i] for i in np.flatnonzero(present)],
            'absent_categories':[labels[i] for i in np.flatnonzero(~present)],
            'per_class':[{'category':c,'support':int(support[i]),'precision':float(precision[i]),
                          'recall':float(recall[i]) if present[i] else None,
                          'f1':float(f1[i]) if present[i] else None} for i,c in enumerate(labels)],
            'confusion_matrix':cm.tolist()}


def evaluate(model, loader, device, labels):
    model.eval();truth=[];predictions=[];probabilities=[];indices=[];loss_sum=0
    with torch.inference_mode():
        for x,y,idx in loader:
            x=x.to(device);y=y.to(device)
            logits=model(x)
            if not torch.isfinite(logits).all():raise FloatingPointError('Nonfinite validation logits')
            loss_sum+=nn.functional.cross_entropy(logits,y,reduction='sum').item()
            p=logits.softmax(1).cpu()
            truth.extend(y.cpu().tolist());predictions.extend(p.argmax(1).tolist())
            probabilities.extend(p.tolist());indices.extend(idx.tolist())
    result=metrics(truth,predictions,labels);result['loss']=loss_sum/len(truth)
    return result,indices,probabilities


def main(args):
    root=Path(args.data).resolve();out=Path(args.output).resolve()
    repo=Path(__file__).resolve().parents[2]
    if out.is_relative_to(repo):raise ValueError('Run artifacts must stay outside Git')
    out.mkdir(parents=True,exist_ok=False)
    started=time.time()
    try:
        config=vars(args).copy();config.update({'model':'torchvision.swin_t','weights':'IMAGENET1K_V1',
          'sampling':'ordinary_shuffle_all_training_records','loss':'unweighted_cross_entropy',
          'augmentations':'random_quarter_turn_and_horizontal_flip_train_only','input_size':224,
          'head_lr':.001,'finetune_backbone_lr':.00001,'finetune_head_lr':.0001,
          'weight_decay':.01,'selection':'validation_macro_f1_over_31_present_categories',
          'test_inference':False,'precision':'float32','balanced_comparison_launched':False})
        write_json(out/'config.json',config)
        torch.set_num_threads(4)
        random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed);torch.cuda.manual_seed_all(args.seed)
        torch.backends.cudnn.benchmark=False
        torch.backends.cuda.matmul.allow_tf32=False
        torch.backends.cudnn.allow_tf32=False
        torch.use_deterministic_algorithms(True)
        rows,labels,audit=verify_inputs(root,Path(args.assignments),Path(args.categories))
        if getattr(args,'specimen_split',None):
            from specimen_split import apply_split
            (out/'specimen_split_helper.py').write_bytes(Path(__file__).with_name('specimen_split.py').read_bytes())
            rows,diagnostic=apply_split(rows,args.specimen_split)
            audit['diagnostic_split']=diagnostic
            (out/'specimen_split.json').write_bytes(Path(args.specimen_split).read_bytes())
            config['selection']='validation_macro_f1_over_32_present_categories'
            config['evaluation_scope']='specimen-level diagnostic with shared train/validation slides'
            write_json(out/'config.json',config)
        if getattr(args,'broad_map',None):
            from broad_labels import apply_broad
            rows,labels,broad_audit=apply_broad(rows,labels,args.broad_map)
            audit['broad_labels']=broad_audit
            (out/'fine_to_broad.csv').write_bytes(Path(args.broad_map).read_bytes())
            (out/'broad_labels.py').write_bytes(Path(__file__).with_name('broad_labels.py').read_bytes())
            write_json(out/'broad_category_map.json',dict(enumerate(labels)))
            config['task']='28-group broad_v1 exploratory classification'
            config['selection']='validation_macro_f1_over_present_broad_categories'
            write_json(out/'config.json',config)
        write_json(out/'data_audit.json',audit)
        trainrows=[r for r in rows if r['split']=='train'];valrows=[r for r in rows if r['split']=='val']
        if args.smoke:
            trainrows=[r for c in labels for r in [x for x in trainrows if x['sponsor_category']==c][:2]]
            valrows=[r for c in labels for r in [x for x in valrows if x['sponsor_category']==c][:2]]
        train=Crops(root,trainrows,labels,True);val=Crops(root,valrows,labels,False)
        gen=torch.Generator().manual_seed(args.seed)
        trainloader=DataLoader(train,batch_size=args.batch_size,shuffle=True,num_workers=0,generator=gen,pin_memory=True)
        valloader=DataLoader(val,batch_size=args.batch_size,shuffle=False,num_workers=0,pin_memory=True)
        if not torch.cuda.is_available():raise RuntimeError('Expected an allocated CUDA GPU')
        device=torch.device('cuda:0')
        weights=Swin_T_Weights.IMAGENET1K_V1
        model=swin_t(weights=weights);model.head=nn.Linear(model.head.in_features,len(labels));model.to(device)
        weight_path=Path(torch.hub.get_dir())/'checkpoints'/weights.url.rsplit('/',1)[1]
        write_json(out/'provenance.json',{'python':sys.version,'torch':torch.__version__,'torchvision':torchvision.__version__,
          'cuda':torch.version.cuda,'gpu_name':torch.cuda.get_device_name(0),'gpu_uuid':os.environ.get('CUDA_VISIBLE_DEVICES'),
          'script_sha256':digest(__file__),'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
          'weights_url':weights.url,'weights_sha256':digest(weight_path),'run_started_unix':started,
          'execution':'user-owned workstation GPU; NOTS project quota prevents normal output storage'})
        (out/'train_swin_snapshot.py').write_bytes(Path(__file__).read_bytes())
        (out/'record_assignments.csv').write_bytes(Path(args.assignments).read_bytes())
        (out/'category_map.csv').write_bytes(Path(args.categories).read_bytes())
        with (out/'environment.txt').open('w') as f:subprocess.run([sys.executable,'-m','pip','freeze'],stdout=f,check=True)
        best=-1;best_epoch=None;optimizer=None
        total_epochs=2 if args.smoke else args.epochs
        head_epochs=1 if args.smoke else args.head_epochs
        for epoch in range(total_epochs):
            ep_start=time.time();head_only=epoch<head_epochs
            if epoch in (0,head_epochs):
                for p in model.parameters():p.requires_grad_(not head_only)
                for p in model.head.parameters():p.requires_grad_(True)
                params=[{'params':model.head.parameters(),'lr':.001}] if head_only else [
                  {'params':[p for n,p in model.named_parameters() if not n.startswith('head.')],'lr':.00001},
                  {'params':model.head.parameters(),'lr':.0001}]
                optimizer=torch.optim.AdamW(params,weight_decay=.01)
            if head_only:model.eval();model.head.train()
            else:model.train()
            total_loss=0;n=0
            for x,y,_ in trainloader:
                x=x.to(device);y=y.to(device);optimizer.zero_grad(set_to_none=True)
                logits=model(x);loss=nn.functional.cross_entropy(logits,y)
                if not torch.isfinite(loss):raise FloatingPointError('Nonfinite training loss')
                loss.backward()
                nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],1.,error_if_nonfinite=True)
                optimizer.step()
                if not torch.stack([torch.isfinite(p).all() for p in model.parameters()]).all().item():raise FloatingPointError('Nonfinite model parameter')
                total_loss+=loss.item()*len(y);n+=len(y)
            result,indices,probs=evaluate(model,valloader,device,labels)
            summary={'epoch':epoch+1,'phase':'head' if head_only else 'full_finetune','train_loss':total_loss/n,
              'validation_loss':result['loss'],'validation_macro_f1_present':result['macro_f1_present'],
              'validation_balanced_accuracy_present':result['balanced_accuracy_present'],
              'validation_accuracy':result['accuracy'],'epoch_seconds':time.time()-ep_start,
              'gpu_peak_memory_bytes':torch.cuda.max_memory_allocated()}
            with (out/'history.jsonl').open('a') as f:f.write(json.dumps(summary,allow_nan=False)+'\n')
            print(json.dumps(summary),flush=True)
            if result['macro_f1_present']>best:
                best=result['macro_f1_present'];best_epoch=epoch+1
                state={'model':model.state_dict(),'optimizer':optimizer.state_dict(),'epoch':epoch+1,'categories':labels,
                       'config':config,'audit':audit,'validation_metrics':result,
                       'rng_python':random.getstate(),'rng_numpy':np.random.get_state(),
                       'rng_torch':torch.get_rng_state(),'rng_cuda':torch.cuda.get_rng_state_all(),
                       'loader_rng':gen.get_state()}
                tmp=out/'best.pt.part';torch.save(state,tmp);tmp.replace(out/'best.pt')
                write_json(out/'best_validation_metrics.json',result)
                with (out/'best_validation_predictions.csv').open('w',newline='') as f:
                    writer=csv.writer(f);writer.writerow(['record_id','category','predicted_category','confidence']+[f'p_{i}' for i in range(len(labels))])
                    for i,p in zip(indices,probs):
                        row=valrows[i];prediction=int(np.argmax(p));writer.writerow([row['record_id'],row['sponsor_category'],labels[prediction],p[prediction]]+p)
            write_json(out/'status.json',{'status':'running','completed_epochs':epoch+1,'best_epoch':best_epoch,'best_validation_macro_f1_present':best,'test_evaluated':False})
        write_json(out/'status.json',{'status':'complete','epochs':total_epochs,'best_epoch':best_epoch,
           'best_validation_macro_f1_present':best,'elapsed_seconds':time.time()-started,
           'allocated_gpu_hours':(time.time()-started)/3600,'test_evaluated':False,'smoke':args.smoke})
    except BaseException:
        write_json(out/'failure.json',{'traceback':traceback.format_exc(),'elapsed_seconds':time.time()-started})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for field in ('data','assignments','categories','output'):p.add_argument('--'+field,required=True)
    p.add_argument('--epochs',type=int,default=40);p.add_argument('--head-epochs',type=int,default=3)
    p.add_argument('--batch-size',type=int,default=32);p.add_argument('--seed',type=int,default=20261007)
    p.add_argument('--specimen-split',help='Explicit diagnostic split; original test remains reserved')
    p.add_argument('--broad-map',help='Frozen fine-to-broad mapping; default retains original categories')
    p.add_argument('--smoke',action='store_true')
    args=p.parse_args()
    if not (args.epochs>args.head_epochs>0 and args.batch_size>0):p.error('Invalid epoch/batch settings')
    main(args)

"""DINOv2 partial backbone adaptation with reserved test set."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import traceback
import numpy as np
import torch
import torchvision
from torch import nn
from torch.utils.data import DataLoader
from train_swin import verify_inputs, Crops, evaluate, write_json, digest

DINO_SOURCE='/mnt/richb/pb52/model-cache/dinov2-source'


def adaptable(name):
    return name.startswith(('head.','backbone.blocks.10.','backbone.blocks.11.','backbone.norm.'))


def frozen_digest(model):
    h=hashlib.sha256()
    for n,p in model.named_parameters():
        if not adaptable(n):h.update(n.encode());h.update(p.detach().cpu().numpy().tobytes())
    return h.hexdigest()


class DinoClassifier(nn.Module):
    def __init__(self,num_classes=32):
        super().__init__()
        self.backbone=torch.hub.load(DINO_SOURCE,'dinov2_vitb14',source='local',pretrained=True)
        if len(self.backbone.blocks)!=12:raise ValueError('Expected 12 DINO blocks')
        self.head=nn.Linear(1536,num_classes)
        self.configure(True)

    def configure(self,head_only):
        for n,p in self.named_parameters():p.requires_grad_(n.startswith('head.') or (not head_only and adaptable(n)))

    def train(self,mode=True):
        super().train(mode);self.backbone.eval()
        if mode:
            self.backbone.blocks[10].train();self.backbone.blocks[11].train();self.head.train()
        return self

    def forward(self,x):
        features=self.backbone.forward_features(x)
        return self.head(torch.cat([features['x_norm_clstoken'],features['x_norm_patchtokens'].mean(1)],dim=1))


def main(args):
    root=Path(args.data).resolve();out=Path(args.output).resolve()
    repo=Path(__file__).resolve().parents[2]
    if out.is_relative_to(repo):raise ValueError('Run artifacts must stay outside Git')
    out.mkdir(parents=True,exist_ok=False)
    started=time.time()
    try:
        config=vars(args).copy();config.update({'model':'dinov2_vitb14','weights':'LVD142M','unfrozen_blocks':[10,11],'unfrozen_norm':True,'features':'CLS plus mean patch tokens',
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
        model=DinoClassifier(len(labels));model.to(device)
        frozen_before=frozen_digest(model)
        weight_path=Path(torch.hub.get_dir())/'checkpoints/dinov2_vitb14_pretrain.pth'
        source_commit=subprocess.check_output(['git','-C',DINO_SOURCE,'rev-parse','HEAD'],text=True).strip()
        write_json(out/'provenance.json',{'python':sys.version,'torch':torch.__version__,'torchvision':torchvision.__version__,
          'cuda':torch.version.cuda,'gpu_name':torch.cuda.get_device_name(0),'gpu_uuid':os.environ.get('CUDA_VISIBLE_DEVICES'),
          'script_sha256':digest(__file__),'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
          'source_commit':source_commit,'weights_url':'https://dl.fbaipublicfiles.com/dinov2/dinov2_vitb14/dinov2_vitb14_pretrain.pth','weights_sha256':digest(weight_path),'run_started_unix':started,
          'execution':'Terminator GPU with local staging; verified artifacts copied to RHF'})
        (out/'train_dino_finetune_snapshot.py').write_bytes(Path(__file__).read_bytes())
        (out/'record_assignments.csv').write_bytes(Path(args.assignments).read_bytes())
        (out/'category_map.csv').write_bytes(Path(args.categories).read_bytes())
        with (out/'environment.txt').open('w') as f:subprocess.run([sys.executable,'-m','pip','freeze'],stdout=f,check=True)
        for helper in ('train_swin.py','specimen_split.py'):
            (out/helper).write_bytes(Path(__file__).with_name(helper).read_bytes())
        best=-1;best_epoch=None;optimizer=None
        total_epochs=2 if args.smoke else args.epochs
        head_epochs=1 if args.smoke else args.head_epochs
        for epoch in range(total_epochs):
            ep_start=time.time();head_only=epoch<head_epochs
            if epoch in (0,head_epochs):
                model.configure(head_only)
                write_json(out/('trainable_head.json' if head_only else 'trainable_backbone.json'),
                           {n:p.numel() for n,p in model.named_parameters() if p.requires_grad})
                params=[{'params':model.head.parameters(),'lr':.001}] if head_only else [
                  {'params':[p for n,p in model.named_parameters() if not n.startswith('head.') and p.requires_grad],'lr':.00001},
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
            summary={'epoch':epoch+1,'phase':'head' if head_only else 'last_two_blocks_finetune','train_loss':total_loss/n,
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
        if frozen_digest(model)!=frozen_before:raise RuntimeError('Frozen parameters changed')
        write_json(out/'frozen_parameter_check.json',{'unchanged':True,'sha256':frozen_before})
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
    p.add_argument('--broad-map',help='Explicit frozen fine-to-broad mapping; default retains 32 classes')
    p.add_argument('--smoke',action='store_true')
    args=p.parse_args()
    if not (args.epochs>args.head_epochs>0 and args.batch_size>0):p.error('Invalid epoch/batch settings')
    main(args)

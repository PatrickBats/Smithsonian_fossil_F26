"""Frozen DINOv2 linear probes on two fixed splits; no test inference."""
import argparse
import csv
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
import traceback
import warnings

import joblib
import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning
import torch
from torch.utils.data import DataLoader
from train_swin import verify_inputs, Crops, metrics, digest, write_json
from specimen_split import apply_split


def main(a):
    out=Path(a.output).resolve();repo=Path(__file__).resolve().parents[2]
    if out.is_relative_to(repo):raise ValueError('Keep experiment outputs outside Git')
    out.mkdir(parents=True,exist_ok=False);started=time.time()
    try:
        locks=Path('/tmp/codex-gpu-locks');locks.mkdir(exist_ok=True)
        with (locks/(a.gpu+'.lock')).open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            active=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True)
            if a.gpu in active:raise RuntimeError('GPU already in use')
            lock.seek(0);lock.truncate();lock.write(json.dumps({'pid':os.getpid(),'purpose':'DINOv2 frozen features','started':started}));lock.flush()
            config={**vars(a),'model':'dinov2_vitb14','frozen_backbone':True,'input_size':224,
              'features':'final normalized CLS concatenated with mean final normalized patch tokens',
              'head':'multinomial logistic regression, L2, C=1.0, lbfgs, tol=1e-6, max_iter=5000',
              'scaling':'StandardScaler fitted independently to training features for each split',
              'augmentation':'none for first frozen-feature probe','seed':20261007,'test_inference':False,
              'selection':'fixed configuration, no hyperparameter search'}
            write_json(out/'config.json',config)
            for file in ('train_dino_probe.py','train_swin.py','specimen_split.py'):
                (out/file).write_bytes(Path(__file__).with_name(file).read_bytes())
            (out/'specimen_split.json').write_bytes(Path(a.specimen_split).read_bytes())
            (out/'record_assignments.csv').write_bytes(Path(a.assignments).read_bytes())
            (out/'category_map.csv').write_bytes(Path(a.categories).read_bytes())
            rows,labels,audit=verify_inputs(Path(a.data),Path(a.assignments),Path(a.categories))
            diagnostic,split_audit=apply_split(rows,a.specimen_split)
            write_json(out/'data_audit.json',{'source':audit,'diagnostic':split_audit})
            non_test=[r for r in rows if r['split']!='test']
            assert len(non_test)==1952
            torch.set_num_threads(4);torch.manual_seed(20261007)
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
            torch.use_deterministic_algorithms(True)
            source=Path(a.source)
            commit=subprocess.check_output(['git','-c','safe.directory='+str(source),'-C',str(source),'rev-parse','HEAD'],text=True).strip()
            if subprocess.check_output(['git','-c','safe.directory='+str(source),'-C',str(source),'status','--porcelain'],text=True).strip():raise ValueError('DINO source dirty')
            write_json(out/'status.json',{'status':'loading_pretrained_model','test_inference':False})
            model=torch.hub.load(str(source),'dinov2_vitb14',source='local',pretrained=True).eval().cuda()
            for p in model.parameters():p.requires_grad_(False)
            weights=Path(torch.hub.get_dir())/'checkpoints/dinov2_vitb14_pretrain.pth'
            write_json(out/'provenance.json',{'source_url':'https://github.com/facebookresearch/dinov2','commit':commit,
              'weights_sha256':digest(weights),'weights_url':'https://dl.fbaipublicfiles.com/dinov2/dinov2_vitb14/dinov2_vitb14_pretrain.pth',
              'torch':torch.__version__,'sklearn':sklearn.__version__,'numpy':np.__version__,'script_sha256':digest(__file__),
              'gpu_uuid':a.gpu,'gpu_name':torch.cuda.get_device_name(0),'host':os.uname().nodename,'test_inference':False})
            (out/'environment.txt').write_text(subprocess.check_output([os.sys.executable,'-m','pip','freeze'],text=True))
            loader=DataLoader(Crops(Path(a.data),non_test,labels,False),batch_size=32,shuffle=False,num_workers=0)
            features=[]
            with torch.inference_mode():
                for batch,(x,y,idx) in enumerate(loader):
                    result=model.forward_features(x.cuda())
                    f=torch.cat([result['x_norm_clstoken'],result['x_norm_patchtokens'].mean(1)],1)
                    if f.shape!=(len(x),1536) or not torch.isfinite(f).all():raise ValueError('Invalid DINO features')
                    features.append(f.cpu().numpy())
                    if batch%10==0:
                        print('Feature batches:',batch+1,'/',len(loader),flush=True)
                        write_json(out/'status.json',{'status':'extracting_features','completed_batches':batch+1,'total_batches':len(loader),'test_inference':False})
            X=np.concatenate(features);np.save(out/'non_test_features.npy',X)
            write_json(out/'feature_ids.json',[r['record_id'] for r in non_test])
            # GPU can be released while the small CPU classifiers are fitted.
            del model;torch.cuda.empty_cache()
            gpu_seconds=time.time()-started
        ids={r['record_id']:i for i,r in enumerate(non_test)};summary={}
        for name,assignment in [('separate_slides',rows),('shared_slides',diagnostic)]:
            train=[r for r in assignment if r['split']=='train'];val=[r for r in assignment if r['split']=='val']
            if set(r['record_id'] for r in train)&set(r['record_id'] for r in val):raise ValueError('Specimen leakage')
            ti=[ids[r['record_id']] for r in train];vi=[ids[r['record_id']] for r in val]
            yt=np.array([labels.index(r['sponsor_category']) for r in train]);yv=np.array([labels.index(r['sponsor_category']) for r in val])
            scaling=StandardScaler();xt=scaling.fit_transform(X[ti].astype(np.float64));xv=scaling.transform(X[vi].astype(np.float64))
            head=LogisticRegression(C=1.,solver='lbfgs',max_iter=5000,tol=1e-6,random_state=20261007)
            write_json(out/'status.json',{'status':'fitting_linear_classifier','split':name,'test_inference':False})
            with warnings.catch_warnings():
                warnings.simplefilter('error',ConvergenceWarning);head.fit(xt,yt)
            if not np.isfinite(head.coef_).all() or not np.array_equal(head.classes_,np.arange(32)):raise ValueError('Invalid classifier')
            probabilities=head.predict_proba(xv)
            if not np.isfinite(probabilities).all() or not np.allclose(probabilities.sum(1),1):raise ValueError('Invalid probabilities')
            predictions=probabilities.argmax(1);result=metrics(yv,predictions,labels)
            result['solver_iterations']=head.n_iter_.tolist();result['test_inference']=False
            folder=out/name;folder.mkdir();write_json(folder/'validation_metrics.json',result)
            joblib.dump({'classifier':head,'scaler':scaling,'categories':labels,'config':config},folder/'linear_classifier.joblib')
            with (folder/'validation_predictions.csv').open('w',newline='') as f:
                writer=csv.writer(f);writer.writerow(['record_id','category','predicted_category','confidence']+[f'p_{i}' for i in range(32)])
                for row,pred,prob in zip(val,predictions,probabilities):writer.writerow([row['record_id'],row['sponsor_category'],labels[pred],float(prob[pred])]+prob.tolist())
            summary[name]={k:result[k] for k in ('accuracy','macro_f1_present','balanced_accuracy_present','solver_iterations')}
            print(name,summary[name],flush=True)
        write_json(out/'summary.json',summary)
        write_json(out/'status.json',{'status':'complete','elapsed_seconds':time.time()-started,'gpu_allocation_seconds':gpu_seconds,'test_inference':False})
    except BaseException:
        write_json(out/'failure.json',{'traceback':traceback.format_exc()})
        write_json(out/'status.json',{'status':'failed','test_inference':False});raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('data','assignments','categories','specimen_split','source','output','gpu'):p.add_argument('--'+key.replace('_','-'),required=True)
    main(p.parse_args())

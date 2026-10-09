"""Run two independent fixed splits on locked GPUs, then verify copies on RHF."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback


def save(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')


def archive(folder,remote):
    files={str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file() and p.name!='transfer_manifest.json'}
    save(folder/'transfer_manifest.json',files)
    subprocess.run(['ssh','-o','BatchMode=yes','rice-nots','mkdir -p '+remote],check=True)
    subprocess.run(['rsync','-a','--chmod=Dg+rwx,Fg+rw',str(folder)+'/', 'rice-nots:'+remote+'/'],check=True)
    code="""import pathlib,hashlib,json
root=pathlib.Path(REMOTE)
files=json.loads((root/'transfer_manifest.json').read_text())
for name,expected in files.items():
 if hashlib.sha256((root/name).read_bytes()).hexdigest()!=expected:raise RuntimeError('RHF copy mismatch: '+name)
print(json.dumps({'verified_files':len(files),'root':str(root)}))
"""
    result=subprocess.check_output(['ssh','-o','BatchMode=yes','rice-nots','python3 -'],input=('REMOTE='+repr(remote)+'\n'+code).encode())
    return json.loads(result)


def main(a):
    root=Path(a.output);root.mkdir(parents=True,exist_ok=False)
    repo=Path(__file__).resolve().parents[2];base=repo.parent/'tenengrad_full_2026-10-07'
    children=[];started=time.time()
    launcher='launch_dino_finetune.py' if a.model=='dino' else 'launch_swin.py'
    run_name='backbone_finetune' if a.model=='dino' else 'ordinary_baseline'
    try:
        for split,gpu in zip(('separate_slides','shared_slides'),a.gpus):
            cmd=[sys.executable,'-u',str(Path(__file__).with_name(launcher)),'--gpu',gpu,
              '--data',str(base/'dataset'),'--assignments',str(base/'record_assignments.csv'),
              '--categories',str(base/'category_map.csv'),'--output_root',str(root/split)]
            if a.broad_map:cmd+=['--broad-map',a.broad_map]
            if split=='shared_slides':cmd+=['--specimen-split',str(repo.parent/'swin_specimen_split_2026-10-07/specimen_split.json')]
            with (root/(split+'.log')).open('x') as log:
                p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
            children.append((split,p));save(root/(split+'_launch.json'),{'pid':p.pid,'command':cmd})
        save(root/'status.json',{'status':'training','pids':{s:p.pid for s,p in children},'test_inference':False})
        failures=[]
        for split,p in children:
            code=p.wait()
            if code:failures.append({'split':split,'returncode':code})
        if failures:raise RuntimeError('Training failures: '+str(failures))
        save(root/'status.json',{'status':'copying_to_rhf','test_inference':False})
        transfers=[]
        for split,_ in children:
            transfers.append(archive(root/split,'/rhf/allocations/dsci435/Smithsonian_F26/runs/'+root.name+'/'+split))
        save(root/'rhf_verification.json',transfers)
        summary={s:json.loads((root/s/run_name/'best_validation_metrics.json').read_text()) for s,_ in children}
        save(root/'summary.json',summary)
        save(root/'status.json',{'status':'complete','elapsed_seconds':time.time()-started,'test_inference':False,'rhf_copies_verified':True})
    except BaseException:
        save(root/'failure.json',{'traceback':traceback.format_exc()})
        save(root/'status.json',{'status':'failed','test_inference':False});raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--gpus',nargs=2,required=True);p.add_argument('--broad-map');p.add_argument('--model',choices=['dino','swin'],default='dino');a=p.parse_args()
    if len(set(a.gpus))!=2:p.error('Use two different GPU UUIDs')
    main(a)

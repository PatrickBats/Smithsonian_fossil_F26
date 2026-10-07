"""Detached continuation: verified focus export -> smoke -> matched Swin run.

Never evaluates test images. Refuses changed code, changed configurations, or an
export failure. Uses the existing UUID-locking launcher for GPU allocation.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,obj):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n');temp.replace(path)


def assert_method_matches(old,new):
    # Every original definition except input validation must be structurally identical.
    def definitions(path):
        tree=ast.parse(path.read_text())
        return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    before=definitions(old);after=definitions(new)
    for name,body in before.items():
        if name!='verify_inputs' and after.get(name)!=body:raise ValueError('Training implementation changed: '+name)


def main(a):
    root=Path(a.export).resolve();previous=Path(a.baseline_run).resolve();here=Path(__file__).resolve().parent
    status=root/'continuation_status.json'
    launcher=here/'launch_swin.py';trainer=here/'train_swin.py'
    assert_method_matches(previous/'train_swin_snapshot.py',trainer)
    bound={str(p):sha(p) for p in (launcher,trainer,Path(__file__))}
    save(root/'continuation_binding.json',{'code_sha256':bound,'previous_run':str(previous),'previous_config_sha256':sha(previous/'config.json'),
      'comparison':'same split, geometry, classes, training order and hyperparameters; crop-wise Tenengrad instead of zero plane',
      'test_inference':False})
    save(status,{'status':'waiting_for_verified_export','pid':os.getpid(),'test_inference':False})
    while True:
        if list(root.glob('failure_*.json')):raise RuntimeError('Export failure recorded; diagnose before retraining')
        state=json.loads((root/'status.json').read_text())
        if state['status']=='export_verified':break
        pid=state.get('pid')
        if pid:
            try:os.kill(pid,0)
            except ProcessLookupError:raise RuntimeError('Exporter disappeared before verification')
        time.sleep(15)
    for path,expected in bound.items():
        if sha(path)!=expected:raise ValueError('Code changed while waiting: '+path)
    from train_swin import verify_inputs
    _,_,audit=verify_inputs(root/'dataset',root/'record_assignments.csv',root/'category_map.csv')
    save(root/'pretraining_audit.json',audit)
    # Do not hold a GPU idle while extraction runs. Select only when inputs are ready.
    processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True)
    devices=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,memory.free','--format=csv,noheader,nounits'],text=True)
    candidates=[line.split(',')[0].strip() for line in devices.splitlines() if int(line.split(',')[1])>=16000 and line.split(',')[0].strip() not in processes]
    if not candidates:raise RuntimeError('No free GPU; verified export retained for subsequent launch')
    output=root/'training_attempt_01'
    command=[sys.executable,'-u',str(launcher),'--gpu',candidates[0],'--data',str(root/'dataset'),
      '--assignments',str(root/'record_assignments.csv'),'--categories',str(root/'category_map.csv'),'--output_root',str(output)]
    save(status,{'status':'training','gpu_uuid':candidates[0],'command':command,'test_inference':False})
    with (root/'training_launcher.log').open('x') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    run=output/'ordinary_baseline'
    old_config=json.loads((previous/'config.json').read_text());new_config=json.loads((run/'config.json').read_text())
    ignored={'data','assignments','categories','output'}
    if {k:v for k,v in old_config.items() if k not in ignored}!={k:v for k,v in new_config.items() if k not in ignored}:
        raise ValueError('Training configurations do not match')
    for key in ('weights_sha256','torch','torchvision','cuda'):
        old=json.loads((previous/'provenance.json').read_text());new=json.loads((run/'provenance.json').read_text())
        if old[key]!=new[key]:raise ValueError('Runtime/pretraining changed: '+key)
    old_metrics=json.loads((previous/'best_validation_metrics.json').read_text())
    new_metrics=json.loads((run/'best_validation_metrics.json').read_text())
    save(root/'comparison.json',{'baseline_run':str(previous),'best_plane_run':str(run),
      'baseline_validation':old_metrics,'best_plane_validation':new_metrics,
      'same_configuration':True,'test_inference':False,'interpretation':'single-seed validation comparison, not final test performance'})
    save(status,{'status':'complete','completed':time.time(),'comparison':str(root/'comparison.json'),'test_inference':False})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--export',required=True);p.add_argument('--baseline-run',required=True);args=p.parse_args()
    try:main(args)
    except BaseException:
        save(Path(args.export)/('continuation_failure_'+str(time.time_ns())+'.json'),{'traceback':traceback.format_exc(),'test_inference':False})
        save(Path(args.export)/'continuation_status.json',{'status':'failed','test_inference':False})
        raise

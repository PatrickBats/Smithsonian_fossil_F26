"""Hold a UUID GPU lock throughout smoke and baseline runs; preserve failures."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    p=argparse.ArgumentParser()
    for key in ('gpu','data','assignments','categories','output_root'):p.add_argument('--'+key,required=True)
    p.add_argument('--specimen-split')
    a=p.parse_args();out=Path(a.output_root);out.mkdir(parents=True,exist_ok=False)
    locks=Path('/tmp/codex-gpu-locks');locks.mkdir(exist_ok=True)
    with (locks/(a.gpu+'.lock')).open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True)
        if a.gpu in processes:raise RuntimeError('GPU already has compute processes')
        free=subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True)
        if int(free.strip())<16000:raise RuntimeError('Insufficient free GPU memory')
        lock.seek(0);lock.truncate();lock.write(json.dumps({'pid':os.getpid(),'purpose':'Smithsonian Swin baseline','started':time.time()}));lock.flush()
        env={**os.environ,'CUDA_VISIBLE_DEVICES':a.gpu,'CUBLAS_WORKSPACE_CONFIG':':4096:8',
             'OMP_NUM_THREADS':'4','TORCH_HOME':'/mnt/richb/pb52/model-cache/torch'}
        command=[sys.executable,'-u',str(Path(__file__).with_name('train_swin.py')),
                 '--data',a.data,'--assignments',a.assignments,'--categories',a.categories]
        if a.specimen_split:command+=['--specimen-split',a.specimen_split]
        for name,extra in [('smoke',['--smoke']),('ordinary_baseline',[])]:
            print('Starting '+name,flush=True)
            with (out/(name+'.log')).open('x') as log:
                subprocess.run(command+['--output',str(out/name)]+extra,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)


if __name__=='__main__':main()

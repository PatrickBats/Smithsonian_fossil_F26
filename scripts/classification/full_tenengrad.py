"""Stream full-resolution best-plane crops from read-only NOTS jobs, then verify.

Fixed image-only preprocessing across the adopted split; no test inference.
Completed batches can be resumed only with identical inputs and code snapshots.
"""
import argparse
import collections
import concurrent.futures
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import traceback

from PIL import Image, ImageStat

BASELINE_SHA = 'b4d803ca764f9941de38014bc5a67eb797f400a595033118c32512f5701e1373'
SPLIT_SHA = 'da2062a127cf6e14945e50fff097e0db102d7f8203250b47daed6b6bb166478d'
CATEGORY_SHA = '127bc3a8fa2dd60aae7bd0dc14f41d93d75e44f6ea277b5f0e0d7d7c9787f5a5'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    path=Path(path); temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n');temporary.replace(path)


def csvrows(path):
    with Path(path).open(newline='') as f:return list(csv.DictReader(f))


def worker_source():
    code=Path(__file__).with_name('tenengrad_pilot.py').read_text()
    old="if r['split']!='train':raise ValueError('Pilot is training-only')"
    assert code.count(old)==1
    code=code.replace(old,"if r['split'] not in ('train','val','test'):raise ValueError('Unknown split')")
    return code.replace("'training-only crop-wide Tenengrad pilot'", "'fixed crop-wide Tenengrad preprocessing; all partitions; no model inference'")


def run_batch(folder, rows, code):
    folder.mkdir(exist_ok=True)
    script=('REQUEST='+repr(rows)+'\n'+code).encode()
    scriptpath=folder/'remote_script.py'
    if scriptpath.exists() and scriptpath.read_bytes()!=script:raise ValueError('Batch input or worker changed')
    if not scriptpath.exists():scriptpath.write_bytes(script)
    done=folder/'complete.json'
    archive=folder/'selected.tar'
    if done.exists():
        meta=json.loads(done.read_text())
        if meta['archive_sha256']!=sha(archive) or meta['script_sha256']!=sha(scriptpath):raise ValueError('Completed batch modified')
        return archive
    attempt=1
    while (folder/f'attempt_{attempt}.json').exists():attempt+=1
    partial=folder/f'attempt_{attempt}.tar'
    command=['ssh','-o','BatchMode=yes','rice-nots',
      'srun --partition=commons --time=1-00:00:00 --ntasks=1 --cpus-per-task=2 --mem=16G '
      '--job-name=f26-tenengrad-full /projects/dsci435/smithsonian_sp26/conda-env/bin/python -B -']
    started=time.time()
    with scriptpath.open('rb') as stdin,partial.open('xb') as stdout,(folder/f'attempt_{attempt}.log').open('x') as stderr:
        process=subprocess.Popen(command,stdin=stdin,stdout=stdout,stderr=stderr)
        meta={'pid':process.pid,'command':command,'started':started,'script_sha256':sha(scriptpath),'records':len(rows)}
        save(folder/f'attempt_{attempt}.json',meta)
        result=process.wait()
    meta.update(returncode=result,elapsed_seconds=time.time()-started)
    save(folder/f'attempt_{attempt}.json',meta)
    if result:raise RuntimeError(f'{folder.name} failed with code {result}; see preserved attempt log')
    # Demand the final report before accepting the transport as complete.
    with tarfile.open(partial) as tar:
        report=json.load(tar.extractfile('report.json'))
        if report['status']!='complete' or len(report['records'])!=len(rows):raise ValueError('Incomplete batch report')
    partial.replace(archive)
    meta.update(archive_sha256=sha(archive),slurm_job_id=report['slurm_job_id'])
    save(done,meta)
    print(json.dumps({'batch':folder.name,'status':'streamed','records':len(rows),'job_id':report['slurm_job_id']}),flush=True)
    return archive


def assemble(root, batches, rows):
    destination=root/'dataset';destination.mkdir(exist_ok=True)
    by_id={r['record_id']:r for r in rows};results={};reports=[];payloads={}
    for archive in batches:
        with tarfile.open(archive) as tar:
            members=tar.getmembers();names=[m.name for m in members]
            if len(names)!=len(set(names)) or any(not m.isfile() for m in members):raise ValueError('Invalid tar members')
            report=json.load(tar.extractfile('report.json'));reports.append({k:v for k,v in report.items() if k!='records'})
            expected={'report.json'}
            for result in report['records']:
                rid=result['record_id']
                if rid not in by_id or rid in results:raise ValueError('Unexpected or duplicate record')
                row=by_id[rid];filename=hashlib.sha256(rid.encode()).hexdigest()+'.png';expected.add(filename)
                if result['selected_file']!=filename or result['split']!=row['split'] or result['category']!=row['sponsor_category']:
                    raise ValueError('Record identity mismatch')
                planes=result['planes']
                if not planes or [p['index'] for p in planes]!=list(range(len(planes))):raise ValueError('Missing plane scores')
                if len({p['z_offset'] for p in planes})!=len(planes) or sum(p['z_offset']==0 for p in planes)!=1:raise ValueError('Invalid plane offsets')
                if any(not math.isfinite(p['tenengrad']) or p['tenengrad']<0 for p in planes):raise ValueError('Invalid focus scores')
                best=max(planes,key=lambda p:(p['tenengrad'],-abs(p['z_offset']),-p['index']))
                if result['selected_index']!=best['index'] or result['selected_z_offset']!=best['z_offset'] or result['zero_plane_matches_baseline'] is not True:
                    raise ValueError('Selection or baseline identity check failed')
                data=tar.extractfile(filename).read()
                if len(data)!=result['selected_bytes'] or hashlib.sha256(data).hexdigest()!=result['selected_sha256']:raise ValueError('PNG integrity failure')
                with Image.open(io.BytesIO(data)) as image:
                    if image.format!='PNG' or image.mode!='RGB' or image.size!=(int(row['crop_side_px']),)*2:raise ValueError('Invalid crop geometry/format')
                    image.load();std=sum(ImageStat.Stat(image).stddev)/3
                path=destination/row['image_relpath'];path.parent.mkdir(exist_ok=True)
                if path.exists() and path.read_bytes()!=data:raise ValueError('Existing output differs; refusing overwrite')
                if not path.exists():path.write_bytes(data)
                updated={**row,'png_bytes':str(len(data)),'png_sha256':result['selected_sha256'],
                         'rgb_channel_std_mean':str(std),'representation':'crop_wide_tenengrad_best_plane',
                         'selected_plane_index':str(best['index']),'selected_z_offset':str(best['z_offset']),
                         'baseline_png_sha256':row['png_sha256']}
                results[rid]=result;payloads[rid]=updated
            if set(names)!=expected:raise ValueError('Unexpected files in stream')
    if set(results)!=set(by_id):raise ValueError('Missing records')
    finalrows=[payloads[r['record_id']] for r in rows]
    # Preserve the baseline order: changing training order would confound the comparison.
    with (destination/'crop_manifest.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(finalrows[0]));writer.writeheader();writer.writerows(finalrows)
    save(destination/'focus_scores.json',{'records':[results[r['record_id']] for r in rows],'batches':reports})
    save(destination/'representation.json',{'representation':'crop_wide_tenengrad_best_plane',
      'baseline_manifest_sha256':BASELINE_SHA,'split_sha256':SPLIT_SHA,'category_map_sha256':CATEGORY_SHA,
      'crop_manifest_sha256':sha(destination/'crop_manifest.csv'),'focus_scores_sha256':sha(destination/'focus_scores.json'),
      'binding_sha256':sha(root/'binding.json'),'records':len(rows),'test_inference':False,
      'method':'RGB2GRAY, mean squared 3x3 Sobel gradient, OpenCV default border; max score, nearest-zero then earliest-index ties',
      'geometry':'unchanged full-resolution baseline crop; no masks or focus stacking',
      'nonzero_planes_selected':sum(r['selected_z_offset']!=0 for r in results.values())})
    return destination


def main(a):
    root=Path(a.output);root.mkdir(parents=True,exist_ok=True)
    baseline=Path(a.baseline);assignments=Path(a.assignments);categories=Path(a.categories)
    if sha(baseline/'crop_manifest.csv')!=BASELINE_SHA or sha(assignments)!=SPLIT_SHA or sha(categories)!=CATEGORY_SHA:
        raise ValueError('Frozen input fingerprint differs')
    rows=csvrows(baseline/'crop_manifest.csv');code=worker_source()
    binding={'baseline_sha256':BASELINE_SHA,'assignments_sha256':SPLIT_SHA,'categories_sha256':CATEGORY_SHA,
      'worker_sha256':hashlib.sha256(code.encode()).hexdigest(),'orchestrator_sha256':sha(__file__),'workers':a.workers}
    if (root/'binding.json').exists() and json.loads((root/'binding.json').read_text())!=binding:raise ValueError('Resume binding changed')
    save(root/'binding.json',binding)
    for source,name in [(baseline/'crop_manifest.csv','baseline_crop_manifest.csv'),(assignments,'record_assignments.csv'),(categories,'category_map.csv'),(Path(__file__),'full_tenengrad_snapshot.py')]:
        target=root/name
        if target.exists() and target.read_bytes()!=source.read_bytes():raise ValueError('Snapshot changed')
        if not target.exists():target.write_bytes(source.read_bytes())
    sources=collections.defaultdict(list)
    for row in rows:sources[row['image_nots_path']].append(row)
    batches=[[] for _ in range(a.workers)];loads=[0]*a.workers
    for path,group in sorted(sources.items(),key=lambda item:(-sum(int(r['crop_side_px'])**2 for r in item[1]),item[0])):
        index=min(range(a.workers),key=lambda i:loads[i]);batches[index].extend(group);loads[index]+=sum(int(r['crop_side_px'])**2 for r in group)
    save(root/'status.json',{'status':'exporting','records':len(rows),'sources':len(sources),'pid':os.getpid(),'started':time.time(),'test_inference':False})
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures=[pool.submit(run_batch,root/f'batch_{i:02}',group,code) for i,group in enumerate(batches)]
        archives=[future.result() for future in futures]
    dataset=assemble(root,archives,rows)
    # The training validator rechecks every source field, PNG, geometry, group and split.
    from train_swin import verify_inputs
    _,_,audit=verify_inputs(dataset,assignments,categories)
    save(root/'verified_data.json',audit)
    save(root/'status.json',{'status':'export_verified','records':len(rows),'completed':time.time(),'test_inference':False})
    print('Full export verified: '+str(dataset),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('baseline','assignments','categories','output'):p.add_argument('--'+key,required=True)
    p.add_argument('--workers',type=int,default=4)
    args=p.parse_args()
    if not 1<=args.workers<=4:p.error('Use one to four workers')
    try:main(args)
    except BaseException:
        root=Path(args.output)
        if root.exists():save(root/('failure_'+str(time.time_ns())+'.json'),{'traceback':traceback.format_exc(),'test_inference':False})
        raise

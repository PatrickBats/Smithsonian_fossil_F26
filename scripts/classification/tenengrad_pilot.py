"""Read-only Slurm pilot; inject REQUEST (selected crop records) before execution.

Stdout is a tar stream of selected PNGs and measurements. No remote file writes.
Uses crop-wide mean squared Sobel gradients, like the prior team's code.
"""
import collections
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import sys
import tarfile
import time

import cv2
import numpy as np
from PIL import Image
import tifffile
import zarr


def score(rgb):
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError('Expected uint8 RGB')
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    gx=cv2.Sobel(gray,cv2.CV_64F,1,0,ksize=3)
    gy=cv2.Sobel(gray,cv2.CV_64F,0,1,ksize=3)
    value=float(np.mean(gx*gx+gy*gy))
    if not np.isfinite(value):raise ValueError('Nonfinite focus score')
    return value


def png(rgb):
    b=io.BytesIO();Image.fromarray(rgb).save(b,format='PNG',compress_level=3)
    return b.getvalue()


def add(archive,name,data):
    item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o644;item.mtime=0
    archive.addfile(item,io.BytesIO(data))


def main(records):
    started=time.monotonic();cv2.setNumThreads(1)
    sources=collections.defaultdict(list)
    for r in records:
        if r['split']!='train':raise ValueError('Pilot is training-only')
        sources[r['image_nots_path']].append(r)
    outputs=[]
    with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as archive:
        for path,rows in sorted(sources.items()):
            before=Path(path).stat();slide_start=time.monotonic()
            with tifffile.TiffFile(path) as tif:
                series=tif.series[0]
                if series.axes!='ZYXS':raise ValueError('Unsupported NDPI axes')
                offsets=[int(page.tags[65424].value) for page in series.pages]
                if offsets.count(0)!=1:raise ValueError('Expected one zero-offset plane')
                with series.aszarr() as store:
                    array=zarr.open(store,mode='r')
                    if isinstance(array,zarr.Group):array=array['0']
                    for r in rows:
                        if tuple(array.shape)!=(len(offsets),int(r['source_height_px']),int(r['source_width_px']),3):
                            raise ValueError('Focal series dimensions differ from crop source')
                        crop_start=time.monotonic();side=int(r['crop_side_px']);x=int(r['crop_left_px']);y=int(r['crop_top_px'])
                        planes=[];best=None;best_key=None;best_index=None;zero_match=False
                        for i,z in enumerate(offsets):
                            t=time.monotonic()
                            rgb=np.asarray(array[i,y:y+side,x:x+side,:])
                            read_seconds=time.monotonic()-t
                            if rgb.shape!=(side,side,3):raise ValueError('Incomplete crop')
                            t=time.monotonic();value=score(rgb);score_seconds=time.monotonic()-t
                            planes.append({'index':i,'z_offset':z,'tenengrad':value,'read_seconds':read_seconds,'score_seconds':score_seconds})
                            # Deterministic ties prefer a plane closer to the existing zero offset.
                            key=(value,-abs(z),-i)
                            if best_key is None or key>best_key:best_key=key;best=rgb.copy();best_index=i
                            if z==0:
                                zero_match=hashlib.sha256(png(rgb)).hexdigest()==r['png_sha256']
                                if not zero_match:raise ValueError('Zero plane differs from verified baseline PNG')
                        payload=png(best);name=hashlib.sha256(r['record_id'].encode()).hexdigest()+'.png'
                        add(archive,name,payload)
                        zero=next(p for p in planes if p['z_offset']==0)
                        result={'record_id':r['record_id'],'category':r['sponsor_category'],'slide_id':r['slide_id'],
                          'split':r['split'],'crop_side_px':side,'baseline_relpath':r['image_relpath'],'selected_file':name,
                          'selected_sha256':hashlib.sha256(payload).hexdigest(),'selected_bytes':len(payload),
                          'selected_index':best_index,'selected_z_offset':offsets[best_index],
                          'zero_plane_matches_baseline':zero_match,'planes':planes,
                          'score_ratio_to_zero':best_key[0]/zero['tenengrad'] if zero['tenengrad'] else None,
                          'crop_elapsed_seconds':time.monotonic()-crop_start}
                        outputs.append(result)
                        print(json.dumps({'record':r['record_id'],'planes':len(planes),'selected_z':offsets[best_index],
                           'seconds':result['crop_elapsed_seconds']}),file=sys.stderr,flush=True)
            after=Path(path).stat()
            if (before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):
                raise ValueError('Source changed during reads')
            print('Slide seconds: '+str(time.monotonic()-slide_start),file=sys.stderr,flush=True)
        report={'status':'complete','scope':'training-only crop-wide Tenengrad pilot','slurm_job_id':os.environ.get('SLURM_JOB_ID'),
          'records':outputs,'elapsed_seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'cpu_seconds':resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,
          'versions':{'numpy':np.__version__,'opencv':cv2.__version__,'tifffile':tifffile.__version__,'zarr':zarr.__version__},
          'method':'RGB to grayscale; mean(Gx^2+Gy^2), 3x3 Sobel, OpenCV default border; highest score; nearest-zero tie break',
          'test_evaluated':False,'remote_files_written':False}
        add(archive,'report.json',(json.dumps(report,indent=2,allow_nan=False)+'\n').encode())


if __name__=='__main__':main(REQUEST)

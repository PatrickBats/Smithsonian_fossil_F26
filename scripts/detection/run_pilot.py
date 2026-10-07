"""Frozen-checkpoint detection diagnostic on annotation-centered slide regions."""
import argparse,collections,csv,datetime,fcntl,hashlib,json,os,pathlib,platform,sys,time,traceback

def box_pixels(center,radius,meta):
 x,y=center
 return [(x-radius-meta.x_offset_nm)/(meta.mpp_x*1000)+meta.full_width/2,
         (y-radius-meta.y_offset_nm)/(meta.mpp_y*1000)+meta.full_height/2,
         (x+radius-meta.x_offset_nm)/(meta.mpp_x*1000)+meta.full_width/2,
         (y+radius-meta.y_offset_nm)/(meta.mpp_y*1000)+meta.full_height/2]

def iou(a,b):
 inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
 union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
 return inter/union if union>0 else 0.0

def run(args):
 import numpy as np,torch,cv2,ultralytics
 from PIL import Image,ImageDraw
 sys.path.insert(0,str(args.root/'upstream'))
 from src.data.ndpi_reader import NDPIData
 from src.annotator.compression import focus_stack,best_focal_plane
 from ultralytics import YOLO
 output=args.root/'outputs'/f'shard_{args.shard}';output.mkdir(parents=True,exist_ok=False)
 assert torch.cuda.is_available(),'Allocated GPU unavailable'
 uuid=str(torch.cuda.get_device_properties(0).uuid)
 lock=open('/tmp/smithsonian-gpu-'+uuid+'.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 start=time.time();config=json.loads((args.root/'config.json').read_text())
 targets=json.loads((args.root/'pilot_targets.json').read_text());targets=[r for i,r in enumerate(targets) if i%2==args.shard]
 sources={r['annotation_file']:r for r in csv.DictReader((args.root/'cluster_source_paths.csv').open())}
 for name in {r['annotation_file'] for r in targets}:
  s=sources[name];assert hashlib.sha256(pathlib.Path(s['annotation_path']).read_bytes()).hexdigest()==s['annotation_sha256']
 models={};weights={}
 for rep,name in config['checkpoints'].items():
  path=args.root/'weights'/name;h=hashlib.sha256(path.read_bytes()).hexdigest();assert h==config['checkpoint_sha256'][name]
  models[rep]=YOLO(str(path));models[rep].to('cuda:0');assert len(models[rep].names)==1,models[rep].names
  weights[rep]=dict(sha256=h,names=models[rep].names,training_args=str(getattr(models[rep],'ckpt',{}).get('train_args',{})))
 provenance=dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),slurm_job_id=os.environ.get('SLURM_JOB_ID'),slurm_array_job_id=os.environ.get('SLURM_ARRAY_JOB_ID'),gpu_uuid=uuid,gpu_name=torch.cuda.get_device_name(0),python=sys.version,torch=torch.__version__,ultralytics=ultralytics.__version__,weights=weights,config=config,shard=args.shard)
 (output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 rows=[];ndpi=None;current=None
 try:
  for n,r in enumerate(sorted(targets,key=lambda x:(x['slide'],x['record_id']))):
   tick=time.time();print('START',args.shard,n+1,len(targets),r['record_id'],flush=True)
   if current!=r['image_file']:
    if ndpi is not None:ndpi.close()
    ndpi=NDPIData(r['image_file']);current=r['image_file']
   m=ndpi.metadata;assert m.mpp_x>0 and m.mpp_y>0
   assert abs(m.objective_power-40)<1e-6,'Pilot requires native 40x'
   gt=box_pixels(r['center_nm'],r['radius_nm'],m)
   assert 0<=gt[0]<gt[2]<=m.full_width and 0<=gt[1]<gt[3]<=m.full_height,(r['record_id'],gt)
   size=config['tile_size'];x=max(0,min(m.full_width-size,int((gt[0]+gt[2])/2-size/2)));y=max(0,min(m.full_height-size,int((gt[1]+gt[3])/2-size/2)))
   localgt=[gt[0]-x,gt[1]-y,gt[2]-x,gt[3]-y];assert min(localgt)>=0 and max(localgt)<=size
   planes=sorted([p for p in ndpi.focal_planes if abs(p.magnification-40)<1e-6],key=lambda p:p.z_offset_nm)
   assert planes and len({p.z_offset_nm for p in planes})==len(planes)
   stack=np.stack([ndpi.get_tile_from_page(p.page_index,x,y,size,size) for p in planes],axis=-1)
   assert stack.shape==(size,size,3,len(planes)) and stack.dtype==np.uint8
   variants={'focus_stack':focus_stack(stack,5),'best_plane':best_focal_plane(stack,3)}
   targetout=output/f'target_{n:03d}';targetout.mkdir()
   for rep,image in variants.items():
    assert image.shape==(size,size,3) and np.isfinite(image).all()
    result=models[rep].predict(source=cv2.cvtColor(image,cv2.COLOR_RGB2BGR),imgsz=size,conf=config['prediction_floor'],iou=config['nms_iou'],device=0,verbose=False,save=False,max_det=300,half=False)[0]
    boxes=result.boxes.xyxy.cpu().numpy().tolist();scores=result.boxes.conf.cpu().numpy().tolist();assert np.isfinite(np.array(boxes)).all() and np.isfinite(scores).all()
    overlaps=[iou(localgt,b) for b in boxes]
    hit=[(score,ov) for score,ov in zip(scores,overlaps) if ov>=config['match_iou']]
    best=max((sc for sc,ov in hit),default=0.0)
    row=dict(record_id=r['record_id'],category=r['mapped_category'],slide=r['slide'],representation=rep,center_inside_roi=r['center_inside_roi'],box_inside_roi=r['box_inside_roi'],hit_conf_050=best>=.5,hit_conf_025=best>=.25,best_matching_score=best,max_iou=max(overlaps,default=0),prediction_count_conf_050=sum(s>=.5 for s in scores),tile_x=x,tile_y=y,focal_planes=len(planes))
    rows.append(row)
    (targetout/(rep+'.json')).write_text(json.dumps(dict(target=r,target_box_xyxy=localgt,global_box_xyxy=gt,z_offsets_nm=[p.z_offset_nm for p in planes],boxes=boxes,scores=scores,ious=overlaps,summary=row),indent=2)+'\n')
    Image.fromarray(image).save(targetout/(rep+'_input.png'))
    overlay=Image.fromarray(image);draw=ImageDraw.Draw(overlay);draw.rectangle(localgt,outline='cyan',width=4)
    for b,sc in zip(boxes,scores):
     if sc>=.5:draw.rectangle(b,outline='orange',width=3)
    draw.rectangle((0,0,size,48),fill='white');draw.text((8,5),f"{r['mapped_category']} | {rep} | found={best>=.5}",fill='black');draw.text((8,25),'CYAN: target annotation | ORANGE: predictions at confidence >= 0.5',fill='black')
    overlay.save(targetout/(rep+'_overlay.png'))
   del stack,variants
   with (output/'results.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,rows[0].keys());w.writeheader();w.writerows(rows)
   print('DONE',args.shard,n+1,'seconds',round(time.time()-tick,1),flush=True)
  summary={}
  for rep in models:
   rr=[r for r in rows if r['representation']==rep];summary[rep]={'targets':len(rr),'found_conf_050':sum(r['hit_conf_050'] for r in rr),'found_conf_025':sum(r['hit_conf_025'] for r in rr)}
  (output/'complete.json').write_text(json.dumps(dict(summary=summary,elapsed_seconds=time.time()-start,gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated()),indent=2)+'\n')
 except BaseException as e:
  (output/'failure.json').write_text(json.dumps(dict(error=repr(e),traceback=traceback.format_exc(),elapsed_seconds=time.time()-start),indent=2)+'\n');raise
 finally:
  if ndpi is not None:ndpi.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--shard',type=int,choices=[0,1],required=True);run(p.parse_args())

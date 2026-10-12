"""Abbas ROI grid: 40x, 1024 native pixels, 10% overlap, LoG k=5.

Image selection depends only on ROI geometry, never specimen locations.
Keeps empty tiles. Uses frozen target-class scope and grouped split.
"""
import argparse,collections,hashlib,json,math,os,zlib
from pathlib import Path
import xml.etree.ElementTree as ET
import cv2,numpy as np,openslide,tifffile,zarr
from PIL import Image
from pipeline_common import validate_inputs,sha,save
from spring_focus_stack import focus_stack

def positions(start,end,size,stride):
    if end-start<size:return []
    return sorted({min(p,end-size) for p in range(start,end,stride)})

def rectangle(ann):
    if ann.get('type')!='freehand':return None
    pts=[(float(p.findtext('x')),float(p.findtext('y'))) for p in ann.findall('.//point')]
    if len(pts)<4:return None
    x0=min(p[0] for p in pts);x1=max(p[0] for p in pts);y0=min(p[1] for p in pts);y1=max(p[1] for p in pts)
    corners=[(x0,y0),(x0,y1),(x1,y0),(x1,y1)]
    # Historical NDPA corners occasionally differ by 1 nanometre.
    if x1<=x0 or y1<=y0:return None
    if not all(any(abs(x-cx)<=1 and abs(y-cy)<=1 for cx,cy in corners) for x,y in pts):return None
    if not all(any(abs(x-cx)<=1 and abs(y-cy)<=1 for x,y in pts) for cx,cy in corners):return None
    return x0,y0,x1,y1

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--plan-only',action='store_true');ap.add_argument('--shard',type=int);ap.add_argument('--shards',type=int,default=4)
    a=ap.parse_args();c,records,mapping=validate_inputs(a.config)
    assert c['representation']=='abbas_log_focus_stack_k5' and c['overlap']==.1
    out=Path(c['workspace']);out.mkdir(parents=True,exist_ok=True);save(out/'contract.json',c)
    cv2.setNumThreads(1);grouped=collections.defaultdict(list)
    for r in records:
        if r['split']!='test':grouped[r['image_nots_path']].append(r)
    total=collections.Counter();covered_by_split=collections.defaultdict(set);excluded=[];references=[];roi_report=[]
    size=c['native_tile_size'];stride=int(size*(1-c['overlap']))
    for n,(image,rr) in enumerate(sorted(grouped.items())):
        if a.shard is not None and n%a.shards!=a.shard:continue
        annotation=Path(rr[0]['annotation_nots_path']);raw=annotation.read_bytes();states=list(ET.fromstring(raw).iter('ndpviewstate'));by_id={s.get('id'):s for s in states}
        assert all(x['annotation_nots_path']==str(annotation) and x['annotation_crc32']==format(zlib.crc32(raw)&0xffffffff,'08x') for x in rr)
        with openslide.OpenSlide(image) as slide:
            width,height=slide.dimensions;p=slide.properties;mx,my=float(p['openslide.mpp-x']),float(p['openslide.mpp-y']);ox,oy=float(p['hamamatsu.XOffsetFromSlideCentre']),float(p['hamamatsu.YOffsetFromSlideCentre'])
            assert float(p['openslide.objective-power'])==40
        def xy(x,y):return (x-ox)/(mx*1000)+width/2,(y-oy)/(my*1000)+height/2
        objects=[]
        for r in rr:
            ann=by_id[r['viewstate_id']].find('annotation');assert ann.get('type')=='circle'
            assert all(float(ann.findtext(k))==float(r[field]) for k,field in [('x','x_nm'),('y','y_nm'),('radius','radius_nm')])
            x,y=xy(float(r['x_nm']),float(r['y_nm']));rx=float(r['radius_nm'])/(mx*1000);ry=float(r['radius_nm'])/(my*1000)
            b=[x-rx,y-ry,x+rx,y+ry];assert rx>0 and ry>0 and all(math.isfinite(v) for v in b)
            objects.append({'record_id':r['record_id'],'box_slide':b,'fine_category':r['sponsor_category'],'broad_category':mapping[r['sponsor_category']]})
        grid={};rois=[]
        for state in states:
            ann=state.find('annotation')
            if ann is None:continue
            bounds=rectangle(ann)
            if bounds is None:continue
            x0,y0=xy(bounds[0],bounds[1]);x1,y1=xy(bounds[2],bounds[3])
            roi=[max(0,math.ceil(x0)),max(0,math.ceil(y0)),min(width,math.floor(x1)),min(height,math.floor(y1))]
            rois.append({'state_id':state.get('id'),'bounds':roi})
            xs=positions(roi[0],roi[2],size,stride);ys=positions(roi[1],roi[3],size,stride)
            for top in ys:
                for left in xs:grid.setdefault((left,top),[]).append(state.get('id'))
        assert rois,'No rectangular ROI found'
        tiles=[];covered=set();split=rr[0]['split'];annsha=sha(annotation)
        for (left,top),roi_ids in sorted(grid.items(),key=lambda p:(p[0][1],p[0][0])):
            kept=[]
            for obj in objects:
                b=obj['box_slide'];x0,y0=max(0,b[0]-left),max(0,b[1]-top);x1,y1=min(size,b[2]-left),min(size,b[3]-top)
                area=max(0,x1-x0)*max(0,y1-y0);fraction=area/((b[2]-b[0])*(b[3]-b[1]))
                # Exact Spring retained-area convention; paper describes <25%.
                if area>=16 and fraction>.25:
                    kept.append(dict(obj,bbox=[x0,y0,x1-x0,y1-y0],area=area,visible_fraction=fraction));covered.add(obj['record_id'])
            identity=f'{image}:{left}:{top}:{size}:abbas-log-k5';tid=hashlib.sha256(identity.encode()).hexdigest()[:24]
            tiles.append({'tile_id':tid,'image':image,'annotation':str(annotation),'annotation_sha256':annsha,'split':split,'group':rr[0]['accession_group_id'],'left':left,'top':top,'size':size,'roi_ids':roi_ids,'objects':kept,'anchors':[x['record_id'] for x in kept],'identity':identity,'representation':c['representation']})
        covered_by_split[split].update(covered)
        references.extend(dict(obj,image=image,split=split,group=rr[0]['accession_group_id']) for obj in objects if obj['record_id'] in covered)
        excluded.extend({'record_id':obj['record_id'],'image':image,'split':split,'reason':'not_retained_in_any_ROI_grid_tile'} for obj in objects if obj['record_id'] not in covered)
        roi_report.append({'image':image,'split':split,'rois':rois,'grid_tiles':len(tiles),'covered_records':len(covered),'excluded_records':len(objects)-len(covered)})
        if a.plan_only:
            total[split]+=len(tiles);total['empty_tiles']+=sum(not t['objects'] for t in tiles)
            print(json.dumps({'source':n,'tiles':len(tiles),'covered':len(covered),'excluded':len(objects)-len(covered)}),flush=True);continue
        folder=out/'dataset'/('valid' if split=='val' else 'train');folder.mkdir(parents=True,exist_ok=True)
        with tifffile.TiffFile(image) as tif:
            pages=[(i,p) for i,p in enumerate(tif.pages) if 65421 in p.tags and 65424 in p.tags and abs(float(p.tags[65421].value)-40)<1e-6]
            assert pages and all(p.shape[:2]==(height,width) for _,p in pages)
            for t in tiles:
                png=folder/(t['tile_id']+'.png');meta=png.with_suffix('.json')
                total[split]+=1;total['empty_tiles']+=not t['objects']
                if meta.exists():
                    old=json.loads(meta.read_text());assert old['identity']==t['identity'] and old['annotation_sha256']==annsha and old['png_sha256']==sha(png)
                    continue
                planes=[]
                for _,page in pages:
                    with page.aszarr() as store:rgb=np.asarray(zarr.open(store,mode='r')[t['top']:t['top']+size,t['left']:t['left']+size,:])
                    assert rgb.shape==(size,size,3) and rgb.dtype==np.uint8;planes.append(rgb)
                rgb,scores=focus_stack(np.stack(planes,axis=-1),k=5);Image.fromarray(rgb).save(png)
                t.update(png_sha256=sha(png),z_offsets_nm=[int(p.tags[65424].value) for _,p in pages],plane_mean_abs_log=scores.tolist())
                save(meta,t)
        print(json.dumps({'source':n,'tiles':len(tiles),'covered':len(covered),'excluded':len(objects)-len(covered)}),flush=True)
    name='plan' if a.plan_only else f'export_shard_{a.shard}'
    save(out/(name+'_references.json'),references);save(out/(name+'_excluded.json'),excluded);save(out/(name+'_rois.json'),roi_report)
    report={'status':'plan' if a.plan_only else 'export_complete','tile_counts':dict(total),'covered_records':{k:len(v) for k,v in covered_by_split.items()},'excluded_records':len(excluded),'test_decoded':False,'selection':'all fixed-grid tiles within rectangular ROIs, including empty tiles; independent of specimen coordinates','representation':c['representation'],'native_tile_size':size,'stride':stride,'nominal_overlap':.1,'edge_policy':'Spring backshift; repeated positions removed; ROI rounded inward; undersized ROIs reported/skipped','job_id':os.environ.get('SLURM_JOB_ID'),'config_sha256':sha(a.config),'focus_helper_sha256':sha(Path(__file__).with_name('spring_focus_stack.py'))}
    save(out/(name+'.json'),report);print(json.dumps(report),flush=True)

if __name__=='__main__':main()

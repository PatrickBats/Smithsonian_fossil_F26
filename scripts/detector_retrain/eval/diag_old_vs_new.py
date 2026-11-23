import json,gzip,os,re,collections,contextlib,io,sys
import numpy as np
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval
R=os.path.expanduser("~/Smithsonian_F26"); C=R+"/processed/coco_detector_v2"; E=R+"/model_A/detector_v2/eval_20261120"
def load_gt(p):
    d=json.load(open(p))
    for a in d["annotations"]: a["category_id"]=1
    d["categories"]=[{"id":1,"name":"p"}]
    return d
def isnew(fn):
    m=re.search(r"_tile_(\d+)_(\d+)\.",fn); return int(m.group(1))%1024==0 and int(m.group(2))%1024==0
print("## A. composition (new = tile offsets on the 1024 grid)")
for s in ["train","val","test"]:
    d=json.load(open(f"{C}/combined/annotations/instances_{s}.json"))
    new={i["id"]:isnew(i["file_name"]) for i in d["images"]}
    for tag,flag in [("old",False),("new",True)]:
        ims=[i for i in new if new[i]==flag]; an=[a for a in d["annotations"] if new[a["image_id"]]==flag]
        has=set(a["image_id"] for a in an)
        full=[a for a in an if a["bbox"][0]>2 and a["bbox"][1]>2 and a["bbox"][0]+a["bbox"][2]<1022 and a["bbox"][1]+a["bbox"][3]<1022]
        w=np.array([a["bbox"][2] for a in full]); h=np.array([a["bbox"][3] for a in full])
        if len(ims): print(f"  {s:5s} {tag}: imgs {len(ims):6d} anns {len(an):6d} empty {1-len(has)/len(ims):.2f}  uncut boxes: median w {np.median(w):.0f} h {np.median(h):.0f}  square(|w-h|<=1) {np.mean(np.abs(w-h)<=1):.2f}")
def iou(b,g):
    x1=np.maximum(b[:,None,0],g[None,:,0]);y1=np.maximum(b[:,None,1],g[None,:,1]);x2=np.minimum(b[:,None,2],g[None,:,2]);y2=np.minimum(b[:,None,3],g[None,:,3])
    inter=np.clip(x2-x1,0,None)*np.clip(y2-y1,0,None)
    return inter/((b[:,2]-b[:,0])*(b[:,3]-b[:,1]))[:,None].clip(1e-9)+0*inter if False else inter/(((b[:,2]-b[:,0])*(b[:,3]-b[:,1]))[:,None]+((g[:,2]-g[:,0])*(g[:,3]-g[:,1]))[None,:]-inter).clip(1e-9)
def coco_ap(gt,pred,scale=1.0,ious=None):
    dets=[]
    for k,v in pred.items():
        for x1,y1,x2,y2,s in v:
            cx,cy,w,h=(x1+x2)/2,(y1+y2)/2,(x2-x1)*scale,(y2-y1)*scale
            a,b,c,d_=max(cx-w/2,0),max(cy-h/2,0),min(cx+w/2,1024),min(cy+h/2,1024)
            if scale==1.0: a,b,c,d_=x1,y1,x2,y2
            dets.append({"image_id":int(k),"category_id":1,"bbox":[a,b,c-a,d_-b],"score":s})
    with contextlib.redirect_stdout(io.StringIO()):
        g=COCO(); g.dataset=gt; g.createIndex(); dt=g.loadRes(dets); ev=COCOeval(g,dt,"bbox"); ev.params.maxDets=[1,100,500]
        if ious is not None: ev.params.iouThrs=np.array(ious)
        ev.evaluate(); ev.accumulate()
    p=ev.eval["precision"][:,:,0,0,2]  # T x R
    return [float(np.mean(p[t][p[t]>-1])) for t in range(p.shape[0])]
def pairs(gt,pred,thr=0.1):
    """for each GT: best-IoU prediction with score>=thr -> (iou, wr, hr, score, gt w, cut)"""
    by=collections.defaultdict(list)
    for a in gt["annotations"]: by[a["image_id"]].append(a["bbox"])
    out=[]
    for im,gs in by.items():
        g=np.array([[x,y,x+w,y+h] for x,y,w,h in gs],float); p=np.array([q for q in pred.get(str(im),[]) if q[4]>=thr],float).reshape(-1,5)
        cut=(g[:,0]<=2)|(g[:,1]<=2)|(g[:,2]>=1022)|(g[:,3]>=1022)
        if len(p)==0:
            for j in range(len(g)): out.append((0,np.nan,np.nan,0,g[j,2]-g[j,0],cut[j]))
            continue
        M=iou(p[:,:4],g)
        for j in range(len(g)):
            i=M[:,j].argmax(); out.append((M[i,j],(p[i,2]-p[i,0])/(g[j,2]-g[j,0]),(p[i,3]-p[i,1])/(g[j,3]-g[j,1]),p[i,4],g[j,2]-g[j,0],cut[j]))
    return np.array(out,float)
SETS={"old_test":C+"/combined/annotations/instances_test.json","test_new":None}
for cand in [C+"/test_new/annotations/instances_test.json"]+[os.path.join(dp,f) for dp,_,fs in os.walk(C+"/test_new") for f in fs if f.endswith(".json")]:
    if os.path.exists(cand): SETS["test_new"]=cand; break
IOUS=[0.1,0.3,0.5,0.75]
for sname,gp in SETS.items():
    gt=load_gt(gp)
    print(f"\n## B. {sname}  ({len(gt['images'])} tiles, {len(gt['annotations'])} grains)")
    P={m:json.load(gzip.open(f"{E}/pred_{m}_{sname}.json.gz")) for m in ["last_semester","new_detector"]}
    for m in P:
        ap=coco_ap(gt,P[m],ious=IOUS); print(f"  {m:14s} AP at IoU 0.1/0.3/0.5/0.75: "+" / ".join(f"{a:.3f}" for a in ap))
    Q={m:pairs(gt,P[m]) for m in P}
    for m in P:
        q=Q[m]; un=q[q[:,5]==0]; f=un[un[:,0]>=0.3]
        print(f"  {m:14s} uncut grains {len(un)}: found(IoU>=.3) {len(f)/len(un):.3f} | of found: median IoU {np.median(f[:,0]):.3f}, IoU>=.5 {np.mean(f[:,0]>=.5):.3f}, IoU>=.75 {np.mean(f[:,0]>=.75):.3f} | pred/GT width median {np.median(f[:,1]):.3f} height {np.median(f[:,2]):.3f} | median score {np.median(f[:,3]):.3f}")
        c=q[q[:,5]==1]; fc=c[c[:,0]>=0.3]
        print(f"  {'':14s} edge-cut grains {len(c)}: found {len(fc)/max(len(c),1):.3f}, IoU>=.5 among found {np.mean(fc[:,0]>=.5) if len(fc) else 0:.3f}")
    a,b=Q["last_semester"],Q["new_detector"]; both=(a[:,0]>=.3)&(b[:,0]>=.3)
    print(f"  grains found (IoU>=.3, score>=.1): both {both.sum()}, only last_sem {((a[:,0]>=.3)&(b[:,0]<.3)).sum()}, only new {((a[:,0]<.3)&(b[:,0]>=.3)).sum()}, neither {((a[:,0]<.3)&(b[:,0]<.3)).sum()}")
    print(f"  on grains found by both: median score last_sem {np.median(a[both,3]):.3f} vs new {np.median(b[both,3]):.3f}; new box wider than last_sem's on {np.mean(b[both,1]>a[both,1]):.2f} of them")
    print("  box rescale sweep (scale every predicted box about its centre) -> mAP50 / mAP50:95")
    for m in P:
        row=[]
        for s in [0.85,0.90,0.95,1.0,1.05,1.10,1.15]:
            ap=coco_ap(gt,P[m],scale=s); row.append(f"{s:.2f}: {ap[0]:.3f}/{np.mean(ap):.3f}")
        print(f"   {m:14s} "+" | ".join(row))

# ---- C. where the ranking gap comes from (old_test), IoU>=0.3 greedy matching by score
gt=load_gt(SETS["old_test"]); P={m:json.load(gzip.open(f"{E}/pred_{m}_old_test.json.gz")) for m in ["last_semester","new_detector"]}
fn={i["id"]:i["file_name"] for i in gt["images"]}
by=collections.defaultdict(list)
for a in gt["annotations"]: x,y,w,h=a["bbox"]; by[a["image_id"]].append([x,y,x+w,y+h])
def match(pred,thr_iou=0.3):
    rows=[]; gfound={}
    for im in fn:
        g=np.array(by.get(im,[]),float).reshape(-1,4); p=np.array(sorted(pred.get(str(im),[]),key=lambda q:-q[4]),float).reshape(-1,5)
        used=np.zeros(len(g),bool); best=np.zeros(len(g))
        M=iou(p[:,:4],g) if len(p) and len(g) else np.zeros((len(p),len(g)))
        for i in range(len(p)):
            tp=False; mx=M[i].max() if len(g) else 0
            if len(g):
                cand=np.where((M[i]>=thr_iou)&~used)[0]
                if len(cand): j=cand[M[i,cand].argmax()]; used[j]=True; best[j]=p[i,4]; tp=True
            rows.append((p[i,4],tp,mx,im,p[i,2]-p[i,0],p[i,3]-p[i,1]))
        for j in range(len(g)): gfound[(im,j)]=best[j]
    return np.array([(r[0],r[1],r[2]) for r in rows],float),rows,gfound
print("\n## C. old_test, precision at matched recall (IoU>=0.3)")
res={}
for m in P:
    A,rows,gf=match(P[m]); res[m]=(A,rows,gf); o=np.argsort(-A[:,0]); tp=np.cumsum(A[o,1]); fp=np.cumsum(1-A[o,1]); rec=tp/1594; prec=tp/(tp+fp)
    line=[]
    for r in [0.5,0.6,0.7,0.8,0.85,0.9,0.95]:
        k=np.searchsorted(rec,r)
        line.append(f"R{r}: P {prec[k]:.3f} (score {A[o[k],0]:.2f})" if k<len(rec) else f"R{r}: not reached")
    print(f"  {m:14s} max recall {rec[-1]:.3f} | "+" | ".join(line))
print("\n## D. false alarms on old_test at score>=0.3 (no label with IoU>=0.3)")
for m in P:
    A,rows,gf=res[m]; hi=[r for r in rows if r[0]>=0.3]; fps=[r for r in hi if not r[1]]
    near=[r for r in fps if r[2]>=0.05]; far=[r for r in fps if r[2]<0.05]
    w=np.array([r[4] for r in far]); edge=0
    print(f"  {m:14s} detections {len(hi)}, false alarms {len(fps)}: duplicate/overlapping a labelled grain {len(near)}, nowhere near a label {len(far)} (median width {np.median(w):.0f}px)")
# are the new detector's far false alarms also seen by last semester's model at any score>=0.05?
A,rows,gf=res["new_detector"]; far=[r for r in rows if r[0]>=0.3 and not r[1] and r[2]<0.05]
print("  (new detector 'nowhere near a label' false alarms: see contact sheet)")
print("\n## E. grains missed by the new detector at score>=0.3 but found by last semester's")
ga,gb=res["last_semester"][2],res["new_detector"][2]
keys=list(ga); a=np.array([ga[k] for k in keys]); b=np.array([gb[k] for k in keys])
G=np.array([by[k[0]][k[1]] for k in keys]); wid=G[:,2]-G[:,0]; hei=G[:,3]-G[:,1]; cut=(G[:,0]<=2)|(G[:,1]<=2)|(G[:,2]>=1022)|(G[:,3]>=1022)
for t in [0.3,0.5]:
    print(f"  score>={t}: both {((a>=t)&(b>=t)).sum()}, only last_sem {((a>=t)&(b<t)).sum()}, only new {((a<t)&(b>=t)).sum()}, neither {((a<t)&(b<t)).sum()}")
lost=(a>=0.3)&(b<0.3); kept=(a>=0.3)&(b>=0.3)
print(f"  lost grains ({lost.sum()}): new detector score on them: median {np.median(b[lost]):.3f}; share with score 0 (not boxed at all above 0.02) {np.mean(b[lost]==0):.2f}; share 0.1-0.3 {np.mean((b[lost]>=0.1)&(b[lost]<0.3)):.2f}")
print(f"  edge-cut share: lost {cut[lost].mean():.2f} vs kept {cut[kept].mean():.2f}")
print(f"  uncut box width median: lost {np.median(wid[lost&~cut]):.0f} vs kept {np.median(wid[kept&~cut]):.0f}; width quartiles lost {np.percentile(wid[lost&~cut],[25,50,75]).round(0)} kept {np.percentile(wid[kept&~cut],[25,50,75]).round(0)}")
for lo,hi_ in [(0,70),(70,100),(100,130),(130,170),(170,2000)]:
    s_=(~cut)&(wid>=lo)&(wid<hi_)
    print(f"   uncut width {lo}-{hi_}px: n {s_.sum():4d}  recall@0.3 last_sem {np.mean(a[s_]>=0.3):.3f}  new {np.mean(b[s_]>=0.3):.3f}")
s_=cut; print(f"   edge-cut: n {s_.sum():4d}  recall@0.3 last_sem {np.mean(a[s_]>=0.3):.3f}  new {np.mean(b[s_]>=0.3):.3f}")
print("  per slide (n grains, recall@0.3 last_sem / new, false alarms@0.3 last_sem / new):")
sl=np.array([re.sub(r"_tile_.*","",fn[k[0]]) for k in keys])
fa={m:collections.Counter(re.sub(r"_tile_.*","",fn[r[3]]) for r in res[m][1] if r[0]>=0.3 and not r[1]) for m in P}
for s_ in sorted(set(sl),key=lambda x:-np.sum(sl==x)):
    q=sl==s_; print(f"   {s_[:58]:58s} n {q.sum():4d}  {np.mean(a[q]>=0.3):.2f} / {np.mean(b[q]>=0.3):.2f}   FA {fa['last_semester'][s_]:3d} / {fa['new_detector'][s_]:3d}")
json.dump({"lost":[[fn[keys[i][0]]]+G[i].tolist()+[float(a[i]),float(b[i])] for i in np.where(lost)[0]],
           "far_fp_new":[[fn[r[3]],float(r[0])] for r in far]},open(E+"/diag_lost.json","w"))

"""Diagnostic: how do both detectors score on tiles from the TRAINING split (old vs new collections) and on old validation?"""
import json,gzip,os,re,random,collections,time
import numpy as np
from PIL import Image
H=os.path.expanduser("~/Smithsonian_F26"); C=H+"/processed/coco_detector_v2/combined"; E=H+"/model_A/detector_v2/eval_20261120"
CK={"last_semester":H+"/weights/rfdetr(2xl)_focus_stack.pth","new_detector":H+"/model_A/detector_v2/runs/dv2_2xl_focus_20261119/checkpoint_best_total.pth"}
def isnew(fn):
    m=re.search(r"_tile_(\d+)_(\d+)\.",fn); return int(m.group(1))%1024==0 and int(m.group(2))%1024==0
random.seed(0); SUB={}
tr=json.load(open(C+"/annotations/instances_train.json")); va=json.load(open(C+"/annotations/instances_val.json"))
def pack(d,ims,split):
    ids={i["id"] for i in ims}; by=collections.defaultdict(list)
    for a in d["annotations"]:
        if a["image_id"] in ids: x,y,w,h=a["bbox"]; by[a["image_id"]].append([x,y,x+w,y+h])
    return [(split,i["id"],i["file_name"],by.get(i["id"],[])) for i in ims]
old=[i for i in tr["images"] if not isnew(i["file_name"])]; new=[i for i in tr["images"] if isnew(i["file_name"])]
SUB["old_train"]=pack(tr,random.sample(old,1500),"train"); SUB["new_train"]=pack(tr,random.sample(new,3000),"train")
SUB["old_val"]=pack(va,[i for i in va["images"] if not isnew(i["file_name"])],"val")
from rfdetr_plus.models.detection import RFDETR2XLarge
P={}
for c,ck in CK.items():
    cache=f"{E}/diag2_pred_{c}.json.gz"
    if os.path.exists(cache): P[c]=json.load(gzip.open(cache,"rt")); continue
    m=RFDETR2XLarge(pretrain_weights=ck,num_classes=1,resolution=1000); P[c]={}; t0=time.time()
    for s,items in SUB.items():
        out=[]
        for k,(split,iid,fn,g) in enumerate(items):
            with Image.open(f"{C}/images/{split}/{fn}") as pil: ds=m.predict(pil.convert("RGB"),threshold=0.02)
            out.append([[float(v) for v in b]+[float(sc)] for b,sc in zip(ds.xyxy,ds.confidence)])
        P[c][s]=out; print(c,s,len(items),round(time.time()-t0),"s",flush=True)
    json.dump(P[c],gzip.open(cache,"wt")); del m
def iou(b,g):
    x1=np.maximum(b[:,None,0],g[None,:,0]);y1=np.maximum(b[:,None,1],g[None,:,1]);x2=np.minimum(b[:,None,2],g[None,:,2]);y2=np.minimum(b[:,None,3],g[None,:,3])
    inter=np.clip(x2-x1,0,None)*np.clip(y2-y1,0,None)
    return inter/(((b[:,2]-b[:,0])*(b[:,3]-b[:,1]))[:,None]+((g[:,2]-g[:,0])*(g[:,3]-g[:,1]))[None,:]-inter).clip(1e-9)
def score(items,preds,T=0.3):
    rows=[];gs=[];ng=0; per=collections.defaultdict(lambda:[0,0,0])  # slide -> dets>=.5, unlabeled dets>=.5, labels
    for (split,iid,fn,g),p in zip(items,preds):
        g=np.array(g,float).reshape(-1,4); p=np.array(sorted(p,key=lambda q:-q[4]),float).reshape(-1,5); ng+=len(g)
        used=np.zeros(len(g),bool); best=np.zeros(len(g)); M=iou(p[:,:4],g) if len(p) and len(g) else np.zeros((len(p),len(g)))
        sl=re.sub(r"_tile_.*","",fn); per[sl][2]+=len(g)
        for i in range(len(p)):
            tp=False
            if len(g):
                cand=np.where((M[i]>=T)&~used)[0]
                if len(cand): j=cand[M[i,cand].argmax()]; used[j]=True; best[j]=p[i,4]; tp=True
            rows.append((p[i,4],tp))
            if p[i,4]>=0.5: per[sl][0]+=1; per[sl][1]+=(not tp)
        gs+=best.tolist()
    A=np.array(rows,float); o=np.argsort(-A[:,0]); tp=np.cumsum(A[o,1]); fp=np.cumsum(1-A[o,1]); rec=tp/ng; prec=tp/(tp+fp)
    ap=0.0; mp=np.maximum.accumulate(prec[::-1])[::-1]
    for r in np.linspace(0,1,101):
        k=np.searchsorted(rec,r); ap+=(mp[k] if k<len(mp) else 0)/101
    gs=np.array(gs); hi=A[A[:,0]>=0.5]
    return dict(n_img=len(items),n_gt=ng,AP_iou30=round(ap,3),median_score_on_labelled=round(float(np.median(gs)),3),recall_at_05=round(float(np.mean(gs>=0.5)),3),recall_at_03=round(float(np.mean(gs>=0.3)),3),
                dets_at_05=len(hi),unlabelled_share_at_05=round(float(1-hi[:,1].mean()),3)),per
for s in SUB:
    for c in CK:
        r,per=score(SUB[s],P[c][s]); print("RESULT",s,c,json.dumps(r))
        if s=="new_train" and c=="last_semester":
            print("  new training slides, last semester's detector at score>=0.5: slide, labels, detections, share of detections with no label")
            for sl,(d,u,n) in sorted(per.items(),key=lambda kv:-kv[1][2])[:45]: print(f"   {sl[:50]:50s} labels {n:4d} dets {d:4d} unlabelled {u/max(d,1):.2f}")
            tot=np.array(list(per.values())); print("  total labels",tot[:,2].sum(),"dets",tot[:,0].sum(),"unlabelled",tot[:,1].sum())
print("DIAG2 DONE")

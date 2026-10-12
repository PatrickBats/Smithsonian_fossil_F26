"""Shared provenance and crop contract for the frozen Swin handoff."""
import csv, hashlib, json, math, tempfile, os
from pathlib import Path
from PIL import Image, ImageOps

def rows(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    # Concurrent array tasks must never share a temporary filename.
    fd, name=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    temp=Path(name)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            f.write(json.dumps(data,indent=2,allow_nan=False)+'\n')
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)

def crop_input(image,box,margin=.1):
    # Same pixels as detector input; fixed context, no focal-plane re-selection.
    x0,y0,x1,y1=box;pad=margin*max(x1-x0,y1-y0)
    bounds=(math.floor(x0-pad),math.floor(y0-pad),math.ceil(x1+pad),math.ceil(y1+pad))
    canvas=Image.new('RGB',(bounds[2]-bounds[0],bounds[3]-bounds[1]),'white')
    clip=(max(0,bounds[0]),max(0,bounds[1]),min(image.width,bounds[2]),min(image.height,bounds[3]))
    if clip[2]>clip[0] and clip[3]>clip[1]:
        canvas.paste(image.crop(clip),(clip[0]-bounds[0],clip[1]-bounds[1]))
    side=max(canvas.size)
    return ImageOps.pad(canvas,(side,side),color='white').resize((224,224),Image.Resampling.BICUBIC)

def validate_inputs(config):
    c=json.loads(Path(config).read_text())
    r=rows(c['assignments']);cats=rows(c['fine_to_broad'])
    assert len(r)==2283 and len({x['record_id'] for x in r})==2283
    assert sha(c['assignments'])==c['assignments_sha256']
    assert sha(c['fine_to_broad'])==c['fine_to_broad_sha256']
    assert len(cats)==32 and len({x['broad_category'] for x in cats})==28
    mapping={x['fine_category']:x['broad_category'] for x in cats}
    group={};slide={}
    for x in r:
        assert x['sponsor_classify']=='YES' and x['sponsor_category'] in mapping
        assert x['split'] in ('train','val','test')
        group.setdefault(x['accession_group_id'],set()).add(x['split'])
        slide.setdefault(x['image_nots_path'],set()).add(x['split'])
    assert all(len(v)==1 for v in group.values()) and all(len(v)==1 for v in slide.values())
    assert sha(c['swin_checkpoint'])==c['swin_checkpoint_sha256']
    return c,r,mapping

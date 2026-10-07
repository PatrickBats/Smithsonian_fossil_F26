"""Select a deterministic diagnostic sample, before observing predictions."""
import collections,csv,hashlib,json,pathlib,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[2]
def select():
 data=ROOT/'data/current'
 rows=list(csv.DictReader((data/'classification_annotations.csv').open()))
 geom={r['record_id']:ET.fromstring(r['geometry_xml']) for r in json.loads((data/'annotation_geometry.json').read_text())}
 rois=collections.defaultdict(list)
 allrows=list(csv.DictReader((data/'annotation_records.csv').open()))
 for r in allrows:
  if r['specialtype']=='rectangle':
   pts=geom[r['record_id']].findall('.//point');xs=[int(p.findtext('x')) for p in pts];ys=[int(p.findtext('y')) for p in pts]
   rois[r['slide']].append((min(xs),min(ys),max(xs),max(ys)))
 for r in rows:
  g=geom[r['record_id']];x=int(g.findtext('x'));y=int(g.findtext('y'));rad=int(g.findtext('radius'))
  r['center_nm']=[x,y];r['radius_nm']=rad
  r['center_inside_roi']=any(a<=x<=c and b<=y<=d for a,b,c,d in rois[r['slide']])
  r['box_inside_roi']=any(a<=x-rad and b<=y-rad and c>=x+rad and d>=y+rad for a,b,c,d in rois[r['slide']])
  r['has_rectangle']=bool(rois[r['slide']])
 by=collections.defaultdict(list)
 for r in rows:by[r['mapped_category']].append(r)
 selected=[]
 for category,group in sorted(by.items()):
  group.sort(key=lambda r:hashlib.sha256(('smithsonian-detection-20260924:'+r['record_id']).encode()).hexdigest())
  # Prefer one outside-ROI specimen and one inside-ROI specimen, on distinct slides.
  a=next((r for r in group if not r['center_inside_roi']),group[0])
  rest=[r for r in group if r['slide']!=a['slide']]
  b=next((r for r in rest if r['center_inside_roi']!=a['center_inside_roi']),rest[0])
  selected.extend([a,b])
 return selected
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('output',type=pathlib.Path);a=p.parse_args();rows=select();a.output.write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps({'targets':len(rows),'categories':len({r['mapped_category'] for r in rows}),'slides':len({r['slide'] for r in rows}),'outside_rectangle_centers':sum(not r['center_inside_roi'] for r in rows)},indent=2))

"""Independently recount source NDPA labels against both original sponsor tables."""
from pathlib import Path
import csv, collections, json, hashlib
import xml.etree.ElementTree as ET
from openpyxl import load_workbook
P=Path(__file__).resolve().parent;root=P.parents[1]
csvpath=root/'docs/sources/data/title_counts.csv'
xlsx=root/'docs/sources/data/category_totals.xlsx'
titles=list(csv.DictReader(csvpath.open()))
lookup={r['Annotation title']:r for r in titles}
assert len(lookup)==len(titles)==185
w=load_workbook(xlsx,data_only=True)
catrows=list(w.active.values)
cats={r[0]:{'count':int(r[1]),'priority':r[2]} for r in catrows[1:] if r[0]}
assert len(cats)==65
counts=collections.Counter();slides=collections.defaultdict(set);trimmed=[];untitled=0
files=sorted((root/'docs/sources/data/Fall_2026').glob('*.ndpa'))
assert len(files)==83
for f in files:
 for v in ET.parse(f).getroot().iter('ndpviewstate'):
  if v.find('annotation') is None:continue
  original=v.findtext('title') or '';t=original.strip()
  if not t:untitled+=1;continue
  assert t in lookup,(f.name,t)
  if original!=t:trimmed.append({'file':f.name,'original':original,'normalized':t})
  counts[t]+=1;slides[lookup[t]['Category']].add(f.name)
assert set(counts)==set(lookup)
assert all(counts[t]==int(r['n']) for t,r in lookup.items())
observed=collections.Counter();csvtotals=collections.Counter()
for t,r in lookup.items():
 observed[r['Category']]+=counts[t];csvtotals[r['Category']]+=int(r['n'])
assert set(observed)==set(cats)
assert all(observed[c]==csvtotals[c]==r['count'] for c,r in cats.items())
summary=list(csv.DictReader((root/'data/current/category_summary.csv').open()))
assert len(summary)==65
for r in summary:
 c=r['category'];assert int(r['annotation_records'])==cats[c]['count']
 assert r['priority']==cats[c]['priority']
 assert int(r['slides'])==len(slides[c])
report={'result':'PASS','source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [csvpath,xlsx]},'ndpa_files_recounted':len(files),'matched_title_rows':len(counts),'matched_categories':len(cats),'named_annotations':sum(counts.values()),'untitled_marks_excluded':untitled,'whitespace_adjustments':trimmed,'category_groups':{k:{'categories':sum(r['priority']==k for r in cats.values()),'annotations':sum(r['count'] for r in cats.values() if r['priority']==k)} for k in ['YES','MAYBE','NO']},'category_summary_count_priority_slide_checks':'PASS','normalization':'Trim leading/trailing whitespace only; no biological aliases.'}
(P/'sponsor_table_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['source_sha256','whitespace_adjustments']},indent=2))

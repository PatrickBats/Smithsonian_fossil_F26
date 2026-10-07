"""Audit a supplied Fall_2026.zip without extracting its large NDPI image.
Usage: python scripts/audit_fall2026_archive.py ARCHIVE --output OUTPUT_DIRECTORY
Reads the existing rice-nots SSH image inventory; writes only local output files.
"""
import argparse,collections,csv,hashlib,json,pathlib,subprocess,zipfile
import xml.etree.ElementTree as ET

def write_csv(path,rows,fields):
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)

def audit(archive,out,repo):
 out.mkdir(parents=True,exist_ok=True);sources=out/'annotations';sources.mkdir(exist_ok=True)
 table=list(csv.DictReader((repo/'docs/sources/data/title_counts.csv').open()))
 mapping={r['Annotation title']:r['Category'] for r in table}
 expected={r['Annotation title']:int(r['n']) for r in table}
 assert len(table)==len(mapping)==185
 priorities={}
 for line in (repo/'docs/CATEGORIES.md').read_text().splitlines():
  a=[x.strip() for x in line.split('|')]
  if len(a)==5 and a[3] in ['YES','NO','MAYBE']:priorities[a[1]]=a[3]
 remote="""from pathlib import Path
import json
root=Path('/rhf/allocations/dsci435/smithsonian_full_sp26/raw')
print(json.dumps([{'path':str(p),'size_bytes':p.stat().st_size} for p in root.rglob('*.ndpi')]))
"""
 images=json.loads(subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','rice-nots','python3 -'],input=remote,text=True,capture_output=True,check=True).stdout)
 (out/'nots_image_inventory.json').write_text(json.dumps(images,indent=2)+'\n')
 lookup=collections.defaultdict(list)
 for r in images:lookup[pathlib.Path(r['path']).name].append(r)
 records=[];inventory=[];counts=collections.Counter();bycat=collections.defaultdict(collections.Counter);bylabel=collections.Counter();source_manifest=[];geometries=[]
 with zipfile.ZipFile(archive) as z:
  members=[x for x in z.infolist() if not x.is_dir()]
  for x in members:
   name=pathlib.PurePosixPath(x.filename)
   if name.is_absolute() or '..' in name.parts or len(name.parts)!=1:raise ValueError('Unexpected archive path '+x.filename)
   source_manifest.append(dict(member=x.filename,size_bytes=x.file_size,crc32=f'{x.CRC:08x}'))
   if not x.filename.endswith('.ndpa'):continue
   b=z.read(x);(sources/x.filename).write_bytes(b);digest=hashlib.sha256(b).hexdigest();source_manifest[-1]['sha256']=digest
   root=ET.fromstring(b);image_name=x.filename[:-5];matches=lookup.get(image_name,[])
   image_path=matches[0]['path'] if len(matches)==1 else ''
   slide=image_name.removesuffix('.ndpi');tally=collections.Counter()
   for i,v in enumerate(root.iter('ndpviewstate')):
    a=v.find('annotation')
    if a is None:continue
    title=v.findtext('title') or '';clean=title.strip();category=mapping.get(clean,'');status=priorities.get(category,'UNMAPPED') if clean else 'UNTITLED';method='exact' if title in mapping else ('trimmed_whitespace' if category else 'unmatched')
    rid=f'{slide}::record_{i}'
    row=dict(record_id=rid,slide=slide,image_file=image_path,annotation_file=x.filename,annotation_sha256=digest,annotation_id=v.get('id',''),record_index=i,original_title=title,matched_title=clean,mapped_category=category,match_method=method,priority=status,shape=a.get('type',''),specialtype=a.findtext('specialtype') or '',details=v.findtext('details') or '')
    records.append(row);tally[status]+=1;counts[clean]+=1;bylabel[(slide,clean,category,status)]+=1
    if category:bycat[category][slide]+=1
    geometries.append(dict(record_id=rid,coordformat=v.findtext('coordformat') or '',geometry_xml=ET.tostring(a,encoding='unicode')))
   inventory.append(dict(slide=slide,annotation_file=x.filename,annotation_sha256=digest,image_file=image_path,image_match_count=len(matches),records=sum(tally.values()),yes=tally['YES'],maybe=tally['MAYBE'],no=tally['NO'],unmatched=tally['UNMAPPED'],untitled=tally['UNTITLED']))
  image_members=[x for x in members if x.filename.endswith('.ndpi')]
  print('Parsed',len(inventory),'NDPA files;',len(records),'annotation records.',flush=True)
  print('Verifying archive and bundled-image checksums; image will not be extracted.',flush=True)
  for x in image_members:
   h=hashlib.sha256()
   with z.open(x) as f:
    while b:=f.read(16*1024*1024):h.update(b)
   next(r for r in source_manifest if r['member']==x.filename)['sha256']=h.hexdigest()
 digest=hashlib.sha256()
 with archive.open('rb') as f:
  while b:=f.read(16*1024*1024):digest.update(b)
 yes=[r for r in records if r['priority']=='YES']
 write_csv(out/'annotation_records.csv',records,list(records[0]));write_csv(out/'classification_annotations.csv',yes,list(records[0]));write_csv(out/'slides.csv',inventory,list(inventory[0]))
 titles=[dict(annotation_title=t,observed=counts[t],expected=n,difference=counts[t]-n) for t,n in expected.items()]
 write_csv(out/'title_reconciliation.csv',titles,list(titles[0]))
 cats=[]
 for cat in sorted(priorities):
  c=bycat[cat];exp=sum(int(r['n']) for r in table if r['Category']==cat)
  cats.append(dict(category=cat,priority=priorities[cat],annotation_records=sum(c.values()),slides=len(c),largest_slide_count=max(c.values(),default=0),spreadsheet_count=exp,difference=sum(c.values())-exp))
 write_csv(out/'category_summary.csv',cats,list(cats[0]))
 matrix=[dict(category=c['category'],priority=c['priority'],**{s:bycat[c['category']][s] for s in sorted(r['slide'] for r in inventory)}) for c in cats]
 write_csv(out/'category_by_slide.csv',matrix,list(matrix[0]))
 ls=[dict(slide=k[0],original_title=k[1],mapped_category=k[2],priority=k[3],count=n) for k,n in sorted(bylabel.items())]
 write_csv(out/'labels_by_slide.csv',ls,list(ls[0]))
 write_csv(out/'formatting_matches.csv',[r for r in records if r['match_method']=='trimmed_whitespace'],list(records[0]))
 (out/'annotation_geometry.json').write_text(json.dumps(geometries,indent=2)+'\n')
 results=dict(date='2026-09-21',archive_filename=archive.name,archive_size_bytes=archive.stat().st_size,archive_sha256=digest.hexdigest(),members=source_manifest,source_category_csv_sha256=hashlib.sha256((repo/'docs/sources/data/title_counts.csv').read_bytes()).hexdigest(),annotation_files=len(inventory),records=len(records),priorities=dict(collections.Counter(r['priority'] for r in records)),geometry_types=dict(collections.Counter(r['shape'] for r in records)),all_title_counts_match=all(r['difference']==0 for r in titles),all_category_counts_match=all(r['difference']==0 for r in cats),unresolved_image_pairs=[r['annotation_file'] for r in inventory if r['image_match_count']!=1],bundled_image_existing_matches={x.filename:lookup.get(x.filename,[]) for x in image_members},notes=['Archive CRC checked by fully reading every member; archive and member SHA-256 hashes recorded.','NOTS pairing is by exact filename; existing image byte identity is NOT checked.','No provisional aliases applied. Only leading/trailing whitespace removed for lookup.','YES selection follows supplied original categories; broad-first hierarchy remains to be defined.'])
 (out/'audit_manifest.json').write_text(json.dumps(results,indent=2)+'\n')
 assert results['all_title_counts_match'] and results['all_category_counts_match']
 assert len(yes)==2290 and not results['unresolved_image_pairs']
 print(json.dumps({k:v for k,v in results.items() if k not in ['members']},indent=2),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('archive',type=pathlib.Path);p.add_argument('--output',required=True,type=pathlib.Path);a=p.parse_args();audit(a.archive,a.output,pathlib.Path(__file__).resolve().parents[1])

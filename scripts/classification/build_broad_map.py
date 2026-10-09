"""Build a draft 32-to-28 operational map without changing original labels/splits."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

SPLIT_SHA='da2062a127cf6e14945e50fff097e0db102d7f8203250b47daed6b6bb166478d'
MERGES={
 'Momipites':('Momipites flexus','Momipites sp','Momipites ventifluminis','Momipites wyomingensis'),
 'Caryapollenites':('Caryapollenites sp.','Caryapollenites veripites'),
}


def read(path):
    with Path(path).open(newline='') as f:return list(csv.DictReader(f))


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def build(a):
    repo=Path(__file__).resolve().parents[2];source=repo/'data/current/baseline_category_map.csv'
    sponsor=repo/'data/current/category_summary.csv';classes=read(source);records=read(a.assignments)
    if sha(a.assignments)!=SPLIT_SHA:raise ValueError('Adopted source split changed')
    fine=[r['sponsor_category'] for r in classes]
    assert len(fine)==len(set(fine))==32
    assert [int(r['classifier_class_id']) for r in classes]==list(range(32))
    mapping={name:name for name in fine}
    for parent,children in MERGES.items():
        for child in children:
            if child not in mapping:raise ValueError('Missing exact source label '+child)
            mapping[child]=parent
    names=sorted(set(mapping.values()));assert len(names)==28
    ids={name:i for i,name in enumerate(names)}
    sponsor_counts={r['category']:int(r['annotation_records']) for r in read(sponsor) if r['priority']=='YES'}
    assert set(sponsor_counts)==set(fine) and sum(sponsor_counts.values())==2290
    assert len(records)==len({r['record_id'] for r in records})==2283
    assert set(r['sponsor_category'] for r in records)==set(fine)
    counts=collections.Counter(r['sponsor_category'] for r in records)
    mapped=[]
    for row in classes:
        name=row['sponsor_category'];parent=mapping[name];merged=parent in MERGES
        mapped.append({'fine_class_id':row['classifier_class_id'],'fine_category':name,
          'broad_class_id':ids[parent],'broad_category':parent,'mapping_action':'merge_same_name_prefix' if merged else 'retain',
          'review_status':'draft_sponsor_review' if merged else 'unchanged_sponsor_category',
          'basis':'Explicit shared Momipites name; user reports wyomingensis belongs within Momipites' if parent=='Momipites' else 'Explicit shared Caryapollenites name' if parent=='Caryapollenites' else 'No broader biological relationship inferred',
          'sponsor_annotation_count':sponsor_counts[name],'eligible_specimens':counts[name]})
    groups=[]
    for name in names:
        children=[v for v in fine if mapping[v]==name]
        groups.append({'broad_class_id':ids[name],'broad_category':name,'fine_categories':' | '.join(children),
          'fine_category_count':len(children),'sponsor_annotation_count':sum(sponsor_counts[v] for v in children),
          'eligible_specimens':sum(counts[v] for v in children),'status':'draft_merged_group' if len(children)>1 else 'retained_category'})
    diagnostic=json.loads(Path(a.diagnostic_split).read_text())['assignments']
    assert set(diagnostic)=={r['record_id'] for r in records}
    assert all((r['split']=='test')==(diagnostic[r['record_id']]=='test') for r in records)
    variants={'separate_slides':{r['record_id']:r['split'] for r in records},'shared_slides':diagnostic}
    coverage=[]
    for split_name,assignments in variants.items():
        assert dict(collections.Counter(assignments.values()))=={'train':1605,'val':347,'test':331}
        for name in names:
            members=[r for r in records if mapping[r['sponsor_category']]==name]
            row={'split_protocol':split_name,'broad_class_id':ids[name],'broad_category':name,'total':len(members)}
            for split in ('train','val','test'):
                selected=[r for r in members if assignments[r['record_id']]==split]
                row[split]=len(selected);row[split+'_accession_groups']=len({r['accession_group_id'] for r in selected})
                row[split+'_slides']=len({r['image_filename'] for r in selected})
            assert row['total']==sum(row[v] for v in ('train','val','test'))
            coverage.append(row)
        for split,total in [('train',1605),('val',347),('test',331)]:assert sum(r[split] for r in coverage if r['split_protocol']==split_name)==total
    out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    write(out/'fine_to_broad.csv',mapped);write(out/'groups.csv',groups);write(out/'split_coverage.csv',coverage)
    manifest={'version':'broad_v1_draft','status':'name-based operational draft for sponsor review; not a uniform taxonomic hierarchy',
      'fine_categories':32,'broad_categories':28,'eligible_specimens':2283,'sponsor_annotation_records':2290,
      'excluded_records':7,'original_labels_preserved':True,'original_split_membership_preserved':True,
      'test_inference':False,'retraining_performed':False,'historical_metrics_rewritten':False,
      'input_sha256':{'fine_map':sha(source),'sponsor_summary':sha(sponsor),'grouped_assignments':sha(a.assignments),'shared_assignments':sha(a.diagnostic_split)},
      'output_sha256':{p.name:sha(p) for p in sorted(out.glob('*.csv'))},'builder_sha256':sha(__file__)}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'groups':len(groups),'records':len(records),'merges':[g for g in groups if g['fine_category_count']>1]},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for field in ('assignments','diagnostic_split','output'):p.add_argument('--'+field.replace('_','-'),required=True)
    build(p.parse_args())

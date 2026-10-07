"""Diagnostic split: random specimens within categories; original test reserved."""
import collections
import hashlib
import json
from pathlib import Path


def apply_split(rows, path):
    path=Path(path);protocol=json.loads(path.read_text())
    assignments=protocol['assignments']
    if len(assignments)!=len(rows) or set(assignments)!={r['record_id'] for r in rows}:
        raise ValueError('Diagnostic IDs differ from verified dataset')
    updated=[]
    for row in rows:
        split=assignments[row['record_id']]
        if split not in ('train','val','test') or (row['split']=='test')!=(split=='test'):
            raise ValueError('Original test membership changed')
        updated.append({**row,'split':split})
    counts=dict(collections.Counter(r['split'] for r in updated))
    if counts!={'train':1605,'val':347,'test':331}:raise ValueError('Diagnostic split sizes differ')
    for split in ('train','val'):
        if len({r['sponsor_category'] for r in updated if r['split']==split})!=32:
            raise ValueError('Every category must appear in train and validation')
    hashes=collections.defaultdict(set)
    for row in updated:hashes[row['png_sha256']].add(row['split'])
    if any(len(s)>1 for s in hashes.values()):raise ValueError('Identical images cross partitions')
    slides={split:{r['image_nots_path'] for r in updated if r['split']==split} for split in ('train','val','test')}
    if slides['test']&(slides['train']|slides['val']):raise ValueError('Test slide isolation changed')
    return updated,{'protocol':'specimen_random_stratified_diagnostic','split_counts':counts,
      'split_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
      'train_val_shared_slides':len(slides['train']&slides['val']),
      'validation_supported_categories':32,'original_test_reserved':True,'test_inference':False}

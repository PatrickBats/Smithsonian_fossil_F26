"""Compare complete saved validation probabilities without test inference."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_fscore_support

def read_run(path):
    with (path / 'best_validation_predictions.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    config = json.loads((path / 'config.json').read_text())
    audit = json.loads((path / 'data_audit.json').read_text())
    labels = list(json.loads((path / 'broad_category_map.json').read_text()).values())
    assert len(labels) == 28 and len(rows) == 347
    rows.sort(key=lambda row: row['record_id'])
    y = np.array([labels.index(row['category']) for row in rows])
    p = np.array([[float(row[f'p_{i}']) for i in range(28)] for row in rows])
    assert np.isfinite(p).all() and np.allclose(p.sum(1), 1, atol=1e-5)
    pred = p.argmax(1)
    binary = np.eye(28)[y]
    supported = np.flatnonzero(binary.sum(0))
    precision, recall, f1, _ = precision_recall_fscore_support(y, pred, labels=supported, average='macro', zero_division=0)
    ap = [average_precision_score(binary[:, i], p[:, i]) for i in supported]
    result = {'objects': len(rows), 'correct': int((pred == y).sum()),
              'accuracy': float((pred == y).mean()), 'macro_precision': float(precision),
              'macro_recall': float(recall), 'macro_f1': float(f1),
              'macro_AP': float(np.mean(ap)), 'micro_AP': float(average_precision_score(binary.ravel(), p.ravel())),
              'supported_classes': len(supported), 'split_sha256': audit['split_sha256'],
              'crop_manifest_sha256': audit['crop_manifest_sha256'],
              'seed': config['seed'], 'unfrozen_blocks': config['unfrozen_blocks']}
    return rows, labels, result

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--policy',required=True);args=parser.parse_args()
    base=Path('/rhf/allocations/dsci435/Smithsonian_F26/model_B/runs')
    paths={'mild':base/'dino_mild_augmentation_20261108/mild','strong':base/'dino_strong_augmentation_20261116/strong',args.policy:args.run/args.policy}
    values={k:read_run(p) for k,p in paths.items()};reference=values['strong']
    for rows,labels,result in values.values():
        assert [(r['record_id'],r['category']) for r in rows]==[(r['record_id'],r['category']) for r in reference[0]]
        assert labels==reference[1]
        assert result['split_sha256']==reference[2]['split_sha256'] and result['crop_manifest_sha256']==reference[2]['crop_manifest_sha256']
    out={'scope':'347 expert-located validation crops','test_used':False,'metrics':{k:v[2] for k,v in values.items()}}
    (args.run/args.policy/'comparison_validation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

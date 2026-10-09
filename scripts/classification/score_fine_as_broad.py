"""Broad-label controls from saved validation predictions; no model/test inference."""
import csv
import json
from pathlib import Path
import numpy as np
from train_swin import metrics,digest,read_csv,write_json
from broad_labels import apply_broad


def main():
    repo=Path(__file__).resolve().parents[2];base=repo.parent
    out=base/'broad_label_controls_2026-10-08';out.mkdir(exist_ok=False)
    fine=[r['sponsor_category'] for r in read_csv(repo/'data/current/baseline_category_map.csv')]
    mapping_path=repo/'data/current/broad_v1/fine_to_broad.csv'
    mapped,broad,audit=apply_broad([{'sponsor_category':c} for c in fine],fine,mapping_path)
    destinations=np.array([broad.index(r['sponsor_category']) for r in mapped])
    assignment=read_csv(base/'tenengrad_full_2026-10-07/record_assignments.csv')
    shared=json.loads((base/'swin_specimen_split_2026-10-07/specimen_split.json').read_text())['assignments']
    locations={('swin','separate_slides'):'tenengrad_full_2026-10-07/training_attempt_01/ordinary_baseline',
      ('swin','shared_slides'):'swin_specimen_split_2026-10-07/training_attempt_01/ordinary_baseline',
      ('dino','separate_slides'):'dino_finetune_2026-10-07/separate_slides/backbone_finetune',
      ('dino','shared_slides'):'dino_finetune_2026-10-07/shared_slides/backbone_finetune'}
    results=[]
    for (model,split),folder in locations.items():
        path=base/folder/'best_validation_predictions.csv';rows=read_csv(path)
        expected={r['record_id']:r['sponsor_category'] for r in assignment if (r['split'] if split=='separate_slides' else shared[r['record_id']])=='val'}
        assert len(rows)==len(expected)==347 and {r['record_id'] for r in rows}==set(expected)
        assert all(expected[r['record_id']]==r['category'] for r in rows)
        probabilities=np.array([[float(r[f'p_{i}']) for i in range(32)] for r in rows])
        assert np.isfinite(probabilities).all() and (probabilities>=0).all() and np.allclose(probabilities.sum(1),1)
        summed=np.zeros((len(rows),len(broad)))
        for i,d in enumerate(destinations):summed[:,d]+=probabilities[:,i]
        truth=destinations[[fine.index(r['category']) for r in rows]]
        mapped_argmax=destinations[probabilities.argmax(1)]
        result={'model':model,'split':split,'source_prediction_sha256':digest(path),
          'mapped_fine_argmax':metrics(truth,mapped_argmax,broad),'summed_broad_probabilities':metrics(truth,summed.argmax(1),broad)}
        results.append(result)
        print(model,split,'mapped accuracy',result['mapped_fine_argmax']['accuracy'],'summed accuracy',result['summed_broad_probabilities']['accuracy'])
    write_json(out/'results.json',{'mapping':audit,'test_inference':False,'checkpoint_selection':'original fine-label validation macro-F1; no new checkpoint search','results':results})
    (out/'score_fine_as_broad_snapshot.py').write_bytes(Path(__file__).read_bytes())


if __name__=='__main__':main()

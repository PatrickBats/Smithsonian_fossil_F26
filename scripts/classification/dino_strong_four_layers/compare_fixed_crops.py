"""Paired DINO inference on exact 258 historical RF-DETR crops; no detector rerun."""
import argparse
import collections
import gc
import hashlib
import json
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
from pathlib import Path
import sys
import numpy as np
import torch
from PIL import Image
from torchvision.transforms import functional as TF
from sklearn.metrics import average_precision_score, precision_recall_fscore_support
from method_b.classification.load_classifier import load_classifier

BASE = Path('/rhf/allocations/dsci435/Smithsonian_F26')
sys.path.insert(0, '/home/yt70/Smithsonian/scripts/rfdetr_rgb_dino_v1')
import compare_rgb_dino as frozen

def metrics(records, labels, key):
    y = np.array([labels.index(r['true_category']) for r in records])
    p = np.array([r[key] for r in records])
    assert len(y) == 258 and p.shape == (258, 28) and np.isfinite(p).all()
    assert np.allclose(p.sum(1), 1, atol=1e-5)
    pred = p.argmax(1); binary = np.eye(28)[y]; present = np.flatnonzero(binary.sum(0))
    pr, re, f1, _ = precision_recall_fscore_support(y, pred, labels=present, average='macro', zero_division=0)
    return {'correct': int((pred == y).sum()), 'accuracy': float((pred == y).mean()),
            'macro_precision': float(pr), 'macro_recall': float(re), 'macro_f1': float(f1),
            'macro_AP': float(np.mean([average_precision_score(binary[:, i], p[:, i]) for i in present])),
            'micro_AP': float(average_precision_score(binary.ravel(), p.ravel())),
            'end_to_end_success_274': float((pred == y).sum() / 274)}

def main(run, policy):
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    old = json.loads((BASE / 'model_B/runs/rfdetr_rgb_dino_classification_ap_v1/scores_28class.json').read_text())
    records = old['records']; labels = old['labels']
    assert len(records) == len({r['record_id'] for r in records}) == 258
    models = {}
    for name in (policy,):
        model, classes = load_classifier('dino', run / name / 'best.pt', os.environ['DINO_SOURCE'], 'cuda')
        assert classes == labels
        models[name] = model
    prior = json.loads((BASE / 'model_B/runs/dino_strong_augmentation_20261116/fixed_detector_crops/scores_28class.json').read_text())
    assert prior['labels'] == labels
    prior_by_id = {r['record_id']: r for r in prior['records']}
    assert len(prior_by_id) == 258
    groups = collections.defaultdict(list)
    for row in records: groups[row['source']].append(row)
    out = run / policy / 'fixed_detector_crops'; out.mkdir(exist_ok=False)
    results = []
    for source, group in sorted(groups.items()):
        folder = frozen.FROZEN / 'slides' / Path(source).stem
        grid = [frozen.TileSpec(**tile) for tile in frozen.read(folder / 'tile_grid.json')]
        hashes = {(tile['x'], tile['y']): tile['rgb_tile_sha256'] for tile in frozen.read(folder / 'paired_tile_inputs.json')}
        needed = collections.defaultdict(list)
        for row in group: needed[tuple(row['tile_origin'])].append(row)
        seen = set(); crops = {}; ndpi = frozen.NDPIData(source)
        try:
            for bx, by, bw, bh, tiles in frozen.NDPIAnnotator._group_into_bands(None, grid, 8192):
                selected = [t for t in tiles if (t.x, t.y) in needed and (t.x, t.y) not in seen]
                if not selected: continue
                band = ndpi.get_tile(x=bx, y=by, w=bw, h=bh, magnification=40)
                for tile_spec in selected:
                    origin = (tile_spec.x, tile_spec.y)
                    if origin in seen: continue
                    tile = frozen.best_focal_plane(band[:, tile_spec.x-bx:tile_spec.x-bx+tile_spec.w, :, :], tenengrad_ksize=3)
                    assert hashlib.sha256(np.ascontiguousarray(tile).tobytes()).hexdigest() == hashes[origin]
                    image = Image.fromarray(tile.astype(np.uint8)).convert('RGB')
                    for row in needed[origin]:
                        crop = frozen.prior.crop_input(image, row['box_tile'])
                        assert hashlib.sha256(crop.tobytes()).hexdigest() == row['crop_rgb224_sha256']
                        crops[row['record_id']] = TF.normalize(TF.to_tensor(crop), [.485,.456,.406], [.229,.224,.225])
                    seen.add(origin)
                del band
        finally: ndpi.close()
        assert len(crops) == len(group)
        for start in range(0, len(group), 32):
            rows = group[start:start+32]
            x = torch.stack([crops[row['record_id']] for row in rows]).cuda()
            with torch.inference_mode():
                probabilities = {name: model(x).softmax(1).cpu().tolist() for name, model in models.items()}
            for i, row in enumerate(rows):
                result = {k: row[k] for k in ('record_id', 'true_category', 'crop_rgb224_sha256', 'frozen_prediction_index')}
                result['historical_probabilities'] = row['dino_probabilities']
                previous = prior_by_id[row['record_id']]
                assert previous['crop_rgb224_sha256'] == row['crop_rgb224_sha256']
                assert previous['true_category'] == row['true_category']
                for name in ('baseline', 'mild', 'strong'): result[name + '_probabilities'] = previous[name + '_probabilities']
                for name in models: result[name + '_probabilities'] = probabilities[name][i]
                results.append(result)
        del crops; gc.collect()
        print(json.dumps({'completed_objects': len(results), 'total': 258}), flush=True)
    summary = {'scope': '258 fixed matched validation crops; 274 known targets', 'test_used': False,
               'detector_rerun': False, 'all_crop_hashes_verified': True,
               'metrics': {name: metrics(results, labels, name + '_probabilities') for name in ('historical', 'baseline', 'mild', 'strong', policy)},
               'caveat': 'Original detector saw 13/14 evaluation slides. Validation diagnostic, not independent test.'}
    (out / 'scores_28class.json').write_text(json.dumps({'labels': labels, 'records': results}))
    (out / 'comparison.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--run', type=Path, required=True)
    parser.add_argument("--policy", choices=["geometry","four_layers"], required=True)
    args=parser.parse_args(); main(args.run,args.policy)

"""Frozen RGB RF-DETR crops: paired existing Swin/DINO inference, no training."""
import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['NO_ALBUMENTATIONS_UPDATE'] = '1'
os.environ['PALYNET_NUM_WORKERS'] = '0'
import ast
import collections
import gc
import hashlib
import json
from pathlib import Path
import sys
import traceback

import numpy as np
import torch
from torch import nn
from PIL import Image
from torchvision.models import swin_t
from torchvision.transforms import functional as TF

HERE = Path(__file__).resolve().parent
ORIGINAL = Path(os.environ.get('SPRING_ADAPTER_ROOT', str(HERE)))
sys.path.insert(0, str(ORIGINAL))
import compare_bestplane as prior
from src.annotator.types import TileSpec
from src.annotator.pipeline import NDPIAnnotator
from src.annotator.compression import best_focal_plane
from src.data.ndpi_reader import NDPIData
from torchvision.ops import box_iou

BASE = prior.BASE
FROZEN = BASE / 'model_B/runs/abbas_rgb_input_check_v1'
OUT = Path(os.environ.get('COMPARISON_OUTPUT', str(BASE / 'model_B/runs/rfdetr_rgb_dino_v1')))
DINO_RUN = BASE / 'runs/broad_dino_2026-10-08/separate_slides/backbone_finetune'
DINO = DINO_RUN / 'best.pt'
COMMIT = '7764ea0f912e53c92e82eb78a2a1631e92725fc8'
DINO_SOURCE = Path(os.environ.get('DINO_SOURCE', str(HERE / ('dinov2-' + COMMIT))))


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    prior.save(path, value)
    path.chmod(0o644)


def load_models(device):
    swin_ckpt = torch.load(prior.SWIN, map_location='cpu', weights_only=False)
    dino_ckpt = torch.load(DINO, map_location='cpu', weights_only=False)
    sl = swin_ckpt['categories']; dl = dino_ckpt['categories']
    assert len(sl) == len(dl) == len(set(dl)) == 28
    assert set(sl) == set(dl), 'Classifier category sets differ'
    swin = swin_t(weights=None)
    swin.head = nn.Linear(swin.head.in_features, len(sl))
    swin.load_state_dict(swin_ckpt['model'], strict=True)
    # Reuse the teammate's class (including its exact forward method), changing
    # only construction: all trained weights come from best.pt, no downloads.
    snapshot = DINO_RUN / 'train_dino_finetune_snapshot.py'
    tree = ast.parse(snapshot.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'DinoClassifier')
    namespace = {'nn': nn, 'torch': torch}
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(snapshot), 'exec'), namespace)
    original_class = namespace['DinoClassifier']

    class InferenceDino(original_class):
        def __init__(self):
            nn.Module.__init__(self)
            self.backbone = torch.hub.load(str(DINO_SOURCE), 'dinov2_vitb14', source='local', pretrained=False)
            assert len(self.backbone.blocks) == 12
            self.head = nn.Linear(1536, len(dl))

    dino = InferenceDino()
    dino.load_state_dict(dino_ckpt['model'], strict=True)
    for model in (swin, dino):
        model.requires_grad_(False).to(device).eval()
    del swin_ckpt, dino_ckpt
    gc.collect()
    return swin, sl, dino, dl


def match(candidates, truth):
    a = torch.tensor([p['box_slide'] for p in candidates], dtype=torch.float32).reshape(-1, 4)
    b = torch.tensor([r['box_slide'] for r in truth], dtype=torch.float32).reshape(-1, 4)
    overlaps = box_iou(a, b)
    pairs = [(float(overlaps[i, j]), i, j) for i, j in torch.nonzero(overlaps >= .5).tolist()]
    usedp = set(); usedt = set(); assigned = {}
    for overlap, i, j in sorted(pairs, reverse=True):
        if i not in usedp and j not in usedt:
            usedp.add(i); usedt.add(j); assigned[j] = (i, overlap)
    results = []
    for j, r in enumerate(truth):
        p = candidates[assigned[j][0]] if j in assigned else None
        results.append({'record_id': r['record_id'], 'source': r['image'],
                        'true_category': r['broad_category'], 'detected': p is not None,
                        'predicted_category': p['category'] if p else None,
                        'classification_correct': p is not None and p['category'] == r['broad_category'],
                        'iou': assigned[j][1] if p else None})
    return results


def summarize(rows):
    found = sum(r['detected'] for r in rows)
    correct = sum(r['classification_correct'] for r in rows)
    return {'known_validation_objects': len(rows), 'detected': found, 'correct': correct,
            'classification_accuracy_on_detected': correct / found,
            'end_to_end_success': correct / len(rows)}


def main():
    preflight = '--preflight' in sys.argv
    device = 'cpu' if preflight else 'cuda'
    if not preflight:
        assert torch.cuda.is_available(), 'GPU required for full inference'
    torch.set_num_threads(2)
    # rfdetr.detr sets this globally at import in the frozen RGB pipeline.
    # Keep the same arithmetic for the Swin replay and paired DINO inference.
    torch.set_float32_matmul_precision('high')
    torch.backends.cudnn.allow_tf32 = True  # PyTorch default used in saved Swin inference.
    frozen_predictions = FROZEN / 'rgb_corrected/predictions.json'
    frozen_matches = FROZEN / 'rgb_corrected/known_reference_results.json'
    predictions = read(frozen_predictions); baseline = read(frozen_matches)
    assert len(predictions) == 1777 and len(baseline) == 274
    assert sum(r['detected'] for r in baseline) == 258
    assert sum(r['classification_correct'] for r in baseline) == 93
    contract = read(FROZEN / 'configuration.json')
    assert prior.sha(prior.SWIN) == contract['swin_sha256']
    refs = [r for i in range(4) for r in read(prior.OLD / f'export_shard_{i}_references.json') if r['split'] == 'val']
    assert len(refs) == 274 and len({r['record_id'] for r in refs}) == 274
    provenance = read(DINO_RUN / 'provenance.json')
    assert provenance['source_commit'] == COMMIT
    checkpoint_hash = prior.sha(DINO)
    swin, sl, dino, dl = load_models(device)
    config = {'training_performed': False, 'test_used': False, 'detector_rerun': False,
              'fixed_detector_confidence': .5, 'fixed_matching_iou': .5,
              'frozen_run': str(FROZEN), 'frozen_predictions_sha256': prior.sha(frozen_predictions),
              'frozen_matches_sha256': prior.sha(frozen_matches), 'dino_checkpoint': str(DINO),
              'dino_checkpoint_sha256': checkpoint_hash, 'swin_checkpoint': str(prior.SWIN),
              'swin_checkpoint_sha256': prior.sha(prior.SWIN), 'dino_source_commit': COMMIT,
              'dino_snapshot_sha256': prior.sha(DINO_RUN / 'train_dino_finetune_snapshot.py'),
              'dino_categories': dl, 'swin_categories': sl, 'torch_version': torch.__version__,
              'float32_matmul_precision': torch.get_float32_matmul_precision(),
              'cuda_matmul_allow_tf32': torch.backends.cuda.matmul.allow_tf32,
              'cudnn_allow_tf32': torch.backends.cudnn.allow_tf32,
              'crop': 'unchanged prior.crop_input: RGB, 10% margin, white square pad, bicubic224, ImageNet normalization',
              'tile': 'native Tenengrad Sobel3 at40x; every reconstructed tile must match saved RGB SHA256',
              'job_id': os.environ.get('SLURM_JOB_ID'),
              'caveat': 'Validation diagnostic: Abbas detector saw 13/14 validation slides in its original training.'}
    if preflight:
        print(json.dumps({'preflight': 'passed', 'strict_checkpoint_loading': True, **config}), flush=True)
        return
    assert not (OUT / 'comparison.json').exists(), 'Completed run exists; refusing overwrite'
    save(OUT / 'configuration.json', config)
    groups = collections.defaultdict(list)
    for i, p in enumerate(predictions):
        groups[p['source']].append(i)
    assert len(groups) == 14
    output = [None] * len(predictions)
    traces = []
    for number, (source, indices) in enumerate(sorted(groups.items()), 1):
        slide = FROZEN / 'slides' / Path(source).stem
        grid = [TileSpec(**t) for t in read(slide / 'tile_grid.json')]
        hashes = {}
        for t in read(slide / 'paired_tile_inputs.json'):
            origin = (t['x'], t['y'])
            if origin in hashes:
                assert hashes[origin] == t['rgb_tile_sha256']
            hashes[origin] = t['rgb_tile_sha256']
        needed = collections.defaultdict(list)
        for i in indices:
            needed[tuple(predictions[i]['tile_origin'])].append(i)
        crops = {}; seen = set(); tile_count = 0
        ndpi = NDPIData(source)
        try:
            # Use original band boundaries so decoder and tile pixels reproduce.
            for bx, by, bw, bh, tiles in NDPIAnnotator._group_into_bands(None, grid, 8192):
                selected = [t for t in tiles if (t.x, t.y) in needed and (t.x, t.y) not in seen]
                if not selected:
                    continue
                band = ndpi.get_tile(x=bx, y=by, w=bw, h=bh, magnification=40)
                for t in selected:
                    origin = (t.x, t.y)
                    if origin in seen:
                        continue
                    tile = best_focal_plane(band[:, t.x-bx:t.x-bx+t.w, :, :], tenengrad_ksize=3)
                    digest = hashlib.sha256(np.ascontiguousarray(tile).tobytes()).hexdigest()
                    assert digest == hashes[origin], f'Frozen tile pixels changed: {source} {origin}'
                    image = Image.fromarray(np.asarray(tile, dtype=np.uint8)).convert('RGB')
                    for i in needed[origin]:
                        p = predictions[i]
                        # The original adapter added offsets to np.float32
                        # scalars, rounding slide coordinates to float32.
                        # Reproduce that arithmetic exactly, without changing
                        # either saved detection boxes or crop coordinates.
                        reconstructed = np.array(p['box_tile'], dtype=np.float32) + np.array([t.x,t.y,t.x,t.y], dtype=np.float32)
                        assert np.array_equal(reconstructed.astype(np.float64), np.array(p['box_slide'])), 'Saved box/origin association changed'
                        crop = prior.crop_input(image, p['box_tile'])
                        crops[i] = (TF.normalize(TF.to_tensor(crop), [.485,.456,.406], [.229,.224,.225]),
                                    hashlib.sha256(crop.tobytes()).hexdigest())
                    traces.append({'source': source, 'tile_origin': list(origin), 'rgb_tile_sha256': digest})
                    seen.add(origin); tile_count += 1
                del band
        finally:
            ndpi.close()
        assert set(crops) == set(indices)
        # Original Swin used groups of32 in detection order for each slide.
        for start in range(0, len(indices), 32):
            batch_indices = indices[start:start+32]
            x = torch.stack([crops[i][0] for i in batch_indices]).to(device)
            with torch.inference_mode():
                sp = swin(x).softmax(-1).cpu()
                dp = dino(x).softmax(-1).cpu()
            for i, s, d in zip(batch_indices, sp, dp):
                p = predictions[i]; si = int(s.argmax()); di = int(d.argmax())
                assert sl[si] == p['category'], f'Swin replay changed at prediction {i}'
                assert abs(float(s[si]) - p['classification_score']) < 1e-4, f'Swin score changed at {i}: replay={float(s[si])}, saved={p["classification_score"]}, precision={torch.get_float32_matmul_precision()}'
                output[i] = {**p, 'category': dl[di], 'classification_score': float(d[di]),
                             'swin_category': p['category'], 'swin_classification_score': p['classification_score'],
                             'crop_rgb224_sha256': crops[i][1], 'frozen_prediction_index': i}
        save(OUT / 'slides' / (Path(source).stem + '.json'), [output[i] for i in indices])
        save(OUT / 'status.json', {'status': 'running', 'completed_slides': number, 'total_slides': 14,
                                  'classified_candidates': sum(p is not None for p in output), 'tile_hashes_verified': len(traces)})
        print(json.dumps({'slide': number, 'of': 14, 'verified_tiles': tile_count, 'classified_candidates': len(indices), 'swin_replay': 'exact categories and scores within1e-4'}), flush=True)
        del crops
        gc.collect()
    matches = []
    for source in sorted(groups):
        matches.extend(match([output[i] for i in groups[source]], [r for r in refs if r['image'] == source]))
    bm = {r['record_id']: r for r in baseline}
    for r in matches:
        before = bm[r['record_id']]
        assert r['detected'] == before['detected'] and r['iou'] == before['iou']
    paired = [r for r in matches if r['detected']]
    transitions = collections.Counter((bool(bm[r['record_id']]['classification_correct']), bool(r['classification_correct'])) for r in paired)
    comparison = {'status': 'complete', 'training_performed': False, 'test_used': False,
                  'detector_rerun': False, 'same_boxes_planes_and_crops_verified': True,
                  'all1777_swin_categories_reproduced': True, 'candidate_predictions': len(output),
                  'swin': summarize(baseline), 'dino': summarize(matches),
                  'paired_detected_objects': len(paired),
                  'both_correct': transitions[True, True], 'swin_only_correct': transitions[True, False],
                  'dino_only_correct': transitions[False, True], 'both_wrong': transitions[False, False],
                  'caveat': config['caveat']}
    per_class = {}
    for label in sorted(dl):
        rr = [r for r in paired if r['true_category'] == label]
        per_class[label] = {'detected_objects': len(rr), 'swin_correct': sum(bm[r['record_id']]['classification_correct'] for r in rr),
                            'dino_correct': sum(r['classification_correct'] for r in rr)}
    save(OUT / 'predictions.json', output)
    save(OUT / 'known_reference_results.json', matches)
    save(OUT / 'verified_tile_inputs.json', traces)
    save(OUT / 'per_class_comparison.json', per_class)
    assert prior.sha(frozen_predictions) == config['frozen_predictions_sha256']
    assert prior.sha(frozen_matches) == config['frozen_matches_sha256']
    save(OUT / 'comparison.json', comparison)
    save(OUT / 'status.json', {'status': 'complete', 'completed_slides': 14})
    print(json.dumps(comparison), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        if '--preflight' not in sys.argv:
            save(OUT / 'status.json', {'status': 'failed', 'traceback': traceback.format_exc()})
        raise

"""Independent Method A sweep: one inference pass, filter before deduplication.

Raw predictions are library outputs at 0.05, not unfiltered model logits.
The personal output base must exist before Slurm submission. No test is used.
"""
from __future__ import annotations

import collections
import json
import os
from pathlib import Path
import uuid

from PIL import Image
from focus_helpers import sha256_file
from spring_nms import deduplicate
from spring_types import Detection, TileSpec

ROOT = Path('/rhf/allocations/dsci435/Smithsonian_F26/processed/method_a_focus_stack_v1')
DATA = ROOT / 'dataset'
RUN = ROOT / 'run_artifacts/detector'
BASE = Path('/home/yk86/method_a_reproduction')
THRESHOLDS = (0.05, 0.10, 0.30, 0.50)
MATCH_IOU = 0.5


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def evaluate_source(source, tiles, truth, raw_tiles, threshold):
    import torch
    from torchvision.ops import box_iou

    by_tile, origin = {}, {}
    for tile, raw in zip(tiles, raw_tiles):
        spec = TileSpec(tile['left'], tile['top'], 1024, 1024, tile['left'], tile['top'])
        by_tile[spec] = []
        for item in raw['detections']:
            if item['score'] < threshold:
                continue
            detection = Detection(*item['box_slide'], item['score'], 0., 0., 0., 0.)
            by_tile[spec].append(detection)
            origin[id(detection)] = {k: v for k, v in item.items() if k != 'box_local'}
    candidates = [origin[id(d)] for d in deduplicate(by_tile, MATCH_IOU)]
    ids = list(truth)
    matches = []
    used_candidates = set()
    if candidates and ids:
        overlap = box_iou(torch.tensor([item['box_slide'] for item in candidates]),
                          torch.tensor([truth[ident]['box'] for ident in ids]))
        pairs = [(float(overlap[i, j]), i, j)
                 for i, j in torch.nonzero(overlap >= MATCH_IOU).tolist()]
        assigned, used_targets = {}, set()
        for iou, i, j in sorted(pairs, reverse=True):
            if i not in used_candidates and j not in used_targets:
                assigned[j] = (i, iou)
                used_candidates.add(i)
                used_targets.add(j)
        for j, ident in enumerate(ids):
            candidate = candidates[assigned[j][0]] if j in assigned else None
            matches.append({
                'record_id': ident, 'source': source,
                'true_category': truth[ident]['category'],
                'detected': candidate is not None,
                'predicted_category': candidate['category'] if candidate else None,
                'category_correct': candidate is not None and candidate['category'] == truth[ident]['category'],
                'iou': assigned[j][1] if candidate else None,
            })
    else:
        matches.extend({'record_id': ident, 'source': source,
                        'true_category': item['category'], 'detected': False,
                        'predicted_category': None, 'category_correct': False, 'iou': None}
                       for ident, item in truth.items())
    for i, item in enumerate(candidates):
        item['matched_known_reference'] = i in used_candidates
    return candidates, matches


def main():
    import torch
    from rfdetr_plus.models.detection import RFDETR2XLarge

    if not torch.cuda.is_available() or not (RUN / 'status.json').is_file():
        raise RuntimeError('Completed training and a Slurm GPU are required')
    status = json.loads((RUN / 'status.json').read_text())
    checkpoint = RUN / 'checkpoint_best_total.pth'
    if status['status'] != 'completed':
        raise RuntimeError('Detector training is incomplete')
    if sha256_file(checkpoint) != status['checkpoint_best_total_sha256']:
        raise ValueError('Trained checkpoint hash changed')
    category_path = ROOT / 'inputs/broad_category_map.json'
    category_map = json.loads(category_path.read_text())
    grouped = collections.defaultdict(list)
    plan_hashes = {}
    for path in sorted((ROOT / 'plan').glob('*.json')):
        plan = json.loads(path.read_text())
        if plan['split'] == 'valid':
            grouped[plan['source_image']].extend(plan['tiles'])
            plan_hashes[path.name] = sha256_file(path)
    if sum(map(len, grouped.values())) != 1432:
        raise ValueError('Validation grid differs from Method B')
    truths = {}
    for source, tiles in sorted(grouped.items()):
        truth = {}
        for tile in tiles:
            for label in tile['objects']:
                truth[label['record_id']] = {'box': label['box_slide'], 'category': label['broad_category']}
        truths[source] = truth
    if sum(map(len, truths.values())) != 274:
        raise ValueError('Known validation reference coverage differs from Method B grid')

    output = BASE / f'confidence_sweep_{uuid.uuid4().hex}'
    output.mkdir(exist_ok=False)
    print(f'Output directory: {output}', flush=True)
    write_json(output / 'run_contract.json', {
        'checkpoint_sha256': status['checkpoint_best_total_sha256'],
        'category_map_sha256': sha256_file(category_path), 'validation_plan_sha256': plan_hashes,
        'script_sha256': sha256_file(Path(__file__)),
        'helper_sha256': {name: sha256_file(Path(__import__(name).__file__))
                          for name in ('focus_helpers', 'spring_nms', 'spring_types')},
        'model': 'RFDETR2XLarge', 'num_classes': 28, 'resolution': 1000,
        'inference_threshold': 0.05, 'thresholds': THRESHOLDS,
        'match_iou': MATCH_IOU, 'deduplication_iou': MATCH_IOU,
        'filter_operator': 'score >= threshold', 'slurm_job_id': os.environ.get('SLURM_JOB_ID'),
        'torch_version': torch.__version__, 'test_used': False,
        'raw_scope': 'Library-returned detections before cross-tile deduplication',
    })
    write_json(output / 'known_references.json', truths)
    detector = RFDETR2XLarge(pretrain_weights=str(checkpoint), num_classes=28, resolution=1000)
    results = {t: {'predictions': [], 'matches': [], 'raw_retained': 0} for t in THRESHOLDS}
    # Stream raw records before scoring so partial inference survives failures.
    with (output / 'raw_tile_predictions.jsonl').open('x', encoding='utf-8') as stream:
        for source, tiles in sorted(grouped.items()):
            raw_tiles = []
            for tile in tiles:
                image_path = DATA / 'valid' / f"{tile['tile_id']}.png"
                if not image_path.is_file() or not image_path.is_symlink():
                    raise FileNotFoundError('Shared validation image link changed')
                with Image.open(image_path) as handle:
                    detected = detector.predict(handle.convert('RGB'), threshold=0.05)
                raw = {'source': source, 'tile_id': tile['tile_id'],
                       'left': tile['left'], 'top': tile['top'], 'size': 1024,
                       'image_sha256': sha256_file(image_path), 'detections': []}
                for box, score, class_id in zip(detected.xyxy, detected.confidence, detected.class_id):
                    local = [float(v) for v in box]
                    slide_box = [local[0] + tile['left'], local[1] + tile['top'],
                                 local[2] + tile['left'], local[3] + tile['top']]
                    class_id = int(class_id)
                    if not 0 <= class_id < 28:
                        raise ValueError('Predicted category ID outside shared mapping')
                    raw['detections'].append({'box_local': local, 'box_slide': slide_box,
                        'score': float(score), 'source': source, 'category_id': class_id,
                        'category': category_map[str(class_id)], 'tile_id': tile['tile_id']})
                stream.write(json.dumps(raw, allow_nan=False) + '\n')
                stream.flush()
                raw_tiles.append(raw)
            for threshold in THRESHOLDS:
                candidates, matches = evaluate_source(source, tiles, truths[source], raw_tiles, threshold)
                results[threshold]['predictions'].extend(candidates)
                results[threshold]['matches'].extend(matches)
                results[threshold]['raw_retained'] += sum(
                    item['score'] >= threshold for raw in raw_tiles for item in raw['detections'])
            print(f"Completed slide {len(raw_tiles)} tiles", flush=True)
    summaries = []
    for threshold, result in results.items():
        folder = output / f'confidence_{threshold:.2f}'
        folder.mkdir()
        matches, predictions = result['matches'], result['predictions']
        known = len(matches)
        if known != 274:
            raise ValueError('Threshold evaluation changed known reference count')
        found = sum(item['detected'] for item in matches)
        correct = sum(item['category_correct'] for item in matches)
        summary = {
            'status': 'complete', 'scope': 'shared fixed-grid annotated-ROI validation',
            'confidence_threshold': threshold, 'match_iou': MATCH_IOU,
            'known_specimens': known, 'localized_known_specimens': found,
            'correctly_localized_and_classified': correct,
            'known_specimen_recall_iou50': found / known,
            'classification_accuracy_on_matched': correct / found if found else None,
            'end_to_end_known_specimen_success': correct / known,
            'raw_retained_predictions': result['raw_retained'],
            'total_deduplicated_predictions': len(predictions),
            'unmatched_prediction_count': sum(not p['matched_known_reference'] for p in predictions),
            'unmatched_predictions': 'unreviewed; not automatically false positives',
            'checkpoint_sha256': status['checkpoint_best_total_sha256'], 'test_used': False,
        }
        write_json(folder / 'predictions.json', predictions)
        write_json(folder / 'known_reference_results.json', matches)
        write_json(folder / 'summary.json', summary)
        summaries.append(summary)
        print(json.dumps(summary, indent=2), flush=True)
    write_json(output / 'summary.json', {'status': 'complete', 'threshold_results': summaries,
        'baseline_check': {'expected_at_0_50': {'localized': 24, 'correct': 20},
                          'reproduces_reported_counts': summaries[-1]['localized_known_specimens'] == 24
                          and summaries[-1]['correctly_localized_and_classified'] == 20}})


if __name__ == '__main__':
    main()

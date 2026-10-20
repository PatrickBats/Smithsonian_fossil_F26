"""Read-only CPU tracing of changed Momipites assignments in saved sweep artifacts.

No images, checkpoints, inference, or output files are used. Requires the original
sweep evaluator and matching helper modules/environment. Prints JSON to stdout;
record IDs and source directories are omitted.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path, PureWindowsPath
import sys

# Keep imports read-only too, including when invoked without Python's -B flag.
sys.dont_write_bytecode = True


def read_json(path):
    with path.open(encoding='utf-8') as stream:
        return json.load(stream)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def match_identities(candidates, truth):
    """Mirror original tuple ordering, float32 IoU, and greedy assignment exactly."""
    import torch
    from torchvision.ops import box_iou

    ids = list(truth)
    selected = {}
    if candidates and ids:
        overlaps = box_iou(torch.tensor([p['box_slide'] for p in candidates]),
                           torch.tensor([truth[key]['box'] for key in ids]))
        pairs = [(float(overlaps[i, j]), i, j)
                 for i, j in torch.nonzero(overlaps >= 0.5).tolist()]
        used_predictions, used_targets = set(), set()
        for iou, i, j in sorted(pairs, reverse=True):
            if i not in used_predictions and j not in used_targets:
                selected[ids[j]] = (candidates[i], iou)
                used_predictions.add(i)
                used_targets.add(j)
    return selected


def verify_identity_matches(selected, matches):
    for row in matches:
        pair = selected.get(row['record_id'])
        require(row['detected'] == (pair is not None), 'Identity replay detection mismatch.')
        require(row['predicted_category'] == (pair[0]['category'] if pair else None),
                'Identity replay category mismatch.')
        require(row['iou'] == (pair[1] if pair else None), 'Identity replay IoU mismatch.')
        require(row['category_correct'] == (pair is not None and
                pair[0]['category'] == row['true_category']), 'Identity replay correctness mismatch.')


def prediction_view(item):
    return {key: item[key] for key in
            ('trace_id', 'box_slide', 'score', 'category', 'category_id', 'tile_id')}


def cluster_survivors(original, tiles, retained, nms, types):
    """Trace connectivity using original boundary/IoU helpers, not a new NMS policy."""
    nodes, tile_nodes = [], []
    for raw in tiles:
        spec = types.TileSpec(raw['left'], raw['top'], 1024, 1024, raw['left'], raw['top'])
        tile_nodes.append((spec, raw))
    tile_nodes.sort(key=lambda pair: (pair[0].iy, pair[0].ix))
    specs = [pair[0] for pair in tile_nodes]
    indices = []
    for _, raw in tile_nodes:
        group = []
        for item in raw['detections']:
            if item['score'] >= 0.05:
                group.append(len(nodes))
                nodes.append((item, types.Detection(*item['box_slide'], item['score'], 0., 0., 0., 0.)))
        indices.append(group)
    edges = collections.defaultdict(set)
    for i in range(len(specs)):
        for j in nms._get_overlapping_tiles(i, specs):
            for a in indices[i]:
                for b in indices[j]:
                    if (nms._has_intersection(nodes[a][1], nodes[b][1]) and
                            nms._iou_pair(nodes[a][1], nodes[b][1]) > 0.5):
                        edges[a].add(b)
                        edges[b].add(a)
    start = next(i for i, (item, _) in enumerate(nodes) if item['trace_id'] == original['trace_id'])
    component, pending = {start}, [start]
    while pending:
        for neighbor in edges[pending.pop()]:
            if neighbor not in component:
                component.add(neighbor)
                pending.append(neighbor)
    return [prediction_view(nodes[i][0]) for i in sorted(component)
            if nodes[i][0]['trace_id'] in retained]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path, help='Saved confidence-sweep directory')
    parser.add_argument('--evaluator', type=Path,
                        default=Path(__file__).with_name('evaluate_confidence_sweep.py'))
    args = parser.parse_args()
    contract = read_json(args.run / 'run_contract.json')
    require(digest(args.evaluator) == contract['script_sha256'], 'Sweep evaluator hash mismatch.')
    require(contract['inference_threshold'] == 0.05 and contract['match_iou'] == 0.5
            and contract['deduplication_iou'] == 0.5, 'Unexpected saved evaluation settings.')
    spec = importlib.util.spec_from_file_location('saved_sweep_reference', args.evaluator)
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)  # Import definitions only; main() is not called.
    for name in ('focus_helpers', 'spring_nms', 'spring_types'):
        require(digest(sys.modules[name].__file__) == contract['helper_sha256'][name],
                f'Helper hash mismatch: {name}.')
    require(evaluator.MATCH_IOU == 0.5, 'Evaluator IoU mismatch.')
    truths = read_json(args.run / 'known_references.json')
    grouped = collections.defaultdict(list)
    tile_ids = set()
    raw_ids = set()
    with (args.run / 'raw_tile_predictions.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            raw = json.loads(line)
            require(raw['tile_id'] not in tile_ids, 'Duplicate raw tile identity.')
            tile_ids.add(raw['tile_id'])
            require(raw['size'] == 1024, 'Unexpected tile size.')
            for index, item in enumerate(raw['detections']):
                require(item['source'] == raw['source'] and item['tile_id'] == raw['tile_id'],
                        'Raw prediction source/tile mismatch.')
                item['trace_id'] = f"{raw['tile_id']}:{index}"
                raw_ids.add(item['trace_id'])
            grouped[raw['source']].append(raw)
    require(len(tile_ids) == 1432 and sum(map(len, truths.values())) == 274,
            'Incomplete grid or known-reference artifacts.')
    require(set(grouped) == set(truths), 'Raw and reference source sets differ.')

    replay, selections = {}, {}
    for threshold in (0.50, 0.05):
        predictions, matches, selected = [], [], {}
        for source in sorted(grouped):
            raw = grouped[source]
            candidates, rows = evaluator.evaluate_source(source, raw, truths[source], raw, threshold)
            identity_matches = match_identities(candidates, truths[source])
            verify_identity_matches(identity_matches, rows)
            selected[source] = identity_matches
            predictions.extend(candidates)
            matches.extend(rows)
        folder = args.run / f'confidence_{threshold:.2f}'
        saved_predictions = read_json(folder / 'predictions.json')
        clean_predictions = [{k: v for k, v in p.items() if k != 'trace_id'} for p in predictions]
        require(clean_predictions == saved_predictions, 'Saved prediction content/order mismatch.')
        saved_matches = read_json(folder / 'known_reference_results.json')
        require(matches == saved_matches, 'Saved GT-level assignments mismatch; no conclusions produced.')
        replay[threshold] = predictions
        selections[threshold] = selected

    # No diagnostic conclusions are emitted until BOTH thresholds pass exact replay.
    reports = []
    for source, truth in truths.items():
        for record, gt in truth.items():
            high = selections[0.50][source].get(record)
            low = selections[0.05][source].get(record)
            if not (gt['category'] == 'Momipites' and high and low
                    and high[0]['category'] == 'Momipites' and low[0]['category'] != 'Momipites'):
                continue
            original, replacement = high[0], low[0]
            retained = {p['trace_id'] for p in replay[0.05] if p['source'] == source}
            survives = original['trace_id'] in retained
            survivors = [] if survives else cluster_survivors(
                original, grouped[source], retained, sys.modules['spring_nms'], sys.modules['spring_types'])
            require(survives or len(survivors) == 1, 'Dedup component survivor is ambiguous.')
            assigned_elsewhere = any(pair[0]['trace_id'] == original['trace_id']
                                     for pair in selections[0.05][source].values())
            reports.append({
                'gt_number': len(reports) + 1, 'slide': PureWindowsPath(source).name,
                'matched_at_0_50': {**prediction_view(original), 'iou': high[1]},
                'matched_at_0_05': {**prediction_view(replacement), 'iou': low[1]},
                'original_present_in_raw': original['trace_id'] in raw_ids,
                'original_survives_confidence_0_05': original['score'] >= 0.05,
                'original_survives_dedup_0_05': survives,
                'original_assigned_to_another_gt_at_0_05': assigned_elsewhere,
                'stage': 'GT matching: original survives but is not selected for this GT'
                         if survives else 'Deduplication removes original; matching selects replacement',
                'original_component_survivor': survivors,
                'identical_selected_boxes': original['box_slide'] == replacement['box_slide'],
                'maximum_coordinate_difference': max(abs(a - b) for a, b in
                    zip(original['box_slide'], replacement['box_slide'])),
                'identical_matching_iou': high[1] == low[1],
            })
    print(json.dumps({'verification': 'Exact saved prediction and GT-assignment replay passed at both thresholds',
                      'expected_changed_gt': 9, 'observed_changed_gt': len(reports),
                      'expected_count_matches': len(reports) == 9, 'objects': reports}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Avoid leaking record IDs, source paths, or path-bearing dependency errors.
        if isinstance(error, ValueError) and str(error).endswith('.'):
            print(f'Analysis stopped: {error}', file=sys.stderr)
        else:
            print(f'Analysis stopped ({type(error).__name__}); check inputs and the original CPU environment.',
                  file=sys.stderr)
        sys.exit(2)

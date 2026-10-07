"""Summarize a completed diagnostic without treating incomplete labels as negatives."""
import argparse
import csv
import json
from pathlib import Path


def summarize(root, selection, historical):
    targets = json.loads(selection.read_text())
    expected = {(r['record_id'], rep) for r in targets
                for rep in ('focus_stack', 'best_plane')}
    rows = []
    completions = []
    for shard in range(2):
        folder = root / 'outputs' / f'shard_{shard}'
        completions.append(json.loads((folder / 'complete.json').read_text()))
        with (folder / 'results.csv').open() as handle:
            rows.extend(csv.DictReader(handle))
    observed = [(r['record_id'], r['representation']) for r in rows]
    assert len(observed) == len(set(observed)), 'Duplicate predictions'
    assert set(observed) == expected, 'Missing or unexpected predictions'
    split = json.loads(historical.read_text())
    for row in rows:
        membership = [k for k, slides in split.items() if row['slide'] in slides]
        assert len(membership) <= 1, 'Overlapping historical split'
        row['historical_split'] = membership[0] if membership else 'unresolved_exact_name'

    def counts(items):
        n = len(items)
        primary = sum(r['hit_conf_050'] == 'True' for r in items)
        diagnostic = sum(r['hit_conf_025'] == 'True' for r in items)
        return dict(targets=n, recovered_conf_050=primary,
                    recovered_conf_025=diagnostic, recovery_fraction=primary/n if n else None)

    result = {'interpretation': 'Known-positive, annotation-centered diagnostic; not precision, AP, or independent generalization.',
              'representations': {}, 'shard_completion': completions}
    for rep in ('focus_stack', 'best_plane'):
        rr = [r for r in rows if r['representation'] == rep]
        summary = {'overall': counts(rr)}
        for field in ('center_inside_roi', 'box_inside_roi', 'category', 'historical_split'):
            summary[field] = {value: counts([r for r in rr if r[field] == value])
                              for value in sorted({r[field] for r in rr})}
        result['representations'][rep] = summary
    return result, rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--historical', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result, rows = summarize(args.root, args.selection, args.historical)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    with (args.output / 'results.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({k: v['overall'] for k, v in result['representations'].items()}, indent=2))

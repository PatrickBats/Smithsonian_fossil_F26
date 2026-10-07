"""Validate source counts and produce report assets without running models."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def main():
    data = ROOT / "data/current"
    categories = read_csv(data / "category_summary.csv")
    annotations = read_csv(data / "annotation_records.csv")
    class_records = read_csv(data / "classification_annotations.csv")
    manifest = json.loads((data / "audit_manifest.json").read_text())
    by_priority = Counter(row["priority"] for row in annotations)
    cat_priorities = Counter(row["priority"] for row in categories)
    expected = {"YES": 2290, "MAYBE": 114, "NO": 8871, "UNTITLED": 227}
    assert dict(by_priority) == expected == manifest["priorities"]
    assert cat_priorities == {"YES": 32, "MAYBE": 5, "NO": 28}
    assert len(annotations) == 11502 == manifest["records"]
    assert len(class_records) == 2290
    assert {r['record_id'] for r in class_records} == {
        r['record_id'] for r in annotations if r['priority'] == 'YES'
    }
    assert len({row["slide"] for row in annotations}) == 83
    assert len({row["matched_title"] for row in annotations if row["matched_title"]}) == 185
    by_category = Counter(row["mapped_category"] for row in annotations if row["priority"] != "UNTITLED")
    slide_counts = defaultdict(Counter)
    for row in annotations:
        if row['priority'] != 'UNTITLED':
            slide_counts[row['mapped_category']][row['slide']] += 1
    for row in categories:
        name = row['category']
        assert by_category[name] == int(row['annotation_records']) == int(row['spreadsheet_count'])
        assert len(slide_counts[name]) == int(row['slides'])
        assert max(slide_counts[name].values()) == int(row['largest_slide_count'])
        assert int(row['difference']) == 0
    assert manifest['all_title_counts_match'] and manifest['all_category_counts_match']
    untitled = Counter(row['shape'] for row in annotations if row['priority'] == 'UNTITLED')
    assert untitled == {'freehand': 133, 'circle': 94}

    results_path = ROOT / 'reports/detection_pilot_2026-09-24/results.csv'
    results = read_csv(results_path)
    assert len(results) == 128
    assert len({r['record_id'] for r in results}) == 64
    assert len({r['slide'] for r in results}) == 29
    assert len({r['category'] for r in results}) == 32
    hits = Counter(r['representation'] for r in results if r['hit_conf_050'] == 'True')
    assert hits == {'best_plane': 54, 'focus_stack': 51}
    one_per_target = {r['record_id']: r for r in results}
    membership = Counter(r['historical_split'] for r in one_per_target.values())
    assert membership['train'] == 50 and membership['test'] == 9
    assert sum(v for k,v in membership.items() if k not in ['train','test']) == 5

    values = {'NamedCount':'11,275', 'YesCount':'2,290', 'MaybeCount':'114',
              'NoCount':'8,871', 'UntitledCount':'227', 'CategoryCount':'65',
              'SlideCount':'83', 'TitleCount':'185', 'YesCategories':'32',
              'MaybeCategories':'5', 'NoCategories':'28', 'BestHits':'54',
              'StackHits':'51', 'BestPercent':'84.4', 'StackPercent':'79.7'}
    (HERE / 'generated_counts.tex').write_text(
        '% Generated from validated project inventories; run build_assets.py.\n' +
        ''.join('\\newcommand{\\'+key+'}{'+value+'}\n' for key,value in values.items()))

    selected = sorted((r for r in categories if r['priority'] == 'YES'),
                      key=lambda r: (-int(r['annotation_records']), r['category']))
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10,
                         'pdf.fonttype':42, 'ps.fonttype':42})
    # Two panels keep all 32 labels readable at IEEE's full text width.
    fig = plt.figure(figsize=(7.16, 4.5))
    for start, left in [(0, 0.245), (16, 0.76)]:
        ax = fig.add_axes([left, 0.14, 0.235, 0.72])
        rows = selected[start:start+16]
        counts = [int(r['annotation_records']) for r in rows]
        ax.barh(range(len(rows)), counts, color='#555555', height=0.68)
        ax.set_yticks(range(len(rows)), [r['category'] for r in rows], fontsize=8)
        ax.invert_yaxis()
        ax.set_xlim(0, 460)
        ax.set_xticks([0,100,200,300])
        ax.tick_params(axis='x', labelsize=8)
        for i, row in enumerate(rows):
            ax.text(counts[i]+5, i, str(counts[i]), va='center', fontsize=8)
            ax.text(430, i, row['slides'], va='center', ha='center', fontsize=8)
        ax.text(430, -1.1, 'Slides', ha='center', va='bottom', fontsize=8)
        ax.spines[['top','right','left']].set_visible(False)
        ax.tick_params(axis='y', length=0)
        ax.set_axisbelow(True)
        ax.grid(axis='x', color='#dddddd', linewidth=0.5)
    fig.suptitle('Fall 2026 inclusion-priority categories', fontsize=10, y=0.98)
    fig.text(0.5, 0.035, 'Annotation records before quality review and sampling',
             ha='center', fontsize=9)
    figures = HERE / 'figures'
    figures.mkdir(exist_ok=True)
    fig.savefig(figures/'category_distribution.pdf', bbox_inches='tight',
                metadata={'CreationDate':None,'ModDate':None})
    fig.savefig(figures/'category_distribution.png', dpi=180, bbox_inches='tight')
    plt.close(fig)
    sources = [data/n for n in ['category_summary.csv','annotation_records.csv',
        'classification_annotations.csv','audit_manifest.json','title_reconciliation.csv',
        'cluster_verification.json']] + [results_path]
    proof = {'inventory':dict(by_priority), 'category_priorities':dict(cat_priorities),
        'pilot_hits':dict(hits), 'pilot_historical_membership':dict(membership),
        'matplotlib_version':matplotlib.__version__,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sources}, 'checks':'passed'}
    (HERE/'asset_validation.json').write_text(json.dumps(proof,indent=2)+'\n')
    print('Inventory, category/slide counts, classification IDs, and pilot results verified; assets generated.')


if __name__ == '__main__':
    main()

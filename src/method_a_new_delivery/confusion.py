"""Aggregate held-out matches into the complete 28-output confusion matrix."""

import argparse
import csv
from collections import Counter
from pathlib import Path

from .cv import read
from .cv_evaluate import RESULTS
from .paths import TRAINING


ROW_ORDER = [
    "Inaperturopollenites sp.",
    "Laevigatosporites sp.",
    "Monocolpites sp.",
    "Arecipites sp.",
    "Psilatriletes sp.",
    "Tetracolporopollenites sp.",
    "Taxodium sp.",
    "Bombacacidites sp.",
    "Rhoipites sp.",
    "Quercus sp.",
    "Cupuliferoipollenites sp.",
    "Retipollenites sp.",
    "Rousea sp.",
    "Psilatricolpites sp.",
    "Alnipollenites verus",
    "Cicatricosisporites sp.",
]


def aggregate(matches, categories):
    assert len(matches) == 540
    assert len({match["record_id"] for match in matches}) == 540
    assert len({match["source"] for match in matches}) == 20
    assert len(categories) == 28 and set(ROW_ORDER) <= set(categories)
    counts = Counter()
    for match in matches:
        true = match["true_category"]
        predicted = match["predicted_category"] or "Missed"
        assert true in ROW_ORDER
        assert predicted in categories or predicted == "Missed"
        assert bool(match["detected"]) == (predicted != "Missed")
        assert bool(match["correct"]) == (true == predicted)
        counts[true, predicted] += 1
    assert sum(counts.values()) == 540
    assert sum(counts[name, name] for name in ROW_ORDER) == 304
    assert sum(counts[name, "Missed"] for name in ROW_ORDER) == 18
    return counts


def write_csv(path, counts, categories):
    columns = ROW_ORDER + [name for name in categories if name not in ROW_ORDER] + ["Missed"]
    assert len(columns) == 29
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["true_category", *columns])
        for name in ROW_ORDER:
            writer.writerow([name, *(counts[name, category] for category in columns)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--training", type=Path, default=TRAINING)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected = read(args.results / "aggregate" / "selection.json")["selected_threshold"]
    tag = f"confidence_{selected:.2f}_matches.json"
    matches = [match for fold in range(5) for match in read(args.results / f"fold_{fold}" / tag)]
    coco = read(args.training / "dataset_base" / "train" / "_annotations.coco.json")
    categories = [item["name"] for item in sorted(coco["categories"], key=lambda item: item["id"])]
    write_csv(args.output, aggregate(matches, categories), categories)


if __name__ == "__main__":
    main()

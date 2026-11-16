"""Checks for scan grouping, recorded aggregate counts, and standalone entry points."""

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from method_a_new_delivery.cv import assign_folds
from method_a_new_delivery.confusion import ROW_ORDER, aggregate, write_csv


class NewDeliveryTests(unittest.TestCase):
    def test_scan_grouping_keeps_four_whole_scans_per_fold(self):
        plans = [
            {"source": f"scan_{index:02d}", "objects": [None] * (index + 1)}
            for index in range(20)
        ]
        assignment = assign_folds(plans)
        self.assertEqual(assignment, assign_folds(list(reversed(plans))))
        self.assertEqual(set(assignment), {plan["source"] for plan in plans})
        self.assertEqual([list(assignment.values()).count(fold) for fold in range(5)], [4] * 5)

    def test_recorded_counts_round_trip_through_match_aggregation(self):
        path = ROOT / "reports" / "method_a_new_delivery_2026-11-16" / "confusion_counts.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames[1:-1]
            rows = list(reader)
        self.assertEqual(len(columns), 28)
        self.assertEqual([row["true_category"] for row in rows], ROW_ORDER)
        matches = []
        for row in rows:
            truth = row["true_category"]
            for predicted in [*columns, "Missed"]:
                for _ in range(int(row[predicted])):
                    matches.append({
                        "record_id": f"object_{len(matches)}",
                        "source": f"scan_{len(matches) % 20}",
                        "true_category": truth,
                        "predicted_category": None if predicted == "Missed" else predicted,
                        "detected": predicted != "Missed",
                        "correct": truth == predicted,
                    })
        self.assertEqual(len(matches), 540)
        counts = aggregate(matches, columns)
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / "counts.csv"
            write_csv(generated, counts, columns)
            self.assertEqual(generated.read_bytes(), path.read_bytes())

    def test_label_mapping_covers_32_sponsor_categories_and_28_outputs(self):
        maps = ROOT / "data" / "current" / "new_delivery_maps"
        broad = json.loads((maps / "broad_category_map.json").read_text())
        with (maps / "fine_to_broad.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 32)
        self.assertEqual(len(broad), 28)
        self.assertEqual({int(row["broad_class_id"]) for row in rows}, set(range(28)))
        self.assertEqual({row["broad_category"] for row in rows}, set(broad.values()))

    def test_entry_points_help_from_another_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ("train_ignore.py", "confusion.py"):
                entry = ROOT / "scripts" / "method_a_new_delivery" / name
                completed = subprocess.run(
                    [sys.executable, str(entry), "--help"], cwd=directory,
                    check=True, capture_output=True, text=True,
                )
                self.assertIn("usage:", completed.stdout)


if __name__ == "__main__":
    unittest.main()

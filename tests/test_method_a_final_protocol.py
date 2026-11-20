"""Check scan isolation, guarded selection, and the joint success denominator."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from method_a_final_evaluation.protocol import choose, partition, split_plans, summarize


class ProtocolTests(unittest.TestCase):
    def plans(self):
        return [
            {
                "source": f"scan_{i}",
                "origin": "old" if i < 30 else "new",
                "group_id": "alias_pair" if i in (1, 2) else f"group_{i}",
                "objects": [{"category": f"class_{i % 4}"}] * (i % 7 + 1),
            }
            for i in range(40)
        ]

    def test_test_and_fold_identity_groups_never_cross_training(self):
        plans = self.plans()
        assignment = partition(plans, candidates=200)
        self.assertEqual(assignment, partition(list(reversed(plans)), candidates=200))
        self.assertEqual(assignment["scan_1"], assignment["scan_2"])
        test = split_plans(plans, assignment, "test")
        self.assertEqual({p["origin"] for p in test}, {"old", "new"})
        test_groups = {p["group_id"] for p in test}
        for fold in range(5):
            train = {
                p["group_id"] for p in split_plans(plans, assignment, "train", fold)
            }
            valid = {
                p["group_id"] for p in split_plans(plans, assignment, "valid", fold)
            }
            self.assertFalse(
                train & valid or train & test_groups or valid & test_groups
            )

    def test_test_results_cannot_select_a_model(self):
        row = {"split": "test", "test_used": True}
        with self.assertRaises(ValueError):
            choose([row])
        base = {
            "split": "cross_validation",
            "test_used": False,
            "mean_scan_success": 0.5,
            "correct": 5,
            "known": 10,
            "record_ids_digest": "same",
            "step": 2400,
            "threshold": 0.3,
        }
        better = {**base, "step": 1200, "correct": 6, "mean_scan_success": 0.6}
        self.assertEqual(choose([base, better])["step"], 1200)
        with self.assertRaises(ValueError):
            choose([base, {**better, "record_ids_digest": "different"}])

    def test_joint_success_includes_misses_and_wrong_categories(self):
        rows = [
            {
                "record_id": "one",
                "source": "s",
                "true_category": "a",
                "predicted_category": "a",
                "detected": True,
                "correct": True,
            },
            {
                "record_id": "two",
                "source": "s",
                "true_category": "a",
                "predicted_category": "b",
                "detected": True,
                "correct": False,
            },
            {
                "record_id": "three",
                "source": "s",
                "true_category": "a",
                "predicted_category": None,
                "detected": False,
                "correct": False,
            },
        ]
        result = summarize(rows, {"s": "old"})
        self.assertEqual(
            (
                result["known"],
                result["correct"],
                result["wrong_class"],
                result["missed"],
            ),
            (3, 1, 1, 1),
        )
        self.assertEqual(result["success"], 1 / 3)
        with self.assertRaises(ValueError):
            summarize(rows + rows, {"s": "old"})


if __name__ == "__main__":
    unittest.main()

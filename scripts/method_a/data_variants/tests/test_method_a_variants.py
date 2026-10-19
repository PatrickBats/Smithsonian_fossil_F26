"""Dependency-free checks for the Method A handoff; no NOTS data or GPU needed."""

import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

CODE = Path(__file__).resolve().parents[1]
REPOSITORY = CODE.parents[2]
REPORT = REPOSITORY / "reports/method_a_data_variants_2026-10-18"
spec = importlib.util.spec_from_file_location("method_a_variants_common", CODE / "common.py")
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)


def algorithm_ast_sha256(node):
    """Ignore locations and empty optional fields across Python AST versions."""

    def normalize(value):
        if isinstance(value, ast.AST):
            return {
                "type": type(value).__name__,
                "fields": {
                    key: normalize(child)
                    for key, child in ast.iter_fields(value)
                    if child is not None and child != []
                },
            }
        if isinstance(value, list):
            return [normalize(child) for child in value]
        return value

    payload = json.dumps(normalize(node), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


class VariantNamingTests(unittest.TestCase):
    def test_public_names_preserve_recorded_paths(self):
        expected = {"A1": "m1_positive_grid", "A2": "m2_retile_matched", "A3": "m2_retile_all"}
        self.assertEqual(len(common.EXPERIMENTS), 3)
        for public, recorded in expected.items():
            self.assertEqual(common.resolve_variant(public), recorded)
            self.assertEqual(common.resolve_variant(public.lower()), recorded)
            self.assertEqual(common.resolve_variant(recorded), recorded)
            self.assertEqual(common.variant_id(recorded), public)

    def test_method_b_is_not_a_method_a_variant(self):
        with self.assertRaises(ValueError):
            common.resolve_variant("Method B")

    def test_shared_architecture_has_no_variant_specific_model_selection(self):
        tree = ast.parse((CODE / "train.py").read_text())
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "RFDETR2XLargeConfig"
        ]
        self.assertEqual(len(calls), 1)
        keywords = {item.arg: item.value for item in calls[0].keywords}
        self.assertEqual(ast.literal_eval(keywords["num_classes"]), 28)
        self.assertEqual(ast.literal_eval(keywords["resolution"]), 1000)
        self.assertEqual(common.SEED, 20261013)


class OutputBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        roots = {key: self.base / key.lower() for key in ("ROOT", "CODE", "LOGS", "RESULTS")}
        self.roots = patch.multiple(common, **roots)
        self.roots.start()
        self.addCleanup(self.roots.stop)

    def test_owned_metadata_replacement_is_atomic(self):
        path = common.ROOT / "audit/result.json"
        common.write(path, {"state": "started"})
        common.write(path, {"state": "completed"})
        self.assertEqual(common.load(path), {"state": "completed"})
        self.assertFalse(path.with_name(path.name + ".tmp").exists())

    def test_outside_destination_creates_no_parent(self):
        path = self.base / "outside/missing/result.json"
        with self.assertRaises(ValueError):
            common.write(path, {"not_written": True})
        self.assertFalse((self.base / "outside").exists())

    def test_parent_symlink_cannot_escape_output_root(self):
        common.ROOT.mkdir()
        outside = self.base / "external-inputs"
        outside.mkdir()
        (common.ROOT / "linked").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            common.write(common.ROOT / "linked/result.json", {})
        self.assertFalse((outside / "result.json").exists())

    def test_destination_symlink_cannot_overwrite_input(self):
        common.ROOT.mkdir()
        source = common.ROOT / "input.json"
        source.write_text('{"preserve": true}')
        target = common.ROOT / "alias.json"
        target.symlink_to(source)
        with self.assertRaises(PermissionError):
            common.write(target, {"preserve": False})
        self.assertEqual(json.loads(source.read_text()), {"preserve": True})

    def test_invalid_json_preserves_existing_file_and_cleans_own_temp(self):
        path = common.RESULTS / "summary.json"
        common.write(path, {"valid": 1})
        with self.assertRaises(ValueError):
            common.write(path, {"invalid": math.nan})
        self.assertEqual(common.load(path), {"valid": 1})
        self.assertFalse(path.with_name(path.name + ".tmp").exists())

    def test_an_existing_temp_is_not_removed_or_reused(self):
        common.RESULTS.mkdir()
        path = common.RESULTS / "summary.json"
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text("existing operation")
        with self.assertRaises(FileExistsError):
            common.write(path, {"valid": 1})
        self.assertEqual(temporary.read_text(), "existing operation")


class RecordedResultsTests(unittest.TestCase):
    def setUp(self):
        self.recorded = json.loads((REPORT / "recorded_comparison.json").read_text())
        self.provenance = json.loads((REPORT / "provenance.json").read_text())

    def test_aggregate_preserves_verified_recorded_bytes(self):
        digest = hashlib.sha256((REPORT / "recorded_comparison.json").read_bytes()).hexdigest()
        self.assertEqual(digest, self.provenance["recorded_aggregate_sha256"])
        self.assertFalse(self.recorded["test_used"])
        self.assertEqual(self.recorded["validation_known_references"], 274)
        self.assertEqual(self.recorded["validation_tiles"], 1432)

    def test_metrics_class_support_and_checkpoint_hashes_agree(self):
        expected = {"A1": (84, 46), "A2": (101, 46), "A3": (99, 55)}
        by_experiment = {row["experiment"]: row for row in self.recorded["experiments"]}
        for public, (detected, correct) in expected.items():
            report = json.loads((REPORT / f"{public.lower()}_validation.json").read_text())
            row = report["primary"]
            recorded = by_experiment[common.resolve_variant(public)]
            self.assertEqual(report["method"], "A")
            self.assertEqual(report["variant"], public)
            self.assertEqual((row["detected"], row["end_to_end_correct"]), (detected, correct))
            self.assertAlmostEqual(row["known_specimen_recall_iou50"], detected / 274)
            self.assertAlmostEqual(row["end_to_end_known_specimen_success"], correct / 274)
            self.assertEqual(sum(item["support"] for item in row["per_class"]), 274)
            self.assertEqual(sum(item["detected"] for item in row["per_class"]), detected)
            self.assertEqual(sum(item["correct"] for item in row["per_class"]), correct)
            self.assertEqual(row["checkpoint_sha256"], recorded["checkpoint_sha256"])
            self.assertEqual(recorded["optimizer_steps"], 2400)
            self.assertEqual(len(report["fixed_threshold_sweep"]), 6)
            self.assertTrue(all(not item["test_used"] for item in report["fixed_threshold_sweep"]))

    def test_a2_incidental_extra_labels_are_explicit(self):
        counts = json.loads((REPORT / "dataset_counts.json").read_text())["variants"]
        self.assertEqual(
            counts["A2"]["train_known_records"] - counts["A1"]["train_known_records"], 2
        )
        self.assertEqual(counts["A3"]["train_known_records"], 1605)
        self.assertEqual(counts["A3"]["train_images"], 1423)

    def test_ast_fingerprint_ignores_optional_field_serialization(self):
        node = ast.parse("def example(): pass").body[0]
        expected = algorithm_ast_sha256(node)
        node.type_params = []
        self.assertEqual(algorithm_ast_sha256(node), expected)
        node.returns = ast.Name(id="int", ctx=ast.Load())
        self.assertNotEqual(algorithm_ast_sha256(node), expected)

    def test_selected_numerical_algorithms_match_executed_ast(self):
        for key, expected in self.provenance["unchanged_algorithm_ast_sha256"].items():
            filename, function = key.split(":")
            tree = ast.parse((CODE / filename).read_text())
            node = next(
                n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function
            )
            digest = algorithm_ast_sha256(node)
            self.assertEqual(digest, expected, key)

    def test_reports_contain_aggregates_without_row_level_payloads(self):
        forbidden = {
            "record_id",
            "record_ids",
            "train_record_ids",
            "box_slide",
            "image_nots_path",
            "annotation_nots_path",
        }

        def inspect(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)

        for path in REPORT.glob("*.json"):
            inspect(json.loads(path.read_text()))


if __name__ == "__main__":
    unittest.main()

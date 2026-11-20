"""Prevent early array completion and retain training chunk provenance."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from method_a_final_evaluation.orchestration import Controller


class SlurmControllerTests(unittest.TestCase):
    def test_partial_array_accounting_does_not_finish_export(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            controller = Controller(
                root, root / "data", root / "runs", root / "code", "100"
            )
            controller.state["jobs"] = {
                "export": {"id": "200", "array": "0-2%2", "attempts": 1}
            }
            with patch("subprocess.check_output", return_value="200_0|COMPLETED|0:0\n"):
                self.assertEqual(controller.statuses()["export"], "active")
            with patch(
                "subprocess.check_output",
                return_value="200_0|COMPLETED|0:0\n200_1|COMPLETED|0:0\n200_2|COMPLETED|0:0\n",
            ):
                self.assertEqual(controller.statuses()["export"], "done")

    def test_resume_submission_retains_prior_job_id(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            controller = Controller(
                root, root / "data", root / "runs", root / "code", "100"
            )
            controller.state["jobs"]["cv-0-model"] = {
                "id": "201",
                "attempts": 1,
                "history": [],
            }
            with patch("subprocess.check_output", return_value="202\n"):
                controller.submit("cv-0-model", ["train"], gpu=True)
            self.assertEqual(
                controller.state["jobs"]["cv-0-model"]["history"], [{"id": "201"}]
            )


if __name__ == "__main__":
    unittest.main()

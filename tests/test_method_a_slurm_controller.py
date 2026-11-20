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

    def test_running_fit_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            controller = Controller(
                root, root / "data", root / "runs", root / "code", "100"
            )
            controller.state["jobs"]["cv-0-model"] = {
                "id": "201",
                "attempts": 1,
                "short": False,
            }
            with patch(
                "subprocess.check_output", return_value="201|RUNNING|scavenge\n"
            ):
                with patch("subprocess.check_call") as mutation:
                    controller.fill_debug()
                    mutation.assert_not_called()

    def test_failed_bundle_submission_releases_pending_fit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            controller = Controller(
                root, root / "data", root / "runs", root / "code", "100"
            )
            controller.state["jobs"]["cv-0-model"] = {
                "id": "201",
                "attempts": 1,
                "short": False,
                "args": ["train"],
            }
            with patch(
                "subprocess.check_output",
                side_effect=[
                    "201|PENDING|scavenge\n",
                    RuntimeError("scheduler unavailable"),
                ],
            ):
                with patch("subprocess.check_call") as hold:
                    with patch("subprocess.run") as release:
                        with self.assertRaises(RuntimeError):
                            controller.fill_debug()
                        hold.assert_called_once_with(["scontrol", "hold", "201"])
                        release.assert_called_once_with(
                            ["scontrol", "release", "201"], check=False
                        )
            self.assertEqual(controller.state["jobs"]["cv-0-model"]["id"], "201")


if __name__ == "__main__":
    unittest.main()

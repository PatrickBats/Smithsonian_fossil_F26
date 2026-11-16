"""Aggregate held-out scan results and select a threshold without reading test."""

import collections
import hashlib
import json

from .cv import DEST, read, write
from .cv_evaluate import RESULTS, THRESHOLDS


def main():
    manifest = read(DEST / "manifest.json")
    assert len(manifest["folds"]) == 5
    output = RESULTS / "aggregate"
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    candidate_results = []
    for threshold in THRESHOLDS:
        tag = f"confidence_{threshold:.2f}"
        all_matches = []
        fold_scores = []
        checkpoint_shas = []
        for fold in range(5):
            directory = RESULTS / f"fold_{fold}"
            status = read(directory / "summary.json")
            assert status["status"] == "completed"
            summary = read(directory / f"{tag}_summary.json")
            matches = read(directory / f"{tag}_matches.json")
            assert len(matches) == summary["known_specimens"]
            all_matches.extend(matches)
            fold_scores.append(
                {
                    "fold": fold,
                    "scans": summary["held_out_scans"],
                    "known": summary["known_specimens"],
                    "detected": summary["detected"],
                    "correct": summary["correct"],
                    "success": summary["end_to_end_success"],
                    "checkpoint_sha256": summary["checkpoint_sha256"],
                }
            )
            checkpoint_shas.append(summary["checkpoint_sha256"])
        assert len(all_matches) == 540
        assert len({m["record_id"] for m in all_matches}) == 540
        assert len({m["source"] for m in all_matches}) == 20
        detected = sum(m["detected"] for m in all_matches)
        correct = sum(m["correct"] for m in all_matches)
        by_scan = collections.defaultdict(list)
        by_class = collections.defaultdict(list)
        for match in all_matches:
            by_scan[match["source"]].append(match)
            by_class[match["true_category"]].append(match)
        scan_scores = [
            {
                "source": source,
                "known": len(group),
                "detected": sum(m["detected"] for m in group),
                "correct": sum(m["correct"] for m in group),
                "success": sum(m["correct"] for m in group) / len(group),
            }
            for source, group in sorted(by_scan.items())
        ]
        class_scores = [
            {
                "category": category,
                "known": len(group),
                "slide_support": len({m["source"] for m in group}),
                "detected": sum(m["detected"] for m in group),
                "correct": sum(m["correct"] for m in group),
            }
            for category, group in sorted(by_class.items())
        ]
        result = {
            "threshold": threshold,
            "folds": fold_scores,
            "known_specimens": 540,
            "held_out_scans": 20,
            "detected": detected,
            "correct": correct,
            "micro_known_recall": detected / 540,
            "micro_end_to_end_success": correct / 540,
            "mean_scan_success": sum(x["success"] for x in scan_scores) / 20,
            "mean_fold_success": sum(x["success"] for x in fold_scores) / 5,
            "scan_scores": scan_scores,
            "class_scores": class_scores,
            "checkpoint_sha256s": checkpoint_shas,
            "test_used": False,
        }
        write(output / f"{tag}_summary.json", result)
        candidate_results.append(result)
    # All candidate thresholds are fixed before test inference.
    chosen = max(
        candidate_results,
        key=lambda r: (r["mean_scan_success"], r["micro_end_to_end_success"], r["threshold"]),
    )
    write(
        output / "selection.json",
        {
            "selection_rule": "Maximize mean held-out-scan end-to-end success; tie-break by micro success, then higher threshold.",
            "candidate_thresholds": list(THRESHOLDS),
            "selected_threshold": chosen["threshold"],
            "selected_mean_scan_success": chosen["mean_scan_success"],
            "selected_micro_success": chosen["micro_end_to_end_success"],
            "known_specimens": 540,
            "held_out_scans": 20,
            "test_used": False,
            "candidate_results": [
                {
                    "threshold": r["threshold"],
                    "detected": r["detected"],
                    "correct": r["correct"],
                    "micro_end_to_end_success": r["micro_end_to_end_success"],
                    "mean_scan_success": r["mean_scan_success"],
                }
                for r in candidate_results
            ],
        },
    )
    print(json.dumps(read(output / "selection.json"), indent=2))


if __name__ == "__main__":
    main()

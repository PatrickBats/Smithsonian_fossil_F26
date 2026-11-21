"""Cross-validation selection and one final mixed-delivery test assessment."""

import collections
import csv
import gzip
import json
from pathlib import Path

from .datasets import load_plans
from .preparation import file_sha
from .protocol import choose, digest, read, split_plans, summarize, write_new


THRESHOLDS = (0.25, 0.30, 0.40, 0.50, 0.75)
STEPS = (1200, 2400)


def predict(root, stage, run_root, results, fold=None):
    """Cache predictions; final testing accepts only the sealed CV operating point."""
    import torch
    from PIL import Image
    from rfdetr_plus.models.detection import RFDETR2XLarge
    from method_a_new_delivery.cv_evaluate import score_fold

    root, run_root, results = Path(root), Path(run_root), Path(results)
    assignment = read(root / "assignment.json")
    all_plans = load_plans(root)
    plans = split_plans(
        all_plans, assignment, "valid" if stage == "cv" else "test", fold
    )
    origin_by_source = {p["source"]: p["origin"] for p in all_plans}
    names = read(root / "categories.json")
    categories = {int(k) - 1: v for k, v in names.items()}
    tag = f"fold_{fold}" if stage == "cv" else "final"
    if stage == "cv":
        steps, thresholds = STEPS, THRESHOLDS
        destination = results / tag
    else:
        selection = read(results / "selection.json")
        if selection["assignment_digest"] != digest(assignment):
            raise ValueError("Final test partition differs from the sealed selection")
        steps, thresholds = (selection["selected"]["step"],), (
            selection["selected"]["threshold"],
        )
        destination = results / "final_test"
        if destination.exists():
            raise FileExistsError(
                "Final test was already opened; no retrospective selection allowed"
            )
        write_new(
            destination / "test_opened.json",
            {
                "selection_sha256": file_sha(results / "selection.json"),
                "assignment_digest": digest(assignment),
                "test_sources_digest": digest(sorted(p["source"] for p in plans)),
            },
        )
    train_contract = read(root / "datasets" / tag / "contract.json")
    if set(train_contract["train_groups"]) & {p["group_id"] for p in plans}:
        raise ValueError("Evaluation identity group occurs in training")
    result_rows = []
    for step in steps:
        path = run_root / tag / "model" / f"checkpoint_step_{step}.pth"
        checkpoint = file_sha(path)
        model = RFDETR2XLarge(
            pretrain_weights=str(path), num_classes=28, resolution=1000
        )
        raw, invalid = {}, 0
        for plan in plans:
            for crop in plan["crops"]:
                with Image.open(root / "images" / (crop["tile_id"] + ".png")) as image:
                    predictions = model.predict(
                        image.convert("RGB"), threshold=min(thresholds)
                    )
                rows = []
                for box, confidence, cid in zip(
                    predictions.xyxy, predictions.confidence, predictions.class_id
                ):
                    cid = int(cid)
                    if cid == 28:
                        invalid += 1
                        continue
                    if cid not in categories:
                        raise ValueError(f"Unexpected output class index {cid}")
                    rows.append(
                        {
                            "box": [float(v) for v in box],
                            "score": float(confidence),
                            "class_id": cid,
                        }
                    )
                raw[crop["tile_id"]] = rows
        destination.mkdir(parents=True, exist_ok=True)
        with gzip.open(
            destination / f"step_{step}_raw.json.gz", "xt", compresslevel=6
        ) as handle:
            json.dump(raw, handle)
        for threshold in thresholds:
            spatial, matches = score_fold(plans, raw, categories, threshold)
            summary = {
                **summarize(matches, origin_by_source),
                "step": step,
                "threshold": threshold,
                "split": "cross_validation" if stage == "cv" else "final_test",
                "fold": fold,
                "checkpoint_sha256": checkpoint,
                "assignment_digest": digest(assignment),
                "invalid_slot_predictions": invalid,
                "predictions_after_nms": spatial["predictions_after_nms"],
                "unmatched_predictions_unreviewed": spatial[
                    "unmatched_predictions_unreviewed"
                ],
                "test_used": stage == "final",
                "interpretation": "Known annotated target recovery on annotation-guided context crops; sparse labels do not establish full-scene precision or whole-slide search.",
            }
            stem = f"step_{step}_confidence_{threshold:.2f}"
            write_new(destination / (stem + "_summary.json"), summary)
            write_new(destination / (stem + "_matches.json"), matches)
            result_rows.append(summary)
        del model
        torch.cuda.empty_cache()
    write_new(
        destination / "status.json",
        {
            "status": "completed",
            "stage": stage,
            "fold": fold,
            "summaries": [
                f"step_{r['step']}_confidence_{r['threshold']:.2f}_summary.json"
                for r in result_rows
            ],
        },
    )
    return {"status": "completed", "summaries": len(result_rows), "stage": stage}


def select(root, run_root, results):
    """Seal checkpoint step/cutoff before the final model is tested."""
    root, results = Path(root), Path(results)
    plans, assignment = load_plans(root), read(root / "assignment.json")
    origins = {p["source"]: p["origin"] for p in plans}
    candidates = []
    for step in STEPS:
        for threshold in THRESHOLDS:
            matches = []
            shas = []
            for fold in range(5):
                directory = results / f"fold_{fold}"
                if read(directory / "status.json")["status"] != "completed":
                    raise ValueError("Incomplete cross-validation")
                stem = f"step_{step}_confidence_{threshold:.2f}"
                summary = read(directory / (stem + "_summary.json"))
                if summary["test_used"] or summary["assignment_digest"] != digest(
                    assignment
                ):
                    raise ValueError("Cross-validation provenance mismatch")
                matches.extend(read(directory / (stem + "_matches.json")))
                shas.append(summary["checkpoint_sha256"])
            expected = {
                o["record_id"]
                for p in split_plans(plans, assignment, "final_train")
                for o in p["objects"]
            }
            if {m["record_id"] for m in matches} != expected:
                raise ValueError(
                    "CV does not cover each development reference exactly once"
                )
            candidates.append(
                {
                    **summarize(matches, origins),
                    "step": step,
                    "threshold": threshold,
                    "split": "cross_validation",
                    "test_used": False,
                    "checkpoint_sha256s": shas,
                }
            )
    result = {
        "selected": choose(candidates),
        "candidates": candidates,
        "assignment_digest": digest(assignment),
        "protocol_sha256": file_sha(root / "protocol.json"),
        "selection_rule": "Max mean scan-level joint recovery, then pooled recovery, then higher cutoff, then earlier checkpoint step.",
        "test_used": False,
    }
    write_new(results / "selection.json", result)
    return {"selected": result["selected"], "test_used": False}


def report(root, run_root, results):
    """Publish aggregate final-test evidence; retain row-level data on NOTS."""
    root, results, run_root = Path(root), Path(results), Path(run_root)
    selection = read(results / "selection.json")
    step, confidence = selection["selected"]["step"], selection["selected"]["threshold"]
    directory = results / "final_test"
    stem = f"step_{step}_confidence_{confidence:.2f}"
    summary, matches = read(directory / (stem + "_summary.json")), read(
        directory / (stem + "_matches.json")
    )
    if read(directory / "status.json")["status"] != "completed":
        raise ValueError("Final test did not complete")
    opened = read(directory / "test_opened.json")
    if opened["selection_sha256"] != file_sha(results / "selection.json"):
        raise ValueError("Selection changed after final test opened")
    categories = list(read(root / "categories.json").values())
    counts = {c: collections.Counter() for c in categories}
    for m in matches:
        counts[m["true_category"]][
            m["predicted_category"] if m["detected"] else "Missed"
        ] += 1
    total = sum(sum(row.values()) for row in counts.values())
    correct = sum(counts[c][c] for c in categories)
    if (total, correct) != (summary["known"], summary["correct"]):
        raise ValueError("Final matrix totals disagree")
    output = results / "publication"
    output.mkdir(parents=True, exist_ok=False)
    with (output / "confusion_counts.csv").open("x", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["true_category", *categories, "Missed"])
        for c in categories:
            writer.writerow(
                [c, *(counts[c][k] for k in categories), counts[c]["Missed"]]
            )
    write_new(output / "final_summary.json", summary)
    write_new(output / "data_summary.json", read(root / "protocol.json"))
    write_new(output / "selection.json", selection)
    training_contract = read(run_root / "final" / "model" / "run_contract.json")
    membership = training_contract["partition_contract"]
    training_contract["partition_contract"] = {
        **{
            k: v
            for k, v in membership.items()
            if k not in {"train_sources", "train_groups"}
        },
        "train_sources_count": len(membership["train_sources"]),
        "train_groups_count": len(membership["train_groups"]),
        "train_sources_digest": digest(membership["train_sources"]),
        "train_groups_digest": digest(membership["train_groups"]),
    }
    write_new(output / "training_contract.json", training_contract)
    write_new(
        output / "artifact_provenance.json",
        {
            "checkpoint_sha256": summary["checkpoint_sha256"],
            "selection_sha256": file_sha(results / "selection.json"),
            "test_opened": opened,
            "test_manifest_digest": summary["assignment_digest"],
            "matrix_sha256": file_sha(output / "confusion_counts.csv"),
            "source_code_sha256": {
                str(p.relative_to(Path(__file__).parent)): file_sha(p)
                for p in sorted(Path(__file__).parent.glob("*.py"))
            },
        },
    )
    from .figures import render

    figure_counts = render(output)
    if (
        figure_counts["targets"] != summary["known"]
        or figure_counts["correct"] != summary["correct"]
    ):
        raise ValueError("Rendered figure counts differ from final results")
    return {
        "status": "published",
        "output": str(output),
        "final_test": {
            k: summary[k]
            for k in (
                "known",
                "detected",
                "correct",
                "success",
                "mean_scan_success",
                "by_origin",
            )
        },
    }

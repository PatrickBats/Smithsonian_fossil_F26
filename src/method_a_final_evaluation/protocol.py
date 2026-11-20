"""Deterministic scan grouping, model selection, and final-test access guards.

These functions require no image, GPU, or cluster dependencies. Source records
stay outside Git; only aggregate protocol and result summaries are published.
"""

import collections
import hashlib
import json
import math
import random
from pathlib import Path


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write_new(path, value):
    """Never silently replace a frozen protocol or an existing result."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _counts(plans):
    return collections.Counter(o["category"] for p in plans for o in p["objects"])


def partition(plans, seed=20261120, test_fraction=0.2, folds=5, candidates=4000):
    """Reserve whole identity groups from both deliveries before model fitting.

    Stratification uses source labels, never model predictions. Existing alias
    evidence and identical image fingerprints define indivisible scan groups.
    Rare classes confined to one group are preferentially retained for training;
    unsupported test classes are reported rather than silently removed.
    """
    plans = sorted(plans, key=lambda p: p["source"])
    if len({p["source"] for p in plans}) != len(plans):
        raise ValueError("Duplicate source identity")
    groups = collections.defaultdict(list)
    for plan in plans:
        if plan["origin"] not in {"old", "new"} or not plan["objects"]:
            raise ValueError("Each scan needs known objects and a delivery origin")
        groups[plan["group_id"]].append(plan)
    names = sorted(groups)
    if len(names) < 2 * folds:
        raise ValueError("Too few independent scan groups")
    total = _counts(plans)
    origin_total = collections.Counter(p["origin"] for p in plans)
    size = max(2, round(len(names) * test_fraction))
    rng = random.Random(seed)
    best = None
    for _ in range(candidates):
        picked = frozenset(rng.sample(names, size))
        test = [p for p in plans if p["group_id"] in picked]
        train = [p for p in plans if p["group_id"] not in picked]
        tc, rc = _counts(test), _counts(train)
        origins = collections.Counter(p["origin"] for p in test)
        if set(origins) != {"old", "new"}:
            continue
        # Class coverage has priority over matching a precise specimen fraction.
        score = 100 * sum(tc[c] > 0 and rc[c] == 0 for c in total)
        score += sum(
            ((tc[c] - test_fraction * n) / max(3, test_fraction * n)) ** 2
            for c, n in total.items()
        )
        score += 8 * sum(
            ((origins[c] - test_fraction * n) / max(1, test_fraction * n)) ** 2
            for c, n in origin_total.items()
        )
        key = (score, sorted(picked))
        if best is None or key < best[0]:
            best = (key, picked)
    if best is None:
        raise ValueError("Cannot reserve a mixed-delivery test set")
    test_groups = best[1]
    remaining = [n for n in names if n not in test_groups]
    remaining_total = _counts([p for n in remaining for p in groups[n]])
    ordered = sorted(
        remaining,
        key=lambda n: (
            -sum(
                1 / remaining_total[o["category"]]
                for p in groups[n]
                for o in p["objects"]
            ),
            -sum(len(p["objects"]) for p in groups[n]),
            digest([seed, n]),
        ),
    )
    bins = [collections.Counter() for _ in range(folds)]
    bin_sizes = [0] * folds
    assignment = {n: {"split": "test", "fold": None} for n in test_groups}
    capacity = math.ceil(len(remaining) / folds)
    for name in ordered:
        gc = _counts(groups[name])

        def cost(index):
            # Incremental normalized squared class imbalance, plus group balance.
            return (
                sum(
                    ((bins[index][c] + gc[c]) ** 2 - bins[index][c] ** 2)
                    / max(1, n / folds) ** 2
                    for c, n in remaining_total.items()
                )
                + bin_sizes[index] / capacity
            )

        index = min(
            (i for i in range(folds) if bin_sizes[i] < capacity),
            key=lambda i: (cost(i), bin_sizes[i], i),
        )
        bins[index].update(gc)
        bin_sizes[index] += 1
        assignment[name] = {"split": "development", "fold": index}
    result = {
        p["source"]: {
            **assignment[p["group_id"]],
            "group_id": p["group_id"],
            "origin": p["origin"],
        }
        for p in plans
    }
    for group in groups.values():
        if (
            len(
                {
                    (result[p["source"]]["split"], result[p["source"]]["fold"])
                    for p in group
                }
            )
            != 1
        ):
            raise AssertionError("A scan identity group crossed partitions")
    return result


def split_plans(plans, assignment, stage, fold=None):
    """Select training/CV/final-test sources with explicit access semantics."""
    if stage not in {"train", "valid", "final_train", "test"}:
        raise ValueError(stage)
    if stage in {"train", "valid"} and fold is None:
        raise ValueError("Cross-validation requires a fold")
    selected = []
    for p in plans:
        a = assignment[p["source"]]
        if stage == "test":
            include = a["split"] == "test"
        elif a["split"] == "test":
            include = False
        elif stage == "final_train":
            include = True
        elif stage == "valid":
            include = a["fold"] == fold
        else:
            include = a["fold"] != fold
        if include:
            selected.append(p)
    return selected


def choose(candidates):
    """Choose checkpoint step and cutoff from complete CV results only."""
    if not candidates or any(
        r.get("split") != "cross_validation" or r.get("test_used") is not False
        for r in candidates
    ):
        raise ValueError("Selection accepts only test-free cross-validation results")
    reference = candidates[0]["record_ids_digest"]
    if any(r["record_ids_digest"] != reference for r in candidates):
        raise ValueError("Candidate models were evaluated on different objects")
    selected = max(
        candidates,
        key=lambda r: (
            r["mean_scan_success"],
            r["correct"] / r["known"],
            r["threshold"],
            -r["step"],
        ),
    )
    return {
        k: selected[k]
        for k in (
            "step",
            "threshold",
            "mean_scan_success",
            "correct",
            "known",
            "record_ids_digest",
        )
    }


def summarize(matches, origin_by_source):
    """Count each reference once; a correct result requires location AND class."""
    if len({m["record_id"] for m in matches}) != len(matches):
        raise ValueError("Reference targets must be unique across crops")
    if not matches:
        raise ValueError("Empty assessment")
    for m in matches:
        if m["correct"] and (
            not m["detected"] or m["true_category"] != m["predicted_category"]
        ):
            raise ValueError("Correct requires both detection and matching category")

    def one(rows):
        known = len(rows)
        detected = sum(m["detected"] for m in rows)
        correct = sum(m["correct"] for m in rows)
        return {
            "known": known,
            "detected": detected,
            "correct": correct,
            "wrong_class": detected - correct,
            "missed": known - detected,
            "success": correct / known if known else None,
        }

    by_scan = collections.defaultdict(list)
    by_class = collections.defaultdict(list)
    for match in matches:
        by_scan[match["source"]].append(match)
        by_class[match["true_category"]].append(match)
    return {
        **one(matches),
        "mean_scan_success": sum(one(v)["success"] for v in by_scan.values())
        / len(by_scan),
        "scan_count": len(by_scan),
        "by_origin": {
            origin: one([m for m in matches if origin_by_source[m["source"]] == origin])
            for origin in ("old", "new")
        },
        "per_class": {
            c: {**one(rows), "scan_support": len({m["source"] for m in rows})}
            for c, rows in sorted(by_class.items())
        },
        "record_ids_digest": digest(sorted(m["record_id"] for m in matches)),
    }

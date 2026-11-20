"""Scientific final-test figures from immutable aggregate confusion counts."""

import csv
import math
from pathlib import Path


def render(folder):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import to_rgb

    folder = Path(folder)
    with (folder / "confusion_counts.csv").open(newline="") as handle:
        reader = csv.DictReader(handle)
        categories = reader.fieldnames[1:-1]
        counts = {
            row["true_category"]: {c: int(row[c]) for c in categories + ["Missed"]}
            for row in reader
        }
    order = sorted(categories, key=lambda c: (-sum(counts[c].values()), c))
    matrix = np.array(
        [[counts[c][p] for p in order + ["Missed"]] for c in order], dtype=int
    )
    colors = np.ones((*matrix.shape, 3))
    maximum = max(1, int(matrix.max()))
    for i in range(len(order)):
        for j in range(len(order) + 1):
            if matrix[i, j]:
                strength = math.log1p(int(matrix[i, j])) / math.log1p(maximum)
                hue = (
                    "#16804a" if i == j else "#6b7280" if j == len(order) else "#c24132"
                )
                colors[i, j] = (1 - strength) + np.array(to_rgb(hue)) * strength

    def label(name):
        return (
            name.removesuffix(" sp.")
            .replace("Platycaryapollenites swasticoidus", "P. swasticoidus")
            .replace("Platycarya platycarioides", "P. platycarioides")
        )

    fig, ax = plt.subplots(figsize=(20, 9), layout="constrained")
    ax.imshow(colors, aspect="auto", interpolation="nearest")
    ax.set_xticks(
        range(len(order) + 1),
        [label(c) for c in order] + ["Missed"],
        rotation=55,
        ha="right",
        rotation_mode="anchor",
        fontsize=8.5,
    )
    ax.set_yticks(
        range(len(order)),
        [f"{label(c)} (n={sum(counts[c].values())})" for c in order],
        fontsize=9,
    )
    ax.set_xticks(np.arange(-0.5, len(order) + 1, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(order), 1), minor=True)
    ax.grid(which="minor", color="#d9dee4", linewidth=0.4)
    ax.tick_params(which="minor", bottom=False, left=False)
    for i in range(len(order)):
        for j in range(len(order) + 1):
            if matrix[i, j]:
                ax.text(
                    j,
                    i,
                    str(matrix[i, j]),
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white" if matrix[i, j] >= 20 else "#17212b",
                )
    ax.set_xlabel("Predicted category", fontsize=10)
    ax.set_ylabel("True category", fontsize=10)
    fig.savefig(folder / "confusion_matrix.png", dpi=180, facecolor="white")
    fig.savefig(folder / "confusion_matrix.pdf", facecolor="white")
    plt.close(fig)
    with (folder / "per_class.csv").open("x", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "category",
                "known",
                "detected",
                "correct",
                "wrong_class",
                "missed",
                "joint_recovery",
                "main_wrong_category",
                "main_wrong_count",
            ]
        )
        for category in order:
            row = counts[category]
            total, correct, missed = sum(row.values()), row[category], row["Missed"]
            wrong = [
                (v, k) for k, v in row.items() if k not in {category, "Missed"} and v
            ]
            maximum_wrong = max(wrong) if wrong else (0, "")
            writer.writerow(
                [
                    category,
                    total,
                    total - missed,
                    correct,
                    total - missed - correct,
                    missed,
                    correct / total if total else "",
                    maximum_wrong[1],
                    maximum_wrong[0],
                ]
            )
    return {
        "targets": int(matrix.sum()),
        "correct": int(np.trace(matrix[:, : len(order)])),
        "missed": int(matrix[:, -1].sum()),
    }

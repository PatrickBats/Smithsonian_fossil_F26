"""Render the held-out confusion matrix with matching true/predicted class order."""

import argparse
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb


REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "reports" / "method_a_new_delivery_2026-11-16"


def load_counts(path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames[1:]
        rows = list(reader)
    order = [row["true_category"] for row in rows]
    assert len(order) == 16 and len(columns) == 29
    assert all(name in columns for name in order) and columns[-1] == "Missed"
    matrix = np.zeros((16, 18), dtype=int)
    for i, row in enumerate(rows):
        for j, name in enumerate(order):
            matrix[i, j] = int(row[name])
        matrix[i, 16] = sum(int(row[name]) for name in columns[:-1] if name not in order)
        matrix[i, 17] = int(row["Missed"])
    assert matrix.sum() == 540 and np.trace(matrix[:, :16]) == 304
    assert matrix[:, 17].sum() == 18
    return order, matrix


def plot(counts_path, output_path):
    order, matrix = load_counts(counts_path)
    labels = order + ["Other 12 outputs", "Missed"]
    colors = np.ones((16, 18, 3))
    maximum = int(matrix.max())
    for i in range(16):
        for j in range(18):
            count = int(matrix[i, j])
            if count:
                intensity = math.log1p(count) / math.log1p(maximum)
                hue = "#16804a" if i == j else "#6b7280" if j == 17 else "#c24132"
                colors[i, j] = (1 - intensity) + np.array(to_rgb(hue)) * intensity

    fig = plt.figure(figsize=(20.5, 10.2), layout="constrained")
    grid = fig.add_gridspec(1, 2, width_ratios=[18, 2.8], wspace=0.02)
    ax = fig.add_subplot(grid[0, 0])
    summary = fig.add_subplot(grid[0, 1])
    ax.imshow(colors, aspect="auto", interpolation="nearest")
    ax.set_xticks(range(18), labels, rotation=62, ha="right", rotation_mode="anchor", fontsize=9)
    ax.set_yticks(
        range(16), [f"{name}  (n={matrix[i].sum()})" for i, name in enumerate(order)], fontsize=9
    )
    ax.set_xlim(-0.5, 17.5)
    ax.set_ylim(15.5, -0.5)
    ax.set_xticks(np.arange(-0.5, 18, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 16, 1), minor=True)
    ax.grid(which="minor", color="#d9dee4", linewidth=0.5)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.axvline(15.5, color="#6b7280", linewidth=1.4)
    ax.axvline(16.5, color="#9ca3af", linewidth=1.0)
    for i in range(16):
        for j in range(18):
            count = int(matrix[i, j])
            if count:
                intensity = math.log1p(count) / math.log1p(maximum)
                ax.text(
                    j,
                    i,
                    str(count),
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white" if intensity > 0.65 else "#17212b",
                    fontweight="bold" if count >= 10 else "normal",
                )
    ax.set_xlabel("Predicted category", fontsize=11)
    ax.set_ylabel("True category", fontsize=11)
    ax.set_title("New scans: five-fold held-out confusion matrix", loc="left", fontsize=17, pad=22)

    summary.set_xlim(0, 1)
    summary.set_ylim(15.5, -0.5)
    summary.set_xticks([])
    summary.set_yticks([])
    for spine in summary.spines.values():
        spine.set_visible(False)
    summary.set_title("Correct / total", fontsize=10, pad=32)
    for i in range(16):
        total = int(matrix[i].sum())
        correct = int(matrix[i, i])
        summary.text(
            0.03,
            i,
            f"{correct}/{total}  ({correct/total:.0%})",
            va="center",
            fontsize=9,
            fontweight="bold" if total >= 30 else "normal",
            color="#18543a" if correct else "#a53f35",
        )
    summary.axvline(0, color="#d9dee4", linewidth=1)
    fig.suptitle(
        "20 new scans  |  540 labeled targets  |  304 correct (56.3%)  |  218 wrong class  |  18 missed",
        fontsize=12,
        y=1.01,
    )
    fig.text(
        0.5,
        -0.025,
        "Green diagonal = correct; red = wrong class; gray = missed. Darker color = more objects (log scale). Same class order on both axes; Other 12 outputs aggregates classes without new truth labels.",
        ha="center",
        va="top",
        fontsize=9,
    )
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts", type=Path, default=REPORT / "confusion_counts.csv")
    parser.add_argument("--output", type=Path, default=REPORT / "confusion_matrix.png")
    args = parser.parse_args()
    plot(args.counts, args.output)


if __name__ == "__main__":
    main()

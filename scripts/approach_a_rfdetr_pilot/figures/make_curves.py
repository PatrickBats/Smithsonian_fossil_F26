"""Validation curves for the Approach A pilot runs (static PNGs for slides)."""
import csv, sys, math
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = Path("/rhf/allocations/dsci435/Smithsonian_F26/model_A/runs")
OUT = Path("/rhf/allocations/dsci435/Smithsonian_F26/model_A/figures"); OUT.mkdir(exist_ok=True)
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
S = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # reference categorical slots 1-4, fixed order

def load(p):
    rows = list(csv.DictReader(open(p)))
    by = {}
    for r in rows:
        if r.get("val/mAP_50_95") or r.get("val/AP/Bisaccate") or r.get("val/ema_mAP_50_95"):
            by[int(r["epoch"])] = {**by.get(int(r["epoch"]), {}), **{k: v for k, v in r.items() if v != ""}}
    return [by[e] for e in sorted(by)]

def f(r, k):
    try: return float(r[k])
    except Exception: return math.nan

def style(ax, title, ylab):
    ax.set_facecolor(SURF); ax.figure.set_facecolor(SURF)
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]: ax.spines[s].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    ax.tick_params(colors=INK2, labelsize=11)
    ax.set_title(title, loc="left", color=INK, fontsize=14, pad=12, fontweight="bold")
    ax.set_xlabel("Epoch", color=INK2, fontsize=11); ax.set_ylabel(ylab, color=INK2, fontsize=11)

def endlabel(ax, xs, ys, text, color):
    pts = [(x, y) for x, y in zip(xs, ys) if not math.isnan(y)]
    if pts:
        x, y = pts[-1]
        ax.plot([x], [y], "o", color=color, markersize=8, markeredgecolor=SURF, markeredgewidth=2, zorder=5)
        ax.annotate(text, (x, y), xytext=(8, 0), textcoords="offset points", va="center", color=INK, fontsize=11)

# Figure 1: per-class validation AP over epochs, Large multiclass
rows = load(R / "A1_pilot_large_bestplane/multiclass_top2/metrics.csv")
fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
for (k, lab), c in zip([("val/AP/Bisaccate", "Bisaccate"), ("val/AP/Momipites sp", "Momipites sp"), ("val/AP/other_palynomorph", "Other palynomorph")], [S[1], S[0], S[2]]):
    xs = [int(r["epoch"]) for r in rows]; ys = [f(r, k) for r in rows]
    ax.plot(xs, ys, color=c, linewidth=2, label=lab); endlabel(ax, xs, ys, lab, c)
style(ax, "RF-DETR Large (multiclass): validation AP by category", "AP@50:95")
ax.set_ylim(0, 0.7); ax.legend(frameon=False, loc="upper left", fontsize=11, labelcolor=INK)
ax.margins(x=0.02); plt.subplots_adjust(right=0.82)
fig.savefig(OUT / "curve_per_class_large.png", bbox_inches="tight", facecolor=SURF); plt.close(fig)

# Figure 2: overall validation mAP per run
runs = [("A1_pilot_large_bestplane/multiclass_top2", "Large · 3-class"),
        ("A1_pilot_large_bestplane/single_class", "Large · 1-class (detection ref.)"),
        ("A1_pilot_top2_bestplane/init_sp26_detector", "2XL · 3-class, from Sp26 detector"),
        ("A1_pilot_top2_bestplane/init_coco", "2XL · 3-class, from general weights")]
fig, ax = plt.subplots(figsize=(9, 5), dpi=160)
for (d, lab), c in zip(runs, S):
    p = R / d / "metrics.csv"
    if not p.exists(): continue
    rows = load(p); xs = [int(r["epoch"]) for r in rows]
    key = "val/mAP_50_95" if any("val/mAP_50_95" in r for r in rows) else "val/ema_mAP_50_95"
    ys = [f(r, key) for r in rows]
    ax.plot(xs, ys, color=c, linewidth=2, label=lab)
    good = [(x, y) for x, y in zip(xs, ys) if not math.isnan(y)]
    bx, by = max(good, key=lambda t: t[1])
    ax.plot([bx], [by], "o", color=c, markersize=8, markeredgecolor=SURF, markeredgewidth=2, zorder=5)
    ax.annotate(f"best {by:.2f}", (bx, by), xytext=(0, 9), textcoords="offset points", ha="center", color=INK, fontsize=10.5)
style(ax, "Validation mAP@50:95 by run (marker = best epoch)", "mAP@50:95")
ax.set_ylim(0, 0.7); ax.legend(frameon=False, loc="lower right", fontsize=10.5, labelcolor=INK)
fig.savefig(OUT / "curve_runs.png", bbox_inches="tight", facecolor=SURF); plt.close(fig)
print("ok")

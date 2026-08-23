#!/usr/bin/env python3
"""Figure 3 v3.2: (a) clear+subtle score drop, (b) sham-adjusted pref, (c) judge×human scatter."""
import json, re
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

CLEAR = json.loads((Path(__file__).resolve().parent.parent.parent / "results" / "diagnostics/lit2test_targeted_corruption_20x3_20260721.json").read_text())
SUBTLE = json.loads((Path(__file__).resolve().parent.parent.parent / "results" / "diagnostics/lit2test_targeted_subtle_corruption_20x3x2_sham_20260722.json").read_text())
MAIN = json.loads((Path(__file__).resolve().parent.parent.parent / "results" / "main/lit2test_corrected_gemini_main_results.json").read_text())
HUMAN_MD = (Path(__file__).resolve().parent.parent.parent / "results" / "human_study/lit2test_human_results_20260721_zh.md").read_text()

DIMS = ["grounding", "decisive_metric", "falsifiability"]
DIM_SHORT = ["Ground.", "Dec.\nmetric", "Falsif."]
MODELS = ["GPT 5.2", "Claude-Sonnet-4.6", "GLM-5", "DeepSeek-V3.2"]
TEAL, ORANGE, GRAY, INK = "#0173B2", "#DE8F05", "#8A8A8A", "#333333"
DIM_COLORS = ["#0173B2", "#029E73", "#D55E00"]
MODEL_COLORS = ["#0173B2", "#029E73", "#D55E00", "#DE8F05"]
MODEL_MARKERS = ["o", "s", "^", "D"]

plt.rcParams.update({"font.size": 8, "axes.labelsize": 8, "axes.titlesize": 9,
                      "font.family": "sans-serif", "axes.spines.top": False,
                      "axes.spines.right": False})

fig, axes = plt.subplots(1, 3, figsize=(7.2, 1.85),
                         gridspec_kw={"width_ratios": [2.2, 1.6, 1.6], "wspace": 0.45})

# ---- (a) score drop: 3 groups × 2 bars, legend OUTSIDE top ----
ax = axes[0]
x = np.arange(len(DIMS))
w = 0.32
for i, d in enumerate(DIMS):
    cd = CLEAR["dimensions"][d]["target_score_drop"]
    sd = SUBTLE["dimensions"][d]["subtle_target_score_drop"]
    col = DIM_COLORS[i]
    ce = [cd["mean"] - cd["mean_ci95"][0], cd["mean_ci95"][1] - cd["mean"]]
    se = [sd["mean"] - sd["mean_ci95"][0], sd["mean_ci95"][1] - sd["mean"]]
    b1 = ax.bar(i - w/2, cd["mean"], w, color=col, edgecolor="white", lw=0.5, zorder=2)
    ax.errorbar(i - w/2, cd["mean"], yerr=[[ce[0]], [ce[1]]], fmt="none", ecolor=INK, capsize=2, lw=0.8, zorder=3)
    ax.text(i - w/2, cd["mean"] + ce[1] + 0.06, f"{cd['mean']:.2f}", ha="center", va="bottom", fontsize=5.5, color=INK)
    b2 = ax.bar(i + w/2, sd["mean"], w, color=col, edgecolor="white", lw=0.5, alpha=0.45, hatch="//", zorder=2)
    ax.errorbar(i + w/2, sd["mean"], yerr=[[se[0]], [se[1]]], fmt="none", ecolor=INK, capsize=2, lw=0.8, zorder=3)
    ax.text(i + w/2, sd["mean"] + se[1] + 0.06, f"{sd['mean']:.2f}", ha="center", va="bottom", fontsize=5.5, color=INK)

ax.set_xticks(x)
ax.set_xticklabels(DIM_SHORT, fontsize=7)
ax.set_ylabel("Target-score drop (0\u20134)")
ax.set_ylim(0, 2.65)
ax.set_title("(a) Targeted corruption (n = 20)", pad=3)
from matplotlib.patches import Patch
leg = ax.legend([Patch(facecolor=GRAY, edgecolor="white"),
                 Patch(facecolor=GRAY, alpha=0.45, hatch="//", edgecolor=GRAY)],
                ["Clear", "Subtle"], fontsize=6, frameon=False,
                loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.0),
                handlelength=1.2, handletextpad=0.3, columnspacing=0.8)

# ---- (b) sham-adjusted preference ----
ax = axes[1]
adj_means, adj_errs = [], []
for d in DIMS:
    ap = SUBTLE["dimensions"][d]["primary_adjusted_preference"]
    adj_means.append(ap["mean"])
    adj_errs.append([ap["mean"] - ap["mean_ci95"][0], ap["mean_ci95"][1] - ap["mean"]])

ax.bar(x, adj_means, 0.55, color=DIM_COLORS, edgecolor="white", lw=0.5, zorder=2)
ax.errorbar(x, adj_means, yerr=np.array(adj_errs).T, fmt="none", ecolor=INK, capsize=3, lw=0.8, zorder=3)
for i, (m, e) in enumerate(zip(adj_means, adj_errs)):
    ax.text(i, m + e[1] + 0.02, f"{m:.2f}", ha="center", va="bottom", fontsize=5.5, color=INK)
ax.set_xticks(x)
ax.set_xticklabels(DIM_SHORT, fontsize=7)
ax.set_ylabel("Sham-adj. preference")
ax.set_ylim(0, 1.0)
ax.set_title("(b) Subtle: net of sham", pad=3)

# ---- (c) judge BT vs human win rate — broken axes ----
ax = axes[2]
judge_bt = MAIN["corrected"]["folded"]["bt_centered_log_ability"]

name_map = {"GPT 5.2": "GPT 5.2", "Sonnet": "Claude-Sonnet-4.6", "GLM-5": "GLM-5", "DeepSeek": "DeepSeek-V3.2"}
h2h_table = re.findall(r"\|\s*(GPT 5\.2|Sonnet|GLM-5|DeepSeek)\s+vs\s+(.*?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", HUMAN_MD)
wins = {m: 0.0 for m in MODELS}
total = {m: 0.0 for m in MODELS}
for row in h2h_table:
    m1 = name_map[row[0]]
    m2 = None
    for k, v in name_map.items():
        if k in row[1].strip(): m2 = v; break
    w1, w2, tie, n = int(row[2]), int(row[3]), int(row[4]), int(row[5])
    wins[m1] += w1 + tie * 0.5; wins[m2] += w2 + tie * 0.5
    total[m1] += n; total[m2] += n
human_wr = {m: wins[m] / total[m] for m in MODELS}

# BT values: GPT 1.26, Sonnet 0.74, GLM -0.73, DS -1.27
# Human WR:  GPT ~0.80, Sonnet ~0.77, GLM ~0.23, DS ~0.21
# Two clusters: top-right and bottom-left. Break both axes to close the gap.
# x break: (-0.3, 0.3)   y break: (0.40, 0.65)

# Instead of true broken axes (complex), use tight limits + annotate gap
ax.set_xlim(-1.55, 1.55)
ax.set_ylim(0.10, 0.90)

model_display = ["GPT-5.2", "Sonnet 4.6", "GLM-5", "DS-V3.2"]
for i, m in enumerate(MODELS):
    ax.scatter(judge_bt[m], human_wr[m], color=MODEL_COLORS[i], s=55, zorder=3,
               edgecolors="white", lw=0.5, marker=MODEL_MARKERS[i])

for i, (m, disp) in enumerate(zip(MODELS, model_display)):
    bx, by = judge_bt[m], human_wr[m]
    if i == 0:  # GPT
        ax.annotate(disp, (bx, by), xytext=(0, -7), textcoords="offset points",
                    fontsize=6.5, color=INK, ha="center", va="top")
    elif i == 1:  # Sonnet — extra low
        ax.annotate(disp, (bx, by), xytext=(0, -10), textcoords="offset points",
                    fontsize=6.5, color=INK, ha="center", va="top")
    elif i == 2:  # GLM — extra high
        ax.annotate(disp, (bx, by), xytext=(0, 9), textcoords="offset points",
                    fontsize=6.5, color=INK, ha="center", va="bottom")
    else:  # DS
        ax.annotate(disp, (bx, by), xytext=(0, 6), textcoords="offset points",
                    fontsize=6.5, color=INK, ha="center", va="bottom")

# tier separator
ax.axhline(0.5, color=GRAY, lw=0.5, ls=":", zorder=0, alpha=0.6)
ax.axvline(0, color=GRAY, lw=0.5, ls=":", zorder=0, alpha=0.6)

ax.set_xlabel("Judge BT (stable)")
ax.set_ylabel("Human majority\nwin rate")
ax.set_title("(c) Judge \u00d7 human", pad=3)

fig.subplots_adjust(bottom=0.24, top=0.86, left=0.07, right=0.97)
fig.savefig(str(Path(__file__).with_name("figure3_rerun.pdf")))
fig.savefig(str(Path(__file__).with_name("figure3_rerun.png")), dpi=300)
print("saved fig3_v3.2")

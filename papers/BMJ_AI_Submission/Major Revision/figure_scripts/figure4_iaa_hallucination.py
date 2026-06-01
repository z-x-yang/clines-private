"""Figure 4 (revision) — IAA + Hallucination panels (Nature-style).

4-panel composite:
  A: Per-note IAA on the cross-annotation subset (6 notes, 3 per dataset):
     mention F1, assertion Cohen's κ, value exact-match.
  B: Rule-trigger breakdown (which of the 5 pre-specified guideline rules
     fired on how many candidate-mention rows).
  C: 7-class hallucination taxonomy (extrapolated population-level %) from
     EXP-E2 stratified manual judging of N=700 candidate FPs.
  D: True hallucination (sum of 6 categories) vs annotation-gap
     (not_an_error) split.

Output: ../figures/figure4.pdf
Reads:  data/hallucination_categories.json
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = (HERE / "../figures/figure4.pdf").resolve()

# ---------------------------------------------------------------------------
# Nature-style aesthetics
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif", "Liberation Serif"],
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 11,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "legend.frameon": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titleweight": "normal",
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "pdf.fonttype": 42,
})


def panel_label(ax, letter, title, dy=1.14, letter_size=14, title_size=11,
                title_offset=0.075):
    """Fig 3-style panel label: bold uppercase letter, regular-weight title."""
    ax.text(-0.005, dy, letter, transform=ax.transAxes,
            fontsize=letter_size, fontweight="bold",
            va="bottom", ha="left", color="black")
    ax.text(title_offset, dy, title, transform=ax.transAxes,
            fontsize=title_size, fontweight="normal",
            va="bottom", ha="left", color="black")

# Wong colorblind-safe palette (Wong B., Nat Methods 2011, "Color blindness").
C_PRE = "#9CA3AF"       # neutral gray for pre-guideline
C_POST = "#0072B2"      # Wong blue
C_F1 = "#009E73"        # Wong bluish green
C_KAPPA = "#CC79A7"     # Wong reddish purple
C_PABAK = "#E69F00"     # Wong orange
C_4CE = "#56B4E9"       # Wong sky blue
C_CORAL = "#D55E00"     # Wong vermillion

PALETTE_HALLUC = {
    "not_an_error":        "#9CA3AF",
    "wrong_code":          "#D55E00",
    "wrong_assertion":     "#E69F00",
    "wrong_value":         "#009E73",
    "span_boundary_error": "#CC79A7",
    "fabricated_entity":   "#56B4E9",
    "wrong_date":          "#0072B2",
}

LABEL_HALLUC = {
    "not_an_error":        "Not an error\n(annotation gap)",
    "wrong_code":          "Wrong code",
    "wrong_assertion":     "Wrong assertion",
    "wrong_value":         "Wrong value",
    "span_boundary_error": "Span-boundary\nerror",
    "fabricated_entity":   "Fabricated entity",
    "wrong_date":          "Wrong date",
}

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
halluc = json.loads((DATA / "hallucination_categories.json").read_text())

# Map the 6 paper-canonical notes to F1 / assertion κ / value-match (kept-by-both),
# pulled from the EXP-A2 per-note breakdown. This mirrors the new Supplementary
# Table S5 reporting (mention F1; assertion κ; value match).
_panelA_rows = [
    # (dataset, note, F1,    assertion_kappa, value_match)
    ("4CE",   "report03",    0.889, 0.842, 0.717),
    ("4CE",   "report04",    0.807, 0.860, 0.717),
    ("4CE",   "KUMC_7",      0.662, 0.773, 0.669),
    ("CORAL", "pdac_17",     0.901, 0.664, 0.839),
    ("CORAL", "pdac_7",      0.845, 0.940, 0.662),
    ("CORAL", "pdac_14",     0.785, 0.900, 0.679),
]
top6 = pd.DataFrame(_panelA_rows, columns=["dataset", "note", "F1", "assertion_kappa", "value_match"])

# ---------------------------------------------------------------------------
# Figure layout — 2x2 panels, ~7" x 6"
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(8.6, 7.0))
gs = fig.add_gridspec(2, 2, hspace=0.50, wspace=0.40,
                      left=0.08, right=0.97, top=0.93, bottom=0.10)

# ===========================================================================
# Panel A — Per-note IAA metrics (post-rule)
# ===========================================================================
axA = fig.add_subplot(gs[0, 0])

x = np.arange(len(top6))
w = 0.27
b1 = axA.bar(x - w, top6["F1"], w, label="Mention F1",
             color=C_F1, edgecolor="white", linewidth=0.4)
b2 = axA.bar(x,     top6["assertion_kappa"], w, label="Assertion $\\kappa$",
             color=C_KAPPA, edgecolor="white", linewidth=0.4)
b3 = axA.bar(x + w, top6["value_match"], w, label="Value match",
             color=C_PABAK, edgecolor="white", linewidth=0.4)

axA.axhline(y=0.81, linestyle=":", linewidth=0.6, color="#6b7280", zorder=0)

axA.set_xticks(x)
labels = [f"{r['note']} ({r['dataset']})" for _, r in top6.iterrows()]
axA.set_xticklabels(labels, fontsize=6.5, rotation=30, ha="right", rotation_mode="anchor")
axA.set_ylim(0, 1.18)
axA.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
axA.set_ylabel("Inter-annotator agreement")
panel_label(axA, "A", "IAA per note (cross-annotation subset)")
axA.legend(loc="upper center", ncol=3, columnspacing=1.0, handletextpad=0.3,
           bbox_to_anchor=(0.5, 1.06))

# ===========================================================================
# Panel B — Rule trigger breakdown (donut/stacked-horizontal)
# ===========================================================================
axB = fig.add_subplot(gs[0, 1])

rule_data = [
    ("B1c: Header-like type +\nNot associated/Absent", 290, "#CC79A7"),
    ("B1: Section header\n(mention match)",            93, "#56B4E9"),
    ("A1: Non-clinical UMLS\ntype (blacklist)",        89, "#009E73"),
    ("B2: Drug brand/generic\nduplicate",              65, "#E69F00"),
    ("B3: Standalone severity\nadjective",             15, "#D55E00"),
]
labels_B = [r[0] for r in rule_data]
counts_B = [r[1] for r in rule_data]
colors_B = [r[2] for r in rule_data]
total_B = sum(counts_B)

y_pos = np.arange(len(labels_B))[::-1]
axB.barh(y_pos, counts_B, color=colors_B, edgecolor="white", linewidth=0.4)
axB.set_yticks(y_pos)
axB.set_yticklabels(labels_B, fontsize=6.5)
axB.set_xlabel("Candidate-mention rows fired")
for yi, ci in zip(y_pos, counts_B):
    axB.text(ci + total_B * 0.01, yi, f"{ci}  ({100*ci/total_B:.1f}%)",
             va="center", fontsize=6.5, color="#374151")
panel_label(axB, "B", "Pre-specified rule triggers (n=552)")
axB.set_xlim(0, max(counts_B) * 1.30)

# ===========================================================================
# Panel C — 7-class hallucination taxonomy
# ===========================================================================
axC = fig.add_subplot(gs[1, 0])

pct = halluc["extrapolated_judge_pct_of_fp"]
order = ["not_an_error", "wrong_code", "wrong_assertion", "wrong_value",
         "span_boundary_error", "fabricated_entity", "wrong_date"]
vals = [pct[k] for k in order]
cols = [PALETTE_HALLUC[k] for k in order]
labs = [LABEL_HALLUC[k] for k in order]

y_pos = np.arange(len(order))[::-1]
bars = axC.barh(y_pos, vals, color=cols, edgecolor="white", linewidth=0.4)
axC.set_yticks(y_pos)
axC.set_yticklabels(labs, fontsize=6.5)
axC.set_xlabel("% of candidate false positives (extrapolated)")
axC.set_xlim(0, max(vals) * 1.20)
axC.axvline(x=20, linestyle=":", linewidth=0.6, color="#6b7280", zorder=0)
for yi, vi in zip(y_pos, vals):
    axC.text(vi + 1.5, yi, f"{vi:.1f}%", va="center", fontsize=6.5, color="#374151")
panel_label(axC, "C", "Hallucination taxonomy on candidate FPs")

# ===========================================================================
# Panel D — True-error vs Not-an-error split (donut)
# ===========================================================================
axD = fig.add_subplot(gs[1, 1])

true_pct = sum(pct[k] for k in pct if k != "not_an_error")
gap_pct = pct["not_an_error"]
sizes = [gap_pct, true_pct]
labels_D = [f"Annotation gap\n{gap_pct:.1f}%",
            f"True hallucination\n{true_pct:.1f}%"]
colors_D = ["#9CA3AF", "#D55E00"]

wedges, texts = axD.pie(sizes, colors=colors_D, startangle=90,
                        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.5),
                        counterclock=False)
axD.text(0, 1.30, labels_D[0], fontsize=7, ha="center", va="center", color="#374151")
axD.text(0, -1.30, labels_D[1], fontsize=7, ha="center", va="center", color="#7f1d1d")
axD.text(0, 0, f"{halluc['total_fp_population']:,}\ncandidate\nFPs",
         ha="center", va="center", fontsize=8, fontweight="bold", color="#111827")
panel_label(axD, "D", "Gap vs true hallucination")
axD.set_xlim(-1.5, 1.5)
axD.set_ylim(-1.55, 1.55)
axD.set_aspect("equal")

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT)
fig.savefig(OUT.with_suffix(".png"))   # PNG preview for quick inspection
print(f"wrote {OUT}")
print(f"wrote {OUT.with_suffix('.png')}")

"""Figure 4 (revision) — IAA + Hallucination panels (Nature-style).

4-panel composite:
  A: Per-note IAA metrics (F1 / Cohen's κ / PABAK) on the cross-annotation
     subset (6 notes, 3 per dataset), pre vs post structural-disambiguation
     guideline reconciliation.
  B: Rule-trigger breakdown (which of the 5 pre-specified guideline rules
     fired on how many candidate-mention rows).
  C: 7-class hallucination taxonomy (extrapolated population-level %) from
     EXP-E2 stratified manual judging of N=700 candidate FPs.
  D: True hallucination (sum of 6 categories) vs annotation-gap
     (not_an_error) split.

Output: ../figures/figure4.pdf
Reads:  data/iaa_per_note.csv, data/hallucination_categories.json
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
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 9,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "legend.frameon": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titleweight": "bold",
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "pdf.fonttype": 42,
})

# Muted, colorblind-safe palette (Nature/Lancet-leaning)
C_PRE = "#9CA3AF"       # neutral gray for pre-guideline
C_POST = "#2B6CB0"      # muted blue
C_F1 = "#4F8A6E"        # muted teal-green
C_KAPPA = "#7E6BA9"     # muted violet
C_PABAK = "#C08A4E"     # muted amber
C_4CE = "#4A88B9"       # muted sky
C_CORAL = "#B25C5C"     # muted red

PALETTE_HALLUC = {
    "not_an_error":        "#9CA3AF",
    "wrong_code":          "#B25C5C",
    "wrong_assertion":     "#C08A4E",
    "wrong_value":         "#4F8A6E",
    "span_boundary_error": "#7E6BA9",
    "fabricated_entity":   "#4A88B9",
    "wrong_date":          "#A56A8C",
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
iaa_df = pd.read_csv(DATA / "iaa_per_note.csv")
halluc = json.loads((DATA / "hallucination_categories.json").read_text())

# Top-3 per dataset by κ_post (matches paper-reported subset)
top6 = (iaa_df.sort_values(["dataset", "kappa_post"], ascending=[True, False])
              .groupby("dataset", sort=False).head(3)
              .reset_index(drop=True))

# Order: 4CE first then CORAL (left → right)
top6["order_key"] = top6["dataset"].map({"4CE": 0, "CORAL": 1}) * 100 - top6["kappa_post"] * 0
top6 = top6.sort_values(["order_key", "kappa_post"], ascending=[True, False]).reset_index(drop=True)

# ---------------------------------------------------------------------------
# Figure layout — 2x2 panels, ~7" x 6"
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(8.0, 7.6))
gs = fig.add_gridspec(2, 2, hspace=0.65, wspace=0.45,
                      left=0.08, right=0.96, top=0.93, bottom=0.10)

# ===========================================================================
# Panel A — Per-note IAA metrics (post-rule)
# ===========================================================================
axA = fig.add_subplot(gs[0, 0])

x = np.arange(len(top6))
w = 0.27
b1 = axA.bar(x - w, top6["f1_post"], w, label="F1", color=C_F1, edgecolor="white", linewidth=0.4)
b2 = axA.bar(x,     top6["kappa_post"], w, label="Cohen's κ", color=C_KAPPA, edgecolor="white", linewidth=0.4)
b3 = axA.bar(x + w, top6["pabak_post"], w, label="PABAK", color=C_PABAK, edgecolor="white", linewidth=0.4)

axA.axhline(y=0.6, linestyle=":", linewidth=0.6, color="#6b7280", zorder=0)

axA.set_xticks(x)
labels = [f"{r['note']} ({r['dataset']})" for _, r in top6.iterrows()]
axA.set_xticklabels(labels, fontsize=6.5, rotation=30, ha="right", rotation_mode="anchor")
axA.set_ylim(0, 1.0)
axA.set_ylabel("Inter-annotator agreement")
axA.set_title("a   IAA per note (post-guideline)", loc="left", fontsize=9, pad=10)
axA.legend(loc="upper right", ncol=3, columnspacing=0.8, handletextpad=0.3,
           bbox_to_anchor=(1.0, 1.18))

# ===========================================================================
# Panel B — Rule trigger breakdown (donut/stacked-horizontal)
# ===========================================================================
axB = fig.add_subplot(gs[0, 1])

rule_data = [
    ("B1c: Header-like type + Notassociated/Absent", 290, "#7E6BA9"),
    ("B1: Section header (mention match)",            93, "#4A88B9"),
    ("A1: Non-clinical UMLS type (blacklist)",        89, "#4F8A6E"),
    ("B2: Drug brand/generic duplicate",              65, "#C08A4E"),
    ("B3: Standalone severity adjective",             15, "#B25C5C"),
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
axB.set_title("b   Pre-specified rule triggers (n=552)",
              loc="left", fontsize=9, pad=10)
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
axC.set_title("c   Hallucination taxonomy on candidate FPs",
              loc="left", fontsize=9, pad=10)

# ===========================================================================
# Panel D — True-error vs Not-an-error split (donut)
# ===========================================================================
axD = fig.add_subplot(gs[1, 1])

true_pct = sum(pct[k] for k in pct if k != "not_an_error")
gap_pct = pct["not_an_error"]
sizes = [gap_pct, true_pct]
labels_D = [f"Annotation gap\n{gap_pct:.1f}%",
            f"True hallucination\n{true_pct:.1f}%"]
colors_D = ["#9CA3AF", "#B25C5C"]

wedges, texts = axD.pie(sizes, colors=colors_D, startangle=90,
                        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.5),
                        counterclock=False)
axD.text(0, 1.30, labels_D[0], fontsize=7, ha="center", va="center", color="#374151")
axD.text(0, -1.30, labels_D[1], fontsize=7, ha="center", va="center", color="#7f1d1d")
axD.text(0, 0, f"{halluc['total_fp_population']:,}\ncandidate\nFPs",
         ha="center", va="center", fontsize=8, fontweight="bold", color="#111827")
axD.set_title("d   Gap vs true hallucination",
              loc="left", fontsize=9, pad=10)
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

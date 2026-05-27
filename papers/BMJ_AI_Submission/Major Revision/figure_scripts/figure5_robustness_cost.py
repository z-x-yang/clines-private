"""Figure 5 (revision) — Robustness + Cost panels (Nature-style).

4-panel composite answering the reviewers' two largest methodological asks:
transparent cost/compute accounting (R5 cost omission) and component-level
ablation justifying the architecture (R5 A1 / R1).

  a: Code F1 with bootstrap 95% CI (primary comparison) — CLINES (GPT-4o)
     vs full-pipeline LLM backbones (DeepSeek, Llama-3.1-405B, o3-mini)
     across the three annotated datasets. Directly answers R1.2's CI ask;
     the assert/value/unit multi-metric breakdown lives in the Supp table.
  b: Per-note cost in dual 口径 — API $/note for hosted LLMs (CLINES GPT-4o,
     o3-mini) and GPU-h/note for self-hosted local models (Llama-3.1-405B-FP8,
     DeepSeek-R1-32B). The two billing units are not same-axis comparable, so
     the panel is split. Source: EXP-D cost table §8.1. (R1 M5 / R4 C4 / R5)
  c: Component ablation — ΔF1 when each module (SapBERT, semantic chunking,
     date module, step-4 reconcile) is removed. [PENDING: EXP-G / EXP-G2]
  d: Architecture vs alternatives, split by metric — mention F1 (left, where
     fine-tuned DL encoders compete) and code F1 (right, only normalization-
     capable systems). Systems: CLINES, o3-mini single-prompt, GPT-4o CoT,
     BERT-base, GatorTron. DL encoders emit no UMLS codes (code F1 = 0).
     Mean over 3 datasets, whiskers = min-max. (R1.7 / R3.8 / R5 A1 / A4)

Output: ../figures/figure5.pdf (+ .png preview)
Reads:  data/metrics_with_ci.json (EXP-BC), data/cost_5b.csv (EXP-D),
        data/ablation_f1.csv (EXP-G/G2), data/panel5d.csv (EXP-F + EXP-H)
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = (HERE / "../figures/figure5.pdf").resolve()

# ---------------------------------------------------------------------------
# Nature-style aesthetics (shared with figure4)
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
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

C_CLINES = "#1f6feb"   # vivid blue — CLINES main (GPT-4o)
C_DEEPSEEK = "#10b981"  # emerald
C_LLAMA = "#f59e0b"     # amber
C_O3MINI = "#7c3aed"    # violet
C_COT = "#ef4444"       # red

DATASETS = [("4CE", "4CE"), ("coral_breastca", "CORAL-B"), ("coral_pdac", "CORAL-P")]

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
ci = json.loads((DATA / "metrics_with_ci.json").read_text())


# ---------------------------------------------------------------------------
# Figure layout — 2x2, ~7.2" x 6"
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(7.2, 6.0))
gs = fig.add_gridspec(2, 2, hspace=0.50, wspace=0.30,
                      left=0.08, right=0.97, top=0.93, bottom=0.09)

# ===========================================================================
# Panel A — Code F1 with bootstrap 95% CI (primary comparison) — answers R1.2.
# Per-dataset point F1 + asymmetric bootstrap CI from metrics_with_ci.json.
# (Multi-metric assert/value/unit breakdown lives in the Supp table.)
# ===========================================================================
axA = fig.add_subplot(gs[0, 0])

models_A = [("gpt4o", "CLINES (GPT-4o)", C_CLINES),
            ("deepseek", "DeepSeek", C_DEEPSEEK),
            ("llama", "Llama-3.1-405B", C_LLAMA),
            ("o3mini", "o3-mini", C_O3MINI)]
x = np.arange(len(DATASETS))
n_m = len(models_A)
w = 0.20
for j, (mkey, mlabel, mcol) in enumerate(models_A):
    pts, los, his = [], [], []
    for ds_key, _ in DATASETS:
        leaf = ci["results"][mkey][ds_key]["code"]["f1"]
        pt = leaf["point"]
        pts.append(pt); los.append(pt - leaf["ci_lo"]); his.append(leaf["ci_hi"] - pt)
    off = (j - (n_m - 1) / 2) * w
    axA.bar(x + off, pts, w, label=mlabel, color=mcol,
            edgecolor="white", linewidth=0.4, zorder=2)
    axA.errorbar(x + off, pts, yerr=[los, his], fmt="none",
                 ecolor="#374151", elinewidth=0.7, capsize=1.8, capthick=0.7, zorder=3)

axA.set_xticks(x)
axA.set_xticklabels([d[1] for d in DATASETS])
axA.set_ylim(0, 1.0)
axA.set_ylabel("Code F1 (95% CI)")
axA.set_title("a   Primary comparison with bootstrap 95% CI", loc="left", fontsize=9, x=-0.10, y=1.02)
axA.legend(loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.40),
           columnspacing=1.0, handletextpad=0.3)

# ===========================================================================
# Panel B — Cost per note (dual 口径: API $/note for hosted models,
# GPU-h/note for self-hosted local models — the two cannot share an axis).
# Data: EXP-D cost table §8.1. Bars = mean over 3 datasets; whiskers = min-max.
# ===========================================================================
cost = pd.read_csv(DATA / "cost_5b.csv")
gsB = gs[0, 1].subgridspec(1, 2, wspace=0.55)
axB1 = fig.add_subplot(gsB[0, 0])   # API $/note
axB2 = fig.add_subplot(gsB[0, 1])   # GPU-h/note
COST_COL = {"CLINES (GPT-4o)": C_CLINES, "o3-mini": C_O3MINI,
            "Llama-3.1-405B": C_LLAMA, "DeepSeek-R1-32B": C_DEEPSEEK}
COST_LBL = {"CLINES (GPT-4o)": "CLINES\n(GPT-4o)", "o3-mini": "o3-mini",
            "Llama-3.1-405B": "Llama\n405B", "DeepSeek-R1-32B": "DeepSeek\n32B"}

for ax, fam, ylab in [(axB1, "api", "API $ / note"), (axB2, "local", "GPU-h / note")]:
    sub = cost[cost.family == fam].reset_index(drop=True)
    xb = np.arange(len(sub))
    for k, row in sub.iterrows():
        lo_err = row["mean"] - row["lo"]
        hi_err = row["hi"] - row["mean"]
        ax.bar(k, row["mean"], 0.62, color=COST_COL[row["model"]],
               edgecolor="white", linewidth=0.4, zorder=2)
        ax.errorbar(k, row["mean"], yerr=[[lo_err], [hi_err]], fmt="none",
                    ecolor="#374151", elinewidth=0.7, capsize=1.8, capthick=0.7, zorder=3)
    ax.set_xticks(xb)
    ax.set_xticklabels([COST_LBL[m] for m in sub.model], fontsize=5.8)
    ax.set_ylabel(ylab, fontsize=7)
    ax.margins(x=0.22)

axB1.set_title("b   Per-note cost (hosted $ vs local GPU-h)", loc="left",
               fontsize=9, x=-0.22, y=1.02)
axB1.text(0.0, -0.34,
          "Hosted LLMs billed in API $; self-hosted in GPU-h — not same-axis comparable.\n"
          "Bars = mean over 3 datasets, whiskers = min-max. Source: EXP-D cost table.",
          transform=axB1.transAxes, ha="left", va="top", fontsize=5.6, color="#6b7280")

# ===========================================================================
# Panel C — Component ablation: mean Δ code F1 per disabled module, 2 backbones
# (EXP-G gpt-4o + EXP-G2 gpt-4o-mini; n=2 notes/dataset, point estimates)
# ===========================================================================
axC = fig.add_subplot(gs[1, 0])
abl_df = pd.read_csv(DATA / "ablation_f1.csv")
abl_order = ["sapbert_off", "semchunk_off", "date_off", "step4_off"]
abl_label = {"sapbert_off": "SapBERT\noff", "semchunk_off": "SemChunk\noff",
             "date_off": "Date\noff", "step4_off": "Step-4\noff"}
models_C = [("gpt-4o", C_CLINES), ("gpt-4o-mini", C_O3MINI)]
xC = np.arange(len(abl_order))
wC = 0.36
for j, (mdl, col) in enumerate(models_C):
    means = []
    for abl in abl_order:
        full = abl_df[(abl_df.model == mdl) & (abl_df.ablation == "full")].set_index("dataset")["code_f1"]
        sub = abl_df[(abl_df.model == mdl) & (abl_df.ablation == abl)].set_index("dataset")["code_f1"]
        means.append((sub - full).mean())
    off = (j - 0.5) * wC
    bars = axC.bar(xC + off, means, wC, label=mdl, color=col, edgecolor="white", linewidth=0.4, zorder=2)
    for xi, mv in zip(xC + off, means):
        axC.annotate(f"{mv:+.2f}", xy=(xi, mv - 0.012), ha="center", va="top", fontsize=5.6, color="#374151")
axC.axhline(0, color="#374151", linewidth=0.6, zorder=1)
axC.set_xticks(xC)
axC.set_xticklabels([abl_label[a] for a in abl_order])
axC.set_ylim(-0.52, 0.06)
axC.set_ylabel("Δ code F1 vs full pipeline")
axC.set_title("c   Component ablation (Δ code F1, mean of 3 datasets)", loc="left", fontsize=9, x=-0.10, y=1.02)
axC.legend(loc="lower left", ncol=1, bbox_to_anchor=(0.02, 0.02), columnspacing=0.8, handletextpad=0.3)
axC.text(0.5, -0.30,
         "n=2 notes/dataset · point estimates, no CI. SapBERT (UMLS normalisation) dominates\n"
         "on both backbones; Date acts on date fields (≈0 on code).",
         transform=axC.transAxes, ha="center", va="top", fontsize=5.8, color="#6b7280")

# ===========================================================================
# Panel D — Architecture vs alternatives, split by metric.
# Left: mention F1 (where DL encoders compete); right: code F1 (only
# normalization-capable systems). 5 systems, mean over 3 datasets, min-max
# whiskers. DL encoders structurally emit no UMLS codes (code F1 = 0).
# ===========================================================================
dpan = pd.read_csv(DATA / "panel5d.csv")
gsD = gs[1, 1].subgridspec(1, 2, wspace=0.45)
axD1 = fig.add_subplot(gsD[0, 0])   # mention
axD2 = fig.add_subplot(gsD[0, 1])   # code
SYS_D = ["CLINES (GPT-4o)", "o3-mini SP", "GPT-4o CoT", "BERT-base", "GatorTron"]
SYS_COL = {"CLINES (GPT-4o)": C_CLINES, "o3-mini SP": C_O3MINI,
           "GPT-4o CoT": C_COT, "BERT-base": "#0e7490", "GatorTron": "#475569"}
SYS_SHORT = {"CLINES (GPT-4o)": "CLINES", "o3-mini SP": "o3-mini SP",
             "GPT-4o CoT": "GPT-4o CoT", "BERT-base": "BERT-base", "GatorTron": "GatorTron"}

for ax, met, mlab in [(axD1, "mention", "Mention F1"), (axD2, "code", "Code F1")]:
    sub = dpan[dpan.metric == met].set_index("system")
    xs = np.arange(len(SYS_D))
    for k, s in enumerate(SYS_D):
        mv = sub.loc[s, "mean"]; lo = sub.loc[s, "lo"]; hi = sub.loc[s, "hi"]
        ax.bar(k, mv, 0.7, color=SYS_COL[s], edgecolor="white", linewidth=0.4, zorder=2)
        if hi > mv or lo < mv:
            ax.errorbar(k, mv, yerr=[[mv - lo], [hi - mv]], fmt="none",
                        ecolor="#374151", elinewidth=0.6, capsize=1.4, capthick=0.6, zorder=3)
        if met == "code" and mv == 0.0:
            ax.text(k, 0.03, "no\nnorm.", ha="center", va="bottom", fontsize=5.0, color="#6b7280")
    ax.set_xticks(xs)
    ax.set_xticklabels([SYS_SHORT[s] for s in SYS_D], fontsize=5.6,
                       rotation=40, ha="right", rotation_mode="anchor")
    ax.set_ylim(0, 1.0)
    ax.set_ylabel(mlab, fontsize=7)

axD1.set_title("d   Architecture vs single-prompt & DL baselines", loc="left",
               fontsize=9, x=-0.18, y=1.02)
axD1.text(0.0, -0.42,
          "Mean over 3 datasets, whiskers = min-max. DL encoders (BERT-base, GatorTron) emit mention\n"
          "spans only — no UMLS codes (code F1 = 0). Mention is DL's fine-tuned sweet spot, yet CLINES\n"
          "still leads. Source: EXP-F (single-prompt) + EXP-H (DL).",
          transform=axD1.transAxes, ha="left", va="top", fontsize=5.2, color="#6b7280")

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT)
fig.savefig(OUT.with_suffix(".png"))
print(f"wrote {OUT}")
print(f"wrote {OUT.with_suffix('.png')}")

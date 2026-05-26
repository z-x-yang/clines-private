"""Re-render Figure 3A-D with 95% bootstrap CIs and Figure 3E with per-bin n.

Reads metrics_with_ci.json (from bootstrap_ci.py) for the CI bars on 3A-D.
Reads per_note_counts.json + (optionally) tiktoken note-length stats for 3E.

Figure 3 panel mapping (per paper conventions):
  A: Code matching
  B: Assertion status
  C: Date extraction (begin_date OR aggregate of begin_date/end_date)
  D: Numeric value+unit

Outputs PDF + PNG.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


MODEL_ORDER = ['gpt4o', 'deepseek', 'llama', 'o3mini', 'phi4']
MODEL_LABELS = {
    'gpt4o': 'GPT-4o',
    'deepseek': 'DeepSeek',
    'llama': 'Llama-3.1-405B',
    'o3mini': 'o3-mini',
    'phi4': 'Phi-4',
}
DATASET_ORDER = ['4CE', 'coral_breastca', 'coral_pdac']
DATASET_LABELS = {
    '4CE': '4CE',
    'coral_breastca': 'CORAL-BreastCa',
    'coral_pdac': 'CORAL-PDAC',
}

PANELS = [
    ('A', 'Entity Code (SapBERT cos >= 0.95)', 'code'),
    ('B', 'Assertion Status', 'assertion_status'),
    ('C', 'Begin Date', 'begin_date'),
    ('D', 'Numeric Value', 'value'),
]


def plot_3abcd(metrics_ci: Dict, out_dir: Path, metric: str = 'f1'):
    fig, axes = plt.subplots(1, 4, figsize=(20, 5), sharey=True)
    bar_width = 0.15

    for ax, (panel_id, panel_title, col) in zip(axes, PANELS):
        x = np.arange(len(DATASET_ORDER))
        for j, model in enumerate(MODEL_ORDER):
            if model not in metrics_ci['results']:
                continue
            ys = []
            yerr_lo = []
            yerr_hi = []
            for ds in DATASET_ORDER:
                cell = metrics_ci['results'].get(model, {}).get(ds, {}).get(col, {}).get(metric)
                if cell is None:
                    ys.append(np.nan)
                    yerr_lo.append(0)
                    yerr_hi.append(0)
                else:
                    ys.append(cell['point'])
                    yerr_lo.append(max(0, cell['point'] - cell['ci_lo']))
                    yerr_hi.append(max(0, cell['ci_hi'] - cell['point']))
            ax.bar(x + j * bar_width, ys, bar_width,
                   label=MODEL_LABELS.get(model, model),
                   yerr=[yerr_lo, yerr_hi], capsize=3, ecolor='black')
        ax.set_xticks(x + bar_width * (len(MODEL_ORDER) - 1) / 2)
        ax.set_xticklabels([DATASET_LABELS[d] for d in DATASET_ORDER], rotation=15)
        ax.set_title(f"({panel_id}) {panel_title}")
        ax.set_ylim(0, 1.05)
        ax.grid(axis='y', linestyle=':', alpha=0.6)
        if panel_id == 'A':
            ax.set_ylabel(f"{metric.upper()} (95% bootstrap CI)")
    axes[-1].legend(loc='lower right', fontsize=9)
    plt.suptitle(f"Figure 3A-D: {metric.upper()} with 95% bootstrap CIs "
                 f"(n_boot={metrics_ci['n_boot']}, seed={metrics_ci['seed']})",
                 y=1.02)
    plt.tight_layout()
    pdf_path = out_dir / f'figure3_ABCD_{metric}.pdf'
    png_path = out_dir / f'figure3_ABCD_{metric}.png'
    plt.savefig(pdf_path, bbox_inches='tight')
    plt.savefig(png_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Wrote {pdf_path}")
    print(f"Wrote {png_path}")


def plot_3e(per_note_counts: Dict, model: str, out_dir: Path,
            note_length_csv: Path | None = None,
            n_bins: int = 8, n_boot: int = 2000, seed: int = 20260525):
    """Figure 3E: F1 vs note-length bins with bootstrap ribbon + per-bin n.

    Computes per-note F1 by aggregating tp/fp/fn across columns (matches the
    original Figure 3E which is a single aggregate F1 line). Reads note-length
    from --note-length-csv if provided; else falls back to estimating from
    summed (tp + fp + fn) as a proxy entity-count axis (the original paper
    uses word-count quantile bins, so a CSV is preferred).
    """
    if model not in per_note_counts:
        print(f"WARN: model {model} not in counts; skipping Figure 3E")
        return

    rows = []
    for ds, note_dict in per_note_counts[model].items():
        for note_id, col_counts in note_dict.items():
            tp = sum(c['tp'] for c in col_counts.values())
            fp = sum(c['fp'] for c in col_counts.values())
            fn = sum(c['fn'] for c in col_counts.values())
            p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
            rows.append({
                'dataset': ds, 'note_id': note_id,
                'tp': tp, 'fp': fp, 'fn': fn, 'f1': f1,
            })
    df = pd.DataFrame(rows)

    # Merge note length
    if note_length_csv and note_length_csv.exists():
        lens = pd.read_csv(note_length_csv)
        df = df.merge(lens[['dataset', 'note_id', 'num_tokens']],
                      on=['dataset', 'note_id'], how='left')
        x_label = 'Note length (tokens) quantile bin'
        x_col = 'num_tokens'
    else:
        df['num_entities'] = df['tp'] + df['fp'] + df['fn']
        x_label = 'Number of entities per note (quantile bin, proxy for length)'
        x_col = 'num_entities'

    df = df.dropna(subset=[x_col])
    if len(df) < n_bins:
        print(f"WARN: only {len(df)} notes; reducing n_bins to {len(df)}")
        n_bins = max(2, len(df))
    df['bin'] = pd.qcut(df[x_col], q=n_bins, duplicates='drop')

    rng = np.random.default_rng(seed)
    bin_stats = []
    for bin_name, sub in df.groupby('bin', observed=True):
        n_in_bin = len(sub)
        if n_in_bin == 0:
            continue
        tp = sub['tp'].to_numpy()
        fp = sub['fp'].to_numpy()
        fn = sub['fn'].to_numpy()
        # bootstrap F1 within bin
        idx = rng.integers(0, n_in_bin, size=(n_boot, n_in_bin))
        tp_b = tp[idx].sum(axis=1)
        fp_b = fp[idx].sum(axis=1)
        fn_b = fn[idx].sum(axis=1)
        with np.errstate(divide='ignore', invalid='ignore'):
            p_b = np.where(tp_b + fp_b > 0, tp_b / (tp_b + fp_b), 0.0)
            r_b = np.where(tp_b + fn_b > 0, tp_b / (tp_b + fn_b), 0.0)
            denom = p_b + r_b
            f1_b = np.where(denom > 0, 2 * p_b * r_b / denom, 0.0)
        point_p = tp.sum() / (tp.sum() + fp.sum()) if tp.sum() + fp.sum() > 0 else 0.0
        point_r = tp.sum() / (tp.sum() + fn.sum()) if tp.sum() + fn.sum() > 0 else 0.0
        point_f1 = 2 * point_p * point_r / (point_p + point_r) if (point_p + point_r) > 0 else 0.0
        bin_stats.append({
            'bin_label': str(bin_name),
            'bin_left': bin_name.left,
            'bin_right': bin_name.right,
            'n_notes': n_in_bin,
            'f1_point': float(point_f1),
            'f1_boot_mean': float(f1_b.mean()),
            'f1_ci_lo': float(np.percentile(f1_b, 2.5)),
            'f1_ci_hi': float(np.percentile(f1_b, 97.5)),
        })

    bin_df = pd.DataFrame(bin_stats)
    if bin_df.empty:
        print("No bins produced; skipping Figure 3E plot")
        return
    bin_df = bin_df.sort_values('bin_left').reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    xs = np.arange(len(bin_df))
    ax.plot(xs, bin_df['f1_point'], marker='o', color='C0', linewidth=2,
            label='Point estimate F1')
    ax.fill_between(xs, bin_df['f1_ci_lo'], bin_df['f1_ci_hi'], color='C0',
                    alpha=0.25, label='95% bootstrap CI')
    ax.set_xticks(xs)
    ax.set_xticklabels([s for s in bin_df['bin_label']], rotation=30, ha='right',
                       fontsize=9)
    ax.set_xlabel(x_label)
    ax.set_ylabel('Aggregated F1 (all columns)')
    ax.set_ylim(0, 1.05)
    ax.grid(linestyle=':', alpha=0.6)

    # annotate per-bin n on top
    for x, n in zip(xs, bin_df['n_notes']):
        ax.annotate(f"n={int(n)}", xy=(x, 1.01), ha='center', va='bottom',
                    fontsize=9, color='black')

    ax.set_title(f"Figure 3E: F1 vs note length ({MODEL_LABELS.get(model, model)})\n"
                 f"n_boot={n_boot}, seed={seed}")
    ax.legend(loc='lower left', fontsize=9)
    plt.tight_layout()
    pdf_path = out_dir / f'figure3_E_{model}.pdf'
    png_path = out_dir / f'figure3_E_{model}.png'
    plt.savefig(pdf_path, bbox_inches='tight')
    plt.savefig(png_path, dpi=200, bbox_inches='tight')
    plt.close()
    bin_df.to_csv(out_dir / f'figure3_E_{model}_bins.csv', index=False)
    print(f"Wrote {pdf_path}")
    print(f"Wrote {png_path}")
    print(f"Wrote {out_dir / f'figure3_E_{model}_bins.csv'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--metrics-ci', required=True)
    ap.add_argument('--counts', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--note-length-csv', default=None,
                    help='Optional CSV with columns dataset, note_id, num_tokens for Figure 3E x-axis')
    ap.add_argument('--n-bins', type=int, default=8)
    ap.add_argument('--n-boot', type=int, default=2000)
    ap.add_argument('--seed', type=int, default=20260525)
    ap.add_argument('--fig3e-model', default='gpt4o')
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(args.metrics_ci) as f:
        metrics_ci = json.load(f)
    with open(args.counts) as f:
        counts = json.load(f)

    plot_3abcd(metrics_ci, out_dir, metric='f1')
    plot_3abcd(metrics_ci, out_dir, metric='accuracy')

    nlen = Path(args.note_length_csv) if args.note_length_csv else None
    plot_3e(counts, args.fig3e_model, out_dir,
            note_length_csv=nlen, n_bins=args.n_bins,
            n_boot=args.n_boot, seed=args.seed)


if __name__ == '__main__':
    main()

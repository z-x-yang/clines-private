"""Document-level bootstrap for Figure 3A-D bars + stability table.

Reads per-note counts from compute_per_note_counts.py and resamples notes
(with replacement) to compute 95% bootstrap CIs and stability statistics
(mean / std / 2.5th / 97.5th percentile) for F1 and accuracy.

Output:
- metrics_with_ci.json  (per-bar mean + 95% CI for precision / recall / F1 /
  accuracy, for every (model, dataset, column))
- stability_table.csv   (long-format: model, dataset, column, metric,
  point_estimate, boot_mean, boot_std, ci_lo, ci_hi, n_notes)
- bootstrap_resamples.npz  (joint resampled indices used across all models,
  so pairwise_significance.py can reproduce paired bootstrap)

A FIXED RNG SEED locks reproducibility. Same seed -> identical CIs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


DEFAULT_COLUMNS = ['code', 'assertion_status', 'begin_date', 'end_date', 'value', 'unit']


def metrics_from_counts(tp: int, fp: int, fn: int) -> Dict[str, float]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
    return {'precision': precision, 'recall': recall, 'f1': f1, 'accuracy': accuracy}


def build_count_arrays(counts: Dict[str, Dict[str, Dict[str, Dict[str, Dict[str, int]]]]],
                       columns: List[str]):
    """Returns:
      arrays[model][dataset][col] -> (note_ids: List[str], tps, fps, fns) np arrays
    """
    arrays: Dict[str, Dict[str, Dict[str, Dict]]] = {}
    for model, ds_dict in counts.items():
        arrays[model] = {}
        for dataset, note_dict in ds_dict.items():
            arrays[model][dataset] = {}
            note_ids = sorted(note_dict.keys())
            for col in columns:
                tp = np.array([note_dict[n].get(col, {'tp': 0})['tp'] for n in note_ids], dtype=np.int64)
                fp = np.array([note_dict[n].get(col, {'fp': 0})['fp'] for n in note_ids], dtype=np.int64)
                fn = np.array([note_dict[n].get(col, {'fn': 0})['fn'] for n in note_ids], dtype=np.int64)
                arrays[model][dataset][col] = {
                    'note_ids': note_ids,
                    'tp': tp, 'fp': fp, 'fn': fn,
                }
    return arrays


def bootstrap_one_cell(tp: np.ndarray, fp: np.ndarray, fn: np.ndarray,
                       indices_matrix: np.ndarray) -> Dict[str, np.ndarray]:
    """Given per-note tp/fp/fn arrays and an [n_boot, n_notes] resampling
    matrix of integer indices, return arrays of bootstrap precision / recall /
    F1 / accuracy."""
    tp_boot = tp[indices_matrix].sum(axis=1)
    fp_boot = fp[indices_matrix].sum(axis=1)
    fn_boot = fn[indices_matrix].sum(axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        prec = np.where((tp_boot + fp_boot) > 0, tp_boot / (tp_boot + fp_boot), 0.0)
        rec = np.where((tp_boot + fn_boot) > 0, tp_boot / (tp_boot + fn_boot), 0.0)
        denom_f1 = prec + rec
        f1 = np.where(denom_f1 > 0, 2 * prec * rec / denom_f1, 0.0)
        denom_acc = tp_boot + fp_boot + fn_boot
        acc = np.where(denom_acc > 0, tp_boot / denom_acc, 0.0)
    return {'precision': prec, 'recall': rec, 'f1': f1, 'accuracy': acc}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--counts', required=True, help='per_note_counts.json from compute_per_note_counts.py')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--n-boot', type=int, default=2000)
    ap.add_argument('--seed', type=int, default=20260525)
    ap.add_argument('--columns', nargs='+', default=DEFAULT_COLUMNS)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.counts) as f:
        counts = json.load(f)

    arrays = build_count_arrays(counts, args.columns)

    # Build per-dataset shared resampling indices keyed by note_id list
    # (so different models with the SAME note set get identical bootstrap
    # indices -> paired bootstrap works). We anchor on the GPT-4o note_ids
    # because it has the full coverage; phi4 (matched-only) gets its own.
    rng = np.random.default_rng(args.seed)

    # Group: dataset -> {model -> arrays} for ergonomics
    # Save per (model, dataset) indices matrix.
    indices_store: Dict[str, np.ndarray] = {}

    ci_out: Dict = {}
    stab_rows: List[Dict] = []

    # determine canonical (most populated) note_id set per dataset across models
    canonical_notes_per_ds: Dict[str, List[str]] = {}
    for model, ds_dict in arrays.items():
        for ds, col_dict in ds_dict.items():
            # all columns share the same note_ids inside one (model, ds)
            sample_col = next(iter(col_dict.values()))
            note_ids = sample_col['note_ids']
            if ds not in canonical_notes_per_ds or len(note_ids) > len(canonical_notes_per_ds[ds]):
                canonical_notes_per_ds[ds] = note_ids

    # For each (model, dataset), generate resample matrix of shape [n_boot, n_notes_for_that_pair]
    # Paired bootstrap (pairwise_significance.py) requires same indices across
    # models when the note_id lists match -> we generate per (dataset, note_id_signature)
    # and reuse.
    sig_to_indices: Dict[Tuple[str, Tuple[str, ...]], np.ndarray] = {}

    for model, ds_dict in arrays.items():
        for ds, col_dict in ds_dict.items():
            sample_col = next(iter(col_dict.values()))
            note_ids = sample_col['note_ids']
            sig = (ds, tuple(note_ids))
            if sig not in sig_to_indices:
                n_notes = len(note_ids)
                sig_to_indices[sig] = rng.integers(0, n_notes, size=(args.n_boot, n_notes))
            idx = sig_to_indices[sig]
            indices_store[f"{model}__{ds}"] = idx

            for col in args.columns:
                tp = col_dict[col]['tp']
                fp = col_dict[col]['fp']
                fn = col_dict[col]['fn']
                point = metrics_from_counts(int(tp.sum()), int(fp.sum()), int(fn.sum()))
                boot = bootstrap_one_cell(tp, fp, fn, idx)
                for metric_name in ('precision', 'recall', 'f1', 'accuracy'):
                    arr = boot[metric_name]
                    boot_mean = float(arr.mean())
                    boot_std = float(arr.std(ddof=1)) if arr.size > 1 else 0.0
                    ci_lo = float(np.percentile(arr, 2.5))
                    ci_hi = float(np.percentile(arr, 97.5))
                    point_val = float(point[metric_name])
                    ci_out.setdefault(model, {}).setdefault(ds, {}).setdefault(col, {})[metric_name] = {
                        'point': point_val,
                        'boot_mean': boot_mean,
                        'boot_std': boot_std,
                        'ci_lo': ci_lo,
                        'ci_hi': ci_hi,
                    }
                    stab_rows.append({
                        'model': model,
                        'dataset': ds,
                        'column': col,
                        'metric': metric_name,
                        'point_estimate': point_val,
                        'boot_mean': boot_mean,
                        'boot_std': boot_std,
                        'ci_lo': ci_lo,
                        'ci_hi': ci_hi,
                        'n_notes': len(note_ids),
                        'n_boot': args.n_boot,
                    })

    # Save metrics_with_ci.json
    with open(out_dir / 'metrics_with_ci.json', 'w') as f:
        json.dump({
            'n_boot': args.n_boot,
            'seed': args.seed,
            'columns': args.columns,
            'results': ci_out,
        }, f, indent=2)

    # Save stability_table.csv
    stab_df = pd.DataFrame(stab_rows)
    stab_df.to_csv(out_dir / 'stability_table.csv', index=False)

    # Save bootstrap_resamples for paired use
    np.savez_compressed(out_dir / 'bootstrap_resamples.npz', **indices_store)

    # Print summary
    print(f"Wrote {out_dir / 'metrics_with_ci.json'}")
    print(f"Wrote {out_dir / 'stability_table.csv'}")
    print(f"Wrote {out_dir / 'bootstrap_resamples.npz'}")

    # Quick screen summary: F1 CI per (model, dataset, col) for sanity
    f1_view = stab_df[stab_df['metric'] == 'f1'][
        ['model', 'dataset', 'column', 'point_estimate', 'ci_lo', 'ci_hi', 'boot_std', 'n_notes']
    ].sort_values(['model', 'dataset', 'column'])
    print("\n--- F1 95% CI (point [ci_lo, ci_hi], boot_std) ---")
    for _, r in f1_view.iterrows():
        print(f"  {r['model']:<10} {r['dataset']:<16} {r['column']:<18} "
              f"{r['point_estimate']:.3f} [{r['ci_lo']:.3f}, {r['ci_hi']:.3f}]  "
              f"std={r['boot_std']:.3f}  n={r['n_notes']}")


if __name__ == '__main__':
    main()

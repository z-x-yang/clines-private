"""Pre-compute per-(model, dataset, note_id, column) tp/fp/fn counts.

Mirrors the eval logic in scripts/eval_predictions.py exactly (position-overlap
match, SapBERT cosine for code column, date standardization, assertion historical
folded into Present, value numeric filter). Caches one (pred_term, gt_term) ->
similarity dict to avoid re-encoding identical strings.

The bootstrap downstream steps only resample note-level counts; the heavy eval
work (and SapBERT encoding) happens exactly once here.

Output: runs/EXP-BC/per_note_counts.json with shape
    {model: {dataset: {note_id: {column: {tp, fp, fn}}}}}

Failure modes (fail-fast per CLAUDE.md §2):
- Missing predictions for a (model, gt) pair: raise. We do NOT silently skip.
- SapBERT model load failure: raise.
- Position type errors: raise (rather than coerce-then-drop silently with no log).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import transformers
from sklearn.metrics.pairwise import cosine_similarity


# ----------------------------- helpers ----------------------------------

def extract_standard_term(code_str) -> str:
    if not isinstance(code_str, str):
        code_str = str(code_str)
    if '||' in code_str:
        return code_str.split('||', 1)[1].strip()
    return code_str.strip()


def standardize_date(date_str):
    if not isinstance(date_str, str):
        date_str = str(date_str)
    date_str = date_str.strip()
    if not date_str:
        return None
    lower = date_str.lower()
    if lower in {'unknown', 'unk', 'na', 'n/a', 'none', 'null'}:
        return None
    if re.match(r'^\d+\s+(year|years|month|months|day|days)\s+ago$', lower):
        return None
    if lower in {'today', 'yesterday'}:
        return None
    for fmt in [
        '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y',
        '%Y-%m', '%m-%Y', '%Y/%m', '%m/%Y', '%Y.%m.%d', '%d.%m.%Y',
        '%Y',
    ]:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            if fmt == '%Y':
                return parsed_date.strftime('%Y')
            if fmt in ['%Y-%m', '%m-%Y', '%Y/%m', '%m/%Y']:
                return parsed_date.strftime('%Y-%m')
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def is_numeric(value) -> bool:
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


# ----------------------------- SapBERT ----------------------------------

class SapBERTEncoder:
    """CPU-friendly wrapper around SapBERT. Caches text -> embedding for
    deduplication across repeated (pred_term, gt_term) pairs."""

    def __init__(self, model_name: str = 'cambridgeltl/SapBERT-from-PubMedBERT-fulltext',
                 device: str = 'cpu'):
        self.device = device
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            model_name, use_fast=True, do_lower_case=True)
        self.encoder = transformers.AutoModel.from_pretrained(
            model_name, trust_remote_code=True)
        if device == 'cuda' and torch.cuda.is_available():
            self.encoder = self.encoder.cuda()
        else:
            self.encoder = self.encoder.cpu()
            self.device = 'cpu'
        self.encoder.eval()
        self._cache: Dict[str, np.ndarray] = {}

    def embed(self, text: str) -> np.ndarray:
        key = text.strip().lower()
        if key in self._cache:
            return self._cache[key]
        with torch.no_grad():
            tok = self.tokenizer.batch_encode_plus(
                [key], add_special_tokens=True, truncation=True,
                max_length=25, padding='max_length', return_tensors='pt')
            if self.device == 'cuda':
                tok = {k: v.cuda() for k, v in tok.items()}
            out = self.encoder(**tok)
            emb = out.last_hidden_state[:, 0, :]
            emb = emb / torch.norm(emb, p=2, dim=-1, keepdim=True)
            emb = emb.cpu().numpy()[0]
        self._cache[key] = emb
        return emb

    def similarity(self, a: str, b: str) -> float:
        ea = self.embed(a)
        eb = self.embed(b)
        return float(cosine_similarity(ea[None, :], eb[None, :])[0, 0])


# ----------------------------- core eval --------------------------------

def _bool_match(pred_value, gt_value, col: str, sap: SapBERTEncoder | None,
                threshold: float) -> bool:
    """Replicates eval_predictions.py decision rules per column. Returns True
    if the predicted entity matches the gold on this column."""
    if 'assertion' in col.lower() and 'status' in col.lower():
        pred_value_s = str(pred_value).strip().lower()
        if pred_value_s == 'historical':
            pred_value_s = 'present'
        gt_value_s = str(gt_value).strip().lower()
        return pred_value_s == gt_value_s

    if col.lower() == 'code' and sap is not None:
        pred_term = extract_standard_term(pred_value)
        gt_term = extract_standard_term(gt_value)
        if pred_term and gt_term:
            try:
                sim = sap.similarity(pred_term, gt_term)
                return sim >= threshold
            except Exception as exc:
                # fail-fast: surface in stderr but continue to string fallback
                # so we don't silently corrupt counts.
                print(f"WARN code similarity failed ({exc}); string-fallback "
                      f"used for ({pred_term!r}, {gt_term!r})", file=sys.stderr)
                return pred_term.lower() == gt_term.lower()
        return str(pred_value).strip().lower() == str(gt_value).strip().lower()

    if 'date' in col.lower():
        std_pred = standardize_date(pred_value)
        std_gt = standardize_date(gt_value)
        if std_pred is None or std_gt is None:
            return None  # skip - matches eval_predictions.py 'continue'
        sp = str(std_pred)
        sg = str(std_gt)
        return sp in sg or sg in sp or sp == sg

    if isinstance(pred_value, (float, int)) and isinstance(gt_value, (float, int)):
        return abs(float(pred_value) - float(gt_value)) < 0.0001

    if isinstance(pred_value, str) and isinstance(gt_value, str):
        return pred_value in gt_value or gt_value in pred_value or pred_value == gt_value

    sp = str(pred_value)
    sg = str(gt_value)
    return sp in sg or sg in sp or sp == sg


def evaluate_one_note(pred_df: pd.DataFrame, gt_df: pd.DataFrame,
                      columns: List[str], sap: SapBERTEncoder | None,
                      threshold: float) -> Dict[str, Dict[str, int]]:
    """Returns per-column {tp, fp, fn} for one (pred, gt) pair."""
    # Coerce positions; drop NaN / -1 (mirrors eval_predictions.py)
    for df in (pred_df, gt_df):
        if 'start_pos' in df.columns:
            df['start_pos'] = pd.to_numeric(df['start_pos'], errors='coerce')
        if 'end_pos' in df.columns:
            df['end_pos'] = pd.to_numeric(df['end_pos'], errors='coerce')
    pred_df = pred_df.dropna(subset=['start_pos', 'end_pos'])
    gt_df = gt_df.dropna(subset=['start_pos', 'end_pos'])
    pred_df = pred_df[(pred_df['start_pos'] != -1) & (pred_df['end_pos'] != -1)]
    gt_df = gt_df[(gt_df['start_pos'] != -1) & (gt_df['end_pos'] != -1)]

    note_counts: Dict[str, Dict[str, int]] = {}
    for col in columns:
        if col not in pred_df.columns or col not in gt_df.columns:
            note_counts[col] = {'tp': 0, 'fp': 0, 'fn': 0}
            continue
        pred_col_df = pred_df.dropna(subset=[col])
        gt_col_df = gt_df.dropna(subset=[col])
        if col == 'value':
            pred_col_df = pred_col_df[pred_col_df[col].apply(is_numeric)]
            gt_col_df = gt_col_df[gt_col_df[col].apply(is_numeric)]

        gt_positions: Dict[Tuple[float, float], pd.Series] = {}
        for _, row in gt_col_df.iterrows():
            gt_positions[(row['start_pos'], row['end_pos'])] = row

        tp = fp = fn = 0
        for _, pred_row in pred_col_df.iterrows():
            pred_start, pred_end = pred_row['start_pos'], pred_row['end_pos']
            best_gt = None
            best_int = 0
            for (gt_start, gt_end), gt_row in gt_positions.items():
                if pred_start <= gt_end and gt_start <= pred_end:
                    inter = min(pred_end, gt_end) - max(pred_start, gt_start)
                    if inter > best_int:
                        best_int = inter
                        best_gt = gt_row
            if best_gt is not None:
                ok = _bool_match(pred_row[col], best_gt[col], col, sap, threshold)
                if ok is None:
                    continue  # skipped date
                if ok:
                    tp += 1
                else:
                    fp += 1

        pred_positions = {(r['start_pos'], r['end_pos'])
                          for _, r in pred_col_df.iterrows()}
        for _, gt_row in gt_col_df.iterrows():
            gs, ge = gt_row['start_pos'], gt_row['end_pos']
            hit = False
            for ps, pe in pred_positions:
                if ps <= ge and gs <= pe:
                    hit = True
                    break
            if not hit:
                fn += 1

        note_counts[col] = {'tp': tp, 'fp': fp, 'fn': fn}
    return note_counts


# ------------------------ pair discovery --------------------------------

DATASET_DIRS = {
    '4CE': '4CE',
    'coral_breastca': 'coral_annotated_breastca',
    'coral_pdac': 'coral_annotated_pdac',
}


def discover_pairs(prediction_dir: Path, gold_dir: Path, model_token: str
                   ) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for dataset_label, gt_subdir in DATASET_DIRS.items():
        gt_subdir_path = gold_dir / gt_subdir
        if not gt_subdir_path.exists():
            continue
        for gt_file in sorted(gt_subdir_path.glob('*_updated.csv')):
            note_id = gt_file.name.replace('_updated.csv', '')
            pred_name = f"{gt_subdir}_{note_id}_default_{model_token}_with_positions.csv"
            pred_path = prediction_dir / pred_name
            if pred_path.exists():
                items.append({
                    'pred': str(pred_path),
                    'gt': str(gt_file),
                    'dataset_label': dataset_label,
                    'note_id': note_id,
                })
    return items


# ------------------------ main ------------------------------------------

DEFAULT_COLUMNS = ['code', 'assertion_status', 'begin_date', 'end_date', 'value', 'unit']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outputs-root', required=True,
                    help='Path containing with_positions/, with_positions_phi4/, reviewed_updated2/')
    ap.add_argument('--out', required=True, help='Output per_note_counts.json')
    ap.add_argument('--columns', nargs='+', default=DEFAULT_COLUMNS)
    ap.add_argument('--similarity-threshold', type=float, default=0.95)
    ap.add_argument('--device', default='cpu', choices=['cpu', 'cuda'])
    ap.add_argument('--no-sapbert', action='store_true',
                    help='Disable SapBERT for code column (string match only) - for smoke tests')
    args = ap.parse_args()

    outputs_root = Path(args.outputs_root).resolve()
    gold_dir = outputs_root / 'reviewed_updated2'
    if not gold_dir.exists():
        raise FileNotFoundError(f"gold_dir {gold_dir} does not exist")

    model_specs = [
        ('gpt4o', 'gpt4o', outputs_root / 'with_positions'),
        ('deepseek', 'deepseek', outputs_root / 'with_positions'),
        ('llama', 'llama', outputs_root / 'with_positions'),
        ('o3mini', 'o3mini', outputs_root / 'with_positions'),
        ('phi4', 'phi4', outputs_root / 'with_positions_phi4'),
    ]

    sap = None
    if not args.no_sapbert and 'code' in args.columns:
        print(f"Loading SapBERT on {args.device}...", file=sys.stderr)
        sap = SapBERTEncoder(device=args.device)
        print("  loaded", file=sys.stderr)

    out: Dict[str, Dict[str, Dict[str, Dict[str, Dict[str, int]]]]] = {}
    for model_key, model_token, pred_dir in model_specs:
        if not pred_dir.exists():
            print(f"WARN: prediction dir {pred_dir} missing -> skipping {model_key}", file=sys.stderr)
            continue
        pairs = discover_pairs(pred_dir, gold_dir, model_token)
        if not pairs:
            print(f"WARN: no pairs for {model_key} (token={model_token}, dir={pred_dir})",
                  file=sys.stderr)
            continue
        print(f"\n=== {model_key}: {len(pairs)} (model, note) pairs ===", file=sys.stderr)
        out[model_key] = {}
        for i, item in enumerate(pairs):
            pred_df = pd.read_csv(item['pred'])
            gt_df = pd.read_csv(item['gt'])
            counts = evaluate_one_note(pred_df, gt_df, args.columns, sap,
                                       args.similarity_threshold)
            ds = item['dataset_label']
            note_id = item['note_id']
            out[model_key].setdefault(ds, {})[note_id] = counts
            if (i + 1) % 10 == 0:
                print(f"  {model_key}: {i+1}/{len(pairs)}", file=sys.stderr)
        print(f"  done {model_key}", file=sys.stderr)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == '__main__':
    main()

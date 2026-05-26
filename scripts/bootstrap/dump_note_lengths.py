"""Dump per-note token / word counts using tiktoken cl100k_base.

Mirrors the helper inside scripts/eval_predictions.py main(). Saves a CSV
with (dataset, note_id, num_tokens, num_words, num_chars_no_space) so
plot_figure3.py's Figure 3E can bin by tokens (matching Figure 3 in the
paper) instead of by entity-count proxy.

If a note's source text is missing, the row is still emitted with NaN to
keep dataset coverage observable (no silent drop).
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
import tiktoken


DATASET_DATA_SUBDIRS = {
    '4CE': '4CE',
    'coral_breastca': 'coral_annotated_breastca',
    'coral_pdac': 'coral_annotated_pdac',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-root', required=True,
                    help='Path to data/ directory containing 4CE/, coral_annotated_breastca/, coral_annotated_pdac/')
    ap.add_argument('--gold-root', required=True,
                    help='Path to outputs/reviewed_updated2 - used to enumerate note_ids')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    data_root = Path(args.data_root)
    gold_root = Path(args.gold_root)
    enc = tiktoken.get_encoding('cl100k_base')

    rows = []
    for label, gt_subdir in DATASET_DATA_SUBDIRS.items():
        gt_path = gold_root / gt_subdir
        if not gt_path.exists():
            print(f"WARN: {gt_path} missing")
            continue
        for gt_file in sorted(gt_path.glob('*_updated.csv')):
            note_id = gt_file.name.replace('_updated.csv', '')
            note_txt = data_root / gt_subdir / f"{note_id}.txt"
            if note_txt.exists():
                try:
                    text = note_txt.read_text(encoding='utf-8', errors='ignore')
                    n_tokens = len(enc.encode(text))
                    n_words = len(text.split())
                    n_chars = len(re.sub(r'\s+', '', text))
                except Exception as exc:
                    print(f"WARN: failed to read {note_txt}: {exc}")
                    n_tokens = n_words = n_chars = None
            else:
                n_tokens = n_words = n_chars = None
            rows.append({
                'dataset': label, 'note_id': note_id,
                'num_tokens': n_tokens, 'num_words': n_words,
                'num_chars_no_space': n_chars,
            })

    df = pd.DataFrame(rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {args.out} ({len(df)} rows, {df['num_tokens'].notna().sum()} with token counts)")


if __name__ == '__main__':
    main()

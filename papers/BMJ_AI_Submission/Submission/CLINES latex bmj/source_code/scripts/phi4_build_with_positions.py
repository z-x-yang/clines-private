#!/usr/bin/env python3
"""
Build with_positions-style predictions for Phi-4 outputs by finding start_pos/end_pos
in the original note text, so we can reuse scripts/eval_predictions.py with the
same algorithm and metrics as eval.sh.

- Input: a file_pairs.json produced earlier by converter (phi4_file <-> gt_file mapping)
         or explicitly provide phi4_dir + groundtruth_dir to derive pairs.
- Output: with_positions CSVs named as: {dataset_dir}_{note_id}_default_phi4_with_positions.csv

We also write minimal required columns: mention, assertion_status, value, unit, begin_date,
end_date, start_pos, end_pos, text.
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / 'data'


def dataset_dir_to_text_path(dataset_dir: str, note_id: str) -> Path:
    # dataset_dir like '4CE', 'coral_annotated_pdac', 'coral_annotated_breastca'
    if dataset_dir == '4CE':
        return DATA_DIR / dataset_dir / f"{note_id}.txt"
    return DATA_DIR / dataset_dir / f"{note_id}.txt"


def escape_phrase_to_regex(phrase: str) -> str:
    # Escape non-space chars; convert whitespace runs to \s+
    # Keep alnum and punctuation escaping; robust to spacing
    parts = re.split(r"\s+", phrase.strip())
    parts = [re.escape(p) for p in parts if p]
    if not parts:
        return re.escape(phrase)
    return r"\s+".join(parts)


def find_span(text: str, phrase: str) -> Optional[Tuple[int, int]]:
    if not phrase or not text:
        return None
    # 1) exact search
    idx = text.find(phrase)
    if idx != -1:
        return idx, idx + len(phrase)
    # 2) case-insensitive search
    tl = text.lower()
    pl = phrase.lower()
    idx = tl.find(pl)
    if idx != -1:
        return idx, idx + len(phrase)
    # 3) regex whitespace-insensitive, case-insensitive
    pattern = escape_phrase_to_regex(phrase)
    try:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.start(), m.end()
    except re.error:
        pass
    return None


def build_with_positions_for_pair(phi4_file: Path, gt_file: Path, out_dir: Path) -> Optional[Path]:
    # derive dataset_dir and note_id from gt_file
    dataset_dir = gt_file.parent.name
    note_id = gt_file.name.replace('_updated.csv', '')

    # resolve text path
    text_path = dataset_dir_to_text_path(dataset_dir, note_id)
    if not text_path.exists():
        print(f"⚠ Note text not found: {text_path}")
        return None

    # read text
    try:
        text = text_path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        print(f"⚠ Failed to read note text {text_path}: {e}")
        return None

    # read phi4 predictions
    try:
        df = pd.read_csv(phi4_file)
    except Exception as e:
        print(f"⚠ Failed to read {phi4_file}: {e}")
        return None

    if df.empty or 'phrase' not in df.columns:
        print(f"⚠ Empty or missing 'phrase': {phi4_file}")
        return None

    # Prepare output rows
    rows = []
    # Track used spans to avoid heavy overlapping duplicates greedily
    used_spans: List[Tuple[int, int]] = []

    for _, r in df.iterrows():
        phrase = str(r.get('phrase', '') or '').strip()
        if not phrase:
            continue
        span = find_span(text, phrase)
        start_pos, end_pos = (-1, -1)
        if span is not None:
            s, e = span
            # prevent pathological overlaps: allow overlaps if necessary but prefer unused
            start_pos, end_pos = s, e
            for us, ue in used_spans:
                if not (end_pos <= us or ue <= start_pos):
                    # overlaps, but keep anyway; evaluation handles intersection logic
                    pass
            used_spans.append((start_pos, end_pos))

        rows.append({
            'mention': phrase,
            'assertion_status': r.get('assertion_status', ''),
            'value': r.get('value', ''),
            'unit': r.get('unit', ''),
            'begin_date': r.get('start_date', ''),
            'end_date': r.get('end_date', ''),
            'start_pos': start_pos,
            'end_pos': end_pos,
            'text': phrase  # minimal context
        })

    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"{dataset_dir}_{note_id}_default_phi4_with_positions.csv"
    out_path = out_dir / out_name
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"✓ Built {out_path} ({len(rows)} rows)")
    return out_path


def main():
    import argparse
    p = argparse.ArgumentParser(
        description='Build with_positions predictions for Phi-4 outputs')
    p.add_argument('--file_pairs', type=str, required=True,
                   help='JSON mapping items with phi4_file and gt_file')
    p.add_argument('--output_dir', type=str, required=True,
                   help='Directory to write with_positions files (e.g., outputs/with_positions)')
    p.add_argument('--limit', type=int, default=None,
                   help='Optional limit for quick build')
    args = p.parse_args()

    pairs = json.loads(Path(args.file_pairs).read_text())
    if args.limit is not None:
        pairs = pairs[:args.limit]

    out_dir = Path(args.output_dir)
    built = 0
    for it in pairs:
        phi4_file = Path(it['phi4_file'])
        gt_file = Path(it['gt_file'])
        res = build_with_positions_for_pair(phi4_file, gt_file, out_dir)
        if res is not None:
            built += 1
    print(f"Built with_positions files: {built}/{len(pairs)}")


if __name__ == '__main__':
    main()

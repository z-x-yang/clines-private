#!/usr/bin/env python3
"""
Build file_pairs.json by reading note_id from Phi-4 CSVs and matching
exactly to groundtruth files named {note_id}_updated.csv in subdirs.
"""
import os
import json
from pathlib import Path
from typing import List, Dict
import pandas as pd


def find_gt_for_note(gt_root: Path, note_id: str) -> Path | None:
    target = f"{note_id}_updated.csv"
    for sub in gt_root.iterdir():
        if sub.is_dir():
            cand = sub / target
            if cand.exists():
                return cand
    return None


def main():
    import argparse
    p = argparse.ArgumentParser(
        description='Build Phi-4 file pairs using internal note_id')
    p.add_argument('--phi4_dir', required=True, help='Directory of Phi-4 CSVs')
    p.add_argument('--groundtruth_dir', required=True,
                   help='Ground truth root (reviewed_updated2)')
    p.add_argument('--output_pairs', required=True,
                   help='Output JSON path for file_pairs.json')
    args = p.parse_args()

    phi4_dir = Path(args.phi4_dir)
    gt_root = Path(args.groundtruth_dir)

    pairs: List[Dict[str, str]] = []
    total = 0
    matched = 0

    for csv_path in sorted(phi4_dir.glob('*.csv')):
        total += 1
        try:
            df = pd.read_csv(csv_path, nrows=1)
            if 'note_id' not in df.columns or df.empty:
                print(f"⚠ Skip (no note_id): {csv_path.name}")
                continue
            note_id = str(df.iloc[0]['note_id']).strip()
            if not note_id:
                print(f"⚠ Skip (empty note_id): {csv_path.name}")
                continue
            gt = find_gt_for_note(gt_root, note_id)
            if gt is None:
                print(f"✗ No GT for note_id={note_id} ({csv_path.name})")
                continue
            pairs.append({
                'phi4_file': str(csv_path),
                'gt_file': str(gt),
                'converted_file': '',
                'note_id': note_id
            })
            matched += 1
            print(f"✓ Pair: {csv_path.name} -> {gt.relative_to(gt_root)}")
        except Exception as e:
            print(f"⚠ Error reading {csv_path.name}: {e}")
            continue

    Path(args.output_pairs).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_pairs).write_text(json.dumps(pairs, indent=2))
    print(f"Built pairs: {matched}/{total} -> {args.output_pairs}")


if __name__ == '__main__':
    main()

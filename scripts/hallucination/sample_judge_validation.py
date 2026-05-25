"""EXP-E step 2.5: build a small validation sample for human spot-check of judge.

Stratified random sample (default 40 total) drawn from `fp_judged.csv`,
covering all judge categories proportionally (min 5 per category if available).
Output CSV has a blank `human_label` column that Zongxin fills manually.

Accuracy is computed via a separate `compute_judge_accuracy.py` from the
filled-in CSV.

PHI: output contains note excerpts — DO NOT commit (gitignored *.csv).
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fp_judged_csv",
        default="runs/EXP-E/fp_judged.csv",
        help="Judged FP CSV from judge_fp.py",
    )
    parser.add_argument(
        "--output_csv",
        default="runs/EXP-E/judge_validation_sample.csv",
        help="Sampled CSV for manual human review (DO NOT COMMIT)",
    )
    parser.add_argument("--total", type=int, default=40)
    parser.add_argument("--min_per_category", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    src = Path(args.fp_judged_csv)
    if not src.exists():
        raise FileNotFoundError(
            f"{src} not found. Run judge_fp.py first."
        )
    df = pd.read_csv(src)
    if "judge_category" not in df.columns:
        raise RuntimeError(
            "Expected 'judge_category' column in judged CSV; aborting."
        )

    rng = random.Random(args.seed)

    # Stratified: take min_per_category from each judge category, then fill
    # remainder proportionally.
    picks_idx: list = []
    cats = sorted(df["judge_category"].dropna().unique())
    floor_total = 0
    for cat in cats:
        pool = df.index[df["judge_category"] == cat].tolist()
        n = min(args.min_per_category, len(pool))
        picks_idx.extend(rng.sample(pool, n))
        floor_total += n

    remaining = args.total - floor_total
    if remaining > 0:
        # Sample remaining from everything not yet picked, proportionally.
        all_remaining = [i for i in df.index if i not in picks_idx]
        if all_remaining:
            n = min(remaining, len(all_remaining))
            picks_idx.extend(rng.sample(all_remaining, n))

    sample = df.loc[picks_idx].copy().reset_index(drop=True)
    # Insert manual-review columns
    sample.insert(0, "human_label", "")
    sample.insert(1, "human_notes", "")
    sample.insert(2, "agree_with_judge", "")

    out = Path(args.output_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(out, index=False)
    print(
        f"[done] wrote {len(sample)} rows to {out}\n"
        f"        stratified per judge_category (>= {args.min_per_category} each, total ~{args.total})\n"
        f"        manual review columns: 'human_label', 'human_notes', 'agree_with_judge'",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

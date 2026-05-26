#!/usr/bin/env python3
"""Build EXP-H comparison_table.csv: CLINES (GPT-4o) vs DL baselines vs
existing MobileBERT/DistilBERT reference numbers.

Outputs runs/EXP-H/eval/comparison_table.csv with one row per
(model, dataset) showing P/R/F1 on the `mention` column (CLINES eval
protocol) plus pointer to source JSON.

Usage:
    python scripts/dl_baseline/build_comparison_table.py \
        --eval_dir runs/EXP-H/eval \
        --gpt4o_eval outputs/evaluation_results_0904/gpt4_eval_20250904_154356.json \
        --output runs/EXP-H/eval/comparison_table.csv
"""

import argparse
import csv
import glob
import json
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--eval_dir", type=Path, required=True,
                   help="dir containing {marker}_eval_*.json files from EXP-H")
    p.add_argument("--gpt4o_eval", type=Path, default=None,
                   help="optional: CLINES GPT-4o eval JSON for direct comparison")
    p.add_argument("--output", type=Path, required=True)
    return p.parse_args()


def load_metrics_from_eval_json(path: Path):
    """Eval JSON layout (from scripts/eval_predictions.py):
    { dataset_label: { column: {precision, recall, f1, accuracy,
                                true_positives, false_positives,
                                false_negatives}, ... }, ... }
    Plus possibly 'overall' / 'note_metrics' keys depending on version.
    We extract mention metrics per dataset_label.
    """
    with open(path) as f:
        data = json.load(f)
    rows = []
    # support both wrapped and unwrapped forms (the eval script writes
    # results under top-level 'metrics' key when --output_file is set)
    if "metrics" in data:
        per_dataset = data["metrics"]
    else:
        per_dataset = data
    for ds, cols in per_dataset.items():
        if not isinstance(cols, dict):
            continue
        m = cols.get("mention") if isinstance(cols.get("mention"), dict) else None
        if m is None:
            continue
        rows.append({
            "dataset": ds,
            "precision": m.get("precision"),
            "recall": m.get("recall"),
            "f1": m.get("f1"),
            "tp": m.get("true_positives"),
            "fp": m.get("false_positives"),
            "fn": m.get("false_negatives"),
        })
    return rows


def main():
    args = parse_args()
    if not args.eval_dir.is_dir():
        raise SystemExit(f"eval_dir not found: {args.eval_dir}")

    all_rows = []

    # CLINES GPT-4o reference (optional)
    if args.gpt4o_eval is not None:
        if not args.gpt4o_eval.is_file():
            raise SystemExit(f"gpt4o_eval not found: {args.gpt4o_eval}")
        rows = load_metrics_from_eval_json(args.gpt4o_eval)
        for r in rows:
            r["model"] = "gpt4o (CLINES)"
            r["source"] = str(args.gpt4o_eval)
            all_rows.append(r)

    # EXP-H DL baseline evals — pick the latest *_eval_*.json per marker
    for marker in ["bertbase_clin", "gatortron_base"]:
        matches = sorted(args.eval_dir.glob(f"{marker}_eval_*.json"))
        if not matches:
            print(f"[WARN] no eval JSON found for {marker} under {args.eval_dir}")
            continue
        latest = matches[-1]
        rows = load_metrics_from_eval_json(latest)
        for r in rows:
            r["model"] = marker
            r["source"] = str(latest)
            all_rows.append(r)

    if not all_rows:
        raise SystemExit("no eval JSON could be parsed; aborting")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    headers = ["model", "dataset", "precision", "recall", "f1",
               "tp", "fp", "fn", "source"]
    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in all_rows:
            w.writerow({h: r.get(h, "") for h in headers})

    print(f"wrote {args.output} ({len(all_rows)} rows)")
    # also echo to stdout in a friendly grid
    print()
    print(f"{'model':<25} {'dataset':<18} {'P':>7} {'R':>7} {'F1':>7}")
    for r in all_rows:
        p = f"{r['precision']:.4f}" if r.get('precision') is not None else "n/a"
        rr = f"{r['recall']:.4f}" if r.get('recall') is not None else "n/a"
        f1 = f"{r['f1']:.4f}" if r.get('f1') is not None else "n/a"
        print(f"{r['model']:<25} {r['dataset']:<18} {p:>7} {rr:>7} {f1:>7}")


if __name__ == "__main__":
    main()

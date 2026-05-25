"""EXP-E step 1: Extract per-entity false positives (FP) from GPT-4o predictions.

Each predicted entity row is classified into exactly one of 5 rule-based FP
categories, with priority order:

  1. fabricated_entity     — no overlap with any gold mention at all
  2. span_boundary_error   — overlap exists but IoU < 0.5
  3. wrong_code            — IoU >= 0.5 but UMLS code differs from gold
  4. wrong_assertion       — code matches but assertion_status differs
  5. wrong_value_or_date   — code+assertion match but value/unit/date differs
  TP                       — none of the above (kept out of the FP set)

We use rule-based code matching (exact normalized string equality on the CUI
portion before "||"); the LLM judge (judge_fp.py) refines this with semantic
checks. The threshold IoU=0.5 follows eval_predictions.py's "any overlap"
heuristic with a stricter cutoff to separate near-misses (span boundary) from
solid matches (code-or-downstream errors).

PHI: output FP CSV embeds note context (predicted/gold mentions, surrounding
chars). NEVER commit to git — see project .gitignore (*.csv ignored).

Fail-fast policy (CLAUDE.md §2):
- Missing data directories / unreadable files raise.
- Missing prediction CSV for a gold note → fail unless --allow_missing_pred.
- Missing raw note text → fail unless --allow_missing_note.
- Numeric-coercion drops in start_pos/end_pos are logged (orthogonal to EXP-E
  scope; never silent).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# Dataset directory naming conventions (mirrors scripts/eval_predictions.py)
DATASET_DIRS = ["4CE", "coral_annotated_pdac", "coral_annotated_breastca"]


def _normalize_code(raw: object) -> str:
    """Extract just the CUI / code id from strings like 'C0004096||asthma'."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    head = s.split("||", 1)[0].strip().lower()
    return head


def _normalize_str(raw: object) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    return str(raw).strip().lower()


def _iou(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    a0, a1 = int(a[0]), int(a[1])
    b0, b1 = int(b[0]), int(b[1])
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = max(a1, b1) - min(a0, b0)
    if union <= 0:
        return 0.0
    return inter / union


def _best_overlap(pred_span: Tuple[int, int], gold_rows: List[dict]) -> Tuple[Optional[dict], float, int]:
    """Return (best_gold_row, iou, intersection_length) for the gold row with
    maximum intersection with pred_span. None if no overlap.
    """
    best_row, best_iou, best_inter = None, 0.0, 0
    p0, p1 = int(pred_span[0]), int(pred_span[1])
    for g in gold_rows:
        g0, g1 = int(g["start_pos"]), int(g["end_pos"])
        if p0 > g1 or g0 > p1:
            continue
        inter = max(0, min(p1, g1) - max(p0, g0))
        if inter <= 0:
            continue
        union = max(p1, g1) - min(p0, g0)
        iou = inter / union if union > 0 else 0.0
        if inter > best_inter:
            best_row, best_iou, best_inter = g, iou, inter
    return best_row, best_iou, best_inter


def _load_note_text(notes_root: Path, dataset_dir: str, note_id: str) -> str:
    """Read the raw note text. fail-fast if missing."""
    path = notes_root / dataset_dir / f"{note_id}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Note text not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def _coerce_span_cols(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Drop rows with non-integer start_pos / end_pos. Source CSVs occasionally
    have column-spill bugs (e.g. agent_type='gpt4o' landing in end_pos for a
    handful of rows in 4CE/UPMC_Note1_updated.csv). We *explicitly* log and
    drop these — not silent, but also not blocking (orthogonal data issue)."""
    df = df.dropna(subset=["start_pos", "end_pos"]).copy()
    df = df[(df["start_pos"].astype(str) != "-1") & (df["end_pos"].astype(str) != "-1")]
    before = len(df)
    df["start_pos"] = pd.to_numeric(df["start_pos"], errors="coerce")
    df["end_pos"] = pd.to_numeric(df["end_pos"], errors="coerce")
    df = df.dropna(subset=["start_pos", "end_pos"])
    dropped = before - len(df)
    if dropped > 0:
        print(
            f"[warn] {source}: dropped {dropped} rows with non-numeric start_pos/end_pos "
            "(likely CSV column-spill upstream — orthogonal to EXP-E)",
            file=sys.stderr,
        )
    df["start_pos"] = df["start_pos"].astype(int)
    df["end_pos"] = df["end_pos"].astype(int)
    return df


def _load_pred(pred_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(pred_csv)
    # Pred CSVs have an "Unnamed: 0" pandas-roundtrip artifact; drop it.
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])
    return _coerce_span_cols(df, str(pred_csv))


def _load_gold(gold_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(gold_csv)
    return _coerce_span_cols(df, str(gold_csv))


def classify_pred_row(
    pred_row: dict,
    gold_rows: List[dict],
    iou_threshold: float = 0.5,
) -> Tuple[str, Optional[dict], dict]:
    """Apply the 5-class rule-based taxonomy to a single predicted entity row.

    Returns (category, matched_gold_or_None, details). Categories:
      - "TP"                     (not an FP — caller will skip)
      - "fabricated_entity"
      - "span_boundary_error"
      - "wrong_code"
      - "wrong_assertion"
      - "wrong_value_or_date"
    """
    pred_span = (pred_row["start_pos"], pred_row["end_pos"])
    best_gold, iou, inter = _best_overlap(pred_span, gold_rows)

    details = {
        "iou": iou,
        "intersection_length": inter,
    }

    if best_gold is None:
        # No overlap with any gold mention at all.
        return "fabricated_entity", None, details

    if iou < iou_threshold:
        return "span_boundary_error", best_gold, details

    # Solid mention-level match. Now check code, then assertion, then value/date.
    pred_code = _normalize_code(pred_row.get("code"))
    gold_code = _normalize_code(best_gold.get("code"))
    if pred_code != gold_code:
        # Code mismatch (rule-based; LLM judge will refine since synonyms exist).
        details["pred_code"] = pred_code
        details["gold_code"] = gold_code
        return "wrong_code", best_gold, details

    # Codes match exactly. Check assertion.
    pred_assert = _normalize_str(pred_row.get("assertion_status"))
    gold_assert = _normalize_str(best_gold.get("assertion_status"))
    # CLINES treats Historical as Present (mirrors eval_predictions.py).
    if pred_assert == "historical":
        pred_assert = "present"
    if gold_assert == "historical":
        gold_assert = "present"
    if pred_assert != gold_assert and (pred_assert or gold_assert):
        details["pred_assertion"] = pred_assert
        details["gold_assertion"] = gold_assert
        return "wrong_assertion", best_gold, details

    # Assertion matches. Check value / unit / begin_date / end_date.
    value_date_cols = ["value", "unit", "begin_date", "end_date"]
    mismatches = {}
    for col in value_date_cols:
        p = _normalize_str(pred_row.get(col))
        g = _normalize_str(best_gold.get(col))
        if p == g:
            continue
        # Treat substring containment as match (mirrors eval_predictions.py
        # final string-comparison fallback).
        if p and g and (p in g or g in p):
            continue
        if p or g:
            mismatches[col] = {"pred": p, "gold": g}
    if mismatches:
        details["value_date_mismatches"] = mismatches
        return "wrong_value_or_date", best_gold, details

    # All four columns match → predicted entity is fully correct on this row.
    return "TP", best_gold, details


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract per-entity FP taxonomy")
    parser.add_argument(
        "--predictions_dir",
        default="outputs/with_positions",
        help="Directory holding *_gpt4o_with_positions.csv files",
    )
    parser.add_argument(
        "--gold_dir",
        default="outputs/reviewed_updated2",
        help="Directory with subdirs per dataset and *_updated.csv files",
    )
    parser.add_argument(
        "--notes_dir",
        default="data",
        help="Root of raw note text files (subdirs per dataset)",
    )
    parser.add_argument(
        "--model_tag",
        default="gpt4o",
        help="Predicted model tag (filename pattern: *_default_<tag>_with_positions.csv)",
    )
    parser.add_argument(
        "--output_csv",
        default="runs/EXP-E/fp_categorized.csv",
        help="Output FP CSV (contains note context — DO NOT COMMIT)",
    )
    parser.add_argument(
        "--output_counts_json",
        default="runs/EXP-E/category_counts.json",
        help="Output category count summary (no PHI; safe to commit)",
    )
    parser.add_argument(
        "--iou_threshold",
        type=float,
        default=0.5,
        help="IoU threshold separating span_boundary_error vs solid match",
    )
    parser.add_argument(
        "--context_chars",
        type=int,
        default=200,
        help="Half-window for note context excerpt around predicted span",
    )
    parser.add_argument(
        "--allow_missing_pred",
        action="store_true",
        help="If set, log + skip gold notes that have no matching prediction CSV. "
        "Without this flag we fail-fast (per CLAUDE.md §2). The default is "
        "strict mode — missing pred files indicate the prediction run was "
        "incomplete and FP counts will be biased.",
    )
    parser.add_argument(
        "--allow_missing_note",
        action="store_true",
        help="If set, log + skip notes whose raw .txt file is missing under "
        "--notes_dir. Without this flag we fail-fast (per CLAUDE.md §2).",
    )
    args = parser.parse_args()

    pred_dir = Path(args.predictions_dir)
    gold_dir = Path(args.gold_dir)
    notes_dir = Path(args.notes_dir)

    if not pred_dir.is_dir():
        raise FileNotFoundError(f"Predictions dir does not exist: {pred_dir}")
    if not gold_dir.is_dir():
        raise FileNotFoundError(f"Gold dir does not exist: {gold_dir}")
    if not notes_dir.is_dir():
        raise FileNotFoundError(f"Notes dir does not exist: {notes_dir}")

    # Enumerate (dataset, note_id) pairs from gold side; require matching pred file.
    pairs: List[Tuple[str, str, Path, Path]] = []
    missing_pred: List[Tuple[str, str, Path]] = []
    for dataset_dir in DATASET_DIRS:
        gold_subdir = gold_dir / dataset_dir
        if not gold_subdir.is_dir():
            # gold subdir absence is a real configuration error (DATASET_DIRS
            # is closed-vocab), fail-fast unconditionally.
            raise FileNotFoundError(
                f"Gold subdir missing: {gold_subdir}. Check --gold_dir and DATASET_DIRS."
            )
        for gold_file in sorted(gold_subdir.glob("*_updated.csv")):
            note_id = gold_file.name.replace("_updated.csv", "")
            pred_file = pred_dir / f"{dataset_dir}_{note_id}_default_{args.model_tag}_with_positions.csv"
            if not pred_file.exists():
                missing_pred.append((dataset_dir, note_id, pred_file))
                continue
            pairs.append((dataset_dir, note_id, pred_file, gold_file))

    if missing_pred and not args.allow_missing_pred:
        msgs = "\n  ".join(f"{ds}/{nid}: {p}" for ds, nid, p in missing_pred[:5])
        more = f"\n  ... +{len(missing_pred) - 5} more" if len(missing_pred) > 5 else ""
        raise FileNotFoundError(
            f"Missing prediction CSVs for {len(missing_pred)} gold notes:\n  {msgs}{more}\n"
            "Aborting per CLAUDE.md §2 fail-fast. Re-invoke with --allow_missing_pred "
            "to log+skip them (and accept incomplete FP coverage)."
        )
    if missing_pred:
        print(
            f"[warn] {len(missing_pred)} gold notes have no matching pred CSV "
            f"(--allow_missing_pred enabled); skipping",
            file=sys.stderr,
        )
        for ds, nid, p in missing_pred:
            print(f"  [skip] no pred for {ds}/{nid}: {p}", file=sys.stderr)

    if not pairs:
        raise RuntimeError(
            f"No (pred, gold) pairs found. pred_dir={pred_dir} gold_dir={gold_dir} model_tag={args.model_tag}"
        )

    print(f"[info] matched {len(pairs)} (pred, gold) pairs", file=sys.stderr)

    out_rows: List[dict] = []
    counts: Dict[str, Dict[str, int]] = {}  # counts[dataset][category]
    tp_count: Dict[str, int] = {}

    for dataset_dir, note_id, pred_file, gold_file in pairs:
        dataset_label = {
            "coral_annotated_pdac": "coral_pdac",
            "coral_annotated_breastca": "coral_breastca",
        }.get(dataset_dir, dataset_dir)

        try:
            note_text = _load_note_text(notes_dir, dataset_dir, note_id)
        except FileNotFoundError as e:
            if not args.allow_missing_note:
                raise FileNotFoundError(
                    f"{e}. Aborting per CLAUDE.md §2 fail-fast. Re-invoke with "
                    "--allow_missing_note to log+skip."
                )
            print(f"[skip] {e}", file=sys.stderr)
            continue

        pred_df = _load_pred(pred_file)
        gold_df = _load_gold(gold_file)
        gold_rows = gold_df.to_dict("records")

        counts.setdefault(dataset_label, {})
        tp_count.setdefault(dataset_label, 0)

        for _, pred_row in pred_df.iterrows():
            pr = pred_row.to_dict()
            cat, matched_gold, details = classify_pred_row(
                pr, gold_rows, iou_threshold=args.iou_threshold
            )

            if cat == "TP":
                tp_count[dataset_label] += 1
                continue

            counts[dataset_label][cat] = counts[dataset_label].get(cat, 0) + 1

            # Build note excerpt around predicted span (for human / LLM judge review)
            p0 = int(pr["start_pos"])
            p1 = int(pr["end_pos"])
            c0 = max(0, p0 - args.context_chars)
            c1 = min(len(note_text), p1 + args.context_chars)
            note_excerpt = note_text[c0:c1]

            row = {
                "dataset": dataset_label,
                "dataset_dir": dataset_dir,
                "note_id": note_id,
                "category_rule": cat,
                "pred_start": p0,
                "pred_end": p1,
                "pred_mention": pr.get("mention"),
                "pred_code": pr.get("code"),
                "pred_assertion_status": pr.get("assertion_status"),
                "pred_value": pr.get("value"),
                "pred_unit": pr.get("unit"),
                "pred_begin_date": pr.get("begin_date"),
                "pred_end_date": pr.get("end_date"),
                "gold_start": matched_gold.get("start_pos") if matched_gold else None,
                "gold_end": matched_gold.get("end_pos") if matched_gold else None,
                "gold_mention": matched_gold.get("mention") if matched_gold else None,
                "gold_code": matched_gold.get("code") if matched_gold else None,
                "gold_assertion_status": matched_gold.get("assertion_status") if matched_gold else None,
                "gold_value": matched_gold.get("value") if matched_gold else None,
                "gold_unit": matched_gold.get("unit") if matched_gold else None,
                "gold_begin_date": matched_gold.get("begin_date") if matched_gold else None,
                "gold_end_date": matched_gold.get("end_date") if matched_gold else None,
                "iou": details.get("iou"),
                "intersection_length": details.get("intersection_length"),
                "details_json": json.dumps(
                    {k: v for k, v in details.items() if k not in ("iou", "intersection_length")},
                    default=str,
                ),
                "note_excerpt": note_excerpt,
                "note_excerpt_start": c0,
                "note_excerpt_end": c1,
            }
            out_rows.append(row)

    out_df = pd.DataFrame(out_rows)
    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    print(f"[done] wrote {len(out_df)} FP rows to {out_path}", file=sys.stderr)

    # Numeric summary (PHI-safe, commit-friendly)
    summary = {
        "model_tag": args.model_tag,
        "iou_threshold": args.iou_threshold,
        "total_pred_entities": len(out_df) + sum(tp_count.values()),
        "total_fp": len(out_df),
        "tp_per_dataset": tp_count,
        "fp_counts_per_dataset": counts,
        "fp_counts_total": {},
        "fp_percent_total": {},
    }
    total_fp = len(out_df)
    totals: Dict[str, int] = {}
    for ds_counts in counts.values():
        for cat, n in ds_counts.items():
            totals[cat] = totals.get(cat, 0) + n
    summary["fp_counts_total"] = totals
    summary["fp_percent_total"] = {
        cat: round(100.0 * n / total_fp, 2) if total_fp else 0.0
        for cat, n in totals.items()
    }

    json_path = Path(args.output_counts_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[done] wrote summary to {json_path}", file=sys.stderr)
    print(json.dumps(summary, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())

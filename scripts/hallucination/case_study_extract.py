"""EXP-E step 3: pick representative case-study examples for paper Discussion.

For each of the 5 FP categories (or 'not_an_error'), select N highest-confidence
judge-agreed examples plus N pure-rule examples (when judge output unavailable).

PHI redaction: note excerpts are scrubbed of obvious PHI patterns before
writing to the committable case_study_examples.md:
  - Dates → "[DATE]"
  - 5-digit zip codes / 9-digit-ish IDs → "[ID]"
  - Names: lower-case "YYYY" placeholder kept as-is (already a CLINES synthetic
    placeholder); other proper-noun heuristic — caller should manually review
    the committed .md before pushing to remote.

NOTE: this redactor is NOT a full safe-harbor implementation. The committed
case_study_examples.md MUST be reviewed manually by Zongxin before sharing.
For internal-only review, prefer reading runs/EXP-E/fp_judged.csv directly
(it stays out of git via *.csv gitignore).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd


# Conservative PHI-ish regexes. Anything ambiguous is left alone for manual review.
_DATE_RE = re.compile(
    r"\b("
    r"\d{4}-\d{1,2}-\d{1,2}"
    r"|\d{1,2}/\d{1,2}/\d{2,4}"
    r"|\d{1,2}-\d{1,2}-\d{2,4}"
    r"|\d{1,2}_\d{1,2}_\d{2,4}"  # CLINES-style [8_4_2019]
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z.]*\s+\d{1,2},?\s+\d{2,4}"
    r")\b",
    re.IGNORECASE,
)
_LONGID_RE = re.compile(r"\b\d{6,}\b")
_PHONE_RE = re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b")
_MRN_RE = re.compile(r"\b(?:MRN|mrn)\s*[:#]?\s*\d+\b")
# Strings of asterisks (already-redacted PHI in CORAL) — collapse to readable token
_STARS_RE = re.compile(r"(\*{3,}\s*){2,}")
# Bracketed placeholder tokens (already-redacted Microsoft Presidio outputs in 4CE)
_BRACKET_PHI_RE = re.compile(
    r"\[\s*(PERSONALNAME|PERSON|ADDRESS|EMAIL|PHONE|SSN|DATE|LOCATION|ORG|MRN|ID)\s*\]",
    re.IGNORECASE,
)


def redact_excerpt(text: str) -> str:
    if text is None:
        return ""
    s = str(text)
    # Order matters: bracketed-PHI placeholders first (already redacted upstream)
    s = _BRACKET_PHI_RE.sub("[REDACTED]", s)
    s = _STARS_RE.sub("[REDACTED] ", s)
    s = _DATE_RE.sub("[DATE]", s)
    s = _PHONE_RE.sub("[PHONE]", s)
    s = _MRN_RE.sub("[MRN]", s)
    s = _LONGID_RE.sub("[ID]", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _pick_examples(
    df: pd.DataFrame,
    judge_col: str,
    category: str,
    n_per_dataset: int,
) -> List[dict]:
    """Pick up to n_per_dataset examples per dataset for the given category.

    Preference: highest judge_confidence, then shortest excerpt (easier to fit
    in paper). Falls back to rule-only if judge_col missing.
    """
    if judge_col in df.columns:
        sub = df[df[judge_col] == category].copy()
    else:
        sub = df[df["category_rule"] == category].copy()

    if sub.empty:
        return []

    examples: List[dict] = []
    for ds, group in sub.groupby("dataset"):
        g = group.copy()
        if "judge_confidence" in g.columns:
            g = g.sort_values(by="judge_confidence", ascending=False, na_position="last")
        # Prefer shorter excerpts as a tiebreaker
        g["_exc_len"] = g["note_excerpt"].fillna("").str.len()
        g = g.sort_values(by="_exc_len", ascending=True, kind="stable")
        examples.extend(g.head(n_per_dataset).to_dict("records"))
    return examples


def _rfield(value, redact: bool) -> str:
    """Render a single field (mention / code / value / date) with optional
    redaction. The redactor MUST be applied to anything that came from the
    source notes — that includes pred_*/gold_* mention/value/date/unit cells
    (these are extracted from note text by GPT-4o and the gold annotators).
    Only code (CUI||term) and assertion_status are safe to emit raw because
    they're closed-vocabulary UMLS / categorical labels."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "nan"
    s = str(value)
    if redact:
        s = redact_excerpt(s)
    return s


def _format_example(ex: dict, redact: bool) -> str:
    excerpt = ex.get("note_excerpt", "")
    if redact:
        excerpt = redact_excerpt(excerpt)
    iou = ex.get("iou")
    iou_str = f"{iou:.2f}" if pd.notna(iou) else "n/a"
    gold_block = ""
    if pd.notna(ex.get("gold_mention")):
        gold_block = (
            f"- **Gold (best overlap, IoU={iou_str})**: "
            f"mention=`{_rfield(ex.get('gold_mention'), redact)}`, "
            f"code=`{ex.get('gold_code')}`, "
            f"assertion=`{ex.get('gold_assertion_status')}`, "
            f"value=`{_rfield(ex.get('gold_value'), redact)}`, "
            f"unit=`{_rfield(ex.get('gold_unit'), redact)}`, "
            f"begin_date=`{_rfield(ex.get('gold_begin_date'), redact)}`, "
            f"end_date=`{_rfield(ex.get('gold_end_date'), redact)}`\n"
        )
    else:
        gold_block = "- **Gold**: no overlapping gold entity\n"

    judge_block = ""
    if pd.notna(ex.get("judge_category")):
        rationale = ex.get("judge_rationale", "")
        if redact:
            rationale = redact_excerpt(rationale)
        judge_block = (
            f"- **Judge ({ex.get('judge_category')}, conf={ex.get('judge_confidence')})**: "
            f"{rationale}\n"
        )

    return (
        f"#### {ex.get('dataset')} / note `{ex.get('note_id')}` / span "
        f"({ex.get('pred_start')}, {ex.get('pred_end')})\n\n"
        f"- **Note excerpt** (chars {ex.get('note_excerpt_start')}–{ex.get('note_excerpt_end')}):\n"
        f"  > {excerpt}\n"
        f"- **Predicted**: mention=`{_rfield(ex.get('pred_mention'), redact)}`, "
        f"code=`{ex.get('pred_code')}`, "
        f"assertion=`{ex.get('pred_assertion_status')}`, "
        f"value=`{_rfield(ex.get('pred_value'), redact)}`, "
        f"unit=`{_rfield(ex.get('pred_unit'), redact)}`, "
        f"begin_date=`{_rfield(ex.get('pred_begin_date'), redact)}`, "
        f"end_date=`{_rfield(ex.get('pred_end_date'), redact)}`\n"
        f"{gold_block}"
        f"- **Rule category**: `{ex.get('category_rule')}`\n"
        f"{judge_block}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract case-study examples per FP category")
    parser.add_argument(
        "--fp_judged_csv",
        default="runs/EXP-E/fp_judged.csv",
        help="Judged FP CSV from judge_fp.py (preferred)",
    )
    parser.add_argument(
        "--fp_rule_csv",
        default="runs/EXP-E/fp_categorized.csv",
        help="Rule-only FP CSV from extract_fp.py (fallback if judge unavailable)",
    )
    parser.add_argument(
        "--output_md",
        default="runs/EXP-E/case_study_examples.md",
        help="Output markdown (PHI-redacted; review manually before commit)",
    )
    parser.add_argument(
        "--n_per_dataset",
        type=int,
        default=2,
        help="Number of examples per (category, dataset)",
    )
    parser.add_argument(
        "--allow_rule_only",
        action="store_true",
        help="EXPLICITLY allow falling back to rule-only categorization when "
        "judged CSV does not exist. Without this flag we fail-fast (per "
        "CLAUDE.md §2) because the rule labels overcount true hallucination.",
    )
    parser.add_argument(
        "--redact",
        action="store_true",
        default=True,
        help="Apply PHI-redaction regexes (default: True)",
    )
    parser.add_argument(
        "--no-redact",
        dest="redact",
        action="store_false",
        help="Disable PHI redaction (DO NOT use for committed output)",
    )
    args = parser.parse_args()

    # Prefer judged file if it exists. If not, fail-fast unless caller
    # explicitly opted-in to rule-only fallback (per CLAUDE.md §2 — silent
    # fallback forbidden).
    judged_path = Path(args.fp_judged_csv)
    rule_path = Path(args.fp_rule_csv)
    if judged_path.exists():
        df = pd.read_csv(judged_path)
        judge_col = "judge_category"
        print(f"[info] using judged FP: {judged_path}", file=sys.stderr)
    elif rule_path.exists() and args.allow_rule_only:
        df = pd.read_csv(rule_path)
        judge_col = "category_rule"
        print(
            f"[warn] judged FP not found; rule-only fallback explicitly enabled "
            f"via --allow_rule_only: {rule_path}. The 'fabricated_entity' bucket "
            "is known to overcount true hallucination by ~the size of the "
            "annotation-gap pool — interpret with care.",
            file=sys.stderr,
        )
    elif rule_path.exists() and not args.allow_rule_only:
        raise RuntimeError(
            f"Judged FP not found at {judged_path}, and --allow_rule_only "
            "was NOT passed. Aborting per CLAUDE.md §2 (no silent fallback). "
            "Either (a) run judge_fp.py first, or (b) re-invoke with "
            "--allow_rule_only to use rule-based categorization (less accurate)."
        )
    else:
        raise FileNotFoundError(
            f"Neither {judged_path} nor {rule_path} exists. Run extract_fp.py first."
        )

    categories = [
        "fabricated_entity",
        "span_boundary_error",
        "wrong_code",
        "wrong_assertion",
        "wrong_value_or_date",
    ]

    out_lines = [
        "# EXP-E: GPT-4o Hallucination — Case Studies",
        "",
        "Selected representative examples per FP category, for paper Discussion §3.5.",
        "Excerpts are PHI-redacted by a conservative regex sweep (dates/MRN/IDs); "
        "**Zongxin must manually review before public release**.",
        "",
        f"Source: `{judged_path.name if judged_path.exists() else rule_path.name}` "
        f"(judge_col=`{judge_col}`).",
        "",
    ]

    for cat in categories:
        out_lines.append(f"## Category: `{cat}`")
        out_lines.append("")
        examples = _pick_examples(df, judge_col, cat, args.n_per_dataset)
        if not examples:
            out_lines.append("_(no examples)_\n")
            continue
        for ex in examples:
            out_lines.append(_format_example(ex, redact=args.redact))
            out_lines.append("")

    out_path = Path(args.output_md)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"[done] wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

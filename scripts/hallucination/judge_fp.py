"""EXP-E step 2: LLM-as-judge (GPT-4.1) refines rule-based FP categorization.

For each rule-categorized FP row, the judge receives:
  - Note excerpt surrounding the predicted span
  - Predicted entity (mention / code / assertion / value / dates)
  - Best-overlapping gold entity (or "none" for fabricated_entity candidates)
  - The 5-class taxonomy definitions
  - The rule-based candidate label

The judge returns a JSON object:
  {
    "category": "<one of the 5 classes or 'not_an_error'>",
    "rationale": "<short>",
    "confidence": <0.0-1.0>
  }

Why GPT-4.1: avoids self-evaluation bias since the predictions came from
gpt-4o-1120 (task constraint).

Fail-fast: OPENAIKEY unset → abort. API exception → explicit retry loop in
openai_provider.py; final failure raises. We do NOT silently drop rows.

PHI: judge_output.csv embeds note context. NEVER commit (already in
project .gitignore: *.csv).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# Ensure llm_interface importable from project root
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from llm_interface.providers.openai_provider import wrap_openai_chat  # noqa: E402


TAXONOMY_DEFINITIONS = """
The 5-class hallucination FP taxonomy:

1. fabricated_entity — The predicted entity refers to a clinical concept that
   is NOT present in the source note at all (e.g., predicting "diabetes" when
   the note never mentions diabetes or any equivalent term/abbreviation).
   The model invented information out of thin air.

2. span_boundary_error — A real clinical concept exists at this approximate
   location in the note, but the predicted span boundaries are wrong
   (too short, too long, or shifted). The mention itself is mostly correct
   semantically; only the character positions are off.

3. wrong_code — The mention is correctly identified (right text span, right
   underlying concept), but the predicted UMLS CUI is wrong (e.g., COVID-19
   labelled when source says "suspected COVID-19" → should be C5203671 not
   C5203670). Includes synonyms that map to a different CUI than gold.

4. wrong_assertion — Mention and code are correct, but assertion status is
   wrong (Present vs. Absent vs. Possible vs. Conditional). Common failure:
   negation scope or hypothetical wording misclassified.

5. wrong_value_or_date — Mention, code, and assertion are correct, but the
   associated numeric value, unit, or date (begin_date / end_date) is wrong
   or fabricated. Includes "model filled in a value gold left blank" (model
   over-specifies) and "model left blank a value gold has" (model omits).

Special label:
- not_an_error — On manual inspection, the predicted entity is actually
   correct and the rule-based system marked it FP due to gold-side
   annotation incompleteness, synonym mismatch, or other artifacts. Use this
   ONLY when confident; it triggers downstream removal from the FP set.
"""

JUDGE_SYSTEM_PROMPT = (
    "You are a clinical NLP error-analysis annotator. You will be shown a "
    "false-positive prediction from a clinical entity extractor (GPT-4o based) "
    "and asked to assign it to one of 5 hallucination categories.\n\n"
    + TAXONOMY_DEFINITIONS
    + "\n\nRespond with ONLY a JSON object of the form:\n"
    '{\n'
    '  "category": "fabricated_entity" | "span_boundary_error" | "wrong_code" | '
    '"wrong_assertion" | "wrong_value_or_date" | "not_an_error",\n'
    '  "rationale": "<one or two sentences>",\n'
    '  "confidence": <float 0.0-1.0>\n'
    '}\n'
    "Do not add any text before or after the JSON."
)


def _build_user_prompt(row: dict) -> str:
    """Build the per-FP judge prompt."""
    gold_block: str
    if pd.isna(row.get("gold_start")) or row.get("gold_mention") is None or (
        isinstance(row.get("gold_mention"), float) and pd.isna(row.get("gold_mention"))
    ):
        gold_block = "GOLD ENTITY (best overlap): NONE — no gold entity overlaps with this predicted span."
    else:
        gold_block = (
            "GOLD ENTITY (best overlap):\n"
            f"  - span: ({int(row['gold_start'])}, {int(row['gold_end'])})\n"
            f"  - mention: {row.get('gold_mention')}\n"
            f"  - code: {row.get('gold_code')}\n"
            f"  - assertion_status: {row.get('gold_assertion_status')}\n"
            f"  - value: {row.get('gold_value')}\n"
            f"  - unit: {row.get('gold_unit')}\n"
            f"  - begin_date: {row.get('gold_begin_date')}\n"
            f"  - end_date: {row.get('gold_end_date')}\n"
            f"  - IoU with prediction: {row.get('iou'):.3f}"
        )

    user = (
        f"DATASET: {row.get('dataset')}    NOTE: {row.get('note_id')}\n\n"
        f"NOTE EXCERPT (chars {row.get('note_excerpt_start')}–{row.get('note_excerpt_end')}):\n"
        f"---\n{row.get('note_excerpt')}\n---\n\n"
        "PREDICTED ENTITY:\n"
        f"  - span: ({int(row['pred_start'])}, {int(row['pred_end'])})\n"
        f"  - mention: {row.get('pred_mention')}\n"
        f"  - code: {row.get('pred_code')}\n"
        f"  - assertion_status: {row.get('pred_assertion_status')}\n"
        f"  - value: {row.get('pred_value')}\n"
        f"  - unit: {row.get('pred_unit')}\n"
        f"  - begin_date: {row.get('pred_begin_date')}\n"
        f"  - end_date: {row.get('pred_end_date')}\n\n"
        f"{gold_block}\n\n"
        f"RULE-BASED CANDIDATE LABEL: {row.get('category_rule')}\n\n"
        "Task: Determine the correct hallucination category for THIS predicted "
        "entity. Re-read the note excerpt carefully. The rule-based label may be "
        "wrong; use your own judgment. Respond with only the JSON object."
    )
    return user


_JSON_PATTERN = re.compile(r"\{[\s\S]*\}")


def _parse_judge_output(content: str) -> Dict:
    """Extract the JSON object from the model response. Fail-fast on parse error."""
    m = _JSON_PATTERN.search(content)
    if not m:
        raise ValueError(f"No JSON object found in judge response: {content[:200]!r}")
    raw = m.group(0)
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Judge response JSON parse error: {e}; raw={raw[:200]!r}")
    if "category" not in obj:
        raise ValueError(f"Judge response missing 'category' key: {obj}")
    return obj


VALID_CATEGORIES = {
    "fabricated_entity",
    "span_boundary_error",
    "wrong_code",
    "wrong_assertion",
    "wrong_value_or_date",
    "not_an_error",
}


def judge_one(chat_fn, row: dict, max_retries: int = 3) -> Dict:
    """Call GPT-4.1 to judge a single FP row. Returns the parsed JSON dict.

    Retries on API failure (handled in openai_provider). Parse failure
    triggers explicit reattempt up to max_retries with stricter system
    instruction; final failure raises.
    """
    user_prompt = _build_user_prompt(row)
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    last_err: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            result = chat_fn(messages, retry=True, max_retries=3, retry_delay=2)
            content = result["content"]
            parsed = _parse_judge_output(content)
            if parsed["category"] not in VALID_CATEGORIES:
                raise ValueError(
                    f"Judge returned invalid category {parsed['category']!r}; "
                    f"expected one of {VALID_CATEGORIES}"
                )
            parsed.setdefault("rationale", "")
            parsed.setdefault("confidence", None)
            return parsed
        except Exception as e:
            last_err = e
            # Stricter retry: add a reminder to user prompt
            messages = [
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt
                    + "\n\nIMPORTANT: respond with ONLY a valid JSON object, no prose."},
            ]
            print(
                f"[warn] judge attempt {attempt + 1}/{max_retries} failed: {e}",
                file=sys.stderr,
            )
            time.sleep(1 + attempt)
    raise RuntimeError(
        f"Judge failed after {max_retries} attempts. Last err: {last_err}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM-as-judge FP categorization")
    parser.add_argument(
        "--fp_csv",
        default="runs/EXP-E/fp_categorized.csv",
        help="Input FP CSV from extract_fp.py",
    )
    parser.add_argument(
        "--output_csv",
        default="runs/EXP-E/fp_judged.csv",
        help="Output CSV: original FP rows + judge_category/judge_rationale/judge_confidence",
    )
    parser.add_argument(
        "--output_counts_json",
        default="runs/EXP-E/judge_category_counts.json",
        help="Output: judge-based category counts and judge-vs-rule agreement",
    )
    parser.add_argument(
        "--sample_per_category",
        type=int,
        default=0,
        help="If > 0, randomly sample N FPs per rule-category to limit cost",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Sampling seed",
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Hard cap on total FPs judged (0 = no cap)",
    )
    parser.add_argument(
        "--model_tag", default="gpt4.1", help="LLM judge model_tag (must be in openai_provider n2n_dict)",
    )
    parser.add_argument(
        "--progress_every", type=int, default=20,
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="If output_csv exists, skip already-judged rows (matched by dataset+note_id+pred_start+pred_end)",
    )
    args = parser.parse_args()

    # Hard fail-fast on missing env vars (per CLAUDE.md §2).
    # Both OPENAIKEY and OPENAIENDPOINT must be explicitly set — no silent
    # default fallback. The user must source their HMS API config before
    # running this script (run_inference.sh does this; reuse that idiom).
    if not os.getenv("OPENAIKEY"):
        print(
            "[fatal] OPENAIKEY env var not set. Aborting per CLAUDE.md §2 fail-fast.",
            file=sys.stderr,
        )
        return 2
    if not os.getenv("OPENAIENDPOINT"):
        print(
            "[fatal] OPENAIENDPOINT env var not set. Aborting per CLAUDE.md §2 "
            "fail-fast. Expected: https://azure-ai.hms.edu",
            file=sys.stderr,
        )
        return 2

    fp_csv = Path(args.fp_csv)
    if not fp_csv.exists():
        raise FileNotFoundError(f"FP CSV does not exist: {fp_csv}. Run extract_fp.py first.")

    df = pd.read_csv(fp_csv)
    print(f"[info] loaded {len(df)} FP rows from {fp_csv}", file=sys.stderr)

    # Attach a stable row identifier from the input CSV. This is the resume
    # dedup key — using (dataset, note_id, pred_start, pred_end) is NOT
    # sufficient because the input CSV contains a small number of duplicate
    # spans (e.g., the same pred entity appearing in two different chunks).
    # fp_row_idx is the row's position in fp_csv (0-indexed) and is unique
    # by construction.
    df = df.reset_index(drop=True)
    df["fp_row_idx"] = df.index

    # Optional sampling
    if args.sample_per_category > 0:
        rng = random.Random(args.seed)
        sampled_idx: List[int] = []
        for cat, group in df.groupby("category_rule"):
            n = min(args.sample_per_category, len(group))
            sampled_idx.extend(rng.sample(list(group.index), n))
        df_to_judge = df.loc[sorted(sampled_idx)].reset_index(drop=True)
        print(
            f"[info] sampled {len(df_to_judge)} rows ({args.sample_per_category} per rule-category)",
            file=sys.stderr,
        )
    else:
        df_to_judge = df.copy()

    if args.limit > 0 and len(df_to_judge) > args.limit:
        df_to_judge = df_to_judge.head(args.limit).copy()
        print(f"[info] limited to first {args.limit} rows", file=sys.stderr)

    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume support: skip rows already in output_csv. Key = fp_row_idx
    # (unique per row in the input CSV) — see "fp_row_idx" assignment above
    # for why (dataset, note_id, pred_start, pred_end) is unsafe.
    already_judged: set = set()
    if args.resume and out_path.exists():
        existing = pd.read_csv(out_path)
        if "fp_row_idx" not in existing.columns:
            raise RuntimeError(
                f"Resume requested but {out_path} has no 'fp_row_idx' column. "
                "Output was likely generated by an older version of judge_fp.py. "
                "Either delete the file and re-run, or back it up and start fresh."
            )
        for _, r in existing.iterrows():
            already_judged.add(int(r["fp_row_idx"]))
        print(f"[info] resume: skipping {len(already_judged)} previously judged rows", file=sys.stderr)

    chat_fn = wrap_openai_chat(args.model_tag)

    # Append mode: open file for appending, but write header if not exists
    write_header = not out_path.exists() or out_path.stat().st_size == 0
    file_handle = open(out_path, "a", buffering=1)  # line-buffered

    judged_rows: List[dict] = []
    skipped = 0
    try:
        for i, row in df_to_judge.iterrows():
            row_d = row.to_dict()
            key = int(row_d["fp_row_idx"])
            if key in already_judged:
                skipped += 1
                continue

            try:
                judged = judge_one(chat_fn, row_d)
            except Exception as e:
                print(
                    f"[fatal] judge_one failed on row {i} "
                    f"(dataset={row_d.get('dataset')}, note_id={row_d.get('note_id')}, "
                    f"pred_span=({row_d.get('pred_start')},{row_d.get('pred_end')})): {e}",
                    file=sys.stderr,
                )
                raise

            row_d["judge_category"] = judged["category"]
            row_d["judge_rationale"] = judged.get("rationale", "")
            row_d["judge_confidence"] = judged.get("confidence")
            judged_rows.append(row_d)

            # Stream incrementally to disk (avoid losing progress on long runs)
            out_df_single = pd.DataFrame([row_d])
            out_df_single.to_csv(file_handle, header=write_header, index=False)
            write_header = False

            if (i + 1) % args.progress_every == 0:
                print(
                    f"[progress] judged {i + 1}/{len(df_to_judge)} (skipped {skipped})",
                    file=sys.stderr,
                )
    finally:
        file_handle.close()

    print(f"[done] judged {len(judged_rows)} rows (skipped {skipped})", file=sys.stderr)

    # Re-load full output for summary (covers resume case)
    full_out = pd.read_csv(out_path)
    summary = {
        "model_tag": args.model_tag,
        "n_judged": int(len(full_out)),
        "judge_category_counts": full_out["judge_category"].value_counts().to_dict(),
        "judge_category_percent": {
            k: round(100.0 * v / len(full_out), 2)
            for k, v in full_out["judge_category"].value_counts().to_dict().items()
        },
        "rule_vs_judge_agreement_overall": float(
            (full_out["category_rule"] == full_out["judge_category"]).mean()
        ),
        "rule_vs_judge_per_rule": {
            k: {
                "n": int((full_out["category_rule"] == k).sum()),
                "agree": int(
                    ((full_out["category_rule"] == k) & (full_out["judge_category"] == k)).sum()
                ),
                "judge_breakdown": full_out.loc[full_out["category_rule"] == k, "judge_category"]
                .value_counts()
                .to_dict(),
            }
            for k in full_out["category_rule"].unique()
        },
    }
    json_path = Path(args.output_counts_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"[done] wrote summary to {json_path}", file=sys.stderr)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

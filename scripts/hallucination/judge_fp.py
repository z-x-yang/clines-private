"""EXP-E2 step 2: LLM-as-judge (GPT-4.1) refines rule-based FP categorization.

7-class taxonomy (EXP-E2 replaces EXP-E's 5+1 with 6+1, splitting
wrong_value_or_date into wrong_value and wrong_date):

  1. fabricated_entity     — model invented; no concept in note
  2. span_boundary_error   — concept real but span boundaries wrong
  3. wrong_assertion       — concept+span ok, assertion polarity wrong
  4. wrong_code            — concept+assertion ok, UMLS code wrong
  5. wrong_value           — value field wrong (numeric or unit error)
  6. wrong_date            — begin_date / end_date wrong
  7. not_an_error          — annotation gap / equivalent / acceptable variant

EXP-E (5+1) lumped value/unit/date errors into a single wrong_value_or_date
bucket which extrapolated to 43.2% of FP — too coarse to act on, and likely
inflated by "value field omission disagreement" cases that are actually
equivalent under reasonable medical-NLP semantics. EXP-E2 fixes by:
  (a) splitting wrong_value vs wrong_date
  (b) broadening the not_an_error definition (see prompt below)
  (c) supplying few-shot examples to anchor each category

Why GPT-4.1 as judge: avoids self-evaluation bias on GPT-4o predictions.

Fail-fast: missing OPENAIKEY / OPENAIENDPOINT → abort. API exception →
explicit retry loop (in openai_provider). Final failure raises. We never
silently drop rows.

PHI: judge_output.csv embeds note context. NEVER commit.
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

# Make llm_interface importable from project root.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from llm_interface.providers.openai_provider import wrap_openai_chat  # noqa: E402


# ----------------------------------------------------------------------------
# 7-class taxonomy + few-shot examples
# ----------------------------------------------------------------------------

TAXONOMY_DEFINITIONS = """
The 7-class hallucination FP taxonomy (one label per row, mutually exclusive,
applied in priority order — pick the EARLIEST category that fits):

1. fabricated_entity — The predicted entity refers to a clinical concept that
   is NOT present in the source note at all (the note never mentions this
   concept or any equivalent term/abbreviation/synonym). The model invented
   information out of thin air.

2. span_boundary_error — A real clinical concept exists at this approximate
   location in the note, but the predicted span boundaries are wrong (too
   short, too long, or shifted). The mention semantics are mostly correct;
   only the character positions are off. Treat as span boundary error ONLY
   if the underlying concept (CUI) is also correct — if the span is off AND
   the CUI is wrong, classify as wrong_code (the span is incidental).

3. wrong_assertion — Mention and code are correct, but assertion status is
   wrong (Present vs Absent vs Possible vs Conditional). Common failure:
   negation scope or hypothetical wording misclassified.

4. wrong_code — The mention text/span is correctly identified, but the
   predicted UMLS CUI is wrong (e.g., COVID-19 labelled when source says
   "suspected COVID-19" — should be C5203671 not C5203670). Includes cases
   where a near-synonym maps to a different CUI than gold.

5. wrong_value — Mention, code, and assertion are correct, but the
   associated numeric VALUE or UNIT is wrong. Includes:
     - Pred fills a value not present in the note (genuine fabrication)
     - Pred reads the wrong number from the note ("3.5" vs "3.6")
     - Unit mismatch that materially changes the meaning ("mg/dL" vs "g/dL"
       where the numeric value also differs by factor of 1000)
   Does NOT include: equivalent unit / format differences ("3.5g/dL" vs
   "3.5 g/dl") — those go to not_an_error.

6. wrong_date — Mention, code, and assertion are correct, but begin_date
   or end_date is wrong. Includes:
     - Pred fabricates a date not in the note
     - Pred picks the wrong date when multiple are mentioned
     - Off-by-one-day errors that materially change meaning
   Does NOT include: equivalent date formats ("2023-01-05" vs "1/5/2023") —
   those go to not_an_error.

7. not_an_error — On careful manual inspection, the predicted entity is
   actually CORRECT and the rule-based system marked it FP due to:
     a) Annotation gap — gold simply did not annotate this valid clinical
        concept (gold-side incompleteness, not a model error).
     b) Synonym mismatch — pred uses a different but EQUIVALENT term/CUI
        ("DM" vs "diabetes mellitus" vs "DM2"; "MI" vs "myocardial
        infarction") that resolves to the same clinical concept.
     c) Equivalent value/unit/date format — different surface form but
        same semantics ("3.5g/dL" vs "3.5 g/dl"; "2023-01-05" vs
        "1/5/2023" vs "January 5, 2023").
     d) Missing-but-not-required — pred leaves a value/unit/date field
        blank, and the note ALSO does not specify it. (Pred is correct to
        leave blank; gold may have inferred it from elsewhere.)
     e) Acceptable alternate value — gold has multiple equivalent
        candidates and pred chose one (e.g. lab value rounded differently
        but within reporting tolerance).
   Use not_an_error WHENEVER the prediction is medically defensible and
   the disagreement reflects annotation noise rather than a model mistake.
"""

# Few-shot examples illustrating each category. Synthetic for clarity; do not
# leak PHI. Each example shows: note excerpt → pred / gold → correct label +
# 1-sentence rationale. Designed to anchor the judge's interpretation of the
# trickier boundaries (especially: wrong_value vs wrong_date vs not_an_error).
FEW_SHOT_EXAMPLES = """
=== EXAMPLES (synthetic, illustrating each category) ===

EXAMPLE 1 — fabricated_entity
NOTE EXCERPT: "Patient presents with persistent cough and fatigue. No fever."
PRED: mention="diabetes", code="C0011847||diabetes mellitus", assertion="Present"
GOLD: NONE (no overlap)
CORRECT: {"category": "fabricated_entity",
          "rationale": "The note discusses cough/fatigue/fever; diabetes is never mentioned in any form.",
          "confidence": 0.99}

EXAMPLE 2 — span_boundary_error
NOTE EXCERPT: "...complaining of severe abdominal pain for 3 days..."
PRED: span=(35,40) mention="pain", code="C0030193||pain"
GOLD: span=(28,40) mention="abdominal pain", code="C0030193||pain"
CORRECT: {"category": "span_boundary_error",
          "rationale": "Concept (pain CUI) is correct but span dropped the 'abdominal' modifier.",
          "confidence": 0.95}

EXAMPLE 3 — wrong_assertion
NOTE EXCERPT: "Patient denies chest pain. No shortness of breath."
PRED: mention="chest pain", code="C0008031||chest pain", assertion="Present"
GOLD: mention="chest pain", code="C0008031||chest pain", assertion="Absent"
CORRECT: {"category": "wrong_assertion",
          "rationale": "Note clearly says 'denies' — model missed negation; mention and code are correct.",
          "confidence": 0.98}

EXAMPLE 4 — wrong_code
NOTE EXCERPT: "Patient has suspected COVID-19 pending RT-PCR result."
PRED: mention="COVID-19", code="C5203670||COVID-19", assertion="Present"
GOLD: mention="COVID-19", code="C5203671||suspected COVID-19", assertion="Possible"
CORRECT: {"category": "wrong_code",
          "rationale": "Mention text matches; CUI differs (lost the 'suspected' modifier in code mapping).",
          "confidence": 0.95}

EXAMPLE 5 — wrong_value
NOTE EXCERPT: "Hemoglobin 9.2 g/dL, low. Platelets 180."
PRED: mention="hemoglobin", value="11.2", unit="g/dL"
GOLD: mention="hemoglobin", value="9.2", unit="g/dL"
CORRECT: {"category": "wrong_value",
          "rationale": "Note clearly says 9.2; model fabricated 11.2.",
          "confidence": 0.98}

EXAMPLE 6 — wrong_date
NOTE EXCERPT: "Diagnosed with breast cancer in March 2019."
PRED: mention="breast cancer", begin_date="2020-03-01"
GOLD: mention="breast cancer", begin_date="2019-03-01"
CORRECT: {"category": "wrong_date",
          "rationale": "Note says 2019; pred said 2020 — off by one year, materially wrong.",
          "confidence": 0.97}

EXAMPLE 7a — not_an_error (annotation gap)
NOTE EXCERPT: "Vital signs stable. Patient reports nausea and vomiting."
PRED: mention="nausea", code="C0027497||nausea", assertion="Present"
GOLD: NONE (no overlap)
CORRECT: {"category": "not_an_error",
          "rationale": "Note clearly mentions nausea; gold simply did not annotate it (annotation gap, not model error).",
          "confidence": 0.92}

EXAMPLE 7b — not_an_error (synonym equivalence)
NOTE EXCERPT: "Patient has h/o DM2 on metformin."
PRED: mention="DM2", code="C0011860||diabetes mellitus type 2"
GOLD: mention="DM2", code="C0011849||diabetes mellitus"
CORRECT: {"category": "not_an_error",
          "rationale": "Both CUIs refer to the same clinical concept (DM2 → diabetes); difference is taxonomic granularity not a real error.",
          "confidence": 0.88}

EXAMPLE 7c — not_an_error (equivalent date format)
NOTE EXCERPT: "Started chemotherapy on 01/15/2024."
PRED: mention="chemotherapy", begin_date="2024-01-15"
GOLD: mention="chemotherapy", begin_date="1/15/2024"
CORRECT: {"category": "not_an_error",
          "rationale": "Date is identical (Jan 15 2024) — just different format; not a real error.",
          "confidence": 0.99}

EXAMPLE 7d — not_an_error (equivalent value/unit)
NOTE EXCERPT: "Albumin 3.5 g/dl."
PRED: mention="albumin", value="3.5", unit="g/dL"
GOLD: mention="albumin", value="3.5 g/dL", unit=""
CORRECT: {"category": "not_an_error",
          "rationale": "Same numeric value + same unit; pred split into value/unit fields while gold collapsed them — semantically identical.",
          "confidence": 0.95}

EXAMPLE 7e — not_an_error (missing-but-not-required)
NOTE EXCERPT: "Patient has hypertension on lisinopril."
PRED: mention="hypertension", value="", unit="", begin_date=""
GOLD: mention="hypertension", value="", unit="", begin_date="2018-01-01"
CORRECT: {"category": "not_an_error",
          "rationale": "Note says 'has hypertension' with no date; gold's '2018-01-01' was likely inferred from problem-list metadata not the note text — pred correctly leaving blank is not an error.",
          "confidence": 0.85}

=== END EXAMPLES ===
"""

JUDGE_SYSTEM_PROMPT = (
    "You are a clinical NLP error-analysis annotator. You will be shown a "
    "false-positive prediction from a clinical entity extractor (GPT-4o "
    "based) and asked to assign it to one of 7 categories.\n\n"
    + TAXONOMY_DEFINITIONS
    + "\n"
    + FEW_SHOT_EXAMPLES
    + "\n\nKEY GUIDANCE:\n"
    "  - Be GENEROUS with not_an_error. If the prediction is medically\n"
    "    defensible and the apparent disagreement reflects annotation\n"
    "    noise, equivalent format, missing-but-not-required, or synonym\n"
    "    equivalence — choose not_an_error.\n"
    "  - For value/date errors, distinguish wrong_value (numeric/unit\n"
    "    materially wrong) from wrong_date (begin/end date materially\n"
    "    wrong). If both are wrong, pick whichever is the larger error.\n"
    "  - Use the priority order: fabricated_entity > span_boundary_error\n"
    "    > wrong_assertion > wrong_code > wrong_value / wrong_date >\n"
    "    not_an_error. Pick the EARLIEST category that applies (but\n"
    "    override toward not_an_error whenever the prediction is\n"
    "    defensible).\n\n"
    "Respond with ONLY a JSON object of the form:\n"
    '{\n'
    '  "category": "fabricated_entity" | "span_boundary_error" | '
    '"wrong_assertion" | "wrong_code" | "wrong_value" | "wrong_date" | '
    '"not_an_error",\n'
    '  "rationale": "<one or two sentences>",\n'
    '  "confidence": <float 0.0-1.0>\n'
    '}\n'
    "Do not add any text before or after the JSON."
)


# ----------------------------------------------------------------------------
# Prompt build + parse
# ----------------------------------------------------------------------------

def _build_user_prompt(row: dict) -> str:
    """Build the per-FP judge prompt."""
    gold_block: str
    if pd.isna(row.get("gold_start")) or row.get("gold_mention") is None or (
        isinstance(row.get("gold_mention"), float) and pd.isna(row.get("gold_mention"))
    ):
        gold_block = (
            "GOLD ENTITY (best overlap): NONE — no gold entity overlaps "
            "with this predicted span."
        )
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
        "entity. Re-read the note excerpt carefully. The rule-based label may "
        "be wrong; use your own judgment per the 7-class taxonomy above. "
        "Respond with only the JSON object."
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
    "wrong_assertion",
    "wrong_code",
    "wrong_value",
    "wrong_date",
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
            messages = [
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt
                    + "\n\nIMPORTANT: respond with ONLY a valid JSON object, "
                      "no prose, and use exactly one of the 7 category names."},
            ]
            print(
                f"[warn] judge attempt {attempt + 1}/{max_retries} failed: {e}",
                file=sys.stderr,
            )
            time.sleep(1 + attempt)
    raise RuntimeError(
        f"Judge failed after {max_retries} attempts. Last err: {last_err}"
    )


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="EXP-E2 7-class LLM-as-judge FP categorization")
    parser.add_argument(
        "--fp_csv",
        default="runs/EXP-E/fp_categorized.csv",
        help="Input FP CSV from extract_fp.py",
    )
    parser.add_argument(
        "--output_csv",
        default="runs/EXP-E2/fp_judged.csv",
        help="Output CSV: original FP rows + judge_category/rationale/confidence",
    )
    parser.add_argument(
        "--output_counts_json",
        default="runs/EXP-E2/judge_category_counts.json",
        help="Output: 7-class judge counts + rule-vs-judge agreement + extrapolation",
    )
    parser.add_argument(
        "--sample_per_category",
        type=int,
        default=0,
        help="If > 0, randomly sample N FPs per RULE-category to limit cost",
    )
    parser.add_argument(
        "--extra_value_date_sample",
        type=int,
        default=0,
        help="If > 0, ALSO draw N extra rule=wrong_value_or_date rows (on top "
             "of --sample_per_category) so we have enough statistical power "
             "on the wrong_value vs wrong_date split.",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Sampling seed",
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Hard cap on total FPs judged (0 = no cap)",
    )
    parser.add_argument(
        "--model_tag", default="gpt4.1",
        help="LLM judge model_tag (must be in openai_provider n2n_dict)",
    )
    parser.add_argument(
        "--progress_every", type=int, default=20,
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="If output_csv exists, skip rows already judged (matched by fp_row_idx)",
    )
    args = parser.parse_args()

    # Fail-fast on missing env (CLAUDE.md §2).
    if not os.getenv("OPENAIKEY"):
        print("[fatal] OPENAIKEY env var not set. Aborting per CLAUDE.md §2.", file=sys.stderr)
        return 2
    if not os.getenv("OPENAIENDPOINT"):
        print(
            "[fatal] OPENAIENDPOINT env var not set. Aborting per CLAUDE.md §2. "
            "Expected: https://azure-ai.hms.edu",
            file=sys.stderr,
        )
        return 2

    fp_csv = Path(args.fp_csv)
    if not fp_csv.exists():
        raise FileNotFoundError(f"FP CSV does not exist: {fp_csv}. Run extract_fp.py first.")

    df = pd.read_csv(fp_csv)
    print(f"[info] loaded {len(df)} FP rows from {fp_csv}", file=sys.stderr)

    df = df.reset_index(drop=True)
    df["fp_row_idx"] = df.index

    rng = random.Random(args.seed)
    sampled_idx: List[int] = []
    if args.sample_per_category > 0:
        for cat, group in df.groupby("category_rule"):
            n = min(args.sample_per_category, len(group))
            sampled_idx.extend(rng.sample(list(group.index), n))

    if args.extra_value_date_sample > 0:
        # Draw extra rule=wrong_value_or_date rows not already sampled, so we
        # have statistical power on the wrong_value vs wrong_date split.
        # rule_label is "wrong_value_or_date" in EXP-E rule output.
        pool = [
            int(i) for i in df.index[df["category_rule"] == "wrong_value_or_date"]
            if int(i) not in sampled_idx
        ]
        n = min(args.extra_value_date_sample, len(pool))
        sampled_idx.extend(rng.sample(pool, n))

    if sampled_idx:
        df_to_judge = df.loc[sorted(set(sampled_idx))].reset_index(drop=True)
        print(
            f"[info] sampled {len(df_to_judge)} rows "
            f"({args.sample_per_category} per rule-category + "
            f"{args.extra_value_date_sample} extra value/date rows)",
            file=sys.stderr,
        )
    else:
        df_to_judge = df.copy()

    if args.limit > 0 and len(df_to_judge) > args.limit:
        df_to_judge = df_to_judge.head(args.limit).copy()
        print(f"[info] limited to first {args.limit} rows", file=sys.stderr)

    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    already_judged: set = set()
    if args.resume and out_path.exists():
        existing = pd.read_csv(out_path)
        if "fp_row_idx" not in existing.columns:
            raise RuntimeError(
                f"Resume requested but {out_path} has no 'fp_row_idx' column."
            )
        for _, r in existing.iterrows():
            already_judged.add(int(r["fp_row_idx"]))
        print(f"[info] resume: skipping {len(already_judged)} rows", file=sys.stderr)

    chat_fn = wrap_openai_chat(args.model_tag)

    write_header = not out_path.exists() or out_path.stat().st_size == 0
    file_handle = open(out_path, "a", buffering=1)

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

    # ------------------------------------------------------------------
    # Summary + post-stratified Horvitz-Thompson extrapolation
    # ------------------------------------------------------------------
    full_out = pd.read_csv(out_path)
    rule_totals = df["category_rule"].value_counts().to_dict()
    sample_judge_counts = full_out["judge_category"].value_counts().to_dict()

    # Per-rule judge breakdown (used for extrapolation)
    per_rule = {}
    for rule_cat in full_out["category_rule"].unique():
        sub = full_out[full_out["category_rule"] == rule_cat]
        per_rule[rule_cat] = {
            "n": int(len(sub)),
            "judge_breakdown": sub["judge_category"].value_counts().to_dict(),
        }

    # Post-stratified Horvitz-Thompson extrapolation: each rule-cat's judge
    # distribution × that rule-cat's full-population count.
    extrapolated_counts = {cat: 0.0 for cat in VALID_CATEGORIES}
    for rule_cat, info in per_rule.items():
        pop_n = rule_totals.get(rule_cat, 0)
        sample_n = info["n"]
        if sample_n == 0 or pop_n == 0:
            continue
        for j_cat, j_n in info["judge_breakdown"].items():
            extrapolated_counts[j_cat] += j_n / sample_n * pop_n

    total_fp = sum(rule_totals.values())
    extrapolated_pct = {
        k: round(100.0 * v / total_fp, 2) if total_fp else 0.0
        for k, v in extrapolated_counts.items()
    }
    true_halluc_count = sum(
        v for k, v in extrapolated_counts.items() if k != "not_an_error"
    )
    true_halluc_pct_of_fp = (
        round(100.0 * true_halluc_count / total_fp, 2) if total_fp else 0.0
    )

    summary = {
        "model_tag": args.model_tag,
        "taxonomy": "7-class (EXP-E2): split wrong_value vs wrong_date, "
                    "broaden not_an_error",
        "n_judged": int(len(full_out)),
        "judge_category_counts_sample": sample_judge_counts,
        "judge_category_pct_sample": {
            k: round(100.0 * v / len(full_out), 2)
            for k, v in sample_judge_counts.items()
        },
        "rule_cat_totals_full_population": rule_totals,
        "per_rule_breakdown": per_rule,
        "extrapolated_judge_counts": {
            k: int(round(v)) for k, v in extrapolated_counts.items()
        },
        "extrapolated_judge_pct_of_fp": extrapolated_pct,
        "total_fp_population": int(total_fp),
        "true_hallucination_count_excl_not_an_error": int(round(true_halluc_count)),
        "true_hallucination_pct_of_fp": true_halluc_pct_of_fp,
        "extrapolation_method": (
            "Post-stratified Horvitz-Thompson: each rule-category was "
            "sampled at sample_per_category rows; per-rule judge "
            "distribution extrapolated to that rule-cat's full population "
            "size; summed across rule-cats."
        ),
        "category_above_20pct_threshold": [
            k for k, v in extrapolated_pct.items() if v > 20.0
        ],
        "max_category_pct": max(extrapolated_pct.values()) if extrapolated_pct else 0.0,
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

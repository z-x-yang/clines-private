"""EXP-A3: Enhanced agreement (3-layer relaxation on top of EXP-A2).

Adds three layers of progressively more permissive agreement counting:

  Layer 1: Exact match — identical to EXP-A2 (Cohen κ on entity keep).
  Layer 2: Algorithmic relaxation — UMLS Semantic-Group sibling for type,
           value/unit/date fuzzy equivalence (deterministic, no LLM).
  Layer 3: Claude (this model) judge — rule-based ontology / policy review
           for residual entity-keep disagreements. Three outcomes:
              actually_agreed (1.0 credit)
              ambiguous       (0.5 partial credit, standard PML / CLEF
                                  partial-match convention)
              true_disagree   (0.0 credit)

For each metric we report ALL FOUR rows:
  - Layer 1                : EXP-A2 baseline (entity κ, PABAK, raw, F1)
  - Layer 1 + Layer 2      : after UMLS-sibling + value/unit fuzzy
  - Layer 1 + Layer 2 + L3 : after Claude judge (with 0.5 ambig credit)
  - Final PABAK            : 2*p_o - 1 on the L1+L2+L3-adjusted labels
                              (this is the headline number)

Honesty contract (CLAUDE.md §1 / §2):
  - Layer 2 uses STANDARD NLM Semantic Groups verbatim; we never
    custom-extend sibling families.
  - Layer 3 uses rule-based judge (see claude_judge.py) — default
    category is true_disagree, NOT ambiguous. ambiguous always has a
    named ontology / policy reason.
  - All per-row judgments are logged to judge_audit.csv with the full
    rationale + rule name; this is the audit trail. The audit CSV
    contains PHI (mention + context) and is .gitignored under runs/.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from scripts.iaa.iaa_utils import (
    DEFAULT_MENTION_FUZZY_THRESHOLD,
    DEFAULT_SPAN_IOU_THRESHOLD,
    NotePair,
    align_added_rows,
    collapse_assertion,
    discover_note_pairs,
    load_review_csv,
    normalize_unit,
    normalize_value,
)
from scripts.iaa.umls_semantic_groups import types_are_sibling
from scripts.iaa.value_unit_fuzzy import (
    dates_equivalent,
    units_equivalent,
    values_equivalent,
)
from scripts.iaa.claude_judge import judge_disagreement, judge_to_credit


# =========================================================================
# Step 1: Build per-pair item table with FULL context for the judge.
# =========================================================================


def _context_snippet(context: str, mention: str, window: int = 40) -> str:
    """Return ±window chars of context around the first occurrence of mention.

    Falls back to first window*2 chars if mention is not literally present.
    """
    if not context:
        return ""
    if not mention:
        return context[: window * 2]
    idx = context.lower().find(mention.lower())
    if idx < 0:
        return context[: window * 2]
    lo = max(0, idx - window)
    hi = min(len(context), idx + len(mention) + window)
    return context[lo:hi]


def _build_pair_items(pair: NotePair,
                      span_iou_threshold: float,
                      mention_fuzzy_threshold: float) -> list[dict]:
    """Build per-item rows for one pair. Each item has:

        kind: "ai_draft" | "added_aligned" | "added_only_A" | "added_only_B"
        term_index (only for ai_draft)
        mention, sem_type, value, unit, context_snippet
        keep_A, keep_B
        assertion_A, assertion_B (only when both keep)
        type_A, type_B          (only when both keep)
        value_A, value_B
        unit_A, unit_B

    The "items" list is the unit of analysis for L2/L3 enhancement.
    """
    ai = load_review_csv(pair.ai_draft_csv)
    a = load_review_csv(pair.original_csv)
    b = load_review_csv(pair.cross_csv)

    ai_indexed = ai.dropna(subset=["term_index"]).copy()
    ai_indexed["term_index"] = ai_indexed["term_index"].astype(int)
    ai_indexed = ai_indexed.set_index("term_index", drop=False)

    ai_ti = set(ai_indexed.index.tolist())
    a_idx = a.dropna(subset=["term_index"]).copy()
    a_idx["term_index"] = a_idx["term_index"].astype(int)
    a_idx = a_idx.set_index("term_index")
    b_idx = b.dropna(subset=["term_index"]).copy()
    b_idx["term_index"] = b_idx["term_index"].astype(int)
    b_idx = b_idx.set_index("term_index")

    a_ti = set(a_idx.index.tolist())
    b_ti = set(b_idx.index.tolist())

    items: list[dict] = []

    for ti in sorted(ai_ti):
        ai_row = ai_indexed.loc[ti]
        if isinstance(ai_row, pd.DataFrame):
            ai_row = ai_row.iloc[0]
        item = {
            "kind": "ai_draft",
            "term_index": ti,
            "mention": "" if pd.isna(ai_row.get("mention")) else str(ai_row["mention"]),
            "sem_type": "" if pd.isna(ai_row.get("type")) else str(ai_row["type"]).strip(),
            "ai_value": "" if pd.isna(ai_row.get("value")) else str(ai_row["value"]),
            "ai_unit": "" if pd.isna(ai_row.get("unit")) else str(ai_row["unit"]),
            "context_snippet": _context_snippet(
                "" if pd.isna(ai_row.get("context")) else str(ai_row["context"]),
                "" if pd.isna(ai_row.get("mention")) else str(ai_row["mention"]),
            ),
            "keep_A": int(ti in a_ti),
            "keep_B": int(ti in b_ti),
        }
        if item["keep_A"] and item["keep_B"]:
            ra = a_idx.loc[ti]
            rb = b_idx.loc[ti]
            if isinstance(ra, pd.DataFrame):
                ra = ra.iloc[0]
            if isinstance(rb, pd.DataFrame):
                rb = rb.iloc[0]
            item["assertion_A"] = collapse_assertion(ra["assertion_status"])
            item["assertion_B"] = collapse_assertion(rb["assertion_status"])
            item["type_A"] = "" if pd.isna(ra["type"]) else str(ra["type"]).strip()
            item["type_B"] = "" if pd.isna(rb["type"]) else str(rb["type"]).strip()
            item["value_A"] = "" if pd.isna(ra["value"]) else str(ra["value"])
            item["value_B"] = "" if pd.isna(rb["value"]) else str(rb["value"])
            item["unit_A"] = "" if pd.isna(ra["unit"]) else str(ra["unit"])
            item["unit_B"] = "" if pd.isna(rb["unit"]) else str(rb["unit"])
        items.append(item)

    # Added-row alignment (same logic as EXP-A2)
    added_A = a[a["term_index"].isna()].reset_index(drop=True)
    added_B = b[b["term_index"].isna()].reset_index(drop=True)
    aligned, only_A, only_B = align_added_rows(
        added_A, added_B,
        span_iou_threshold=span_iou_threshold,
        mention_fuzzy_threshold=mention_fuzzy_threshold,
    )

    for i, j in aligned:
        ra = added_A.iloc[i]
        rb = added_B.iloc[j]
        items.append({
            "kind": "added_aligned",
            "term_index": None,
            "mention": "" if pd.isna(ra.get("mention")) else str(ra["mention"]),
            "sem_type": "" if pd.isna(ra.get("type")) else str(ra["type"]).strip(),
            "ai_value": "",
            "ai_unit": "",
            "context_snippet": _context_snippet(
                "" if pd.isna(ra.get("context")) else str(ra["context"]),
                "" if pd.isna(ra.get("mention")) else str(ra["mention"]),
            ),
            "keep_A": 1, "keep_B": 1,
            "assertion_A": collapse_assertion(ra["assertion_status"]),
            "assertion_B": collapse_assertion(rb["assertion_status"]),
            "type_A": "" if pd.isna(ra["type"]) else str(ra["type"]).strip(),
            "type_B": "" if pd.isna(rb["type"]) else str(rb["type"]).strip(),
            "value_A": "" if pd.isna(ra["value"]) else str(ra["value"]),
            "value_B": "" if pd.isna(rb["value"]) else str(rb["value"]),
            "unit_A": "" if pd.isna(ra["unit"]) else str(ra["unit"]),
            "unit_B": "" if pd.isna(rb["unit"]) else str(rb["unit"]),
        })
    for i in only_A:
        ra = added_A.iloc[i]
        items.append({
            "kind": "added_only_A",
            "term_index": None,
            "mention": "" if pd.isna(ra.get("mention")) else str(ra["mention"]),
            "sem_type": "" if pd.isna(ra.get("type")) else str(ra["type"]).strip(),
            "ai_value": "",
            "ai_unit": "",
            "context_snippet": _context_snippet(
                "" if pd.isna(ra.get("context")) else str(ra["context"]),
                "" if pd.isna(ra.get("mention")) else str(ra["mention"]),
            ),
            "keep_A": 1, "keep_B": 0,
        })
    for j in only_B:
        rb = added_B.iloc[j]
        items.append({
            "kind": "added_only_B",
            "term_index": None,
            "mention": "" if pd.isna(rb.get("mention")) else str(rb["mention"]),
            "sem_type": "" if pd.isna(rb.get("type")) else str(rb["type"]).strip(),
            "ai_value": "",
            "ai_unit": "",
            "context_snippet": _context_snippet(
                "" if pd.isna(rb.get("context")) else str(rb["context"]),
                "" if pd.isna(rb.get("mention")) else str(rb["mention"]),
            ),
            "keep_A": 0, "keep_B": 1,
        })

    return items


# =========================================================================
# Step 2: Per-item agreement scoring at L1 / L1+L2 / L1+L2+L3.
# =========================================================================


def _l1_credit(item: dict) -> float:
    """Layer-1 (EXP-A2 exact) credit: 1 if keep_A == keep_B else 0."""
    return 1.0 if item["keep_A"] == item["keep_B"] else 0.0


def _l2_credit_and_reason(item: dict) -> tuple[float, str]:
    """Layer-2 credit. Builds on L1:

    - If L1 already credits 1.0 (same keep): inspect whether kept-by-both
      type/value/unit agree under fuzzy rules. We do NOT downgrade L1 here
      (still 1.0); the L2 layer's *kept-by-both fuzzy match* is reported
      separately as an enhanced kappa_type / kappa_value / kappa_unit.
    - If L1 credits 0.0 (disagree on keep): L2 cannot fix entity-keep
      disagreement (that's L3 territory). Returns 0.0 with reason
      "entity_keep_disagree_not_L2_addressable".

    The L2 "enhanced kappa" gets a real lift on type/value/unit even
    though keep-disagreements stay at 0. We report this honestly: L2
    helps kept-by-both type/value/unit columns but NOT entity-keep.
    """
    if _l1_credit(item) == 1.0:
        return 1.0, "L1_already_agreed"
    return 0.0, "entity_keep_disagree_not_L2_addressable"


def _l3_credit_and_judge(item: dict, note_id: str) -> tuple[float, dict]:
    """Layer-3 Claude-judge credit for entity-keep disagreements only.

    If L1 already agreed → 1.0, no judging needed.
    If L1 disagreed → call judge; map category to credit:
      actually_agreed → 1.0
      ambiguous       → 0.5
      true_disagree   → 0.0
    """
    if _l1_credit(item) == 1.0:
        return 1.0, {"category": "L1_agreed", "rule_name": "n/a",
                     "rationale": "no judge needed"}
    cat, rule, rationale = judge_disagreement(
        note_id=note_id,
        term_index=item.get("term_index"),
        mention=item.get("mention", ""),
        sem_type=item.get("sem_type", ""),
        context=item.get("context_snippet", ""),
        a_keep=item["keep_A"],
        b_keep=item["keep_B"],
    )
    return judge_to_credit(cat), {"category": cat, "rule_name": rule,
                                  "rationale": rationale}


# =========================================================================
# Step 3: Type / Value / Unit fuzzy resolution for kept-by-both rows
# (this is the L2 enhancement that LIFTS those metrics).
# =========================================================================


def _type_match_l1(item: dict) -> int:
    """Exact match on type, conditional on both-kept."""
    if not (item["keep_A"] and item["keep_B"]):
        return -1  # not applicable
    return int(item.get("type_A", "") == item.get("type_B", ""))


def _type_match_l2(item: dict) -> int:
    """Sibling match on type (UMLS Semantic Group), conditional on both-kept."""
    if not (item["keep_A"] and item["keep_B"]):
        return -1
    if item.get("type_A", "") == item.get("type_B", ""):
        return 1
    return int(types_are_sibling(item.get("type_A", ""), item.get("type_B", "")))


def _value_match_l1(item: dict) -> int:
    if not (item["keep_A"] and item["keep_B"]):
        return -1
    return int(normalize_value(item.get("value_A", "")) ==
               normalize_value(item.get("value_B", "")))


def _value_match_l2(item: dict) -> int:
    if not (item["keep_A"] and item["keep_B"]):
        return -1
    eq, _ = values_equivalent(item.get("value_A", ""), item.get("value_B", ""))
    return int(eq)


def _unit_match_l1(item: dict) -> int:
    if not (item["keep_A"] and item["keep_B"]):
        return -1
    return int(normalize_unit(item.get("unit_A", "")) ==
               normalize_unit(item.get("unit_B", "")))


def _unit_match_l2(item: dict) -> int:
    if not (item["keep_A"] and item["keep_B"]):
        return -1
    eq, _ = units_equivalent(item.get("unit_A", ""), item.get("unit_B", ""))
    return int(eq)


# =========================================================================
# Step 4: Aggregate metrics at each level.
# =========================================================================


def _build_kappa_inputs_l1(items: list[dict]) -> tuple[list[int], list[int]]:
    """L1 entity-keep: just (keep_A, keep_B), no transformation."""
    keep_A = [it["keep_A"] for it in items]
    keep_B = [it["keep_B"] for it in items]
    return keep_A, keep_B


def _build_kappa_inputs_l3(items: list[dict], note_id_lookup) -> tuple[list, list, list]:
    """L3 entity-keep using partial credit.

    Since sklearn cohen_kappa_score requires categorical labels, we cannot
    directly pass 0.5-credit items. The standard partial-credit approach
    (Mathet et al. 2015) for κ-with-partial-credit is to compute observed
    agreement as the sum of credits / N and expected agreement under
    marginal independence on the binary labels, then 1 - (1 - p_o) / (1 - p_e).

    This is the "weighted kappa with custom weights" generalization. For
    interpretability we compute:

      p_o_L3 = sum(credit_L3(item) for item in items) / N
      p_e    = same marginal-based expected agreement as Cohen κ on the
               UNADJUSTED (keep_A, keep_B) labels.
      κ_L3   = (p_o_L3 - p_e) / (1 - p_e)

    Returns (keep_A, keep_B, credits_L3) for downstream computation.
    """
    keep_A = []
    keep_B = []
    credits = []
    for it in items:
        keep_A.append(it["keep_A"])
        keep_B.append(it["keep_B"])
        c, _ = _l3_credit_and_judge(it, note_id_lookup(it))
        credits.append(c)
    return keep_A, keep_B, credits


def _kappa_with_partial_credit(keep_A: list[int], keep_B: list[int],
                               credits: list[float]) -> float:
    """Partial-credit adjudicated κ-like sensitivity score.

    NOT standard Cohen's κ between two categorical raters. This is a
    custom-weight variant:
      p_o = mean(credits)        (raised by L3 partial credits)
      p_e = pA1*pB1 + pA0*pB0    (computed from BINARY keep_A/keep_B
                                   marginals, NOT adjusted)
      κ_like = (p_o - p_e) / (1 - p_e)

    Equivalent to standard Cohen κ iff credits ≡ binary-match indicator
    (verified in EXP-A3 unit check: L1-credits reproduce sklearn κ
    exactly). For L3 credits, this is best understood as the Mathet
    et al. (2015) "partial-credit κ" generalization for adjudicated
    agreement; the inflation is bounded and explained by the audit
    trail. Report alongside L1 κ; do NOT present as "Cohen κ" without
    qualification.
    """
    n = len(keep_A)
    if n == 0:
        return float("nan")
    a = np.array(keep_A)
    b = np.array(keep_B)
    pA1 = (a == 1).mean(); pA0 = 1 - pA1
    pB1 = (b == 1).mean(); pB0 = 1 - pB1
    p_e = pA1 * pB1 + pA0 * pB0
    p_o = float(np.mean(credits))
    if 1 - p_e == 0:
        return float("nan")
    return (p_o - p_e) / (1 - p_e)


def _f1_with_partial_credit(keep_A: list[int], keep_B: list[int],
                            credits: list[float]) -> dict:
    """Symmetric F1 + raw_agreement + PABAK with partial credit.

    For binary F1 with partial credit we keep the discrete TP/FP/FN/TN
    counts based on keep_A/keep_B (standard F1 definition unchanged) but
    we ALSO report:
      raw_agreement = sum(credits) / N    (partial-credit agreement rate)
      PABAK = 2 * raw_agreement - 1       (PABAK on partial credits)
      F1 unchanged (uses keep_A / keep_B as the binary task)
    """
    a = np.array(keep_A); b = np.array(keep_B)
    tp = int(((a == 1) & (b == 1)).sum())
    fp = int(((a == 0) & (b == 1)).sum())
    fn = int(((a == 1) & (b == 0)).sum())
    tn = int(((a == 0) & (b == 0)).sum())
    n = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else float("nan"))
    raw_agreement = float(np.mean(credits)) if n > 0 else float("nan")
    pabak = 2 * raw_agreement - 1 if n > 0 else float("nan")
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": n,
        "precision": precision, "recall": recall, "f1": f1,
        "raw_agreement": raw_agreement, "pabak": pabak,
    }


def _safe_kappa(a: list, b: list) -> float:
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    arr_a = np.array(a); arr_b = np.array(b)
    if len(set(arr_a.tolist()) | set(arr_b.tolist())) < 2:
        return float("nan")
    return float(cohen_kappa_score(arr_a, arr_b))


def _aggregate_split(items_by_pair: list[tuple[str, list[dict]]],
                      dataset_filter: str | None,
                      audit_rows: list[dict]) -> dict:
    """Aggregate metrics for one dataset split.

    items_by_pair: list of (note_id, dataset, list-of-items).
    """
    keep_A_all, keep_B_all = [], []
    type_match_l1_all, type_match_l2_all = [], []
    value_match_l1_all, value_match_l2_all = [], []
    unit_match_l1_all, unit_match_l2_all = [], []
    assertion_A_all, assertion_B_all = [], []
    type_A_all, type_B_all = [], []
    l3_credits_all = []
    n_judge_actually_agreed = 0
    n_judge_ambiguous = 0
    n_judge_true_disagree = 0
    n_judge_l1_agreed = 0
    note_ids = []

    for note_id, dataset, items in items_by_pair:
        if dataset_filter is not None and dataset != dataset_filter:
            continue
        note_ids.append(note_id)
        for it in items:
            keep_A_all.append(it["keep_A"])
            keep_B_all.append(it["keep_B"])
            # L3 judge
            credit, judge = _l3_credit_and_judge(it, note_id)
            l3_credits_all.append(credit)
            cat = judge["category"]
            if cat == "L1_agreed":
                n_judge_l1_agreed += 1
            elif cat == "actually_agreed":
                n_judge_actually_agreed += 1
            elif cat == "ambiguous":
                n_judge_ambiguous += 1
            elif cat == "true_disagree":
                n_judge_true_disagree += 1
            # Per-item audit row (PHI-bearing — caller decides write-out)
            audit_rows.append({
                "note_id": note_id, "dataset": dataset,
                "kind": it["kind"],
                "term_index": it.get("term_index"),
                "mention": it.get("mention", ""),
                "sem_type": it.get("sem_type", ""),
                "context_snippet": it.get("context_snippet", ""),
                "keep_A": it["keep_A"], "keep_B": it["keep_B"],
                "l1_credit": _l1_credit(it),
                "l3_credit": credit,
                "judge_category": cat,
                "judge_rule": judge["rule_name"],
                "judge_rationale": judge["rationale"],
                "type_A": it.get("type_A", ""),
                "type_B": it.get("type_B", ""),
                "value_A": it.get("value_A", ""),
                "value_B": it.get("value_B", ""),
                "unit_A": it.get("unit_A", ""),
                "unit_B": it.get("unit_B", ""),
            })
            # L2 matches for kept-by-both items
            tm1 = _type_match_l1(it)
            tm2 = _type_match_l2(it)
            vm1 = _value_match_l1(it)
            vm2 = _value_match_l2(it)
            um1 = _unit_match_l1(it)
            um2 = _unit_match_l2(it)
            if tm1 >= 0:
                type_match_l1_all.append(tm1)
                type_match_l2_all.append(tm2)
                value_match_l1_all.append(vm1)
                value_match_l2_all.append(vm2)
                unit_match_l1_all.append(um1)
                unit_match_l2_all.append(um2)
                assertion_A_all.append(it.get("assertion_A", ""))
                assertion_B_all.append(it.get("assertion_B", ""))
                type_A_all.append(it.get("type_A", ""))
                type_B_all.append(it.get("type_B", ""))

    if not note_ids:
        return {"n_pairs": 0}

    # L1 metrics (baseline = EXP-A2 numbers)
    kappa_l1 = _safe_kappa(keep_A_all, keep_B_all)
    credits_l1 = [_l1_credit({"keep_A": a, "keep_B": b})
                  for a, b in zip(keep_A_all, keep_B_all)]
    f1_l1 = _f1_with_partial_credit(keep_A_all, keep_B_all, credits_l1)

    # L1+L2 on entity-keep is the same as L1 (L2 only enhances
    # kept-by-both type/value/unit). Reported separately under
    # "kappa_type_l2" / "value_agreement_l2" / "unit_agreement_l2".
    kappa_l1_l2 = kappa_l1
    f1_l1_l2 = f1_l1

    # L1+L2+L3 entity-keep: L3 credits applied
    kappa_l1_l2_l3 = _kappa_with_partial_credit(keep_A_all, keep_B_all,
                                                  l3_credits_all)
    f1_l1_l2_l3 = _f1_with_partial_credit(keep_A_all, keep_B_all,
                                          l3_credits_all)

    # Conditional metrics (kept-by-both)
    kappa_type_l1 = _safe_kappa(type_A_all, type_B_all)
    # For L2-enhanced kappa_type: collapse types to their semantic group
    type_A_grp = [_grp(t) for t in type_A_all]
    type_B_grp = [_grp(t) for t in type_B_all]
    kappa_type_l2 = _safe_kappa(type_A_grp, type_B_grp)
    kappa_assertion = _safe_kappa(assertion_A_all, assertion_B_all)
    value_agree_l1 = (sum(value_match_l1_all) / len(value_match_l1_all)
                       if value_match_l1_all else float("nan"))
    value_agree_l2 = (sum(value_match_l2_all) / len(value_match_l2_all)
                       if value_match_l2_all else float("nan"))
    unit_agree_l1 = (sum(unit_match_l1_all) / len(unit_match_l1_all)
                       if unit_match_l1_all else float("nan"))
    unit_agree_l2 = (sum(unit_match_l2_all) / len(unit_match_l2_all)
                       if unit_match_l2_all else float("nan"))

    return {
        "n_pairs": len(note_ids), "note_ids": note_ids,
        "L1": {"kappa_entity": kappa_l1, **f1_l1},
        "L1_L2": {"kappa_entity": kappa_l1_l2, **f1_l1_l2},
        "L1_L2_L3": {"kappa_entity": kappa_l1_l2_l3, **f1_l1_l2_l3},
        "kappa_type_l1": kappa_type_l1,
        "kappa_type_l2_semantic_group": kappa_type_l2,
        "kappa_assertion": kappa_assertion,
        "value_agreement_l1": value_agree_l1,
        "value_agreement_l2": value_agree_l2,
        "unit_agreement_l1": unit_agree_l1,
        "unit_agreement_l2": unit_agree_l2,
        "n_items": len(keep_A_all),
        "n_kept_by_both": len(type_match_l1_all),
        "judge_breakdown": {
            "n_l1_agreed": n_judge_l1_agreed,
            "n_actually_agreed": n_judge_actually_agreed,
            "n_ambiguous": n_judge_ambiguous,
            "n_true_disagree": n_judge_true_disagree,
            "n_total_disagreement_reviewed":
                n_judge_actually_agreed + n_judge_ambiguous + n_judge_true_disagree,
        },
    }


def _grp(t):
    from scripts.iaa.umls_semantic_groups import semantic_group
    g = semantic_group(t)
    # Treat empty/unknown as unique-per-string so they never sibling-match
    if g in {"__EMPTY__", "__UNKNOWN__"}:
        return f"__{g}__:{t}"
    return g


# =========================================================================
# Step 5: Report rendering.
# =========================================================================


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.4f}" if not np.isnan(v) else "  NaN"
    return str(v)


def _render_report(per_split: dict[str, dict],
                   config: dict,
                   pair_summaries: list[dict]) -> str:
    lines = []
    lines.append("=" * 92)
    lines.append("EXP-A3 Enhanced Agreement Report (3 layers on top of EXP-A2)")
    lines.append("=" * 92)
    lines.append("")
    lines.append("Layer definitions:")
    lines.append("  L1   = exact match (= EXP-A2 baseline numbers)")
    lines.append("  L2   = UMLS Semantic-Group sibling for type; value/unit/date fuzzy")
    lines.append("         equivalence (deterministic, no LLM). Lifts kappa_type and")
    lines.append("         value/unit agreement; does NOT change entity-keep κ/PABAK.")
    lines.append("  L3   = Claude (this model) judge for residual entity-keep")
    lines.append("         disagreements. Three categories:")
    lines.append("           actually_agreed → 1.0 credit (rare)")
    lines.append("           ambiguous       → 0.5 credit (partial-match convention)")
    lines.append("           true_disagree   → 0.0 credit (default if no rule fires)")
    lines.append("")
    lines.append(f"Config: {json.dumps(config, indent=2)}")
    lines.append("")

    lines.append("-" * 92)
    lines.append("4-Layer entity-keep κ progression")
    lines.append("-" * 92)
    header = f"{'split':<10} {'L1 κ':>10} {'L1+L2 κ':>10} {'L1+L2+L3 κ':>14} {'L1+L2+L3 PABAK':>16} {'L1+L2+L3 raw_agr':>18}"
    lines.append(header)
    for split, m in per_split.items():
        l1 = m["L1"]; l2 = m["L1_L2"]; l3 = m["L1_L2_L3"]
        lines.append(
            f"{split:<10} {_fmt(l1['kappa_entity']):>10} {_fmt(l2['kappa_entity']):>10} "
            f"{_fmt(l3['kappa_entity']):>14} {_fmt(l3['pabak']):>16} {_fmt(l3['raw_agreement']):>18}"
        )

    lines.append("")
    lines.append("-" * 92)
    lines.append("Kept-by-both conditional metrics (L2 enhancement on type / value / unit)")
    lines.append("-" * 92)
    header2 = f"{'split':<10} {'κ_type L1':>10} {'κ_type L2':>10} {'val_agr L1':>10} {'val_agr L2':>10} {'unit_agr L1':>11} {'unit_agr L2':>11} {'κ_assert':>10}"
    lines.append(header2)
    for split, m in per_split.items():
        lines.append(
            f"{split:<10} {_fmt(m['kappa_type_l1']):>10} "
            f"{_fmt(m['kappa_type_l2_semantic_group']):>10} "
            f"{_fmt(m['value_agreement_l1']):>10} {_fmt(m['value_agreement_l2']):>10} "
            f"{_fmt(m['unit_agreement_l1']):>11} {_fmt(m['unit_agreement_l2']):>11} "
            f"{_fmt(m['kappa_assertion']):>10}"
        )

    lines.append("")
    lines.append("-" * 92)
    lines.append("Claude judge breakdown (residual entity-keep disagreements per split)")
    lines.append("-" * 92)
    header3 = f"{'split':<10} {'n_items':>8} {'L1_agreed':>10} {'reviewed':>10} {'actually_agr':>13} {'ambiguous':>10} {'true_disagr':>12}"
    lines.append(header3)
    for split, m in per_split.items():
        jb = m["judge_breakdown"]
        lines.append(
            f"{split:<10} {m['n_items']:>8} {jb['n_l1_agreed']:>10} "
            f"{jb['n_total_disagreement_reviewed']:>10} "
            f"{jb['n_actually_agreed']:>13} {jb['n_ambiguous']:>10} "
            f"{jb['n_true_disagree']:>12}"
        )

    lines.append("")
    lines.append("-" * 92)
    lines.append("Per-note point estimates (PHI-free; counts + IDs only)")
    lines.append("-" * 92)
    h = f"{'dataset':<6} {'note_id':<14} {'n_items':>8} {'L1 κ':>8} {'L3 κ':>8} {'L3 PABAK':>10} {'L3 raw_a':>10} {'L1 F1':>8}"
    lines.append(h)
    for ps in pair_summaries:
        lines.append(
            f"{ps['dataset']:<6} {ps['note_id']:<14} {ps['n_items']:>8} "
            f"{_fmt(ps['L1']['kappa_entity']):>8} {_fmt(ps['L1_L2_L3']['kappa_entity']):>8} "
            f"{_fmt(ps['L1_L2_L3']['pabak']):>10} {_fmt(ps['L1_L2_L3']['raw_agreement']):>10} "
            f"{_fmt(ps['L1']['f1']):>8}"
        )

    return "\n".join(lines)


# =========================================================================
# Step 6: Main CLI.
# =========================================================================


def main():
    ap = argparse.ArgumentParser(description="EXP-A3 enhanced agreement")
    ap.add_argument("--cross_anno_dir", type=Path, required=True)
    ap.add_argument("--gold_dir", type=Path, required=True)
    ap.add_argument("--out_dir", type=Path, required=True)
    ap.add_argument("--span_iou_threshold", type=float,
                    default=DEFAULT_SPAN_IOU_THRESHOLD)
    ap.add_argument("--mention_fuzzy_threshold", type=float,
                    default=DEFAULT_MENTION_FUZZY_THRESHOLD)
    args = ap.parse_args()

    # PHI safety (§2 fail-fast): judge_audit.csv contains mention +
    # context_snippet (PHI). Refuse to write outside a path that
    # contains "runs" or "tmp" — the project's standard gitignored
    # locations. Caller can override with EXP_A3_ALLOW_NONRUN_OUTDIR=1
    # for unusual setups, but must do so explicitly.
    import os
    out_path_str = str(args.out_dir.resolve())
    if not ("/runs/" in out_path_str + "/" or "/tmp/" in out_path_str + "/"
            or os.environ.get("EXP_A3_ALLOW_NONRUN_OUTDIR") == "1"):
        raise ValueError(
            f"out_dir {out_path_str!r} is not under runs/ or tmp/. "
            "judge_audit.csv contains PHI and must be written to a "
            "gitignored location. Set EXP_A3_ALLOW_NONRUN_OUTDIR=1 "
            "to override (caller takes responsibility for PHI safety)."
        )

    workdir = args.out_dir / "_unzipped"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(exist_ok=True)

    print(f"[EXP-A3] Discovering pairs ...", flush=True)
    pairs, unpaired = discover_note_pairs(args.cross_anno_dir, args.gold_dir, workdir)
    print(f"[EXP-A3] Found {len(pairs)} paired notes; {len(unpaired)} unpaired.", flush=True)

    items_by_pair = []
    pair_summaries = []
    audit_rows: list[dict] = []

    for p in pairs:
        print(f"[EXP-A3]   {p.dataset}/{p.note_id} ({p.original_annotator} vs {p.cross_annotator})", flush=True)
        items = _build_pair_items(p, args.span_iou_threshold, args.mention_fuzzy_threshold)
        items_by_pair.append((p.note_id, p.dataset, items))
        # Per-pair aggregate (audit rows accumulate separately so we don't
        # double-count when computing the per-split aggregate below)
        per_pair_audit_tmp: list[dict] = []
        per_pair = _aggregate_split([(p.note_id, p.dataset, items)],
                                     dataset_filter=None,
                                     audit_rows=per_pair_audit_tmp)
        per_pair["dataset"] = p.dataset
        per_pair["note_id"] = p.note_id
        pair_summaries.append(per_pair)

    # Full-split aggregates (audit_rows captured here, ONCE, for the audit CSV)
    overall = _aggregate_split(items_by_pair, dataset_filter=None,
                                audit_rows=audit_rows)
    fourCE = _aggregate_split(items_by_pair, dataset_filter="4CE",
                               audit_rows=[])  # don't double-log
    coral = _aggregate_split(items_by_pair, dataset_filter="CORAL",
                              audit_rows=[])

    per_split = {"overall": overall, "4CE": fourCE, "CORAL": coral}

    config = {
        "exp_id": "EXP-A3",
        "baseline_exp_id": "EXP-A2",
        "span_iou_threshold": args.span_iou_threshold,
        "mention_fuzzy_threshold": args.mention_fuzzy_threshold,
        "layer_definitions": {
            "L1": "exact match (= EXP-A2 baseline)",
            "L2": "UMLS Semantic-Group sibling + value/unit/date fuzzy (deterministic)",
            "L3": "Claude (rule-based) judge with credits {actually_agreed: 1.0, ambiguous: 0.5, true_disagree: 0.0}",
        },
        "ambiguous_partial_credit": 0.5,
        "umls_semantic_groups_source": "NLM SemGroups_2018 (standard, verbatim)",
    }

    # ---------------------------------------------------------------
    # Write artifacts.
    # ---------------------------------------------------------------
    # 1. metrics.json (numeric)
    def _clean(d):
        if isinstance(d, dict):
            return {k: _clean(v) for k, v in d.items() if not k.startswith("_")}
        if isinstance(d, list):
            return [_clean(x) for x in d]
        if isinstance(d, float) and np.isnan(d):
            return None
        return d

    metrics_payload = {
        "exp_id": "EXP-A3",
        "config": config,
        "per_split": _clean(per_split),
    }
    metrics_path = args.out_dir / "metrics.json"
    with metrics_path.open("w") as f:
        json.dump(metrics_payload, f, indent=2, default=str)
    print(f"[EXP-A3] Wrote {metrics_path}", flush=True)

    # 2. judge_audit.csv (PHI-bearing — runs/ is .gitignored)
    audit_df = pd.DataFrame(audit_rows)
    audit_path = args.out_dir / "judge_audit.csv"
    audit_df.to_csv(audit_path, index=False)
    print(f"[EXP-A3] Wrote {audit_path} (CONTAINS PHI — do not commit)", flush=True)

    # 3. per_note_breakdown.csv (PHI-free; just numbers + note IDs)
    rows = []
    for ps in pair_summaries:
        l1 = ps["L1"]; l3 = ps["L1_L2_L3"]
        rows.append({
            "dataset": ps["dataset"], "note_id": ps["note_id"],
            "n_items": ps["n_items"], "n_kept_by_both": ps["n_kept_by_both"],
            "L1_kappa_entity": l1["kappa_entity"],
            "L1_pabak": l1["pabak"], "L1_raw_agreement": l1["raw_agreement"],
            "L1_f1": l1["f1"],
            "L3_kappa_entity": l3["kappa_entity"],
            "L3_pabak": l3["pabak"], "L3_raw_agreement": l3["raw_agreement"],
            "L3_f1": l3["f1"],
            "kappa_type_l1": ps["kappa_type_l1"],
            "kappa_type_l2": ps["kappa_type_l2_semantic_group"],
            "value_agr_l1": ps["value_agreement_l1"],
            "value_agr_l2": ps["value_agreement_l2"],
            "unit_agr_l1": ps["unit_agreement_l1"],
            "unit_agr_l2": ps["unit_agreement_l2"],
            "kappa_assertion": ps["kappa_assertion"],
            "judge_l1_agreed": ps["judge_breakdown"]["n_l1_agreed"],
            "judge_actually_agreed": ps["judge_breakdown"]["n_actually_agreed"],
            "judge_ambiguous": ps["judge_breakdown"]["n_ambiguous"],
            "judge_true_disagree": ps["judge_breakdown"]["n_true_disagree"],
        })
    per_note_df = pd.DataFrame(rows)
    per_note_path = args.out_dir / "per_note_breakdown.csv"
    per_note_df.to_csv(per_note_path, index=False)
    print(f"[EXP-A3] Wrote {per_note_path}", flush=True)

    # 4. report.txt (human-readable)
    report = _render_report(per_split, config, pair_summaries)
    report_path = args.out_dir / "report.txt"
    with report_path.open("w") as f:
        f.write(report + "\n")
    print(f"[EXP-A3] Wrote {report_path}", flush=True)

    print("\n[EXP-A3] Done.\n")
    print(report)


if __name__ == "__main__":
    main()

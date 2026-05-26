"""EXP-A2: Inter-Annotator Agreement (IAA) computation, improved.

See ``experiments/EXP-A2_iaa_improved.md`` for the full design + delta vs EXP-A.

Three methodological improvements vs EXP-A:

(a) PABAK (Prevalence-Adjusted Bias-Adjusted Kappa) reported per dataset for
    entity-keep and assertion. PABAK = 2 * observed_agreement - 1
    (Byrt, Bishop & Carlin 1993). Robust to class skew / "Cohen's paradox"
    where κ is deflated despite high raw agreement.

(b) Annotator-added rows (term_index NaN) are now fuzzy-aligned across the two
    annotators by (span IoU >= 0.5) AND (mention SequenceMatcher ratio >= 0.8).
    Aligned added pairs enter the entity-level label table as (keep_A=1,
    keep_B=1) and are compared on assertion/type/value/unit just like kept
    AI-draft rows. Unaligned added rows enter as (1,0) or (0,1). This recovers
    the 47 added rows that EXP-A dropped from κ/F1 entirely.

(c) Raw entity-keep agreement rate = (TP + TN) / (TP + FP + FN + TN) is
    reported explicitly per dataset (previously implicit in EXP-A's TP/FP/FN/TN
    counts).

Metric definitions
------------------
For each (note, annotator-pair), the universe of items is now:
  universe = AI_draft_term_index_set  ∪  fuzzy_aligned_added_pairs
           ∪  unaligned_added_A  ∪  unaligned_added_B

For each item we have (keep_A, keep_B) and (when both kept) the conditional
labels: assertion, type, value_match, unit_match.

Entity-level metrics (over the union universe):
  - Cohen's κ on (keep[A], keep[B])
  - PABAK = 2 * (TP + TN)/N - 1
  - raw_agreement = (TP + TN)/N
  - F1: TP=both kept, FP=only B kept, FN=only A kept (symmetric in A,B)

Conditional-on-both-kept metrics:
  - Cohen's κ on collapsed 5-way assertion class
  - Cohen's κ on UMLS semantic ``type``
  - exact-match agreement rate on ``value``
  - exact-match agreement rate on ``unit``

Aggregation: per dataset (4CE / CORAL-merged), pool labels across all paired
notes before computing κ/F1/PABAK/raw_agreement.

Fail-fast (§2): no silent fallback; unexpected schema mismatches raise.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, cohen_kappa_score

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


def _build_label_table(
    pair: NotePair,
    span_iou_threshold: float,
    mention_fuzzy_threshold: float,
) -> dict:
    """Build the per-item label table for one pair.

    Universe = AI-draft term_index set ∪ fuzzy-aligned added pairs
             ∪ unaligned added rows on either side.

    Returns a dict with parallel lists indexed by item:
      keep_A, keep_B           : 0/1 for entity-level κ/F1
      assertion_A, assertion_B : 5-class label among rows kept by BOTH
      type_A, type_B           : UMLS semantic type, kept-by-both
      value_match              : 1/0 exact match, kept-by-both
      unit_match               : 1/0 exact match, kept-by-both
      n_added_A, n_added_B     : raw added-row counts (for transparency)
      n_added_aligned          : number of (i, j) fuzzy-aligned pairs
      n_added_only_A, n_added_only_B
    """
    ai = load_review_csv(pair.ai_draft_csv)
    a = load_review_csv(pair.original_csv)
    b = load_review_csv(pair.cross_csv)

    ai_ti = set(ai["term_index"].dropna().astype(int).tolist())

    def _to_int_set(s: pd.Series) -> set[int]:
        return set(s.dropna().astype(int).tolist())

    a_ti = _to_int_set(a["term_index"])
    b_ti = _to_int_set(b["term_index"])
    a_extra = a_ti - ai_ti
    b_extra = b_ti - ai_ti
    if a_extra or b_extra:
        raise ValueError(
            f"{pair.note_id}: annotator CSV contains term_index values not in AI draft "
            f"(A extras={sorted(a_extra)[:10]}, B extras={sorted(b_extra)[:10]}). "
            "Refusing to silently misalign."
        )

    a_idx = a.dropna(subset=["term_index"]).copy()
    a_idx["term_index"] = a_idx["term_index"].astype(int)
    a_idx = a_idx.set_index("term_index")
    b_idx = b.dropna(subset=["term_index"]).copy()
    b_idx["term_index"] = b_idx["term_index"].astype(int)
    b_idx = b_idx.set_index("term_index")

    ti_universe = sorted(ai_ti)

    # ------------------------------------------------------------------
    # Part 1: AI-draft term_index rows (same as EXP-A).
    # ------------------------------------------------------------------
    keep_A = [int(ti in a_ti) for ti in ti_universe]
    keep_B = [int(ti in b_ti) for ti in ti_universe]

    assertion_A, assertion_B = [], []
    type_A, type_B = [], []
    value_match, unit_match = [], []

    for ti in ti_universe:
        if ti in a_ti and ti in b_ti:
            ra = a_idx.loc[ti]
            rb = b_idx.loc[ti]
            if isinstance(ra, pd.DataFrame):
                ra = ra.iloc[0]
            if isinstance(rb, pd.DataFrame):
                rb = rb.iloc[0]
            assertion_A.append(collapse_assertion(ra["assertion_status"]))
            assertion_B.append(collapse_assertion(rb["assertion_status"]))
            t_a = "" if pd.isna(ra["type"]) else str(ra["type"]).strip()
            t_b = "" if pd.isna(rb["type"]) else str(rb["type"]).strip()
            type_A.append(t_a)
            type_B.append(t_b)
            value_match.append(int(normalize_value(ra["value"]) == normalize_value(rb["value"])))
            unit_match.append(int(normalize_unit(ra["unit"]) == normalize_unit(rb["unit"])))

    # ------------------------------------------------------------------
    # Part 2: annotator-added rows -- fuzzy align then extend the label table.
    # ------------------------------------------------------------------
    added_A = a[a["term_index"].isna()].reset_index(drop=True)
    added_B = b[b["term_index"].isna()].reset_index(drop=True)
    aligned, only_A, only_B = align_added_rows(
        added_A,
        added_B,
        span_iou_threshold=span_iou_threshold,
        mention_fuzzy_threshold=mention_fuzzy_threshold,
    )

    # Each aligned pair = TP-like item; both kept, with conditional comparison.
    for i, j in aligned:
        ra = added_A.iloc[i]
        rb = added_B.iloc[j]
        keep_A.append(1)
        keep_B.append(1)
        assertion_A.append(collapse_assertion(ra["assertion_status"]))
        assertion_B.append(collapse_assertion(rb["assertion_status"]))
        t_a = "" if pd.isna(ra["type"]) else str(ra["type"]).strip()
        t_b = "" if pd.isna(rb["type"]) else str(rb["type"]).strip()
        type_A.append(t_a)
        type_B.append(t_b)
        value_match.append(int(normalize_value(ra["value"]) == normalize_value(rb["value"])))
        unit_match.append(int(normalize_unit(ra["unit"]) == normalize_unit(rb["unit"])))

    # Each only-A added row = FN-like item (A added, B didn't).
    for _ in only_A:
        keep_A.append(1)
        keep_B.append(0)
    # Each only-B added row = FP-like item (B added, A didn't).
    for _ in only_B:
        keep_A.append(0)
        keep_B.append(1)

    return {
        "term_index": ti_universe,  # AI-draft IDs only (kept for back-compat)
        "keep_A": keep_A,
        "keep_B": keep_B,
        "assertion_A": assertion_A,
        "assertion_B": assertion_B,
        "type_A": type_A,
        "type_B": type_B,
        "value_match": value_match,
        "unit_match": unit_match,
        "n_added_A": int(a["term_index"].isna().sum()),
        "n_added_B": int(b["term_index"].isna().sum()),
        "n_added_aligned": len(aligned),
        "n_added_only_A": len(only_A),
        "n_added_only_B": len(only_B),
        "n_ai_draft": len(ti_universe),
    }


def _f1_keep(keep_A: list[int], keep_B: list[int]) -> dict:
    """Symmetric F1 + raw agreement + PABAK on the keep-vs-drop labeling.

    PABAK and raw_agreement are computed here (rather than in a separate
    helper) because they share the same 2x2 contingency table as F1 -- no
    point reloading data.
    """
    a = np.array(keep_A)
    b = np.array(keep_B)
    tp = int(((a == 1) & (b == 1)).sum())
    fp = int(((a == 0) & (b == 1)).sum())
    fn = int(((a == 1) & (b == 0)).sum())
    tn = int(((a == 0) & (b == 0)).sum())
    n = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else float("nan")
    )
    raw_agreement = (tp + tn) / n if n > 0 else float("nan")
    # PABAK = 2*p_o - 1; bounded [-1, 1]; collapses prevalence + bias to
    # the same denominator as κ has (1 - p_e_max), making it directly
    # comparable across imbalanced datasets (Byrt 1993).
    pabak = 2 * raw_agreement - 1 if n > 0 else float("nan")
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "n": n,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "raw_agreement": raw_agreement,
        "pabak": pabak,
    }


def _pabak_from_labels(a_labels: list, b_labels: list) -> dict:
    """PABAK on multi-class labels (e.g. collapsed assertion). N must be >0.

    Returns dict with raw_agreement and pabak. For multi-class PABAK we use
    the symmetric definition (2 * p_o - 1) — same as the binary case but
    applied to multi-way agreement rate. NB: multi-class PABAK is sometimes
    written with k-class adjustment (Brennan-Prediger), but the simple
    2*p_o-1 form is what most clinical NLP papers report; we stick with it
    for consistency with (a)'s definition.
    """
    if len(a_labels) == 0 or len(b_labels) == 0:
        return {"raw_agreement": float("nan"), "pabak": float("nan"), "n": 0}
    n = len(a_labels)
    matches = sum(1 for x, y in zip(a_labels, b_labels) if x == y)
    raw = matches / n
    return {"raw_agreement": raw, "pabak": 2 * raw - 1, "n": n}


def _safe_kappa(a: list, b: list) -> float:
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    a_arr = np.array(a)
    b_arr = np.array(b)
    if len(set(a_arr.tolist()) | set(b_arr.tolist())) < 2:
        return float("nan")
    return float(cohen_kappa_score(a_arr, b_arr))


def _agreement_rate(matches: list[int]) -> float:
    if len(matches) == 0:
        return float("nan")
    return float(sum(matches) / len(matches))


def _pool_metrics(pair_results: list[dict], dataset_filter: Optional[str] = None) -> dict:
    """Pool labels across notes and compute aggregate metrics."""
    keep_A_all, keep_B_all = [], []
    assertion_A_all, assertion_B_all = [], []
    type_A_all, type_B_all = [], []
    value_match_all, unit_match_all = [], []
    n_added_A_total = 0
    n_added_B_total = 0
    n_added_aligned_total = 0
    n_added_only_A_total = 0
    n_added_only_B_total = 0
    note_ids = []
    n_ai_draft_total = 0

    for r in pair_results:
        if dataset_filter is not None and r["dataset"] != dataset_filter:
            continue
        keep_A_all.extend(r["labels"]["keep_A"])
        keep_B_all.extend(r["labels"]["keep_B"])
        assertion_A_all.extend(r["labels"]["assertion_A"])
        assertion_B_all.extend(r["labels"]["assertion_B"])
        type_A_all.extend(r["labels"]["type_A"])
        type_B_all.extend(r["labels"]["type_B"])
        value_match_all.extend(r["labels"]["value_match"])
        unit_match_all.extend(r["labels"]["unit_match"])
        n_added_A_total += r["labels"]["n_added_A"]
        n_added_B_total += r["labels"]["n_added_B"]
        n_added_aligned_total += r["labels"]["n_added_aligned"]
        n_added_only_A_total += r["labels"]["n_added_only_A"]
        n_added_only_B_total += r["labels"]["n_added_only_B"]
        n_ai_draft_total += r["labels"]["n_ai_draft"]
        note_ids.append(r["note_id"])

    if not note_ids:
        return {
            "n_pairs": 0,
            "note_ids": [],
            "n_ai_draft_total": 0,
            "kappa_entity_keep": float("nan"),
            "f1_entity_keep": {
                "f1": float("nan"),
                "raw_agreement": float("nan"),
                "pabak": float("nan"),
            },
            "kappa_assertion": float("nan"),
            "pabak_assertion": {"raw_agreement": float("nan"), "pabak": float("nan"), "n": 0},
            "kappa_type": float("nan"),
            "value_agreement": float("nan"),
            "unit_agreement": float("nan"),
            "n_kept_by_both": 0,
            "n_added_A_total": 0,
            "n_added_B_total": 0,
            "n_added_aligned_total": 0,
            "n_added_only_A_total": 0,
            "n_added_only_B_total": 0,
        }

    kappa_entity = _safe_kappa(keep_A_all, keep_B_all)
    f1_entity = _f1_keep(keep_A_all, keep_B_all)
    kappa_assertion = _safe_kappa(assertion_A_all, assertion_B_all)
    pabak_assertion = _pabak_from_labels(assertion_A_all, assertion_B_all)
    kappa_type = _safe_kappa(type_A_all, type_B_all)
    value_agree = _agreement_rate(value_match_all)
    unit_agree = _agreement_rate(unit_match_all)

    return {
        "n_pairs": len(note_ids),
        "note_ids": note_ids,
        "n_ai_draft_total": n_ai_draft_total,
        "kappa_entity_keep": kappa_entity,
        "f1_entity_keep": f1_entity,  # contains f1, raw_agreement, pabak, tp/fp/fn/tn
        "kappa_assertion": kappa_assertion,
        "pabak_assertion": pabak_assertion,
        "kappa_type": kappa_type,
        "value_agreement": value_agree,
        "unit_agreement": unit_agree,
        "n_kept_by_both": len(assertion_A_all),
        "n_added_A_total": n_added_A_total,
        "n_added_B_total": n_added_B_total,
        "n_added_aligned_total": n_added_aligned_total,
        "n_added_only_A_total": n_added_only_A_total,
        "n_added_only_B_total": n_added_only_B_total,
        "_labels": {
            "assertion_A": assertion_A_all,
            "assertion_B": assertion_B_all,
            "type_A": type_A_all,
            "type_B": type_B_all,
        },
    }


def _render_report(
    overall: dict,
    per_dataset: dict[str, dict],
    pair_results: list[dict],
    unpaired: list[dict],
    config: dict,
) -> str:
    lines = []
    lines.append("=" * 88)
    lines.append("EXP-A2 Inter-Annotator Agreement Report (improved vs EXP-A)")
    lines.append("=" * 88)
    lines.append("")
    lines.append("Improvements vs EXP-A:")
    lines.append("  (a) PABAK = 2*p_o - 1 added per dataset (entity-keep and assertion).")
    lines.append(f"  (b) Annotator-added rows fuzzy-aligned by (span IoU >= {config['span_iou_threshold']})")
    lines.append(f"      AND (mention SequenceMatcher ratio >= {config['mention_fuzzy_threshold']}).")
    lines.append("  (c) raw_agreement = (TP+TN)/N now reported explicitly per dataset.")
    lines.append("")
    lines.append("Caveat (unchanged from EXP-A): Both annotators worked from the same")
    lines.append("AI-suggested draft. κ values reflect agreement on acceptance/rejection/")
    lines.append("edit of AI suggestions, not de-novo agreement on free text. Methods must")
    lines.append("state this explicitly (review-style cross-annotation).")
    lines.append("")

    def _fmt(v):
        if isinstance(v, float):
            return f"{v:.4f}" if not np.isnan(v) else "  NaN"
        return str(v)

    lines.append("-" * 88)
    lines.append("Aggregate entity-level metrics (per dataset, labels pooled across notes)")
    lines.append("Universe = AI-draft term_index UNION fuzzy-aligned added pairs UNION unaligned added rows")
    lines.append("-" * 88)
    header = (
        f"{'split':<10} {'n_pairs':>8} {'n_items':>8} {'κ_entity':>10} {'PABAK_e':>10} "
        f"{'raw_agr':>10} {'F1_entity':>10} {'κ_assert':>10} {'PABAK_a':>10} "
        f"{'κ_type':>10} {'val_agr':>10} {'unit_agr':>10}"
    )
    lines.append(header)
    for split_name, m in [("overall", overall)] + sorted(per_dataset.items()):
        f1 = m["f1_entity_keep"]
        pa = m["pabak_assertion"]
        lines.append(
            f"{split_name:<10} {m['n_pairs']:>8} {f1.get('n', 0):>8} "
            f"{_fmt(m['kappa_entity_keep']):>10} {_fmt(f1.get('pabak', float('nan'))):>10} "
            f"{_fmt(f1.get('raw_agreement', float('nan'))):>10} {_fmt(f1['f1']):>10} "
            f"{_fmt(m['kappa_assertion']):>10} {_fmt(pa.get('pabak', float('nan'))):>10} "
            f"{_fmt(m['kappa_type']):>10} "
            f"{_fmt(m['value_agreement']):>10} {_fmt(m['unit_agreement']):>10}"
        )

    lines.append("")
    lines.append("-" * 88)
    lines.append("F1-entity-keep components (per split; N = TP+FP+FN+TN)")
    lines.append("-" * 88)
    for split_name, m in [("overall", overall)] + sorted(per_dataset.items()):
        f1 = m["f1_entity_keep"]
        lines.append(
            f"{split_name:<10} TP={f1['tp']:>5}  FP={f1['fp']:>5}  FN={f1['fn']:>5}  "
            f"TN={f1['tn']:>5}  N={f1['n']:>5}  P={_fmt(f1['precision'])}  "
            f"R={_fmt(f1['recall'])}  F1={_fmt(f1['f1'])}"
        )

    lines.append("")
    lines.append("-" * 88)
    lines.append("Added-row alignment summary (n_added_A / n_added_B / aligned pairs / only_A / only_B)")
    lines.append("-" * 88)
    for split_name, m in [("overall", overall)] + sorted(per_dataset.items()):
        lines.append(
            f"{split_name:<10} "
            f"n_added_A={m['n_added_A_total']:>4}  n_added_B={m['n_added_B_total']:>4}  "
            f"aligned={m['n_added_aligned_total']:>4}  "
            f"only_A={m['n_added_only_A_total']:>4}  only_B={m['n_added_only_B_total']:>4}"
        )

    lines.append("")
    lines.append("-" * 88)
    lines.append("sklearn classification_report — assertion (kept-by-both rows, includes aligned added pairs)")
    lines.append("-" * 88)
    for split_name, m in [("overall", overall)] + sorted(per_dataset.items()):
        labs = m.get("_labels", {})
        a_lab = labs.get("assertion_A", [])
        b_lab = labs.get("assertion_B", [])
        if not a_lab:
            lines.append(f"\n[{split_name}] n=0, skipped")
            continue
        try:
            rep = classification_report(
                a_lab, b_lab, zero_division=0, digits=4
            )
        except Exception as e:
            rep = f"(report failed: {e})"
        lines.append(f"\n[{split_name}] assertion (A as ref, B as pred):")
        lines.append(rep)

    lines.append("")
    lines.append("-" * 88)
    lines.append("Per-note point estimates (no PHI; counts + note ids only)")
    lines.append("-" * 88)
    per_note_hdr = (
        f"{'dataset':<6} {'note_id':<14} {'orig':<5} {'cross':<5} {'n_items':>8} "
        f"{'n_A':>5} {'n_B':>5} {'n_both':>7} {'aln':>4} {'oA':>4} {'oB':>4} "
        f"{'κ_kept':>8} {'PABAK':>8} {'raw_a':>8} {'F1_kept':>8}"
    )
    lines.append(per_note_hdr)
    for r in pair_results:
        lab = r["labels"]
        n_a = sum(lab["keep_A"])
        n_b = sum(lab["keep_B"])
        kappa = _safe_kappa(lab["keep_A"], lab["keep_B"])
        f1d = _f1_keep(lab["keep_A"], lab["keep_B"])
        lines.append(
            f"{r['dataset']:<6} {r['note_id']:<14} {r['original_annotator']:<5} {r['cross_annotator']:<5} "
            f"{f1d['n']:>8} {n_a:>5} {n_b:>5} {f1d['tp']:>7} "
            f"{lab['n_added_aligned']:>4} {lab['n_added_only_A']:>4} {lab['n_added_only_B']:>4} "
            f"{_fmt(kappa):>8} {_fmt(f1d['pabak']):>8} {_fmt(f1d['raw_agreement']):>8} {_fmt(f1d['f1']):>8}"
        )

    lines.append("")
    lines.append("-" * 88)
    lines.append("Unpaired / excluded notes")
    lines.append("-" * 88)
    if not unpaired:
        lines.append("(none)")
    else:
        for u in unpaired:
            lines.append(f"- {u['dataset']}/{u['note_id']}: {u['reason']}")

    lines.append("")
    lines.append("-" * 88)
    lines.append("Added-row alignment outcome summary")
    lines.append("-" * 88)
    a_total = sum(r["labels"]["n_added_A"] for r in pair_results)
    b_total = sum(r["labels"]["n_added_B"] for r in pair_results)
    aligned_total = sum(r["labels"]["n_added_aligned"] for r in pair_results)
    only_a_total = sum(r["labels"]["n_added_only_A"] for r in pair_results)
    only_b_total = sum(r["labels"]["n_added_only_B"] for r in pair_results)
    lines.append(f"Total added rows in original-annotator CSVs (across all pairs):  {a_total}")
    lines.append(f"Total added rows in cross-annotator CSVs (across all pairs):     {b_total}")
    lines.append(f"Fuzzy-aligned pairs (counted as TP, both keep=1):                {aligned_total}")
    lines.append(f"Unaligned A-side (counted as FN, keep_A=1 keep_B=0):             {only_a_total}")
    lines.append(f"Unaligned B-side (counted as FP, keep_A=0 keep_B=1):             {only_b_total}")
    lines.append(
        f"Coverage: 2*aligned + only_A + only_B = "
        f"{2*aligned_total + only_a_total + only_b_total} of {a_total + b_total} total added rows."
    )
    lines.append("")
    lines.append(
        "Note: each aligned pair contributes ONE TP row to the entity-level "
        "contingency table (not two). 2*aligned + only_A + only_B should equal "
        "the sum of added rows on both sides; if not, the alignment is double-counting."
    )

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="EXP-A2 IAA computation (improved)")
    ap.add_argument("--cross_anno_dir", type=Path, required=True)
    ap.add_argument("--gold_dir", type=Path, required=True)
    ap.add_argument("--out_dir", type=Path, required=True)
    ap.add_argument(
        "--span_iou_threshold",
        type=float,
        default=DEFAULT_SPAN_IOU_THRESHOLD,
        help=f"Minimum span IoU for added-row alignment (default {DEFAULT_SPAN_IOU_THRESHOLD})",
    )
    ap.add_argument(
        "--mention_fuzzy_threshold",
        type=float,
        default=DEFAULT_MENTION_FUZZY_THRESHOLD,
        help=f"Minimum SequenceMatcher.ratio() on mention text for added-row alignment "
             f"(default {DEFAULT_MENTION_FUZZY_THRESHOLD})",
    )
    args = ap.parse_args()

    workdir = args.out_dir / "_unzipped"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(exist_ok=True)

    config = {
        "span_iou_threshold": args.span_iou_threshold,
        "mention_fuzzy_threshold": args.mention_fuzzy_threshold,
    }

    print(f"[EXP-A2] Discovering pairs in {args.cross_anno_dir} ...", flush=True)
    pairs, unpaired = discover_note_pairs(args.cross_anno_dir, args.gold_dir, workdir)
    print(f"[EXP-A2] Found {len(pairs)} paired notes, {len(unpaired)} unpaired entries.", flush=True)
    print(f"[EXP-A2] Added-row fuzzy align thresholds: span_IoU>={args.span_iou_threshold}, "
          f"mention_fuzzy>={args.mention_fuzzy_threshold}", flush=True)

    pair_results = []
    for p in pairs:
        print(f"[EXP-A2]   pairing {p.dataset}/{p.note_id} ({p.original_annotator} vs {p.cross_annotator}) ...", flush=True)
        labels = _build_label_table(
            p,
            span_iou_threshold=args.span_iou_threshold,
            mention_fuzzy_threshold=args.mention_fuzzy_threshold,
        )
        pair_results.append({
            "dataset": p.dataset,
            "note_id": p.note_id,
            "original_annotator": p.original_annotator,
            "cross_annotator": p.cross_annotator,
            "labels": labels,
        })

    overall = _pool_metrics(pair_results, dataset_filter=None)
    per_dataset = {
        "4CE": _pool_metrics(pair_results, dataset_filter="4CE"),
        "CORAL": _pool_metrics(pair_results, dataset_filter="CORAL"),
    }

    def _strip_labels(d):
        return {k: v for k, v in d.items() if k != "_labels"}

    metrics_payload = {
        "exp_id": "EXP-A2",
        "n_pairs_total": len(pairs),
        "n_unpaired": len(unpaired),
        "overall": _strip_labels(overall),
        "per_dataset": {k: _strip_labels(v) for k, v in per_dataset.items()},
        "unpaired_notes": unpaired,
        "config": {
            "improvements_vs_EXP-A": [
                "(a) PABAK reported per dataset (entity + assertion)",
                "(b) Annotator-added rows fuzzy-aligned by (span IoU >= "
                f"{args.span_iou_threshold}) AND (mention SequenceMatcher ratio >= "
                f"{args.mention_fuzzy_threshold}); aligned pairs now contribute to κ/F1",
                "(c) raw_agreement = (TP+TN)/N reported per dataset",
            ],
            "span_iou_threshold": args.span_iou_threshold,
            "mention_fuzzy_threshold": args.mention_fuzzy_threshold,
            "assertion_collapse": "5-way (Present/Absent/Possible/Conditional/Notassociated; see iaa_utils.ASSERTION_COLLAPSE)",
            "value_normalization": "exact string after .strip()",
            "unit_normalization": "exact string after .strip().lower()",
            "type_comparison": "exact string after .strip() (94-class UMLS semantic type space)",
            "kept_dropped_unit": "presence of term_index in annotator CSV (for AI-draft items); fuzzy alignment (for added items)",
            "span_alignment": "exact (annotator tool preserves AI-suggested span for kept rows); fuzzy IoU+ratio for added rows",
            "pabak_formula": "2 * (TP+TN)/N - 1 = 2*raw_agreement - 1  (Byrt, Bishop & Carlin 1993)",
        },
    }
    metrics_path = args.out_dir / "metrics.json"
    with metrics_path.open("w") as f:
        json.dump(metrics_payload, f, indent=2, default=str)
    print(f"[EXP-A2] Wrote {metrics_path}", flush=True)

    rows = []
    for r in pair_results:
        lab = r["labels"]
        f1d = _f1_keep(lab["keep_A"], lab["keep_B"])
        rows.append({
            "dataset": r["dataset"],
            "note_id": r["note_id"],
            "original_annotator": r["original_annotator"],
            "cross_annotator": r["cross_annotator"],
            "n_ai_draft": lab["n_ai_draft"],
            "n_items": f1d["n"],
            "n_kept_original": sum(lab["keep_A"]),
            "n_kept_cross": sum(lab["keep_B"]),
            "n_kept_both": f1d["tp"],
            "n_only_original": f1d["fn"],
            "n_only_cross": f1d["fp"],
            "n_neither": f1d["tn"],
            "n_added_original": lab["n_added_A"],
            "n_added_cross": lab["n_added_B"],
            "n_added_aligned": lab["n_added_aligned"],
            "n_added_only_A": lab["n_added_only_A"],
            "n_added_only_B": lab["n_added_only_B"],
            "kappa_entity_keep": _safe_kappa(lab["keep_A"], lab["keep_B"]),
            "pabak_entity_keep": f1d["pabak"],
            "raw_agreement_entity_keep": f1d["raw_agreement"],
            "f1_entity_keep": f1d["f1"],
            "kappa_assertion_kept_by_both": _safe_kappa(lab["assertion_A"], lab["assertion_B"]),
            "kappa_type_kept_by_both": _safe_kappa(lab["type_A"], lab["type_B"]),
            "value_agreement_kept_by_both": _agreement_rate(lab["value_match"]),
            "unit_agreement_kept_by_both": _agreement_rate(lab["unit_match"]),
        })
    per_note_df = pd.DataFrame(rows)
    per_note_path = args.out_dir / "per_note_breakdown.csv"
    per_note_df.to_csv(per_note_path, index=False)
    print(f"[EXP-A2] Wrote {per_note_path}", flush=True)

    manifest_rows = []
    for r in pair_results:
        manifest_rows.append({
            "dataset": r["dataset"],
            "note_id": r["note_id"],
            "original_annotator": r["original_annotator"],
            "cross_annotator": r["cross_annotator"],
            "status": "paired",
        })
    for u in unpaired:
        manifest_rows.append({
            "dataset": u.get("dataset"),
            "note_id": u.get("note_id"),
            "original_annotator": u.get("original_annotator", ""),
            "cross_annotator": u.get("cross_annotator", ""),
            "status": "unpaired: " + u.get("reason", ""),
        })
    manifest_df = pd.DataFrame(manifest_rows)
    manifest_path = args.out_dir / "pair_manifest.csv"
    manifest_df.to_csv(manifest_path, index=False)
    print(f"[EXP-A2] Wrote {manifest_path}", flush=True)

    report_text = _render_report(overall, per_dataset, pair_results, unpaired, config)
    report_path = args.out_dir / "report.txt"
    with report_path.open("w") as f:
        f.write(report_text + "\n")
    print(f"[EXP-A2] Wrote {report_path}", flush=True)

    print("[EXP-A2] Done.", flush=True)
    print()
    print(report_text)


if __name__ == "__main__":
    main()

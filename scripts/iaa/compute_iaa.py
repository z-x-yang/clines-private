"""EXP-A: Inter-Annotator Agreement (IAA) computation for the BMJ revision.

See ``experiments/EXP-A_iaa_cohen_kappa.md`` for the full design.

Metric definitions
------------------
For each (note, annotator-pair), the universe of items is the AI-draft
``term_index`` set. For each ``term_index`` row in the AI draft we form
two parallel labels:

  keep[A]   = 1 if A kept the row in their returned CSV, else 0
  keep[B]   = 1 if B kept the row, else 0

Entity-level metrics (over the AI-draft universe):
  - Cohen's κ on (keep[A], keep[B])
  - F1: precision = TP / (TP + FP), recall = TP / (TP + FN) where
        TP = both kept, FP = only B kept, FN = only A kept.
        F1 is symmetric in A,B, so the choice of "ref" is cosmetic.
  - Span-aligned F1: identical to entity-level F1 because the EHR
    annotation tool keeps the AI-suggested span verbatim for kept rows
    (verified empirically on the cross-annotation set with zero
    start_pos/end_pos edits). Span IoU >= 0.5 is trivially satisfied.

Conditional-on-both-kept metrics (over rows kept by both):
  - Cohen's κ on collapsed 5-way assertion class
  - Cohen's κ on UMLS semantic ``type``
  - exact-match agreement rate on ``value``
  - exact-match agreement rate on ``unit``

Aggregation
-----------
Per dataset (4CE / CORAL-merged), we pool labels across all paired notes
within that dataset before computing κ/F1. This matches CLINES paper
style and gives the highest-power point estimate. Per-note metrics are
also reported in the breakdown CSV for downstream EXP-B bootstrap CI.
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
    NotePair,
    collapse_assertion,
    discover_note_pairs,
    load_review_csv,
    normalize_unit,
    normalize_value,
)


def _build_label_table(pair: NotePair) -> dict:
    """Build the per-term_index label table for one pair.

    Returns a dict with parallel lists keyed by ``term_index``:
      keep_A, keep_B           : 0/1 for entity-level κ/F1 (universe = AI-draft term_index)
      assertion_A, assertion_B : 5-class label among rows kept by BOTH
      type_A, type_B           : UMLS semantic type, kept-by-both
      value_match              : 1/0 exact match, kept-by-both
      unit_match               : 1/0 exact match, kept-by-both
      n_added_A, n_added_B     : count of NaN-term_index rows in each CSV (for §10 reporting)
    """
    ai = load_review_csv(pair.ai_draft_csv)
    a = load_review_csv(pair.original_csv)
    b = load_review_csv(pair.cross_csv)

    # The AI draft is the universe of term_index. Validate that A/B CSVs use
    # the same draft (any term_index in A/B that's not in AI is either an
    # added row (NaN) or a schema mismatch).
    ai_ti = set(ai["term_index"].dropna().astype(int).tolist())

    def _to_int_set(s: pd.Series) -> set[int]:
        # Annotator CSVs sometimes have term_index as float (because of NaN
        # rows for additions). Drop NaN, cast int.
        return set(s.dropna().astype(int).tolist())

    a_ti = _to_int_set(a["term_index"])
    b_ti = _to_int_set(b["term_index"])
    a_extra = a_ti - ai_ti
    b_extra = b_ti - ai_ti
    if a_extra or b_extra:
        # Annotator-edited term_index values would corrupt alignment. Fail fast
        # so we surface the schema event instead of silently misaligning rows.
        raise ValueError(
            f"{pair.note_id}: annotator CSV contains term_index values not in AI draft "
            f"(A extras={sorted(a_extra)[:10]}, B extras={sorted(b_extra)[:10]}). "
            "Refusing to silently misalign."
        )

    # Index A/B by term_index for fast lookup (only non-NaN ti).
    a_idx = a.dropna(subset=["term_index"]).copy()
    a_idx["term_index"] = a_idx["term_index"].astype(int)
    a_idx = a_idx.set_index("term_index")
    b_idx = b.dropna(subset=["term_index"]).copy()
    b_idx["term_index"] = b_idx["term_index"].astype(int)
    b_idx = b_idx.set_index("term_index")

    ti_universe = sorted(ai_ti)
    keep_A = [int(ti in a_ti) for ti in ti_universe]
    keep_B = [int(ti in b_ti) for ti in ti_universe]

    assertion_A, assertion_B = [], []
    type_A, type_B = [], []
    value_match, unit_match = [], []

    for ti in ti_universe:
        if ti in a_ti and ti in b_ti:
            ra = a_idx.loc[ti]
            rb = b_idx.loc[ti]
            # If duplicate term_index in a CSV, pandas .loc returns DataFrame;
            # take the first row (no known case, but defensive).
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

    n_added_A = int(a["term_index"].isna().sum())
    n_added_B = int(b["term_index"].isna().sum())

    return {
        "term_index": ti_universe,
        "keep_A": keep_A,
        "keep_B": keep_B,
        "assertion_A": assertion_A,
        "assertion_B": assertion_B,
        "type_A": type_A,
        "type_B": type_B,
        "value_match": value_match,
        "unit_match": unit_match,
        "n_added_A": n_added_A,
        "n_added_B": n_added_B,
        "n_ai_draft": len(ti_universe),
    }


def _f1_keep(keep_A: list[int], keep_B: list[int]) -> dict:
    """Symmetric F1 on the keep-vs-drop labeling.

    Treat A's kept rows as ref, B's kept as predicted (or vice versa — both
    give the same F1, so the choice is purely cosmetic). Returns the
    precision/recall/F1 plus TP/FP/FN counts.
    """
    a = np.array(keep_A)
    b = np.array(keep_B)
    tp = int(((a == 1) & (b == 1)).sum())
    fp = int(((a == 0) & (b == 1)).sum())
    fn = int(((a == 1) & (b == 0)).sum())
    tn = int(((a == 0) & (b == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else float("nan")
    )
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _safe_kappa(a: list, b: list) -> float:
    """Cohen's κ; return NaN if either side is constant (κ undefined).

    No silent fallback (§2 fail-fast): if both lists are empty or one side
    is constant, return NaN with the caller responsible for reporting it."""
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    # sklearn returns 0 (degenerate) when both annotators agree perfectly +
    # only one class present. We surface this as NaN so the report shows
    # the degeneracy explicitly.
    a_arr = np.array(a)
    b_arr = np.array(b)
    if len(set(a_arr.tolist()) | set(b_arr.tolist())) < 2:
        # Only one label present across both — κ is undefined; report
        # agreement rate as the surrogate.
        return float("nan")
    return float(cohen_kappa_score(a_arr, b_arr))


def _agreement_rate(matches: list[int]) -> float:
    if len(matches) == 0:
        return float("nan")
    return float(sum(matches) / len(matches))


def _pool_metrics(pair_results: list[dict], dataset_filter: Optional[str] = None) -> dict:
    """Pool labels across notes and compute aggregate metrics.

    dataset_filter='4CE' or 'CORAL', or None for 'overall'."""
    keep_A_all, keep_B_all = [], []
    assertion_A_all, assertion_B_all = [], []
    type_A_all, type_B_all = [], []
    value_match_all, unit_match_all = [], []
    n_added_A_total = 0
    n_added_B_total = 0
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
        n_ai_draft_total += r["labels"]["n_ai_draft"]
        note_ids.append(r["note_id"])

    if not note_ids:
        return {
            "n_pairs": 0,
            "note_ids": [],
            "n_ai_draft_total": 0,
            "kappa_entity_keep": float("nan"),
            "f1_entity_keep": {"f1": float("nan")},
            "kappa_assertion": float("nan"),
            "kappa_type": float("nan"),
            "value_agreement": float("nan"),
            "unit_agreement": float("nan"),
            "n_kept_by_both": 0,
            "n_added_A_total": 0,
            "n_added_B_total": 0,
        }

    kappa_entity = _safe_kappa(keep_A_all, keep_B_all)
    f1_entity = _f1_keep(keep_A_all, keep_B_all)
    kappa_assertion = _safe_kappa(assertion_A_all, assertion_B_all)
    kappa_type = _safe_kappa(type_A_all, type_B_all)
    value_agree = _agreement_rate(value_match_all)
    unit_agree = _agreement_rate(unit_match_all)

    return {
        "n_pairs": len(note_ids),
        "note_ids": note_ids,
        "n_ai_draft_total": n_ai_draft_total,
        "kappa_entity_keep": kappa_entity,
        "f1_entity_keep": f1_entity,
        "kappa_assertion": kappa_assertion,
        "kappa_type": kappa_type,
        "value_agreement": value_agree,
        "unit_agreement": unit_agree,
        "n_kept_by_both": len(assertion_A_all),
        "n_added_A_total": n_added_A_total,
        "n_added_B_total": n_added_B_total,
        # Stash pooled label lists for the sklearn classification_report below.
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
) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("EXP-A Inter-Annotator Agreement Report")
    lines.append("=" * 72)
    lines.append("")
    lines.append("Caveat: Both annotators worked from the same AI-suggested draft.")
    lines.append("κ values reflect agreement on acceptance/rejection/edit of the")
    lines.append("AI suggestions, not de-novo agreement on free text. Methods must")
    lines.append("state this explicitly (review-style cross-annotation).")
    lines.append("")
    lines.append("-" * 72)
    lines.append("Aggregate metrics (per dataset, labels pooled across notes)")
    lines.append("-" * 72)

    def _fmt(v):
        if isinstance(v, float):
            return f"{v:.4f}" if not np.isnan(v) else "  NaN"
        return str(v)

    header = f"{'split':<14} {'n_pairs':>8} {'n_draft':>8} {'n_both':>8} {'κ_entity':>10} {'F1_entity':>10} {'κ_assert':>10} {'κ_type':>10} {'val_agr':>10} {'unit_agr':>10}"
    lines.append(header)
    for split_name, m in [("overall", overall)] + sorted(per_dataset.items()):
        lines.append(
            f"{split_name:<14} {m['n_pairs']:>8} {m['n_ai_draft_total']:>8} {m['n_kept_by_both']:>8} "
            f"{_fmt(m['kappa_entity_keep']):>10} {_fmt(m['f1_entity_keep']['f1']):>10} "
            f"{_fmt(m['kappa_assertion']):>10} {_fmt(m['kappa_type']):>10} "
            f"{_fmt(m['value_agreement']):>10} {_fmt(m['unit_agreement']):>10}"
        )

    lines.append("")
    lines.append("-" * 72)
    lines.append("F1-entity-keep components (per split)")
    lines.append("-" * 72)
    for split_name, m in [("overall", overall)] + sorted(per_dataset.items()):
        f1 = m["f1_entity_keep"]
        lines.append(
            f"{split_name:<14} TP={f1['tp']:>5}  FP={f1['fp']:>5}  FN={f1['fn']:>5}  TN={f1['tn']:>5}  "
            f"P={_fmt(f1['precision'])}  R={_fmt(f1['recall'])}  F1={_fmt(f1['f1'])}"
        )

    lines.append("")
    lines.append("-" * 72)
    lines.append("sklearn classification_report — assertion (kept-by-both rows)")
    lines.append("-" * 72)
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
    lines.append("-" * 72)
    lines.append("Per-note point estimates (no PHI; counts + note ids only)")
    lines.append("-" * 72)
    per_note_hdr = f"{'dataset':<6} {'note_id':<14} {'orig':<5} {'cross':<5} {'n_draft':>8} {'n_A':>5} {'n_B':>5} {'n_both':>7} {'κ_kept':>10} {'F1_kept':>10}"
    lines.append(per_note_hdr)
    for r in pair_results:
        lab = r["labels"]
        n_a = sum(lab["keep_A"])
        n_b = sum(lab["keep_B"])
        kappa = _safe_kappa(lab["keep_A"], lab["keep_B"])
        f1d = _f1_keep(lab["keep_A"], lab["keep_B"])
        lines.append(
            f"{r['dataset']:<6} {r['note_id']:<14} {r['original_annotator']:<5} {r['cross_annotator']:<5} "
            f"{lab['n_ai_draft']:>8} {n_a:>5} {n_b:>5} {f1d['tp']:>7} "
            f"{_fmt(kappa):>10} {_fmt(f1d['f1']):>10}"
        )

    lines.append("")
    lines.append("-" * 72)
    lines.append("Unpaired / excluded notes")
    lines.append("-" * 72)
    if not unpaired:
        lines.append("(none)")
    else:
        for u in unpaired:
            lines.append(f"- {u['dataset']}/{u['note_id']}: {u['reason']}")

    lines.append("")
    lines.append("-" * 72)
    lines.append("Annotator-added rows (term_index = NaN; excluded from κ/F1)")
    lines.append("-" * 72)
    a_total = sum(r["labels"]["n_added_A"] for r in pair_results)
    b_total = sum(r["labels"]["n_added_B"] for r in pair_results)
    lines.append(f"Total added rows in original-annotator CSVs (across all pairs):  {a_total}")
    lines.append(f"Total added rows in cross-annotator CSVs (across all pairs):     {b_total}")
    lines.append("")
    lines.append("These cannot be aligned across annotators (no shared key) and are")
    lines.append("excluded from κ/F1. Reported as raw counts for §10 transparency.")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="EXP-A IAA computation")
    ap.add_argument("--cross_anno_dir", type=Path, required=True)
    ap.add_argument("--gold_dir", type=Path, required=True)
    ap.add_argument("--out_dir", type=Path, required=True)
    args = ap.parse_args()

    workdir = args.out_dir / "_unzipped"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(exist_ok=True)

    print(f"[EXP-A] Discovering pairs in {args.cross_anno_dir} ...", flush=True)
    pairs, unpaired = discover_note_pairs(args.cross_anno_dir, args.gold_dir, workdir)
    print(f"[EXP-A] Found {len(pairs)} paired notes, {len(unpaired)} unpaired entries.", flush=True)

    pair_results = []
    for p in pairs:
        print(f"[EXP-A]   pairing {p.dataset}/{p.note_id} ({p.original_annotator} vs {p.cross_annotator}) ...", flush=True)
        labels = _build_label_table(p)
        pair_results.append({
            "dataset": p.dataset,
            "note_id": p.note_id,
            "original_annotator": p.original_annotator,
            "cross_annotator": p.cross_annotator,
            "labels": labels,
        })

    # Aggregate
    overall = _pool_metrics(pair_results, dataset_filter=None)
    per_dataset = {
        "4CE": _pool_metrics(pair_results, dataset_filter="4CE"),
        "CORAL": _pool_metrics(pair_results, dataset_filter="CORAL"),
    }

    # ----- Write metrics.json (no PHI, just numbers + note ids) -----
    def _strip_labels(d):
        out = {k: v for k, v in d.items() if k != "_labels"}
        return out

    metrics_payload = {
        "exp_id": "EXP-A",
        "n_pairs_total": len(pairs),
        "n_unpaired": len(unpaired),
        "overall": _strip_labels(overall),
        "per_dataset": {k: _strip_labels(v) for k, v in per_dataset.items()},
        "unpaired_notes": unpaired,
        "config": {
            "assertion_collapse": "5-way (Present/Absent/Possible/Conditional/Notassociated; see iaa_utils.ASSERTION_COLLAPSE)",
            "value_normalization": "exact string after .strip()",
            "unit_normalization": "exact string after .strip().lower()",
            "type_comparison": "exact string after .strip() (94-class UMLS semantic type space)",
            "kept_dropped_unit": "presence of term_index in annotator CSV",
            "span_alignment": "exact (annotator tool preserves AI-suggested span; verified empirically)",
        },
    }
    metrics_path = args.out_dir / "metrics.json"
    with metrics_path.open("w") as f:
        json.dump(metrics_payload, f, indent=2, default=str)
    print(f"[EXP-A] Wrote {metrics_path}", flush=True)

    # ----- Write per-note breakdown CSV (no PHI: counts only) -----
    rows = []
    for r in pair_results:
        lab = r["labels"]
        rows.append({
            "dataset": r["dataset"],
            "note_id": r["note_id"],
            "original_annotator": r["original_annotator"],
            "cross_annotator": r["cross_annotator"],
            "n_ai_draft": lab["n_ai_draft"],
            "n_kept_original": sum(lab["keep_A"]),
            "n_kept_cross": sum(lab["keep_B"]),
            "n_kept_both": sum(1 for a, b in zip(lab["keep_A"], lab["keep_B"]) if a and b),
            "n_only_original": sum(1 for a, b in zip(lab["keep_A"], lab["keep_B"]) if a and not b),
            "n_only_cross": sum(1 for a, b in zip(lab["keep_A"], lab["keep_B"]) if (not a) and b),
            "n_neither": sum(1 for a, b in zip(lab["keep_A"], lab["keep_B"]) if (not a) and (not b)),
            "n_added_original": lab["n_added_A"],
            "n_added_cross": lab["n_added_B"],
            "kappa_entity_keep": _safe_kappa(lab["keep_A"], lab["keep_B"]),
            "f1_entity_keep": _f1_keep(lab["keep_A"], lab["keep_B"])["f1"],
            "kappa_assertion_kept_by_both": _safe_kappa(lab["assertion_A"], lab["assertion_B"]),
            "kappa_type_kept_by_both": _safe_kappa(lab["type_A"], lab["type_B"]),
            "value_agreement_kept_by_both": _agreement_rate(lab["value_match"]),
            "unit_agreement_kept_by_both": _agreement_rate(lab["unit_match"]),
        })
    per_note_df = pd.DataFrame(rows)
    per_note_path = args.out_dir / "per_note_breakdown.csv"
    per_note_df.to_csv(per_note_path, index=False)
    print(f"[EXP-A] Wrote {per_note_path}", flush=True)

    # ----- Write pair manifest -----
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
    print(f"[EXP-A] Wrote {manifest_path}", flush=True)

    # ----- Write human-readable report -----
    report_text = _render_report(overall, per_dataset, pair_results, unpaired)
    report_path = args.out_dir / "report.txt"
    with report_path.open("w") as f:
        f.write(report_text + "\n")
    print(f"[EXP-A] Wrote {report_path}", flush=True)

    print("[EXP-A] Done.", flush=True)
    # Also print the report to stdout so it shows up in any monitor.
    print()
    print(report_text)


if __name__ == "__main__":
    main()

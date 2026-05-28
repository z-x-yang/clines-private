#!/usr/bin/env python
"""EXP-J: run-to-run output consistency of the CLINES pipeline.

Reads the 5 independent runs' per-note i2b2-style CSVs for the same 20 notes
and quantifies how much the structured outputs vary across runs (reviewer
R5.4.5; Supplementary S4).

Metrics
-------
1. Pairwise mention-set Jaccard and code-set Jaccard over the C(5,2)=10 run
   pairs, per note. mention set = set of (start,end,mention) spans; code set =
   set of `code` values. Report mean across pairs and notes, plus min/max.
2. Per-field majority-vote stability: for each mention matched across runs and
   each field in {assertion_status,value,unit,begin_date,end_date}, the
   fraction of the 5 runs equal to the modal value; averaged over cells.
   A mention is keyed by its (start,end,mention) span; we only score spans that
   appear in >=2 runs (a singleton has no cross-run agreement to measure). For a
   given span+field we take, per run, the field value if that span is present in
   that run (else the run does not contribute to that cell's denominator).
"""
import os
import re
import sys
import json
import glob
import math
from collections import defaultdict, Counter
from itertools import combinations

import pandas as pd

RUN_ROOT = os.path.dirname(os.path.abspath(__file__))  # runs/EXP-J or runs/EXP-J2
EXP_ID = os.path.basename(RUN_ROOT)                     # "EXP-J" or "EXP-J2"
N_RUNS = 5
SLICES = ["4CE", "coral_breastca", "coral_pdac"]
FIELDS = ["assertion_status", "value", "unit", "begin_date", "end_date"]


def norm(v):
    """Normalize a field value to a comparable string; NaN/empty -> ''."""
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    s = str(v).strip()
    if s.lower() in ("nan", "none"):
        return ""
    return s


def span_key(row):
    return (norm(row.get("mention_start_pos")),
            norm(row.get("mention_end_pos")),
            norm(row.get("mention")))


def note_id_from_filename(fname, slice_name, run):
    """{EXP_ID}_run{R}_{slice}_{noteid}_default.csv -> noteid."""
    base = os.path.basename(fname)
    prefix = f"{EXP_ID}_run{run}_{slice_name}_"
    suffix = "_default.csv"
    if base.startswith(prefix) and base.endswith(suffix):
        return base[len(prefix):-len(suffix)]
    return None


def load_run_note(slice_name, run, note_id):
    fname = os.path.join(RUN_ROOT, f"run{run}", slice_name,
                         f"{EXP_ID}_run{run}_{slice_name}_{note_id}_default.csv")
    if not os.path.exists(fname):
        return None
    try:
        df = pd.read_csv(fname, dtype=str, keep_default_na=False)
    except Exception as e:
        print(f"  WARN: failed to read {fname}: {e}", file=sys.stderr)
        return None
    return df


def jaccard(a, b):
    if not a and not b:
        return 1.0  # both empty == identical
    u = a | b
    if not u:
        return 1.0
    return len(a & b) / len(u)


def main():
    # 1. discover note ids per slice from run1 outputs (all runs share the list)
    notes_per_slice = {}
    for sl in SLICES:
        ids = set()
        for r in range(1, N_RUNS + 1):
            for f in glob.glob(os.path.join(RUN_ROOT, f"run{r}", sl,
                                            f"{EXP_ID}_run{r}_{sl}_*_default.csv")):
                nid = note_id_from_filename(f, sl, r)
                if nid:
                    ids.add(nid)
        notes_per_slice[sl] = sorted(ids)

    all_notes = [(sl, nid) for sl in SLICES for nid in notes_per_slice[sl]]

    # ---- coverage: which runs each note has. A note is SCORABLE if it has
    # >=2 runs (need at least one pair for Jaccard / one cross-run vote). We do
    # NOT require all N_RUNS — a note seen in k>=2 runs still yields C(k,2) valid
    # pairs and k-way majority votes, all legitimate consistency observations.
    # Hard-gating on ==N_RUNS would discard usable data when a run is partial.
    coverage = {}
    scorable_notes = []          # (sl, nid, [present_runs])
    for sl, nid in all_notes:
        present = [r for r in range(1, N_RUNS + 1)
                   if load_run_note(sl, r, nid) is not None]
        coverage[f"{sl}/{nid}"] = present
        if len(present) >= 2:
            scorable_notes.append((sl, nid, present))

    # ---- metric 1: pairwise jaccard over each note's available runs ----
    mention_jac_per_note = {}
    code_jac_per_note = {}
    for sl, nid, present in scorable_notes:
        run_mentions = {}
        run_codes = {}
        for r in present:
            df = load_run_note(sl, r, nid)
            run_mentions[r] = set(span_key(row) for _, row in df.iterrows())
            run_codes[r] = set(norm(c) for c in df["code"].tolist() if norm(c))
        m_pair, c_pair = [], []
        for a, b in combinations(present, 2):
            m_pair.append(jaccard(run_mentions[a], run_mentions[b]))
            c_pair.append(jaccard(run_codes[a], run_codes[b]))
        mention_jac_per_note[f"{sl}/{nid}"] = sum(m_pair) / len(m_pair)
        code_jac_per_note[f"{sl}/{nid}"] = sum(c_pair) / len(c_pair)

    def agg(d):
        vals = list(d.values())
        if not vals:
            return None
        return {"mean": sum(vals) / len(vals),
                "min": min(vals), "max": max(vals), "n": len(vals)}

    # ---- metric 2: per-field majority-vote stability ----
    # per field -> list of cell stabilities (one per span seen in >=2 runs)
    field_cells = defaultdict(list)
    for sl, nid, present in scorable_notes:
        # span -> {field -> {run -> value}}
        span_runs = defaultdict(lambda: defaultdict(dict))
        span_present_runs = defaultdict(set)
        for r in present:
            df = load_run_note(sl, r, nid)
            for _, row in df.iterrows():
                sk = span_key(row)
                span_present_runs[sk].add(r)
                for fld in FIELDS:
                    span_runs[sk][fld][r] = norm(row.get(fld))
        for sk, runs_set in span_present_runs.items():
            if len(runs_set) < 2:
                continue  # singleton span: no cross-run agreement to score
            for fld in FIELDS:
                vals = [span_runs[sk][fld][r] for r in sorted(runs_set)]
                cnt = Counter(vals)
                modal_freq = cnt.most_common(1)[0][1]
                field_cells[fld].append(modal_freq / len(vals))

    field_stability = {}
    for fld in FIELDS:
        cells = field_cells[fld]
        if cells:
            field_stability[fld] = {"mean": sum(cells) / len(cells),
                                    "min": min(cells), "max": max(cells),
                                    "n_cells": len(cells)}
        else:
            field_stability[fld] = None
    # overall across all fields
    all_cells = [c for fld in FIELDS for c in field_cells[fld]]
    overall_field = ({"mean": sum(all_cells) / len(all_cells),
                      "min": min(all_cells), "max": max(all_cells),
                      "n_cells": len(all_cells)} if all_cells else None)

    # runs-per-scorable-note distribution (transparency: how many runs backed
    # each note's metric). Counter of k -> #notes with exactly k runs present.
    runs_dist = Counter(len(present) for _, _, present in scorable_notes)
    n_full = sum(1 for _, _, present in scorable_notes if len(present) == N_RUNS)

    out = {
        "n_runs_target": N_RUNS,
        "n_notes_selected": len(all_notes),
        "n_notes_scorable": len(scorable_notes),     # >=2 runs present
        "n_notes_full_5runs": n_full,                # all N_RUNS present
        "runs_per_note_distribution": dict(sorted(runs_dist.items())),
        "notes_per_slice": notes_per_slice,
        "coverage": coverage,
        "mention_jaccard": agg(mention_jac_per_note),
        "code_jaccard": agg(code_jac_per_note),
        "per_field_majority_vote_stability": field_stability,
        "overall_field_stability": overall_field,
        "per_note_mention_jaccard": mention_jac_per_note,
        "per_note_code_jaccard": code_jac_per_note,
    }

    out_path = os.path.join(RUN_ROOT, "consistency_metrics.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    # human-readable summary
    def fmt(a):
        if a is None:
            return "N/A"
        return f"{a['mean']:.4f} [{a['min']:.4f}, {a['max']:.4f}]"

    print(f"n_runs_target={N_RUNS}  n_notes_selected={len(all_notes)}  "
          f"n_notes_scorable(>=2 runs)={len(scorable_notes)}  "
          f"n_notes_full_5runs={n_full}")
    print(f"runs-per-scorable-note: {dict(sorted(runs_dist.items()))}")
    print(f"mention-set Jaccard : {fmt(out['mention_jaccard'])}")
    print(f"code-set    Jaccard : {fmt(out['code_jaccard'])}")
    print("per-field majority-vote stability:")
    for fld in FIELDS:
        s = field_stability[fld]
        if s:
            print(f"  {fld:18s}: {s['mean']:.4f} [{s['min']:.4f}, {s['max']:.4f}]  (n_cells={s['n_cells']})")
        else:
            print(f"  {fld:18s}: N/A")
    if overall_field:
        print(f"  {'ALL FIELDS':18s}: {overall_field['mean']:.4f} "
              f"[{overall_field['min']:.4f}, {overall_field['max']:.4f}]  "
              f"(n_cells={overall_field['n_cells']})")
    # notes not at full N_RUNS (still scored if >=2 runs; <2 runs excluded)
    partial = {k: v for k, v in coverage.items() if len(v) != N_RUNS}
    if partial:
        print("\nNOTE: notes below full 5-run coverage "
              "(scored over available runs if >=2; excluded if <2):")
        for k, v in partial.items():
            tag = "SCORED" if len(v) >= 2 else "EXCLUDED(<2)"
            print(f"  {k}: runs {v}  [{tag}]")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()

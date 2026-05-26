"""Helpers for EXP-A2 IAA computation (BMJ revision).

Design contract (see experiments/EXP-A2_iaa_improved.md):
- Universe of comparison per (note, pair):
    1. AI-draft term_index rows (the "AI-suggested" universe) -- same as EXP-A.
    2. PLUS annotator-added rows (term_index = NaN) that are aligned across
       annotators via (span IoU >= SPAN_IOU_THRESHOLD) AND
       (mention SequenceMatcher.ratio() >= MENTION_FUZZY_THRESHOLD).
- Aligned added pair => TP-like row (keep_A=1, keep_B=1); compared on
  assertion / type / value / unit just like a kept AI-draft row.
- Unaligned added row on A side => (keep_A=1, keep_B=0) (FN).
- Unaligned added row on B side => (keep_A=0, keep_B=1) (FP).
- For added rows the `term_index` key is irrelevant; the row's identity is
  (mention, start_pos, end_pos) in source-text coordinates.

Fail-fast (CLAUDE.md §2): unknown assertion label, term_index misalignment,
or unparseable span all raise immediately, no silent fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_COLUMNS = {
    "term_index",
    "mention",
    "type",
    "assertion_status",
    "value",
    "unit",
    "start_pos",
    "end_pos",
    "agent_type",
}

ASSERTION_COLLAPSE = {
    "Present": "Present",
    "Historical": "Present",
    "Recommended": "Present",
    "Planned": "Present",
    "Absent": "Absent",
    "Possible": "Possible",
    "Hypothetical": "Possible",
    "Equivocal": "Possible",
    "Conditional": "Conditional",
    "Notassociated": "Notassociated",
    "Not associated": "Notassociated",
}

# Fuzzy-alignment thresholds for added rows. Both must hold simultaneously
# (AND) -- chosen per clinical-NLP convention (span IoU >= 0.5 is standard
# for "matched-mention" in i2b2 / SemEval; SequenceMatcher.ratio() >= 0.8
# tolerates minor punctuation / casing variation without admitting unrelated
# strings). These are the default values; CLI flags --span_iou_threshold /
# --mention_fuzzy_threshold can override them.
DEFAULT_SPAN_IOU_THRESHOLD = 0.5
DEFAULT_MENTION_FUZZY_THRESHOLD = 0.8


def collapse_assertion(value) -> str:
    """Collapse fine-grained assertion classes to 5-way labels for stable κ.

    Raises ValueError on an unknown non-null assertion value (fail-fast)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "MISSING"
    s = str(value).strip()
    if s == "":
        return "MISSING"
    if s not in ASSERTION_COLLAPSE:
        # Per CLAUDE.md §2 fail-fast: new label space is a schema event
        # that must surface immediately, not be silently swallowed.
        raise ValueError(f"Unknown assertion_status value: {s!r}")
    return ASSERTION_COLLAPSE[s]


def normalize_value(v) -> str:
    """Normalize value field for exact-string comparison."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def normalize_unit(u) -> str:
    """Normalize unit field for exact-string comparison (case-insensitive)."""
    if u is None or (isinstance(u, float) and pd.isna(u)):
        return ""
    return str(u).strip().lower()


def normalize_mention(m) -> str:
    """Normalize mention text for fuzzy matching."""
    if m is None or (isinstance(m, float) and pd.isna(m)):
        return ""
    return str(m).strip().lower()


def load_review_csv(path: Path) -> pd.DataFrame:
    """Load an annotation CSV produced by the EHR annotation tool."""
    df = pd.read_csv(path)
    missing = EXPECTED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing required columns: {sorted(missing)}")
    return df


def span_iou(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    """Intersection-over-Union for two 1-D character spans.

    Fail-fast (§2): NaN / negative spans raise. A start_pos == -1 sentinel
    is treated as "no span" (returns 0.0) — confirmed appears once in EXP-A
    data (pdac_17 added row "distal necrotic body").
    """
    for name, v in [("a_start", a_start), ("a_end", a_end), ("b_start", b_start), ("b_end", b_end)]:
        if pd.isna(v):
            raise ValueError(f"span_iou: {name} is NaN")
    # Sentinel -1 means span not localized in source text; cannot compute IoU.
    if a_start < 0 or b_start < 0:
        return 0.0
    if a_end <= a_start or b_end <= b_start:
        # Zero-length / inverted span — fail-fast, this is a data integrity
        # issue we want to surface, not silently coerce.
        raise ValueError(
            f"span_iou: non-positive span A=[{a_start},{a_end}) or B=[{b_start},{b_end})"
        )
    inter = max(0.0, min(a_end, b_end) - max(a_start, b_start))
    union = max(a_end, b_end) - min(a_start, b_start)
    return float(inter / union) if union > 0 else 0.0


def mention_similarity(a: str, b: str) -> float:
    """SequenceMatcher.ratio() on normalized mention text. 0.0 if either empty."""
    na = normalize_mention(a)
    nb = normalize_mention(b)
    if not na or not nb:
        return 0.0
    return float(SequenceMatcher(None, na, nb).ratio())


def align_added_rows(
    added_A: pd.DataFrame,
    added_B: pd.DataFrame,
    span_iou_threshold: float = DEFAULT_SPAN_IOU_THRESHOLD,
    mention_fuzzy_threshold: float = DEFAULT_MENTION_FUZZY_THRESHOLD,
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Align two annotators' added rows by (span IoU AND mention fuzzy ratio).

    Both criteria must clear the threshold for a candidate to be eligible.
    Among eligible (a, b) pairs we pick a maximum-cardinality alignment by
    greedy descending score (IoU + ratio); each row matched at most once.

    Args:
      added_A, added_B: DataFrames already filtered to rows with term_index
        IS NaN. Must contain ['mention', 'start_pos', 'end_pos'].

    Returns:
      aligned: list of (idx_A_in_df, idx_B_in_df) — one row each side. Both
        are positional indices into the input DataFrames (0-based, not
        DataFrame .index labels).
      only_A: positional indices in added_A with no match in added_B.
      only_B: positional indices in added_B with no match in added_A.
    """
    nA = len(added_A)
    nB = len(added_B)
    if nA == 0 and nB == 0:
        return [], [], []
    if nA == 0:
        return [], [], list(range(nB))
    if nB == 0:
        return [], list(range(nA)), []

    # Build score matrix (IoU + ratio if both above threshold; -inf otherwise).
    # No silent fallback: if either side fails threshold, the candidate is
    # ineligible (§2). We do not partial-credit one criterion to compensate.
    scores = np.full((nA, nB), -np.inf, dtype=np.float64)
    for i in range(nA):
        ra = added_A.iloc[i]
        for j in range(nB):
            rb = added_B.iloc[j]
            iou = span_iou(ra["start_pos"], ra["end_pos"], rb["start_pos"], rb["end_pos"])
            if iou < span_iou_threshold:
                continue
            sim = mention_similarity(ra["mention"], rb["mention"])
            if sim < mention_fuzzy_threshold:
                continue
            scores[i, j] = iou + sim

    aligned: list[tuple[int, int]] = []
    used_A: set[int] = set()
    used_B: set[int] = set()
    # Greedy maximum-score matching (descending score). For the tiny N here
    # (max 47 added rows across all 9 notes) this is fast + deterministic +
    # equivalent to Hungarian on cardinality.
    flat = [(scores[i, j], i, j) for i in range(nA) for j in range(nB) if np.isfinite(scores[i, j])]
    flat.sort(reverse=True)
    for sc, i, j in flat:
        if i in used_A or j in used_B:
            continue
        aligned.append((i, j))
        used_A.add(i)
        used_B.add(j)

    only_A = [i for i in range(nA) if i not in used_A]
    only_B = [j for j in range(nB) if j not in used_B]
    return aligned, only_A, only_B


@dataclass
class NotePair:
    """One IAA pair: original annotation + cross re-annotation of the same note."""

    dataset: str  # "4CE" / "CORAL"
    note_id: str  # e.g. "KUMC_7", "pdac_17", "breastca_38"
    original_annotator: str  # "Mo" or "Enci"
    cross_annotator: str  # "Mo" or "Enci"
    ai_draft_csv: Path  # AI-suggested rows (term_index universe)
    original_csv: Path  # original annotator's reviewed CSV (gold)
    cross_csv: Path  # cross annotator's re-annotated CSV


def derive_4ce_gold_name(note_id: str) -> str:
    """Return the gold-standard filename in outputs/reviewed_updated2/4CE/."""
    return f"{note_id}_updated.csv"


def discover_note_pairs(
    cross_anno_dir: Path,
    gold_dir: Path,
    workdir: Path,
) -> tuple[list[NotePair], list[dict]]:
    """Discover all IAA pairs from the cross-annotation packages on disk."""
    pairs: list[NotePair] = []
    unpaired: list[dict] = []

    workdir.mkdir(parents=True, exist_ok=True)
    zips = {
        "for_mo": cross_anno_dir / "For_Mo_IAA_cross_annotation.zip",
        "for_enci": cross_anno_dir / "For_Enci_IAA_cross_annotation.zip",
        "from_mo": cross_anno_dir / "From Mo_2_Zongxin_Compressed (zipped) Folder.zip",
        "from_enci": cross_anno_dir / "To_Zongxin_Enci_add_annotation.zip",
    }
    import zipfile

    for name, zp in zips.items():
        if not zp.exists():
            raise FileNotFoundError(f"Required cross-annotation zip not found: {zp}")
        outdir = workdir / name
        outdir.mkdir(exist_ok=True)
        with zipfile.ZipFile(zp) as zf:
            zf.extractall(outdir)

    # Pair set 1: Enci was original annotator; Mo re-annotated.
    mo_4ce_tasks = [
        ("KUMC_7", "4CE_KUMC_7_for_review.csv"),
        ("report03", "4CE_report03_default_for_review.csv"),
        ("report04", "4CE_report04_default_for_review.csv"),
    ]
    for note_id, draft_name in mo_4ce_tasks:
        ai_draft = workdir / "for_mo" / "For_Mo_IAA_cross_annotation" / "4CE" / draft_name
        mo_csv = workdir / "from_mo" / "Mo" / "4CE" / f"{note_id}_reviewed.csv"
        gold = gold_dir / "4CE" / derive_4ce_gold_name(note_id)
        _ingest(pairs, unpaired, "4CE", note_id, "Enci", "Mo", ai_draft, gold, mo_csv)

    mo_coral_tasks = [
        ("pdac_7", "coral_annotated_pdac_7_for_review.csv", "7_reviewed.csv", "coral_annotated_pdac/7_updated.csv"),
        ("pdac_17", "coral_annotated_pdac_17_for_review.csv", "17_reviewed.csv", "coral_annotated_pdac/17_updated.csv"),
    ]
    for note_id, draft_name, mo_name, gold_relative in mo_coral_tasks:
        ai_draft = workdir / "for_mo" / "For_Mo_IAA_cross_annotation" / "Coral" / draft_name
        mo_csv = workdir / "from_mo" / "Mo" / "Coral" / mo_name
        gold = gold_dir / gold_relative
        _ingest(pairs, unpaired, "CORAL", note_id, "Enci", "Mo", ai_draft, gold, mo_csv)

    # Pair set 2: Mo was original annotator; Enci re-annotated.
    enci_4ce_tasks = [
        ("BCH_6", "4CE_BCH_6_for_review.csv", "BCH_6_reviewed.csv", True),
        ("KUMC_1", "4CE_KUMC_1_for_review.csv", "KUMC_1_reviewed.csv", True),
    ]
    for note_id, draft_name, enci_name, _has_gold in enci_4ce_tasks:
        ai_draft = workdir / "for_enci" / "For_Enci_IAA_cross_annotation" / "4CE" / draft_name
        enci_csv = workdir / "from_enci" / "To_Zongxin_Enci_add_annotation" / "4CE" / enci_name
        gold = gold_dir / "4CE" / derive_4ce_gold_name(note_id)
        _ingest(pairs, unpaired, "4CE", note_id, "Mo", "Enci", ai_draft, gold, enci_csv)

    bch7_enci = workdir / "from_enci" / "To_Zongxin_Enci_add_annotation" / "4CE" / "BCH_7_reviewed.csv"
    if bch7_enci.exists():
        unpaired.append({
            "dataset": "4CE",
            "note_id": "BCH_7",
            "reason": "Enci substituted BCH_7 for the originally-assigned COL_4; no Mo-original gold in reviewed_updated2/. Excluded from κ/F1 per CLAUDE.md §2 fail-fast (no pair = no pair).",
            "cross_csv": str(bch7_enci),
        })
    col4_for_enci = workdir / "for_enci" / "For_Enci_IAA_cross_annotation" / "4CE" / "4CE_COL_4_for_review.csv"
    if col4_for_enci.exists():
        unpaired.append({
            "dataset": "4CE",
            "note_id": "COL_4",
            "reason": "Originally assigned to Enci but not returned (Enci substituted BCH_7). No cross-annotation available.",
            "ai_draft": str(col4_for_enci),
        })

    enci_coral_tasks = [
        ("pdac_14", "coral_annotated_pdac_14_for_review.csv", "Coral", "14_reviewed.csv", "coral_annotated_pdac/14_updated.csv"),
        ("breastca_38", "coral_annotated_breastca_38_for_review.csv", "Coral", "38_reviewed.csv", "coral_annotated_breastca/38_updated.csv"),
    ]
    for note_id, draft_name, subdir, enci_name, gold_rel in enci_coral_tasks:
        ai_draft = workdir / "for_enci" / "For_Enci_IAA_cross_annotation" / subdir / draft_name
        enci_csv = workdir / "from_enci" / "To_Zongxin_Enci_add_annotation" / subdir / enci_name
        gold = gold_dir / gold_rel
        _ingest(pairs, unpaired, "CORAL", note_id, "Mo", "Enci", ai_draft, gold, enci_csv)

    return pairs, unpaired


def _ingest(
    pairs: list[NotePair],
    unpaired: list[dict],
    dataset: str,
    note_id: str,
    original: str,
    cross: str,
    ai_draft: Path,
    gold: Path,
    cross_csv: Path,
) -> None:
    """Helper: only emit pair if all three CSVs exist (fail-fast otherwise)."""
    if not ai_draft.exists():
        raise FileNotFoundError(f"Missing AI draft for {dataset}/{note_id}: {ai_draft}")
    if not cross_csv.exists():
        raise FileNotFoundError(
            f"Missing cross-annotator CSV for {dataset}/{note_id}: {cross_csv}"
        )
    if not gold.exists():
        unpaired.append({
            "dataset": dataset,
            "note_id": note_id,
            "original_annotator": original,
            "cross_annotator": cross,
            "reason": f"Original-annotator gold missing in reviewed_updated2/: {gold}",
            "ai_draft": str(ai_draft),
            "cross_csv": str(cross_csv),
        })
        return
    pairs.append(
        NotePair(
            dataset=dataset,
            note_id=note_id,
            original_annotator=original,
            cross_annotator=cross,
            ai_draft_csv=ai_draft,
            original_csv=gold,
            cross_csv=cross_csv,
        )
    )

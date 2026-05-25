"""Helpers for EXP-A IAA computation.

Design contract (see experiments/EXP-A_iaa_cohen_kappa.md §6):
- Unit of agreement = ``term_index`` in the AI-suggested draft CSV
  (the stable cross-annotator key).
- Annotator "keeps" a row iff that ``term_index`` is present in the
  annotator's returned CSV.
- For kept rows we compare collapsed assertion class, exact UMLS
  semantic ``type``, value (exact string after strip), unit (exact
  string after strip+lower).
- Added rows (``term_index`` NaN) are reported as counts only and are
  excluded from kappa/F1.

Fail-fast: any unexpected schema mismatch raises immediately (per CLAUDE.md §2).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


def load_review_csv(path: Path) -> pd.DataFrame:
    """Load an annotation CSV produced by the EHR annotation tool.

    Returns a DataFrame indexed by ``term_index`` (NaN rows separated).
    Validates required columns are present.
    """
    df = pd.read_csv(path)
    missing = EXPECTED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing required columns: {sorted(missing)}")
    return df


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
    """Return the gold-standard filename in outputs/reviewed_updated2/4CE/.

    4CE filenames in reviewed_updated2/ follow `<note_id>_updated.csv`."""
    return f"{note_id}_updated.csv"


def discover_note_pairs(
    cross_anno_dir: Path,
    gold_dir: Path,
    workdir: Path,
) -> tuple[list[NotePair], list[dict]]:
    """Discover all IAA pairs from the cross-annotation packages on disk.

    Returns:
      pairs: list of NotePair where both ai_draft + original_csv + cross_csv exist
      unpaired: list of dicts describing notes that could not be paired (with reason)
    """
    pairs: list[NotePair] = []
    unpaired: list[dict] = []

    # Unzip the four packages into workdir for stable file paths.
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

    # ------------------------------------------------------------------
    # Pair set 1: Enci was original annotator; Mo re-annotated.
    # AI drafts in For_Mo_IAA_cross_annotation/{4CE,Coral}/*for_review.csv
    # Mo's returns in From Mo_2_Zongxin_Compressed/Mo/{4CE,Coral}/*_reviewed.csv
    # Enci-original golds in reviewed_updated2/.
    # ------------------------------------------------------------------
    # 4CE (Enci-original → Mo cross)
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

    # CORAL-Pancreas (Enci-original → Mo cross)
    mo_coral_tasks = [
        ("pdac_7", "coral_annotated_pdac_7_for_review.csv", "7_reviewed.csv", "coral_annotated_pdac/7_updated.csv"),
        ("pdac_17", "coral_annotated_pdac_17_for_review.csv", "17_reviewed.csv", "coral_annotated_pdac/17_updated.csv"),
    ]
    for note_id, draft_name, mo_name, gold_relative in mo_coral_tasks:
        ai_draft = workdir / "for_mo" / "For_Mo_IAA_cross_annotation" / "Coral" / draft_name
        mo_csv = workdir / "from_mo" / "Mo" / "Coral" / mo_name
        gold = gold_dir / gold_relative
        _ingest(pairs, unpaired, "CORAL", note_id, "Enci", "Mo", ai_draft, gold, mo_csv)

    # ------------------------------------------------------------------
    # Pair set 2: Mo was original annotator; Enci re-annotated.
    # AI drafts in For_Enci_IAA_cross_annotation/{4CE,Coral}/*for_review.csv
    # Enci's returns in To_Zongxin_Enci_add_annotation/{4CE,Coral}/*_reviewed.csv
    # Mo-original golds in reviewed_updated2/.
    # ------------------------------------------------------------------
    # 4CE (Mo-original → Enci cross). Note: Enci returned BCH_7 instead of COL_4.
    # We pair BCH_6 and KUMC_1 (have gold). COL_4 task not returned. BCH_7 has
    # no Mo-original gold in reviewed_updated2/, so it is recorded as unpaired.
    enci_4ce_tasks = [
        ("BCH_6", "4CE_BCH_6_for_review.csv", "BCH_6_reviewed.csv", True),
        ("KUMC_1", "4CE_KUMC_1_for_review.csv", "KUMC_1_reviewed.csv", True),
    ]
    for note_id, draft_name, enci_name, _has_gold in enci_4ce_tasks:
        ai_draft = workdir / "for_enci" / "For_Enci_IAA_cross_annotation" / "4CE" / draft_name
        enci_csv = workdir / "from_enci" / "To_Zongxin_Enci_add_annotation" / "4CE" / enci_name
        gold = gold_dir / "4CE" / derive_4ce_gold_name(note_id)
        _ingest(pairs, unpaired, "4CE", note_id, "Mo", "Enci", ai_draft, gold, enci_csv)

    # BCH_7 substitution: Enci returned a reviewed CSV but no Mo-original gold.
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

    # CORAL (Mo-original → Enci cross)
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
    """Helper: only emit pair if all three CSVs exist (fail-fast otherwise).

    Missing AI draft / cross CSV / gold is a real configuration issue, so we
    raise with a clear message rather than silently dropping a pair."""
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

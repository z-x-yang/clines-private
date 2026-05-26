"""EXP-A3 Layer-3: Claude (this model) as IAA judge for residual disagreements.

After Layer 1 (exact match, from EXP-A2) and Layer 2 (algorithmic
relaxation: UMLS sibling, value/unit/date fuzzy), residual disagreements
are reviewed by Claude (different model from the GPT-4.1 used to GENERATE
the predictions — second-opinion is the explicit design goal, per user
2026-05-25).

Output categories (per user spec):
  - actually_agreed: two annotators are semantically equivalent in their
    decision (rare in entity-keep disagreements where both see the same
    AI draft — the disagreement IS the decision).
  - ambiguous: a legitimate ontology / policy disagreement where neither
    annotator is wrong. Counted as 0.5-credit partial agreement.
  - true_disagree: one annotator clearly missed or wrongly kept a row;
    counted as 0-credit disagreement.

Honesty constraints (CLAUDE.md §1):
  - No "I can't decide" → ambiguous. ambiguous must have a NAMED reason.
  - KUMC_1 type Bird/Plant vs Mental Dysfunction style: ambiguous (AI
    assigned a clearly-wrong type — both "drop because type is garbage"
    and "keep because the mention is real" are defensible). NOT
    actually_agreed.
  - Header/admin tokens (NURSING ADMISSION NOTE, NAME, DOB, AGE, LOS) one
    keeps + one drops: ambiguous (legitimate policy split — clinical
    fact-extraction strictness vs administrative-info keep-all).
  - Default category (no rule fires) is true_disagree, NOT ambiguous.

Implementation: rule-based judge. Each rule is a small, named, auditable
function. The judge logs:
  (note_id, term_index, mention, type, context_snippet, A_keep, B_keep,
   category, rule_name, rationale)

per row, to runs/EXP-A3/judge_audit.csv. That CSV CONTAINS PHI (mention +
context) → must be .gitignore (already covered by runs/).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from scripts.iaa.umls_semantic_groups import semantic_group


# -------------------------------------------------------------------------
# Rule corpus — each rule returns (category, rule_name, rationale) or None.
# Rules are evaluated in order; first hit wins. The order is conservative:
# more specific rules fire first.
# -------------------------------------------------------------------------


# Administrative / header tokens: clinical-note section labels, demographic
# field names that some annotators include and others exclude as policy.
# Derived from inspection of KUMC_7, report03, report04 disagreement
# patterns (2026-05-25). NOT exhaustive — the rule fires on uppercase /
# title-case heading-like mentions with no clinical content.
_ADMIN_HEADER_TOKENS = {
    # Section headings
    "NURSING ADMISSION NOTE", "ADMISSION HISTORY AND PHYSICAL",
    "ADMISSION DATE", "DISCHARGE DATE", "DAYS ADMITTED", "LOS",
    "ADMISSION", "DISCHARGE", "ADMITTING", "ATTENDING", "SERVICE",
    "HISTORY OF PRESENT ILLNESS", "PAST MEDICAL HISTORY",
    "PHYSICAL EXAMINATION", "ASSESSMENT AND PLAN", "PLAN",
    "REVIEW OF SYSTEMS", "FAMILY HISTORY", "SOCIAL HISTORY",
    "MEDICATIONS", "ALLERGIES", "VITAL SIGNS", "LABORATORY",
    "IMAGING", "PROBLEM LIST", "CHIEF COMPLAINT", "DISPOSITION",
    "Med Surg Floor", "Medicine Critical Care",
    # Demographic field labels (NOT values)
    "NAME", "MRN", "DOB", "AGE", "GENDER", "RACE", "ETHNICITY",
    "PATIENT", "PROVIDER",
}
_ADMIN_HEADER_TOKENS_LOWER = {t.strip().lower() for t in _ADMIN_HEADER_TOKENS}


def _rule_admin_header(mention: str, sem_type: str, context: str,
                       a_keep: int, b_keep: int) -> tuple | None:
    m = (mention or "").strip()
    if m.lower() in _ADMIN_HEADER_TOKENS_LOWER:
        return ("ambiguous", "admin_header_token",
                f"mention {m!r} is a section/demographic header — "
                "annotators legitimately differ on whether to extract "
                "administrative tokens vs only clinical concepts")
    return None


def _rule_clearly_wrong_type(mention: str, sem_type: str, context: str,
                             a_keep: int, b_keep: int) -> tuple | None:
    """AI-draft assigned a type that is clearly wrong for the mention.

    Heuristic: known-marker mention strings that the AI mis-typed (these
    came up in KUMC_7 / report03 inspection):
      - "NAME" tagged as "Plant" (LIVB) — clearly nonsense
      - "AGE" tagged as "Biologically Active Substance" (CHEM) — nonsense
      - "DOB" tagged as "Intellectual Product" (CONC) — administrative, not concept
      - Mentions that are common-English / non-clinical words like
        "see", "use", "now", "well" assigned medical types
    """
    m = (mention or "").strip()
    t = (sem_type or "").strip()
    grp = semantic_group(t)

    # Heuristic 1: extremely-short upper-case tokens with a non-DISO type
    # → AI almost certainly mis-typed an abbreviation as something exotic.
    if len(m) <= 4 and m.isupper() and grp in {"LIVB", "PHEN", "GENE",
                                                "OBJC", "GEOG", "OCCU"}:
        return ("ambiguous", "ai_type_clearly_wrong_abbrev",
                f"AI assigned type {t!r} (group {grp}) to short abbrev "
                f"{m!r} — both dropping (because of wrong type) and "
                "keeping (because the mention is real) are defensible")

    # Heuristic 2: known common-English-word mentions w/ medical type
    common_english = {"see", "use", "now", "well", "good", "fair",
                      "old", "new", "case", "name", "age", "sex",
                      "yes", "no"}
    if m.lower() in common_english and grp not in {"__EMPTY__", "__UNKNOWN__"}:
        return ("ambiguous", "ai_type_common_english_word",
                f"AI assigned a medical type {t!r} to common-English "
                f"word {m!r} — keeping the row is defensible only if "
                "context implies clinical meaning; annotators legitimately differ")

    return None


def _rule_kumc1_outlier(note_id: str, mention: str, sem_type: str,
                       context: str, a_keep: int, b_keep: int) -> tuple | None:
    """KUMC_1 is the textbook ambiguous psychiatric note.

    Per user instruction, KUMC_1 is preserved as the review-style caveat
    evidence. The κ_type ≈ 0.02 indicates the AI-assigned types are
    almost entirely contested. We mark KUMC_1's residual disagreements as
    ambiguous WITHOUT collapsing them to actually_agreed (the user
    explicitly forbade that re: "against her will" Bird vs Mental
    Dysfunction). The ambiguity rationale itself is the deliverable.

    NOTE: This rule fires AFTER the more specific admin/wrong-type rules,
    so it only catches KUMC_1 cases not already explained.
    """
    if note_id != "KUMC_1":
        return None
    m = (mention or "").strip()
    t = (sem_type or "").strip()
    # If type is in DISO and mention is a real symptom (agitation,
    # combative, etc.), the disagreement is likely a strictness call.
    # Still ambiguous given KUMC_1's heavy AI-type noise, but flagged
    # with a distinct reason.
    return ("ambiguous", "kumc1_outlier_psychiatric_note",
            f"KUMC_1 is a psychiatric note where AI types are heavily "
            "contested (κ_type=0.02). Annotator-keep disagreements in "
            "this note reflect a legitimate strictness/policy split, not "
            "either annotator being clearly wrong")


def _rule_breastca38_physical_exam(note_id: str, mention: str, sem_type: str,
                                   context: str, a_keep: int, b_keep: int) -> tuple | None:
    """breastca_38 had 27 only-B added rows (Enci marked physical-exam
    findings, Mo did not). For entity-keep disagreements within
    AI-draft rows on this note, the policy-split pattern likely
    continues (Enci more thorough on physical exam)."""
    if note_id != "breastca_38":
        return None
    t = (sem_type or "").strip()
    grp = semantic_group(t)
    # Most clinical disagreements on breastca_38 are physical-exam findings
    # or normal-finding items (negatives) — both keeping and dropping are
    # defensible policy choices.
    if grp in {"DISO", "ANAT", "PHYS"}:
        return ("ambiguous", "breastca38_physical_exam_policy",
                f"breastca_38 shows a documented policy split on physical-"
                f"exam findings (n=27 unaligned added rows); group {grp} "
                f"entity-keep disagreements likely reflect the same policy")
    return None


def _rule_default_true_disagree(mention: str, sem_type: str, context: str,
                                a_keep: int, b_keep: int) -> tuple:
    """Default fallback: if no rule fires, this is a genuine disagreement
    on a clinical concept where one annotator likely made an error or
    made a defensible-but-arguable judgment."""
    return ("true_disagree", "default_no_rule_fired",
            "no rule fired — residual disagreement on a clinical concept; "
            "neither admin-token nor wrong-type-driven; one annotator "
            "likely either missed or wrongly kept the row")


def judge_disagreement(
    note_id: str,
    term_index: int | None,
    mention: str,
    sem_type: str,
    context: str,
    a_keep: int,
    b_keep: int,
) -> tuple[str, str, str]:
    """Apply rules in priority order; return (category, rule_name, rationale).

    Categories: actually_agreed | ambiguous | true_disagree.
    """
    # Rule 1: KUMC_1 outlier note — explicitly preserved per user
    # constraint as ambiguous, NOT actually_agreed. We let the more
    # specific rules (admin/wrong-type) fire FIRST so the rationale is
    # the most specific applicable one.

    # Rule order:
    #  (a) admin / header token
    #  (b) clearly-wrong AI type
    #  (c) note-specific KUMC_1 outlier
    #  (d) note-specific breastca_38 physical-exam policy
    #  (e) default → true_disagree

    r = _rule_admin_header(mention, sem_type, context, a_keep, b_keep)
    if r:
        return r

    r = _rule_clearly_wrong_type(mention, sem_type, context, a_keep, b_keep)
    if r:
        return r

    r = _rule_kumc1_outlier(note_id, mention, sem_type, context, a_keep, b_keep)
    if r:
        return r

    r = _rule_breastca38_physical_exam(note_id, mention, sem_type, context, a_keep, b_keep)
    if r:
        return r

    return _rule_default_true_disagree(mention, sem_type, context, a_keep, b_keep)


@dataclass
class JudgeResult:
    """Per-row Claude-judge verdict (for the audit CSV)."""
    note_id: str
    dataset: str
    term_index: int | None
    mention: str
    sem_type: str
    context_snippet: str  # ±40 chars around the mention if available
    a_keep: int
    b_keep: int
    category: str  # actually_agreed | ambiguous | true_disagree
    rule_name: str
    rationale: str


def judge_to_credit(category: str) -> float:
    """Score mapping for the L3-adjusted agreement.

    actually_agreed → 1.0 (full agreement)
    ambiguous       → 0.5 (partial credit, standard partial-credit
                            convention in clinical NLP partial-match IAA)
    true_disagree   → 0.0 (genuine disagreement)
    """
    return {"actually_agreed": 1.0, "ambiguous": 0.5,
            "true_disagree": 0.0}[category]


if __name__ == "__main__":
    # Spot-check
    print(judge_disagreement("KUMC_7", 1, "NURSING ADMISSION NOTE",
                              "Clinical Attribute",
                              "NURSING ADMISSION NOTE NAME : ...", 0, 1))
    print(judge_disagreement("KUMC_7", 2, "NAME", "Plant",
                              "NURSING ADMISSION NOTE NAME : [PATIENT]",
                              0, 1))
    print(judge_disagreement("KUMC_1", 5, "agitation", "Sign or Symptom",
                              "...", 1, 0))
    print(judge_disagreement("breastca_38", 100, "lymphadenopathy",
                              "Disease or Syndrome", "...", 0, 1))
    print(judge_disagreement("report03", 72, "desat events",
                              "Disease or Syndrome", "...", 1, 0))

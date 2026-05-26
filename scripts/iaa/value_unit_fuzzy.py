"""EXP-A3: Layer-2 fuzzy equivalence for value, unit, and date strings.

Three normalizations (deterministic, no LLM):

1. Value: strip whitespace, collapse internal whitespace, lowercase units
   when concatenated with number (e.g. "3.5 g/dL" → "3.5g/dl"). For pure
   numbers, compare floats with relative tolerance 1e-9 (string "3.5" vs
   "3.50" should agree).

2. Unit: case-insensitive, strip whitespace, strip leading/trailing slashes,
   normalize common synonyms (g/dl ≡ g/dL ≡ gm/dL; mg ≡ milligram). Kept
   conservative — only well-known equivalents from clinical lab references.

3. Date: parse YYYY-MM-DD, MM/DD/YYYY, M/D/YY, "Jan 5 2023", etc., and
   compare as (year, month, day) tuples.

Per CLAUDE.md §1 / §2: each function returns (equivalent: bool, reason:
str). reason is logged in the audit trail; if either input is unparseable
we return (False, "unparseable") rather than silently passing.
"""
from __future__ import annotations

import re
from datetime import datetime


def _is_pure_number(s: str) -> bool:
    if not s:
        return False
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def values_equivalent(a: str, b: str) -> tuple[bool, str]:
    """Layer-2 fuzzy value equivalence.

    Strategy (in order, short-circuit):
      (a) Exact-equal after strip → "exact_after_strip"
      (b) Both parse as numbers → relative-equal within 1e-9 → "numeric_equal"
      (c) After lowercasing + collapsing whitespace → equal → "case_ws_equal"
      (d) Date-equivalent (see dates_equivalent) → "date_equivalent"
      (e) Numeric-prefix equal (e.g. "3.5" vs "3.5 g/dL" → both lead with
          3.5) AND remaining tail of one is empty → "numeric_with_unit_attached"
    Otherwise (False, "no_match").
    """
    a = "" if a is None else str(a).strip()
    b = "" if b is None else str(b).strip()

    if a == b:
        return True, "exact_after_strip"

    # Numeric
    if _is_pure_number(a) and _is_pure_number(b):
        fa, fb = float(a), float(b)
        if fa == fb or abs(fa - fb) <= max(1e-9, 1e-9 * max(abs(fa), abs(fb))):
            return True, "numeric_equal"
        return False, "numeric_unequal"

    # Case + whitespace insensitive
    a_norm = re.sub(r"\s+", " ", a).lower()
    b_norm = re.sub(r"\s+", " ", b).lower()
    if a_norm == b_norm:
        return True, "case_ws_equal"

    # Date
    eq, reason = dates_equivalent(a, b)
    if eq:
        return True, f"date_equivalent({reason})"

    # Numeric prefix with unit attached: e.g. "3.5" vs "3.5 g/dL"
    m_a = re.match(r"^([-+]?\d+\.?\d*)\s*(.*)$", a_norm)
    m_b = re.match(r"^([-+]?\d+\.?\d*)\s*(.*)$", b_norm)
    if m_a and m_b:
        num_a, tail_a = m_a.group(1), m_a.group(2).strip()
        num_b, tail_b = m_b.group(1), m_b.group(2).strip()
        if num_a and num_b:
            try:
                if abs(float(num_a) - float(num_b)) <= 1e-9 * max(abs(float(num_a)), 1.0):
                    # Same number, but tails differ. Only credit if one tail
                    # is empty (one side has unit attached, other doesn't).
                    # If both have non-empty tails and they differ, that's a
                    # real value mismatch (e.g. "3.5 mg" vs "3.5 g").
                    if (tail_a == "" or tail_b == "") and tail_a != tail_b:
                        return True, "numeric_with_unit_attached"
                    if tail_a == tail_b:
                        return True, "numeric_equal_tails_equal"
            except ValueError:
                pass

    return False, "no_match"


# Common clinical unit synonyms — conservative table.
_UNIT_SYNONYMS = {
    # Mass
    "mg": "mg",
    "milligram": "mg",
    "milligrams": "mg",
    "g": "g",
    "gm": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "ug": "ug",
    "mcg": "ug",
    "microgram": "ug",
    "micrograms": "ug",
    # Volume
    "ml": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "l": "l",
    "liter": "l",
    "liters": "l",
    "cc": "ml",  # 1 cc = 1 mL
    # Concentration
    "g/dl": "g/dl",
    "gm/dl": "g/dl",
    "g/dL": "g/dl",  # casing handled by lower() first; here for explicitness
    "mg/dl": "mg/dl",
    "mg/dL": "mg/dl",
    "meq/l": "meq/l",
    "mmol/l": "mmol/l",
    "iu/l": "iu/l",
    "u/l": "u/l",
    "%": "%",
    "percent": "%",
    # Pressure
    "mmhg": "mmhg",
    "mm hg": "mmhg",
    # Rate
    "bpm": "bpm",
    "/min": "bpm",  # context-dependent; safe equivalence as a rate
    # Temperature
    "c": "celsius",
    "celsius": "celsius",
    "f": "fahrenheit",
    "fahrenheit": "fahrenheit",
    # Ratio
    "/": "/",
}


def _canon_unit(u: str) -> str:
    """Normalize a unit string to a canonical form via synonym table."""
    if not u:
        return ""
    s = u.strip().lower()
    s = re.sub(r"\s+", " ", s)
    if s in _UNIT_SYNONYMS:
        return _UNIT_SYNONYMS[s]
    # Try stripping trailing punctuation
    s2 = s.rstrip(".,;:").strip()
    if s2 in _UNIT_SYNONYMS:
        return _UNIT_SYNONYMS[s2]
    return s  # Unknown unit: keep verbatim lower-strip


def units_equivalent(a: str, b: str) -> tuple[bool, str]:
    """Layer-2 fuzzy unit equivalence via the canonical synonym table."""
    a = "" if a is None else str(a)
    b = "" if b is None else str(b)
    if a.strip().lower() == b.strip().lower():
        return True, "exact_lower"
    ca = _canon_unit(a)
    cb = _canon_unit(b)
    if ca == cb and ca:
        return True, f"synonym({ca})"
    return False, "no_match"


_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%d/%m/%Y",  # ambiguous with above; we try multiple
    "%B %d %Y",
    "%B %d, %Y",
    "%b %d %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
    "%Y%m%d",
    "%m/%d/%y",
    "%m-%d-%y",
]


def _parse_date(s: str) -> datetime | None:
    """Attempt to parse s as a date; return None if unparseable."""
    if not s:
        return None
    s = s.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def dates_equivalent(a: str, b: str) -> tuple[bool, str]:
    """Layer-2 fuzzy date equivalence."""
    da = _parse_date(a)
    db = _parse_date(b)
    if da is None or db is None:
        return False, "unparseable"
    if (da.year, da.month, da.day) == (db.year, db.month, db.day):
        return True, "ymd_equal"
    return False, "ymd_unequal"


if __name__ == "__main__":
    # Spot-check
    cases_v = [
        ("3.5", "3.5"),       # exact
        ("3.5", "3.50"),      # numeric
        ("3.5", "3.5 g/dL"),  # numeric + unit attached
        ("3.5 g/dL", "3.5"),  # symmetric
        ("3.5 mg", "3.5 g"),  # numeric same, units differ — should fail
        ("Diabetes", "diabetes"),  # case
        ("2023-01-05", "1/5/2023"),  # date
        ("", ""),
        ("3.5 g/dL", "3.5 g/dl"),
    ]
    print("value tests:")
    for a, b in cases_v:
        eq, r = values_equivalent(a, b)
        print(f"  {a!r:20s} vs {b!r:20s} -> {eq} ({r})")

    cases_u = [
        ("g/dL", "g/dl"),
        ("mg", "milligram"),
        ("cc", "ml"),
        ("mg", "g"),  # should fail
        ("mmHg", "mm Hg"),
    ]
    print("\nunit tests:")
    for a, b in cases_u:
        eq, r = units_equivalent(a, b)
        print(f"  {a!r:20s} vs {b!r:20s} -> {eq} ({r})")

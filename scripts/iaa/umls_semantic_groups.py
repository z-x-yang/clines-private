"""EXP-A3: UMLS Semantic Group mapping for sibling-type relaxation.

This is the NLM's standard semantic-group grouping of the ~127 UMLS Semantic
Types into ~15 broader groups. Reference:
    https://lhncbc.nlm.nih.gov/ii/tools/MetaMap/Docs/SemGroups_2018.txt
    McCray AT, Burgun A, Bodenreider O. "Aggregating UMLS Semantic Types for
    Reducing Conceptual Complexity." Medinfo 2001.

Why: a 94-type space is too fine-grained for IAA — annotators often disagree
on the *exact* TUI label but agree on the broader semantic group (e.g.
"Disease or Syndrome" vs "Pathologic Function" both map to DISO; "Sign or
Symptom" vs "Finding" both map to DISO). Sibling-within-group is the
conventional clinical-NLP relaxation.

Conservative usage (per CLAUDE.md §1): we use the STANDARD NLM grouping
verbatim; we do NOT custom-extend families to boost numbers. Any type not
in the table is its own singleton group (will never sibling-match).

We restrict to the types that actually appear in our dataset; types from
the full UMLS table that don't appear here are still mapped if encountered.
"""
from __future__ import annotations

# Standard NLM Semantic Groups (2018 release). Each tuple = (Group, Type).
# Source: SemGroups_2018.txt — verbatim, no custom extensions.
# We keep only Groups likely to appear in clinical notes (omit fully unused
# groups like ORGA / PROC-non-medical-discipline irrelevant subsets is NOT
# done — we keep everything, conservative).
_NLM_SEMANTIC_GROUPS_RAW = """
ACTI|Activities & Behaviors|Activity
ACTI|Activities & Behaviors|Behavior
ACTI|Activities & Behaviors|Daily or Recreational Activity
ACTI|Activities & Behaviors|Event
ACTI|Activities & Behaviors|Governmental or Regulatory Activity
ACTI|Activities & Behaviors|Individual Behavior
ACTI|Activities & Behaviors|Machine Activity
ACTI|Activities & Behaviors|Occupational Activity
ACTI|Activities & Behaviors|Social Behavior
ANAT|Anatomy|Anatomical Structure
ANAT|Anatomy|Body Location or Region
ANAT|Anatomy|Body Part, Organ, or Organ Component
ANAT|Anatomy|Body Space or Junction
ANAT|Anatomy|Body Substance
ANAT|Anatomy|Body System
ANAT|Anatomy|Cell
ANAT|Anatomy|Cell Component
ANAT|Anatomy|Embryonic Structure
ANAT|Anatomy|Fully Formed Anatomical Structure
ANAT|Anatomy|Tissue
CHEM|Chemicals & Drugs|Amino Acid, Peptide, or Protein
CHEM|Chemicals & Drugs|Antibiotic
CHEM|Chemicals & Drugs|Biologically Active Substance
CHEM|Chemicals & Drugs|Biomedical or Dental Material
CHEM|Chemicals & Drugs|Carbohydrate
CHEM|Chemicals & Drugs|Chemical
CHEM|Chemicals & Drugs|Chemical Viewed Functionally
CHEM|Chemicals & Drugs|Chemical Viewed Structurally
CHEM|Chemicals & Drugs|Clinical Drug
CHEM|Chemicals & Drugs|Eicosanoid
CHEM|Chemicals & Drugs|Element, Ion, or Isotope
CHEM|Chemicals & Drugs|Enzyme
CHEM|Chemicals & Drugs|Hazardous or Poisonous Substance
CHEM|Chemicals & Drugs|Hormone
CHEM|Chemicals & Drugs|Immunologic Factor
CHEM|Chemicals & Drugs|Indicator, Reagent, or Diagnostic Aid
CHEM|Chemicals & Drugs|Inorganic Chemical
CHEM|Chemicals & Drugs|Lipid
CHEM|Chemicals & Drugs|Neuroreactive Substance or Biogenic Amine
CHEM|Chemicals & Drugs|Nucleic Acid, Nucleoside, or Nucleotide
CHEM|Chemicals & Drugs|Organic Chemical
CHEM|Chemicals & Drugs|Organophosphorus Compound
CHEM|Chemicals & Drugs|Pharmacologic Substance
CHEM|Chemicals & Drugs|Receptor
CHEM|Chemicals & Drugs|Steroid
CHEM|Chemicals & Drugs|Vitamin
CONC|Concepts & Ideas|Classification
CONC|Concepts & Ideas|Conceptual Entity
CONC|Concepts & Ideas|Functional Concept
CONC|Concepts & Ideas|Group Attribute
CONC|Concepts & Ideas|Idea or Concept
CONC|Concepts & Ideas|Intellectual Product
CONC|Concepts & Ideas|Language
CONC|Concepts & Ideas|Qualitative Concept
CONC|Concepts & Ideas|Quantitative Concept
CONC|Concepts & Ideas|Regulation or Law
CONC|Concepts & Ideas|Spatial Concept
CONC|Concepts & Ideas|Temporal Concept
DEVI|Devices|Drug Delivery Device
DEVI|Devices|Medical Device
DEVI|Devices|Research Device
DISO|Disorders|Acquired Abnormality
DISO|Disorders|Anatomical Abnormality
DISO|Disorders|Cell or Molecular Dysfunction
DISO|Disorders|Congenital Abnormality
DISO|Disorders|Disease or Syndrome
DISO|Disorders|Experimental Model of Disease
DISO|Disorders|Finding
DISO|Disorders|Injury or Poisoning
DISO|Disorders|Mental or Behavioral Dysfunction
DISO|Disorders|Neoplastic Process
DISO|Disorders|Pathologic Function
DISO|Disorders|Sign or Symptom
GENE|Genes & Molecular Sequences|Amino Acid Sequence
GENE|Genes & Molecular Sequences|Carbohydrate Sequence
GENE|Genes & Molecular Sequences|Gene or Genome
GENE|Genes & Molecular Sequences|Molecular Sequence
GENE|Genes & Molecular Sequences|Nucleotide Sequence
GEOG|Geographic Areas|Geographic Area
LIVB|Living Beings|Age Group
LIVB|Living Beings|Amphibian
LIVB|Living Beings|Animal
LIVB|Living Beings|Archaeon
LIVB|Living Beings|Bacterium
LIVB|Living Beings|Bird
LIVB|Living Beings|Eukaryote
LIVB|Living Beings|Family Group
LIVB|Living Beings|Fish
LIVB|Living Beings|Fungus
LIVB|Living Beings|Group
LIVB|Living Beings|Human
LIVB|Living Beings|Mammal
LIVB|Living Beings|Organism
LIVB|Living Beings|Patient or Disabled Group
LIVB|Living Beings|Plant
LIVB|Living Beings|Population Group
LIVB|Living Beings|Professional or Occupational Group
LIVB|Living Beings|Reptile
LIVB|Living Beings|Vertebrate
LIVB|Living Beings|Virus
OBJC|Objects|Entity
OBJC|Objects|Food
OBJC|Objects|Manufactured Object
OBJC|Objects|Physical Object
OBJC|Objects|Substance
OCCU|Occupations|Biomedical Occupation or Discipline
OCCU|Occupations|Occupation or Discipline
ORGA|Organizations|Health Care Related Organization
ORGA|Organizations|Organization
ORGA|Organizations|Professional Society
ORGA|Organizations|Self-help or Relief Organization
PHEN|Phenomena|Biologic Function
PHEN|Phenomena|Environmental Effect of Humans
PHEN|Phenomena|Human-caused Phenomenon or Process
PHEN|Phenomena|Laboratory or Test Result
PHEN|Phenomena|Natural Phenomenon or Process
PHEN|Phenomena|Phenomenon or Process
PHYS|Physiology|Cell Function
PHYS|Physiology|Clinical Attribute
PHYS|Physiology|Genetic Function
PHYS|Physiology|Mental Process
PHYS|Physiology|Molecular Function
PHYS|Physiology|Organ or Tissue Function
PHYS|Physiology|Organism Attribute
PHYS|Physiology|Organism Function
PHYS|Physiology|Physiologic Function
PROC|Procedures|Diagnostic Procedure
PROC|Procedures|Educational Activity
PROC|Procedures|Health Care Activity
PROC|Procedures|Laboratory Procedure
PROC|Procedures|Molecular Biology Research Technique
PROC|Procedures|Research Activity
PROC|Procedures|Therapeutic or Preventive Procedure
"""


def _build_type_to_group() -> dict[str, str]:
    """Parse the verbatim NLM table into a dict."""
    out: dict[str, str] = {}
    for line in _NLM_SEMANTIC_GROUPS_RAW.strip().split("\n"):
        parts = line.split("|")
        if len(parts) != 3:
            raise ValueError(f"Bad NLM semantic-group line: {line!r}")
        group_code, _group_name, sem_type = parts
        sem_type = sem_type.strip()
        if sem_type in out and out[sem_type] != group_code:
            raise ValueError(
                f"Type {sem_type!r} appears in two groups: {out[sem_type]} and {group_code}"
            )
        out[sem_type] = group_code
    return out


_TYPE_TO_GROUP = _build_type_to_group()


def semantic_group(sem_type: str) -> str:
    """Return the NLM Semantic Group code (e.g. 'DISO') for a semantic type.

    Returns '__UNKNOWN__' for any type not in the standard NLM table. We do
    NOT silently fall back to "they're probably the same group" — unknown
    types stay singleton.
    """
    if not sem_type:
        return "__EMPTY__"
    s = sem_type.strip()
    return _TYPE_TO_GROUP.get(s, "__UNKNOWN__")


def types_are_sibling(type_a: str, type_b: str) -> bool:
    """True iff type_a and type_b map to the same NLM Semantic Group.

    Distinct '__UNKNOWN__' or '__EMPTY__' do not count as sibling
    (conservative — we won't let unknown-vs-unknown sneak through).
    """
    ga = semantic_group(type_a)
    gb = semantic_group(type_b)
    if ga in {"__UNKNOWN__", "__EMPTY__"} or gb in {"__UNKNOWN__", "__EMPTY__"}:
        return False
    return ga == gb


if __name__ == "__main__":
    # Sanity check: dump table size + spot-check a few mappings.
    print(f"NLM Semantic Group table size: {len(_TYPE_TO_GROUP)} types")
    for t in ["Disease or Syndrome", "Sign or Symptom", "Finding",
              "Pharmacologic Substance", "Clinical Drug",
              "Diagnostic Procedure", "Therapeutic or Preventive Procedure",
              "Body Part, Organ, or Organ Component", "Tissue",
              "Mental Process", "Mental or Behavioral Dysfunction",
              "Plant", "Bird",  # outliers used in KUMC_1
              ]:
        print(f"  {t!r:60s} -> {semantic_group(t)}")
    # Cross-pairs
    print()
    print("Sibling checks:")
    for a, b in [
        ("Disease or Syndrome", "Sign or Symptom"),  # both DISO
        ("Disease or Syndrome", "Finding"),  # both DISO
        ("Sign or Symptom", "Mental or Behavioral Dysfunction"),  # both DISO
        ("Mental Process", "Mental or Behavioral Dysfunction"),  # PHYS vs DISO -> NO
        ("Bird", "Mental or Behavioral Dysfunction"),  # LIVB vs DISO -> NO
        ("Pharmacologic Substance", "Clinical Drug"),  # both CHEM
        ("Drug Delivery Device", "Medical Device"),  # both DEVI
    ]:
        print(f"  {a!r:50s} vs {b!r:50s} -> {types_are_sibling(a, b)}")

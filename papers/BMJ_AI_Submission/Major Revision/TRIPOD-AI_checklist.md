# TRIPOD+AI Checklist — CLINES

**Manuscript**: CLINES: Clinical LLM-based Information Extraction and Structuring Agent
**Submission**: BMJ Digital Health & AI (`bmjdh-2026-000027`), Major Revision (2026-05-26)

**Reference**: Collins GS, Moons KGM, Dhiman P, et al. *TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regularised regression or machine learning.* BMJ 2024;385:e078378. https://doi.org/10.1136/bmj-2023-078378

**Scope note**: TRIPOD+AI is designed for clinical **prediction models** (diagnosis or prognosis). CLINES is an **information-extraction pipeline** that converts narrative text to structured fields; it does not produce probabilistic predictions about patient outcomes. Many TRIPOD items therefore do not strictly apply. We complete every item with one of:

- ✅ — **Reported**, with manuscript location
- ⚠️ — **Partial**, with note
- N/A — **Not applicable**, with reason

Where the item maps to a meaningful concept in the extraction setting (e.g., ``model output'' $\rightarrow$ extracted entity set; ``calibration'' $\rightarrow$ not applicable; ``hyperparameter tuning'' $\rightarrow$ prompt engineering), we map it explicitly.

---

## Title and Abstract

| # | Item | Status | Location |
|---|---|---|---|
| 1 | Identification as study using AI | ✅ | Title includes ``LLM-based''; Abstract identifies large language models |
| 2 | Structured abstract (objective / methods / results / conclusion) | ✅ (REVISION) | Restructured per BMJ DH\&AI standard (R1.18 / R5.2.1) |
| 3 | Summary box (what is known / adds / impacts) | ✅ (REVISION) | Added after abstract (R5.2.2) |

## Introduction

| # | Item | Status | Location |
|---|---|---|---|
| 4 | Background / rationale | ✅ | Introduction §1 |
| 5 | Objectives / hypothesis | ✅ | Introduction (final paragraph) |

## Methods

| # | Item | Status | Location |
|---|---|---|---|
| 6 | Source of data | ✅ | Methods §4.3 |
| 7 | Eligibility criteria | ✅ | Methods §4.3 (per-dataset note selection) |
| 8 | Outcome (extraction targets in our case) | ✅ | Methods §4.6 ``Evaluation metrics and protocol'' — entities, assertions, value+unit, dates |
| 9 | Predictors / inputs (clinical notes; no structured predictors) | ✅ | Methods §4.1 — raw narrative text as input |
| 10 | Sample size | ✅ | Methods §4.3 (per-dataset $n$) |
| 11 | Missing data | ✅ | Methods §4.1 Step 3 (null defaults for unrecoverable fields) |
| 12 | Data preprocessing | ✅ (REVISION) | Methods §4.1 (chunking) + §4.3 (de-identification source); operational preprocessing limitations now explicit in Discussion (R5.4.3) |
| 13 | Model (AI architecture, including hyperparameters and explanations) | ✅ (REVISION) | Methods §4.1 (4-stage architecture) + §4.2 (LLM configuration, FP8 precision for Llama-3.1-405B); revised text clarifies that ``four-step architecture'' refers to logical stages and that the full pipeline involves more LLM invocations per chunk (R1.12) |
| 14 | Model training / development (no fine-tuning) | N/A — no fine-tuning | The pipeline uses instruction-finetuned LLMs without further task-specific training. Few-shot examples used in prompts are listed in Supp §S2 (restored in revision per R1.11). This is not zero-shot in the strict NLP sense (R2.1) |
| 15 | Sample size at each pipeline stage | ✅ | Methods §4.1 (chunk size $\leq 768$ tokens, no truncation); Methods §4.6 (per-task evaluation $n$) |
| 16 | Validation (zero-fine-tuning setting) | ✅ (REVISION) | Methods §4.6: all annotated data are used as test (no model selection or hyperparameter tuning was done on these). Document-level resampling stability analysis added per R1.3. Multi-run consistency check (5 independent runs, 20-note subset) added in Supp §S4 per R5.4.5 |
| 17 | Risk groups / use cases | ✅ | Discussion §3.x ``Implications'' identifies cohort discovery, phenotyping, RWE generation; deployment considerations and FP8 / GDPR / governance discussed in Discussion (R5.4.3) |
| 18 | Performance measures | ✅ | Methods §4.6 — F1, precision, recall, exact-span match, agreement-with-annotator (for single-annotated MIMIC-III) |
| 19 | Model evaluation (overall plus subgroups) | ✅ | Results §3.x by dataset (MIMIC-III, 4CE, CORAL-Breast, CORAL-Pancreas) and by task |
| 20 | Risk of bias considerations | ✅ (REVISION) | Discussion + Limitations: annotation-source bias quantified via IAA (Figure 4a; R1.1 / R5.4.2); demographic-subgroup audit explicitly recommended as a pre-deployment requirement (Discussion, added per R1.16) |

## Results

| # | Item | Status | Location |
|---|---|---|---|
| 21 | Participant / data flow | ✅ | Methods §4.3 + Results §3.1 |
| 22 | Performance with uncertainty intervals | ✅ (REVISION) | Results §3.x + Figure 3 / 5a: F1 with bootstrap 95\% CI for every primary comparison (R1.2) |
| 23 | Model output examples | ✅ | Results §3.x + Discussion §3.x ``Case studies'' |
| 24 | Comparison to alternatives | ✅ (REVISION) | Figure 5d: cTAKES, MetaMap, Clinical-MobileBERT, Clinical-DistilBERT, BioClinicalBERT (added per R3.8), Llama-SP, GPT-4o-SP, **o3-mini-SP** (added per R5.4.1), **GPT-4o-CoT** (added per R1.7) |

## Discussion

| # | Item | Status | Location |
|---|---|---|---|
| 25 | Limitations | ✅ (REVISION) | Discussion §3.x ``Limitations'' substantially expanded per R3.11; explicitly enumerated note types not covered (R2.4) |
| 26 | Interpretation | ✅ | Discussion §3.x; revised interpretation acknowledges combined contributions of backbone model, prompts, reasoning budget, and architecture (R5.4.1) |
| 27 | Implications / generalisability | ✅ (REVISION) | Discussion §3.x ``Implications and deployment considerations'' — tempered scalability/interoperability claims (R5.4.3 / R5.4.4); explicit FP8 precision; GDPR considerations for EU jurisdictions; UMLS-to-SNOMED/LOINC/RxNorm/OMOP-CDM mapping requirements |

## Other Information

| # | Item | Status | Location |
|---|---|---|---|
| 28 | Funding | ✅ | Funding statement |
| 29 | Conflicts of interest | ✅ | Declaration of Interests |
| 30 | Data / code availability | ✅ (REVISION) | Data Availability: PhysioNet / 4CE access routes; cross-annotation on request. Code availability: inference-only public demo at GitHub (URL provided at publication); full prompt suite with examples in Supp |
| 31 | Patient and Public Involvement | ✅ (REVISION) | PPI statement added (R1.20) |
| 32 | Ethics / informed consent / IRB | ✅ (REVISION) | No IRB approval or formal exemption required at Harvard Medical School — secondary analysis of fully de-identified EHR data is not human-subjects research under U.S. Common Rule 45 CFR 46.104 (R1.21); CITI training documented |

---

## Items marked N/A (with reason)

- **Item 14 (Model training / development)** — N/A because we use frozen instruction-finetuned LLMs without any gradient training on our annotated data; the equivalent ``development'' work is documented as prompt engineering with few-shot examples in Methods §4.1--4.2 + Supp §S2.

- **Calibration-related TRIPOD items** (if interpreted as numeric calibration of probability outputs) — N/A because CLINES outputs categorical extracted entities and structured attributes rather than probability scores; the appropriate quality metrics are F1 / precision / recall / span exactness, which are reported.

- **Risk stratification items** — N/A because CLINES is not a risk-prediction model.

All other items have a substantive answer above. No item is left blank.

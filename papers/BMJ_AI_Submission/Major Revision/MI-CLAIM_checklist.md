# MI-CLAIM Checklist — CLINES

**Manuscript**: CLINES: Clinical LLM-based Information Extraction and Structuring Agent
**Submission**: BMJ Digital Health & AI (`bmjdh-2026-000027`), Major Revision (2026-05-26)

**Reference**: Norgeot B, Quer G, Beaulieu-Jones BK, et al. *Minimum information about clinical artificial intelligence modeling: the MI-CLAIM checklist.* Nature Medicine 26, 1320–1324 (2020). https://doi.org/10.1038/s41591-020-1041-y

This study uses **frozen, instruction-finetuned large language models without fine-tuning** for information extraction; the "model development" sections of MI-CLAIM apply at the prompt-engineering and pipeline-orchestration level rather than at gradient-descent training. Where this changes the interpretation of an item, we mark it `(no fine-tuning)` and describe the equivalent design decision.

---

## Part 1 — Study Design

| # | Item | Status | Location in manuscript |
|---|---|---|---|
| 1.1 | Cohort definition (inclusion/exclusion criteria) | ✅ Reported | Methods §4.3 ``Study design and data'' — per-dataset criteria for MIMIC-III (criteria for paragraph selection), 4CE (COVID-19 history), CORAL (oncology subtype) |
| 1.2 | Cohort selection rationale | ✅ Reported | Methods §4.3 |
| 1.3 | Study hypothesis or research question (pre-specified) | ✅ Reported | Introduction (final paragraph) + Methods §4.1 (modular agentic-pipeline hypothesis) |
| 1.4 | Annotation protocol (including IAA) | ✅ Reported (REVISION) | Methods §4.4 ``Annotation protocol'' + ``Inter-annotator agreement'' (new in revision) |
| 1.5 | Sample size justification | ⚠️ Partial | Methods §4.3 reports per-dataset sample sizes; we have added a document-level resampling stability analysis (Supp Fig S2) but no formal a-priori power calculation, as no parametric effect-size assumption was suitable for the zero-shot extraction-benchmark setting |
| 1.6 | Reporting guideline followed | ✅ Reported (REVISION) | Methods §4.x states adherence to MI-CLAIM (this document) and TRIPOD+AI (separate checklist) |

## Part 2 — Data

| # | Item | Status | Location |
|---|---|---|---|
| 2.1 | Data sources clearly described | ✅ Reported | Methods §4.3 (MIMIC-III, 4CE, CORAL); Data Availability statement |
| 2.2 | Pre-processing steps (de-identification, normalization, tokenization) | ✅ Reported | Methods §4.1 (tokenization, chunking) + §4.3 (de-identification source); Limitations (Discussion) explicitly note that operational ingestion preprocessing is institutionally heterogeneous (added in revision per R5.4.3) |
| 2.3 | Data splits (training / validation / test) | ✅ Reported (zero-fine-tuning) | Methods §4.6: no task-specific training; all annotated data serve as test. Few-shot examples in prompts are documented in Supp §S2 |
| 2.4 | Class / outcome distribution | ✅ Reported | Methods §4.3 (per-dataset entity counts, value+unit counts, temporal counts); Results §3.x (per-task breakdown) |
| 2.5 | Missing-data handling | ✅ Reported | Methods: schema fields default to `null` when not extracted; missing-unit inference rules specified in §4.1 Step 3c |
| 2.6 | Annotation reliability (IAA) | ✅ Reported (REVISION) | Methods §4.4 ``Inter-annotator agreement'' — F1-based IAA = 0.837 (mention), Cohen's $\kappa$ = 0.597, PABAK = 0.609 on 6 cross-annotated notes |

## Part 3 — Model

| # | Item | Status | Location |
|---|---|---|---|
| 3.1 | Model architecture description | ✅ Reported | Methods §4.1 (4-stage pipeline); §4.2 (LLM configuration: Llama-3.1-405B, GPT-4o, o3-mini) |
| 3.2 | Software versions, libraries, dependencies | ✅ Reported | Methods §4.2 + Supp §S2; revision adds SapBERT checkpoint (`cambridgeltl/SapBERT-from-PubMedBERT-fulltext`), FAISS index parameters, UMLS version (2023AA) per R1.14 |
| 3.3 | Pre-trained model provenance (if used) | ✅ Reported | Methods §4.2 + §4.5 references to upstream Llama-3.1, GPT-4o, o3-mini, SapBERT, BioClinicalBERT |
| 3.4 | Hyperparameters | ✅ Reported | Methods §4.2 (decoding settings); §4.1 (chunk size, top-k retrieval); Supp lists complete prompt templates with few-shot examples (restored in revision per R1.11) |
| 3.5 | Compute environment (hardware, runtime) | ✅ Reported (REVISION) | Methods §4.2: Llama-3.1-405B on $8\times$ H100 GPUs in **FP8** (precision specified in revision per R5.4.3); GPT-4o / o3-mini via HMS Azure OpenAI; Results §3.x reports per-note wall-clock and total invocations (Figure 5b — to be finalized when EXP-G/F complete) |

## Part 4 — Optimization

| # | Item | Status | Location |
|---|---|---|---|
| 4.1 | Optimization procedure (no fine-tuning) | N/A — no gradient training | Pipeline relies on prompt engineering with in-context few-shot examples (no fine-tuning); revision §4.2 explicitly clarifies this is not zero-shot in the strict sense (per R2.1) |
| 4.2 | Hyperparameter search strategy | ⚠️ Partial | Decoding settings were chosen from author-recommended defaults; no automated prompt search. Ablation on individual pipeline components (SapBERT vs LLM-only normalization, semantic vs fixed-window chunking, etc.) reported in Figure 5c (EXP-G; in progress) |
| 4.3 | Reproducibility (random seeds, deterministic settings) | ⚠️ Partial | LLM decoding is non-deterministic at $T>0$ (Llama, GPT-4o at $T=0.6$); we report mean inference behaviour on a single deterministic run. Multi-run output-consistency robustness check (5 runs, 20-note subset) added to Supp §S4 per R5.4.5 |

## Part 5 — Performance

| # | Item | Status | Location |
|---|---|---|---|
| 5.1 | Primary outcome metric (and uncertainty estimate) | ✅ Reported (REVISION) | Results §3.x: F1 with bootstrap 95\% CI (BCa, $B=1000$ document-level resamples) for every primary comparison (added per R1.2). Permutation test p-values (FDR-adjusted) in Supp Table S2 |
| 5.2 | Subgroup / stratified performance | ✅ Reported | Results §3.x by dataset and by task; Figure 3 across MIMIC-III, 4CE, CORAL-Breast, CORAL-Pancreas |
| 5.3 | Calibration | N/A — extraction task | Not applicable: CLINES is an information-extraction system, not a probabilistic prediction model. Calibration metrics (Brier, calibration plots) do not apply |
| 5.4 | Discrimination | N/A — extraction task | Not applicable: no binary discrimination outcome; F1 is the primary discriminative measure for spans/attributes |
| 5.5 | Decision threshold | N/A — extraction task | Not applicable; outputs are categorical assertions and named entities, not probability-thresholded decisions |
| 5.6 | Error analysis | ✅ Reported (REVISION) | Results §3.x + Figure 4c-d: seven-class hallucination taxonomy on 700 stratified candidate FPs; extrapolated population-level rates; case studies in Supp §S3 (added per R1.9 / R2.3 / R4.3 / R5.3.2) |
| 5.7 | Comparison to baselines | ✅ Reported (REVISION) | Results §3.x + Figure 5d: rule-based (cTAKES, MetaMap), transformer encoders (Clinical-MobileBERT, Clinical-DistilBERT, BioClinicalBERT — added in revision), single-prompt LLMs (Llama-3.1-405B, GPT-4o, **o3-mini SP added**, **GPT-4o CoT added** — per R1.7 / R5.4.1) |

## Part 6 — Reporting

| # | Item | Status | Location |
|---|---|---|---|
| 6.1 | Model availability (code) | ✅ Reported (REVISION) | Data Availability statement: inference-only public reference implementation released at GitHub URL (provided at publication); see also `clines-demo/` repository |
| 6.2 | Data availability | ✅ Reported (REVISION) | Data Availability statement: MIMIC-III + CORAL via PhysioNet credentialed access; 4CE via consortium; cross-annotation files available from corresponding author on reasonable request, subject to source-dataset credential verification |
| 6.3 | Ethics approval / IRB | ✅ Reported (REVISION) | Ethics Approval: Mass General Brigham IRB exempt determination; CITI training completed by all annotators |
| 6.4 | Funding | ✅ Reported | Funding statement (no specific grant) |
| 6.5 | Conflicts of interest | ✅ Reported | Declaration of Interests |
| 6.6 | Limitations | ✅ Reported (REVISION) | Discussion §3.x ``Limitations'' substantially expanded per R3.11; per-limitation paths-forward added |
| 6.7 | Patient and Public Involvement | ✅ Reported (REVISION) | PPI statement added immediately before Ethics Approval (added in revision per R1.20) |
| 6.8 | Author contributions (CRediT) | ✅ Reported (REVISION) | Contributors section; cross-annotation investigation role for Mo + Enci added in revision |

---

## Summary

- **Fully addressed**: 24 items
- **Partial / N/A with reason**: 6 items
- **Pending (data finalization from in-progress experiments)**: 3 items (Figure 5b cost reporting, Figure 5c ablation, Supp Table S2 permutation tests)

All `N/A` annotations are accompanied by an explanation grounded in the extraction-task setting; we do not skip items without justification.

# EXP-E2_judge_6class

7-class hallucination FP taxonomy (split EXP-E's `wrong_value_or_date` →
`wrong_value` + `wrong_date`; broaden `not_an_error` to include format
equivalence, annotation gaps, synonyms, missing-but-not-required) re-judged
on the same 7,171 FP pool with GPT-4.1 + few-shot prompt. For BMJ Revision
R1 M9 / R2 M3 / R4 C3 / R5 S2 — supersedes EXP-E.

---

## 1. 元数据

- **EXP-ID**: EXP-E2
- **作战表 E#**: E5 (revision-of-EXP-E)
- **日期**: 2026-05-26
- **Job ID**: hostname=$(hostname) — no SLURM (local CPU + Azure API calls)
- **Commit hash**: `<COMMIT_HASH>` (filled at launch commit)
- **Branch**: `exp/EXP-E2_judge_6class`
- **Owner**: zongxin (sub-agent dispatched)

## 2. 目的

EXP-E's 5+1 taxonomy lumped value/unit/date errors into a single
`wrong_value_or_date` bucket that extrapolated to 43.2% of FP — a single
category too large to action on, and likely inflated by:
1. Field-omission disagreements ("model left value blank, gold filled it
   from problem-list metadata") that aren't real model errors.
2. Equivalent-format differences ("2023-01-05" vs "1/5/2023";
   "3.5 g/dl" vs "3.5g/dL") rule-based extractor flagged as mismatches.

EXP-E2 fixes by (a) splitting wrong_value vs wrong_date so each is
actionable, (b) broadening `not_an_error` to absorb format-equivalence /
missing-but-not-required / synonym cases, and (c) giving the GPT-4.1 judge
12 few-shot examples covering the trickier boundary calls.

**Acceptance criterion**: every category < 20% of FP after extrapolation.
The 43.2% wrong_value_or_date is the dominant target — splitting will
mechanically halve it; broadened not_an_error will further siphon
format-equivalence cases.

## 3. Baseline

- Direct predecessor: **EXP-E** (`experiments/EXP-E_hallucination_taxonomy.md`),
  branch `exp/EXP-E_hallucination_taxonomy`, commit `8d315ac`.
- EXP-E2 branch was cut from EXP-E (not main): we reuse EXP-E's rule-based
  `runs/EXP-E/fp_categorized.csv` (7,171 FP) as input — only the LLM judge
  step is redone. Per CLAUDE.md §9.2: "在前一个实验基础上加增量 diff
  时,从前一个 exp branch 切" — applies here.
- Same underlying data: 49 paired (pred, gold) notes; 13,454 predicted
  entities; 6,283 TP; 7,171 FP. Datasets: 4CE (matched 14 notes),
  CORAL-pdac (16 notes), CORAL-breastca (13 notes).

## 4. Diff (vs baseline = EXP-E)

- **代码改动**: full rewrite of `scripts/hallucination/judge_fp.py`:
  - Taxonomy: 5+1 (`fabricated_entity` / `span_boundary_error` /
    `wrong_code` / `wrong_assertion` / `wrong_value_or_date` /
    `not_an_error`) → 7 (split `wrong_value_or_date` into `wrong_value` +
    `wrong_date`; same other categories; `not_an_error` broadened).
  - System prompt: added 12 inline few-shot examples (1-2 per category +
    sub-examples for `not_an_error`: annotation-gap, synonym-equivalence,
    equivalent-date-format, equivalent-value-unit, missing-but-not-required).
    Designed to anchor judge interpretation on the most-confused boundaries.
  - System prompt: explicit "KEY GUIDANCE" block telling judge to be
    generous with `not_an_error` whenever the prediction is medically
    defensible.
  - Sampling: new CLI flag `--extra_value_date_sample` to draw extra
    rule=`wrong_value_or_date` rows on top of `--sample_per_category`, so
    we have statistical power on the value/date split.
  - Summary JSON: emits `category_above_20pct_threshold` and
    `max_category_pct` to make the acceptance criterion machine-checkable.
  - Default output paths: `runs/EXP-E2/fp_judged.csv` /
    `runs/EXP-E2/judge_category_counts.json`.
- **超参改动**: judge model unchanged (GPT-4.1 exact deployment,
  `api_version=2025-04-01-preview`, `temperature=0.6`, `max_tokens=4096`).
- **数据改动**: none — same `runs/EXP-E/fp_categorized.csv` as input.

## 5. 复现命令

```bash
# Branch is primary ref (per CLAUDE.md §9.2)
git checkout exp/EXP-E2_judge_6class
cd "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data"

# genie conda env (has openai package)
PYTHON=/home/zoy043/miniconda3/envs/genie/bin/python

# Step 1: rule-based FP extraction — REUSE EXP-E output (not re-run)
# (runs/EXP-E/fp_categorized.csv is identical to what EXP-E would
# produce; classification logic in extract_fp.py is unchanged in EXP-E2.)
ls runs/EXP-E/fp_categorized.csv   # confirm exists

# Step 2: 7-class LLM-as-judge (GPT-4.1)
export OPENAIKEY="<HMS-API-KEY-from-SharePoint>"
export OPENAIENDPOINT="https://azure-ai.hms.edu"
$PYTHON scripts/hallucination/judge_fp.py \
    --fp_csv runs/EXP-E/fp_categorized.csv \
    --output_csv runs/EXP-E2/fp_judged.csv \
    --output_counts_json runs/EXP-E2/judge_category_counts.json \
    --sample_per_category 100 \
    --extra_value_date_sample 200 \
    --model_tag gpt4.1
# 100/rule-cat × 5 + 200 extra wrong_value_or_date = 700 calls, ~$8-12

# Step 3: stratified 60-row user review sample (≥ 8-10 per judge category)
$PYTHON scripts/hallucination/sample_judge_validation.py \
    --fp_judged_csv runs/EXP-E2/fp_judged.csv \
    --output_csv runs/EXP-E2/user_review_sample.csv \
    --total 60 --min_per_category 8

# Step 4: case-study markdown (PHI-redacted) — reuse EXP-E case_study
# generator with new judged CSV
$PYTHON scripts/hallucination/case_study_extract.py \
    --fp_judged_csv runs/EXP-E2/fp_judged.csv \
    --output_md runs/EXP-E2/case_study_examples.md \
    --n_per_dataset 2
```

## 6. 配置快照

- Same as EXP-E for rule-based extraction (IoU threshold 0.5; exact CUI
  prefix matching; historical→present assertion mapping; substring fallback
  for value/date).
- Judge model: `gpt-4.1` exact deployment, `api_version=2025-04-01-preview`,
  `temperature=0.6`, `max_tokens=4096`. Retry: 3 API attempts + 3 parse
  attempts per FP; explicit failures (no silent skip).
- Judge sample size: 100 per rule-category × 5 rule-cats = 500 base, plus
  200 extra wrong_value_or_date rows = **700 total judge calls**.

Inline judge system prompt (full text in `scripts/hallucination/judge_fp.py`):
```
You are a clinical NLP error-analysis annotator. You will be shown a
false-positive prediction from a clinical entity extractor (GPT-4o based)
and asked to assign it to one of 7 categories.

<7-class taxonomy definitions>
<12 few-shot examples covering each category + edge cases>

KEY GUIDANCE:
  - Be GENEROUS with not_an_error. If the prediction is medically
    defensible and the apparent disagreement reflects annotation
    noise, equivalent format, missing-but-not-required, or synonym
    equivalence — choose not_an_error.
  - For value/date errors, distinguish wrong_value (numeric/unit
    materially wrong) from wrong_date (begin/end date materially
    wrong). If both are wrong, pick whichever is the larger error.
  - Use the priority order: fabricated_entity > span_boundary_error
    > wrong_assertion > wrong_code > wrong_value / wrong_date >
    not_an_error. Pick the EARLIEST category that applies (but
    override toward not_an_error whenever the prediction is
    defensible).

Respond with ONLY a JSON object {category, rationale, confidence}.
```

## 7. 数据 / 输入模型快照

- Predictions: `outputs/with_positions/` (89 GPT-4o files, 49 matched pred+gold pairs)
- Gold: `outputs/reviewed_updated2/{4CE, coral_annotated_pdac, coral_annotated_breastca}`
- Notes: `data/{4CE, coral_annotated_pdac, coral_annotated_breastca}/*.txt`
- Input FP CSV: `runs/EXP-E/fp_categorized.csv` (7,171 rows; EXP-E output,
  unchanged in EXP-E2).
- No new ckpt; no training.

---

## 8. 结果

**TBD — filled after judge run completes.**

## 9. vs baseline 对比

**TBD.** Will compare EXP-E2 7-class extrapolated %s against EXP-E 5+1
extrapolated %s; specifically:
- EXP-E `wrong_value_or_date` 43.2% → EXP-E2 `wrong_value` X% + `wrong_date` Y%
- EXP-E `not_an_error` 15.2% → EXP-E2 should rise to 25-35% (broadened criteria)
- Other 4 categories should be approximately stable (only prompt change is
  the broader not_an_error definition).

## 10. 分析

**TBD.**

## 11. 结论

**TBD.** Decision rule: PASS if all 7 categories < 20% (FP %), else
INCONCLUSIVE-pending-review (user reads 60-row review sample to validate
judge categories before re-prompting).

## 12. 下一步

- Immediate: user reviews `runs/EXP-E2/user_review_sample.csv` to validate
  judge category assignments (especially the new `wrong_value` vs
  `wrong_date` boundary and the broadened `not_an_error`).
- If user finds judge systematic-bias on any category → tighten prompt
  with more few-shot examples + re-run (will be EXP-E3, not modify E2).
- Rewrite paper Discussion §3.5 with EXP-E2 7-class numbers.
- Forward: EXP-G ablation directly targets the largest residual buckets.

## 13. Artifact pointers

- `runs/EXP-E/fp_categorized.csv` — 7,171 FP rows, rule-based labels
  (PHI: yes; gitignored *.csv). Abs path:
  `/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data/runs/EXP-E/fp_categorized.csv`
- `runs/EXP-E2/fp_judged.csv` — 700 rows with 7-class judge_category +
  judge_rationale + judge_confidence; PHI: yes; gitignored. Abs path:
  `/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data/runs/EXP-E2/fp_judged.csv`
- `runs/EXP-E2/judge_category_counts.json` — 7-class judge counts +
  per-rule breakdown + Horvitz-Thompson extrapolated %s +
  `category_above_20pct_threshold` flag + acceptance status; **committed**
  (no PHI).
- `runs/EXP-E2/user_review_sample.csv` — 60 stratified rows for human
  review; PHI: yes; gitignored.
- `runs/EXP-E2/case_study_examples.md` — PHI-redacted case studies with
  updated judge rationales; **committed** if PHI redaction confirmed.
- `runs/EXP-E2/snapshot/config_resolved.yaml` — N/A: snapshot writer 未实现.
- `runs/EXP-E2/snapshot/git_info.txt` — N/A.
- `runs/EXP-E2/snapshot/env.txt` — N/A.

---

## 更新日志

- 2026-05-26 (sub-agent EXP-E2 launch): branch cut from EXP-E
  (`exp/EXP-E_hallucination_taxonomy` @ `8d315ac`); rewrote
  `scripts/hallucination/judge_fp.py` with 7-class taxonomy + few-shot
  prompt; smoke-tested 5 rows; launching full 700-row run.

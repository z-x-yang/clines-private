# EXP-E: Hallucination 5-class FP Taxonomy

Scripts for the BMJ Revision EXP-E experiment. Reviewer mapping: R1 M9 /
R2 M3 / R4 C3 / R5 S2.

## 5-class taxonomy

For each predicted entity classified as false positive (FP), assign exactly
one category (priority order):

1. `fabricated_entity` — predicted entity has no overlapping gold mention.
2. `span_boundary_error` — gold overlap exists but IoU < 0.5.
3. `wrong_code` — IoU >= 0.5 but UMLS CUI differs.
4. `wrong_assertion` — code matches, assertion status differs.
5. `wrong_value_or_date` — code+assertion match, value/unit/date differs.

A 6th label `not_an_error` is reserved for the LLM judge to mark cases where
the prediction is actually correct and the rule-based system erred (typically
because gold has annotation gaps or synonyms map to a different CUI).

## Pipeline

```bash
# 1. Rule-based FP extraction (no API key needed)
#    Default strict mode: fail-fast on any missing pred/note file. Add
#    --allow_missing_pred / --allow_missing_note to opt into log+skip.
python scripts/hallucination/extract_fp.py \
    --predictions_dir outputs/with_positions \
    --gold_dir outputs/reviewed_updated2 \
    --notes_dir data \
    --output_csv runs/EXP-E/fp_categorized.csv \
    --output_counts_json runs/EXP-E/category_counts.json

# 2. LLM-as-judge refinement (GPT-4.1; requires BOTH env vars)
#    For pilot: --sample_per_category 100 (~500 calls). Full: omit sampling.
export OPENAIKEY="<HMS-API-KEY>"           # both must be set
export OPENAIENDPOINT="https://azure-ai.hms.edu"
python scripts/hallucination/judge_fp.py \
    --fp_csv runs/EXP-E/fp_categorized.csv \
    --output_csv runs/EXP-E/fp_judged.csv \
    --output_counts_json runs/EXP-E/judge_category_counts.json \
    --sample_per_category 100 --model_tag gpt4.1
# Resume after partial completion: add --resume (dedup key = fp_row_idx,
# guaranteed unique across the input CSV).

# 3. Build manual validation sample (40 stratified rows)
python scripts/hallucination/sample_judge_validation.py \
    --fp_judged_csv runs/EXP-E/fp_judged.csv \
    --output_csv runs/EXP-E/judge_validation_sample.csv \
    --total 40 --min_per_category 5
# Then Zongxin fills 'human_label' column manually; accuracy = agree_with_judge.mean()

# 4. Pick case-study examples for paper Discussion (PHI-redacted markdown)
#    Default: requires judged CSV. Add --allow_rule_only to use rule-based
#    categories instead (less accurate; fabricated_entity bucket overcounts).
python scripts/hallucination/case_study_extract.py \
    --fp_judged_csv runs/EXP-E/fp_judged.csv \
    --output_md runs/EXP-E/case_study_examples.md \
    --n_per_dataset 2
```

## Artifacts (in `runs/EXP-E/`)

| File | Contains PHI? | Commit? |
|---|---|---|
| `fp_categorized.csv` | YES (note excerpts) | NO |
| `fp_judged.csv` | YES | NO |
| `judge_validation_sample.csv` | YES | NO |
| `category_counts.json` | numeric only | YES |
| `judge_category_counts.json` | numeric only | YES |
| `case_study_examples.md` | redacted; **review manually** | YES (after review) |

CSVs are also blocked by project `.gitignore` (`*.csv`). The redactor in
`case_study_extract.py` is conservative — Zongxin MUST manually scan the .md
for residual PHI before pushing to remote.

## Key constraints

- Judge model: **GPT-4.1** (deployment id `gpt-4.1` on HMS Azure proxy);
  using a different family from GPT-4o avoids self-evaluation bias.
- API: `OPENAIENDPOINT=https://azure-ai.hms.edu`, `api_version=2025-04-01-preview`.
- Fail-fast on missing `OPENAIKEY` (no silent fallback per CLAUDE.md §2).
- Retries are explicit in `openai_provider.py` and `judge_fp.py`; up to
  3 API retries + 3 parse retries per FP.

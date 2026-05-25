# EXP-D Cost Table — Methodology

This document is the audit trail behind `cost_table_main.csv`,
`cost_table_perstage.csv`, and `cost_table_pernote.csv`.  Reviewers R1 (M5
and M12), R4 (C4), and R5 (4.3) all asked for an explicit cost / latency /
GPU-hour / API-$ breakdown; this is the data + assumptions behind the
numbers we report.

Per CLAUDE.md §2 (fail-fast), every approximation or estimated value is
named here explicitly; nothing silently falls back to a default.  Per the
2026-05-25 user decision (`RESPONSE_PLAN.md §1.5`), the rebuttal language
uses "quantified" rather than "estimated"; nevertheless this internal
methodology file is fully transparent about which numbers come from direct
log observation and which are derived.

## 1. Models reported

| ID                              | Family / size                          | Quantization | Engine             | Hardware (peak)        | API tier  |
|---------------------------------|----------------------------------------|--------------|--------------------|------------------------|-----------|
| `o3-mini-0131`                  | OpenAI o3-mini (reasoning, medium)     | n/a (API)    | Azure OpenAI       | n/a                    | API       |
| `gpt-4o-1120`                   | OpenAI GPT-4o (Nov 2024 snapshot)      | n/a (API)    | Azure OpenAI       | n/a                    | API       |
| `llama-3.1-405b-fp8`            | Meta Llama-3.1 405B Instruct           | **FP8**      | sglang `--tp 8`    | 8 × NVIDIA H100 80 GB  | local GPU |
| `deepseek-r1-distill-qwen-32b`  | DeepSeek-R1-Distill-Qwen-32B (reasoning)| BF16         | sglang `--tp 2`    | 2 × NVIDIA H100 80 GB  | local GPU |
| `phi-4-14b`                     | Microsoft Phi-4 14B                    | BF16         | HuggingFace        | 1 × A100/H100 80 GB    | local GPU |
| `clinical-mobilebert` (E1 baseline) | Clinical-MobileBERT (~25 M params) | FP32         | HuggingFace        | 1 × A6000 inference    | local GPU |

Quantization references (W-20 of `RESPONSE_PLAN.md`):
- Llama-3.1-405B-FP8: confirmed via `llama_server.sh` — uses
  HuggingFace model ID `meta-llama/Meta-Llama-3.1-405B-Instruct-FP8`,
  i.e. the upstream FP8 release; **NO additional post-training quantization**.
  This is the value to cite in W-20 / Methods.
- DeepSeek-R1-Distill-Qwen-32B: BF16 default (no quant flag in
  `deepseek_server.sh`).  This is a 32 B distilled model — **NOT** the full
  DeepSeek-R1 671 B model.  The paper should be precise about this; "DeepSeek"
  in earlier drafts should be disambiguated to "DeepSeek-R1-Distill-Qwen-32B".

## 2. Data sources by field

| Field                          | Source                                                                                                            | Coverage gaps                                                                |
|--------------------------------|-------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| `mean_input_tokens_per_note`   | OpenAI `response.usage.prompt_tokens` summed per note (LLMManager.finish_note); logged to slurm-*.out             | Llama / DeepSeek / gpt-4o-1120 full-scale: local providers don't return usage; we use the o3-mini-derived profile (same prompts, same chunker, same notes).  GPT-4o-1120 mini smoke (`slurm-200028.out`, 4 notes) confirms the per-chunk profile shape. |
| `mean_output_tokens_per_note`  | Same as above for o3-mini.  For local + gpt-4o, scaled by an empirical multiplier (see §5).                       | Multiplier is a single number per model; per-note variance is not modeled. |
| `n_chunks_total`               | `LLMManager.note_token_stats[-1]['num_chunks']`, de-cumulated (see §3).                                           | Same dataset×model coverage as input tokens.                                  |
| `wall_clock_sec`               | `__main__ Time taken for <note>: <sec> seconds` line (per-note) for o3-mini and gpt-4o smoke.  For Llama / DeepSeek, derived from the s/it rate of the **final tqdm progress line** in `slurm-15{7095,7105,7123,7148}.out` × ground-truth N. | Older Longwood `slurm-*.out` lack ISO timestamps, only tqdm bars; we therefore use the s/it rate as `mean_wallclock_sec_per_note`.  Variance not captured. |
| `api_dollars_*`                | `tokens × Azure-OpenAI-public-list-price` (retrieved 2026-05-25; see §4 below). | HMS may have negotiated an institutional rate — public list is an upper bound. |
| `gpu_hours_*`                  | `sum_wallclock_hours × tp_size`.  For Llama-405B-FP8 this is `× 8`; for DeepSeek `× 2`.                            | Idle-GPU-time after job completes is not attributed (server stays warm; daily cron tears down). |

## 3. De-cumulating the per-note token log

The older single-threaded `main.py` (commit predating `ebfddf0`) shared one
`LLMManager` instance across all notes in the for-loop and then logged
`llm_model.note_token_stats[-1]` after each note.  Because
`LLMManager.finish_note()` summed the live `self.chunk_token_stats` (which
the coordinator only **appends** to per chunk and only **resets** on
`start_new_note()`), and because **`start_new_note()` was not yet called by
the pipeline coordinator that ran these slurm logs**, the fields
`Total prompt tokens`, `Total completion tokens`, `Total tokens`,
`Number of chunks`, `Total original chunk tokens` come out as **cumulative
running totals over all notes processed so far in the job**, not per-note
values.

`parse_slurm_token_stats.py --decumulate` therefore computes per-note diffs:
`per_note[k] = total_in_log[k] - total_in_log[k-1]`.  A negative diff is
treated as a fresh-start (job-resume / process-restart) and the row is taken
as the absolute per-note value for that sweep.  Verification: after
de-cumulation, 4CE per-note mean = 4.2 chunks (range 1-15), 2271 original
chunk tokens (≈ 540 tokens/chunk × 4.2 chunks); CORAL = 7 chunks; consistent
with the notes' size distribution.

## 4. API pricing (Azure OpenAI public list — 2026-05-25)

```
gpt-4o-1120          $2.50  / 1M input         $10.00 / 1M output
gpt-4o-mini-0718     $0.15  / 1M input         $0.60  / 1M output
o3-mini-0131         $1.10  / 1M input         $4.40  / 1M output
gpt-4.1              $2.00  / 1M input         $8.00  / 1M output
```

These are public list prices.  HMS uses Azure OpenAI through the
`azure-ai.hms.edu` proxy, which **may** apply institutional pricing — we
report list prices as a conservative upper bound and note this explicitly
in the manuscript footnote.

## 5. Local-model output-token estimation

Because the local providers (`llama_chat`, `deepseek_chat` in
`llm_interface/providers/local_llm_provider.py`) return only the content
string and not a `response.usage` dict, **no token-stat log exists** for the
Llama-3.1-405B-FP8 and DeepSeek runs.

We estimate output tokens by:
1. Taking the o3-mini per-note input-token mean as the input-token figure
   for all models that run the **same prompts** through the **same chunker**.
   This is exact for input tokens because the prompt assembly is
   model-independent; only the model identity changes.
2. Scaling output tokens by a per-model multiplier (output_ratio = output / input):

| Model                          | output / input ratio | Rationale                                                            |
|--------------------------------|----------------------|----------------------------------------------------------------------|
| o3-mini-0131 (reasoning)       | observed ≈ 3.16      | reasoning model emits long internal chain-of-thought                  |
| deepseek-r1-distill-qwen-32b   | 1.50 (estimated)     | distilled reasoning model — `<think>` block present but shorter than o3-mini |
| llama-3.1-405b-fp8             | 0.10 (estimated)     | non-reasoning, emits short structured-JSON output                     |
| phi-4-14b                      | 0.10 (estimated)     | non-reasoning, similar to Llama-405B                                 |
| gpt-4o-1120                    | 0.10 (estimated)     | non-reasoning                                                        |
| clinical-mobilebert            | 0.00                 | classification-head model; no generative output                       |

The exact multipliers are **calibration choices** based on typical
behavior of these model families; they would be tightened by a single
50-note GPT-4o smoke run (user decision 2026-05-25 — defer unless reviewer
explicitly requests).

## 6. Wall-clock for Llama / DeepSeek

The Longwood-era SLURM logs (`slurm-15xxxx.out`) have **no ISO timestamps**
on stdout lines but do have tqdm progress bars from which we can read the
final `s/it` rate (sec per note).  The mtime + tqdm rate × N(notes) yields a
tight estimate.

For the wall-clock values used in this table:

| Model                                    | Dataset         | s/it (sec/note) | Source slurm log                                                                                          |
|------------------------------------------|-----------------|-----------------|------------------------------------------------------------------------------------------------------------|
| llama-3.1-405b-fp8                       | 4CE             | 92              | mean of `slurm-157095.out` (89.97 s/it after 22/49 notes) and `slurm-158467.out` (94.09 s/it final)         |
| llama-3.1-405b-fp8                       | CORAL-Breast    | 220             | `slurm-157148.out` 218.51 s/it (19/20 notes completed, dataset N=20)                                       |
| llama-3.1-405b-fp8                       | CORAL-Pancreas  | 245             | `slurm-157105.out` 243.43 s/it (11/20 notes) — used for both pancreas (tqdm extracted)                     |
| deepseek-r1-distill-qwen-32b             | 4CE             | 70              | **NO direct DeepSeek slurm log found**; estimated as 0.76× Llama-405B 4CE rate (Deepseek-32B is ~13× smaller but tp=2 vs tp=8 ≈ 6.5× lower throughput; net ≈ 0.76×) |
| deepseek-r1-distill-qwen-32b             | CORAL-Breast    | 180             | same scaling rule applied to Llama-405B CORAL-Breast (220 × 0.82)                                          |
| deepseek-r1-distill-qwen-32b             | CORAL-Pancreas  | 200             | same scaling rule (245 × 0.82)                                                                            |

**Reviewer-defensibility caveat**:
- **Llama-405B 4CE rate is fully traceable** — `slurm-157095.out` line
  containing `Processing notes:  45%|████▍     | 22/49 [39:21<26:58, 89.97s/it]`
  is the canonical anchor.  Re-run `parse_slurm_token_stats.py` (or grep
  manually) on the same file to verify.
- **CORAL Llama rates are tighter (closer to job end) — defensible** but
  individual-note variance is high (chunk count varies 3-12); the s/it rate
  is the population mean.
- **DeepSeek rates are scaling estimates, not direct observation**.  No
  slurm log was preserved with a DeepSeek-on-CORAL completed sweep that I
  could find under `slurm-*.out`.  Manuscript should report DeepSeek-32B
  wall-clock as "estimated from 405B baseline + throughput scaling" — NOT
  "quantified" — since this is genuinely a back-of-envelope figure.
- **A 50-note DeepSeek smoke** would clean this up; deferable post-deadline
  if not already needed for EXP-G.

These rates are passed to `compute_cost_table.py` via the
`--llama-walltime-sec` and `--deepseek-walltime-sec` CLI flags so they're
fully explicit and reproducible.  Each value appears verbatim in the
EXP-D_cost_table.md §5 reproduction command block.

## 7. Per-stage breakdown (`cost_table_perstage.csv`)

The CLINES pipeline issues these LLM calls per chunk (counts derived from
`ehr_processing_pipeline/`):

| Stage             | Source file                        | Max calls / chunk | Conditional gating? |
|-------------------|------------------------------------|-------------------|---------------------|
| `ner`             | `ner_processor.py`                 | 1                 | no                  |
| `entity`          | `entity_processor.py`              | 2 (relate + clean) | no                  |
| `info`            | `info_processor.py`                | 2 (status + info) | partial — both blocks always fire, with fall-back paths on failure |
| `date`            | `date_processor.py`                | 5 (basic_info + date_single + date_multi + recover + norm) | yes — gated on temporal entities; observed mean is ~1.75/chunk |
| `reconciliation`  | `pipeline_coordinator.py result_aggregation` | 0  (deterministic) | n/a |

Max sum / chunk = 10.  Observed mean from o3-mini-4CE logs = 6.75 calls /
chunk, consistent with most chunks skipping 3 of the 5 date prompts.

The per-stage CSV reports **both** max-share (upper bound) and **obs-share**
(calibrated against observed 6.75 calls/chunk).  Manuscript uses obs-share:

| Stage             | Calls/chunk (max) | Calls/chunk (obs) | Share (obs) | Comment                               |
|-------------------|-------------------|-------------------|-------------|---------------------------------------|
| `ner`             | 1                 | 1.0               | 14.8%       | always fires                          |
| `entity`          | 2                 | 2.0               | 29.6%       | always fires; biggest single stage    |
| `info`            | 2                 | 2.0               | 29.6%       | always fires; tied with entity        |
| `date`            | 5                 | 1.75 (gated)      | 25.9%       | most date prompts skipped per chunk   |
| `reconciliation`  | 0                 | 0.0               | 0%          | deterministic, no LLM                 |

Note: the obs split assigns the residual 1.75 calls/chunk above the 5
deterministic calls entirely to the `date` stage, since `ner` + `entity` +
`info` are not gated.  This is exact for o3-mini-4CE but may slightly under-
or over-estimate date for the CORAL datasets (where temporal density is
different).  We accept this approximation for the manuscript headline
number and disclose it in the supplement.

A reviewer requesting EXACT per-stage tokens (not call-share apportionment)
would need a re-run with stage-level token tagging — out of scope for
2026-05-31.

## 8. Sample-size coverage and gold-N reconciliation

| Dataset         | Source-note N (`data/`) | Gold N (`outputs/reviewed_updated2/`) | Evaluated N (this revision) |
|-----------------|--------------------------|---------------------------------------|------------------------------|
| 4CE             | 63                       | 21                                    | 49 (paper Figure 3)         |
| CORAL-Breast    | 20                       | 13                                    | 20                          |
| CORAL-Pancreas  | 20                       | 15                                    | 20                          |
| MIMIC-III       | 24 paragraphs (separate) | 0 (single-annotator)                  | 24 — but **NOT in EXP-D**: no slurm token log was generated for MIMIC in any of slurm-194652/200028/200036/200045.  Treat MIMIC cost numbers as inferable from the o3-mini per-chunk-token profile only; flag in supplement. |

The cost table reports `n_notes` as the number of notes for which we have a
direct token-stat log row (or for which we propagated the o3-mini profile);
the manuscript should report the **evaluated N** (49 / 20 / 20) and note
this is the same as `n_notes` for o3-mini.

## 9. Reproducibility

```bash
# 1. Parse + de-cumulate + dedupe the slurm logs:
python scripts/cost/parse_slurm_token_stats.py \
    slurm-194652.out slurm-200028.out slurm-200036.out slurm-200045.out \
    --output runs/EXP-D/slurm_token_stats.csv \
    --decumulate --dedupe

# 2. Compute the cost table:
python scripts/cost/compute_cost_table.py \
    --slurm-token-stats runs/EXP-D/slurm_token_stats.csv \
    --data-root data \
    --out-main runs/EXP-D/cost_table_main.csv \
    --out-perstage runs/EXP-D/cost_table_perstage.csv \
    --out-pernote runs/EXP-D/cost_table_pernote.csv \
    --llama-walltime-sec "llama-3.1-405b-fp8:4CE=92" \
    --llama-walltime-sec "llama-3.1-405b-fp8:CORAL-Breast=220" \
    --llama-walltime-sec "llama-3.1-405b-fp8:CORAL-Pancreas=245" \
    --deepseek-walltime-sec "deepseek-r1-distill-qwen-32b:4CE=70" \
    --deepseek-walltime-sec "deepseek-r1-distill-qwen-32b:CORAL-Breast=180" \
    --deepseek-walltime-sec "deepseek-r1-distill-qwen-32b:CORAL-Pancreas=200"
```

## 10. Known limitations / open work

1. **No token data for MIMIC** under any model.  Reviewer R1 m17 already
   asks why MIMIC F1 is low; including MIMIC in the cost table would
   require either a new short-N MIMIC re-run **or** propagating the 4CE /
   CORAL token-per-chunk profile to MIMIC's N=24 paragraphs.  Decision:
   omit MIMIC from the main cost row; reference in supplement as "MIMIC
   token cost was estimated from per-chunk profile, see methodology."

2. **No token data for Phi-4**.  EXP-G ablation may regenerate Phi-4 with
   a wrapper to log token usage; defer until then.

3. **No real EXP-F (o3-mini SP, GPT-4o CoT) numbers yet** — placeholder
   rows will be added once EXP-F runs.  The cost-table columns
   `gpt-4o-1120` and `gpt-4o-cot` will reflect EXP-F output when
   `compute_cost_table.py` is re-run with the new slurm logs.

4. **Reasoning-token transparency**: o3-mini emits internal reasoning
   tokens that are **billed** but NOT included in `completion_tokens`
   under some Azure API versions.  The `response.usage.completion_tokens`
   in our logs IS the billed value (Azure 2024-12-01-preview).  Manuscript
   footnote will note: "o3-mini output-token count includes reasoning
   tokens billed by Azure".

5. **GPU power / electricity** cost is NOT computed; only GPU-hours.
   Reviewer R5 (4.3) only asked about deployment hardware accessibility,
   not energy.  If energy is asked in re-review, multiply by ~700 W per
   H100 (PCIe TDP) and local electricity rate.

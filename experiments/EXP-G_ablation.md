# EXP-G_ablation — SapBERT / SemChunk / Date / Step-4 reconciliation ablation

> **Covers**: R1 M8, R3 C5, R4 — "show that each CLINES component is necessary."
> **Strategy** (per RESPONSE_PLAN §1.5): 5 representative notes per dataset
> (not full datasets) to keep total SLURM cost ≤ ~6 h. Four single-component
> ablations + one "full pipeline" control, all on the same matched 5-note
> slice for a fair ΔF1 comparison (the existing `outputs/with_positions/`
> can't be reused because that aggregated output covers a different note set
> and lacks per-component switches — pre-flight finding §1.6).

---

## 1. 元数据

- **绝对日期**: 2026-05-25 (launch)
- **SLURM Job IDs**: TBD (recorded in `runs/EXP-G/logs/job_ids.txt` after `bash jobs/EXP-G_submit_all.sh`)
- **commit hash (launch)**: `95b3292d7934b7456996179be2fabd4f187192de`
- **branch**: `exp/EXP-G_ablation`
- **baseline**: i2b2 @ `8735bbb` (HEAD at branch-out)

## 2. 目的

Quantify the marginal F1 contribution of each of the four explicit
components in the CLINES four-step pipeline:

| Sub-ablation | Component disabled | Replacement / behavior |
|---|---|---|
| (a) `sapbert_off` | SapBERT/FAISS UMLS retrieval | placeholder `CODE = {"NORM_OFF\|\|<mention>": ["<mention>","NA"]}` — the LLM clean output is kept but never normalized to UMLS |
| (b) `semchunk_off` | `semchunk.chunkerify` semantic chunking | naive fixed-length `tiktoken.encode → decode` slicing at the same chunk_size (768) |
| (c) `date_off` | Entire Date module (`DateProcessor` worker) | skipped; downstream gets `DateData(basic_results=None, date_results=[])` |
| (d) `step4_off` | Step-4 reconciliation: tag-based dedup + alignment (`process_lists_based_on_list1` + per-tag `deduplication`) | replaced by positional concat with `_pad` to length of `clean_results`; unaligned / duplicate LLM rows preserved |

Each ablation runs with one flag set, all other components intact, on the
same 5-note slice as the "full" control.

## 3. Baseline

- **commit baseline**: i2b2 @ `8735bbb docs(revision): add response plan + revision artifacts for BMJ R1`
- **previous EXP**: none — this is a stand-alone ablation, not a continuation of EXP-A / EXP-B/C / EXP-D / EXP-E / EXP-F.
- **Matched control**: the `ABLATION=full` cell of this same experiment is the matched-sample 5-note baseline against which ΔF1 is computed (NOT the historical `outputs/with_positions/` runs — different note set, different code version).

## 4. Diff (vs baseline `8735bbb`)

**代码改动**:

- `llm_interface/llm_manager.py`
  - New `_fixed_length_chunker_factory(tokenizer, chunk_size)` — emits `text → list[str]` chunks by encoding to token ids and slicing at fixed size (no semantic boundaries).
  - `LLMManager.__init__` accepts `disable_semchunk=False`. When `True`, `self.chunker` uses the fixed-length factory instead of `semchunk.chunkerify`.
- `ehr_processing_pipeline/pipeline_coordinator.py`
  - `PipelineCoordinator.__init__` accepts `ablation_flags: dict`. Toggles routed to entity/info/date processors.
  - When `disable_sapbert`: `self.retriever = None`, UMLS dict + FAISS index load skipped.
  - When `disable_date`: `_process_parallel_with_executor` skips the Date worker entirely (2-thread pool instead of 3).
  - When `disable_step4_reconcile`: `_aggregate_results` skips `process_lists_based_on_list1`; uses positional `_pad` instead.
- `ehr_processing_pipeline/entity_processor.py`
  - `EntityProcessor.__init__` accepts `disable_sapbert`, `disable_step4_reconcile`.
  - `entity_linking()` writes placeholder `CODE` when SapBERT off.
  - `process_entities()` skips tag-based dedup when step4 off (uses `safe_deduplication_input` plain pass-through).
- `ehr_processing_pipeline/info_processor.py`
  - Same flag pair; placeholder `body_code` when SapBERT off; skip dedup when step4 off.
- `ehr_processing_pipeline/date_processor.py`
  - `disable_step4_reconcile` skips tag-based dedup inside `_process_initial_dates` / `_process_subsequent_dates`.
- `main.py`
  - Four new CLI flags: `--disable_sapbert / --disable_semchunk / --disable_date / --disable_step4_reconcile`.
  - One new flag `--note_id_list` for per-dataset 5-note subsampling.
  - Skips `shared_retriever` construction when SapBERT disabled.

**超参改动**: none vs paper baseline — `chunk_size=768`, `max_retries=1`, `schema=default`, `model_name=gpt4o` (resolved to `gpt-4o-1120` via `openai_provider.py n2n_dict`), `num_workers=2`. Only the four ablation flags change between cells.

**数据改动**: per-dataset 5-note subsampling via `runs/EXP-G/notes_lists/{4CE,coral_pdac,coral_breastca}.txt`. Selection criteria (mixed, per RESPONSE_PLAN §1.5 user guidance):
- mix of large notes (many entities, multi-chunk → tests semchunk + step4)
- mix of date-heavy notes (many dated rows in gold → tests date module)
- one smaller baseline note per dataset

| Dataset | Notes |
|---|---|
| 4CE | report06, KUMC_5, d30982c684512d4f0b6fd79836539d9ac, report03, BCH_1 |
| coral_pdac | 9, 14, 1, 10, 6 |
| coral_breastca | 23, 34, 36, 21, 24 |

**Scoping note**: original brief asked for "4CE / CORAL-pancreas / CORAL-breast / MIMIC / i2b2" (5 datasets). The repo at HEAD `8735bbb` does **not** ship gold standards for MIMIC or i2b2 under `outputs/reviewed_updated2/` (only `4CE`, `coral_annotated_pdac`, `coral_annotated_breastca` are present). EXP-A IAA also drops MIMIC for the same reason. → EXP-G covers the **3 datasets with usable gold**. If MIMIC / i2b2 gold becomes available later, the same `--note_id_list` machinery can extend the ablation; no code change needed.

## 5. 复现命令

```bash
git checkout exp/EXP-G_ablation
cd "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data"
source /home/zoy043/miniconda3/etc/profile.d/conda.sh
conda activate sglang

export OPENAIKEY="<HMS Azure OpenAI key from SharePoint>"
export OPENAIENDPOINT="https://azure-ai.hms.edu"
export MODEL_NAME="gpt4o"

# (1) Submit all 5×3 = 15 sbatch jobs (each ≤30min, gpu_quad backfill-friendly)
HOLD_ON_FAIL=1 bash jobs/EXP-G_submit_all.sh
# Ledger written to runs/EXP-G/logs/job_ids.txt

# (2) Monitor each job (sacct + .err/.out grep, dual-track per CLAUDE.md §10)
while read -r abl ds jobid; do
    bash scripts/slurm_monitor.sh "${jobid}" \
        "runs/EXP-G/logs/slurm-${jobid}.err" \
        "runs/EXP-G/logs/slurm-${jobid}.out" &
done < runs/EXP-G/logs/job_ids.txt
wait

# (3) After all jobs COMPLETED, evaluate per (ablation, dataset) cell.
#     Builds symlink trees that bridge our marker naming → eval_predictions.py
#     naming, then computes precision/recall/F1 on mention / assertion_status /
#     value / unit / code columns.
bash jobs/EXP-G_eval_all.sh
# Metrics: runs/EXP-G/eval/<ablation>/<dataset>/metrics.json
```

Single-cell rerun (e.g. just `sapbert_off` on `4CE`):

```bash
ABLATION=sapbert_off DATASET=4CE MODEL_NAME=gpt4o \
    HOLD_ON_FAIL=1 sbatch jobs/EXP-G_run.sh
```

## 6. 配置快照

- **Config source**: `jobs/EXP-G_run.sh` (parametrized sbatch).
- **关键超参 inline copy (Plan C, 2026-05-26)**:

```bash
# jobs/EXP-G_run.sh inlined defaults
MODEL_NAME=gpt4o                   # → gpt-4o-1120 deployment via openai_provider.n2n_dict
SCHEMA=default
MAX_RETRIES=1
CHUNK_SIZE=768                     # same as paper baseline
NUM_WORKERS=2
# walltime: 04:00:00  (CPU partition; SapBERT auto-falls-back to CPU
#                     via use_gpu = use_gpu AND torch.cuda.is_available())
# partition: short    (12h max, ~10k CPUs, immediate scheduling)
# mem: 96G            (17.4GB SapBERT cache + model + workspace headroom)
# -c 8                (more threads for CPU FAISS / tokenizer / sapbert inference)
# gres: <none>        (no GPU)
# OPENAIENDPOINT: https://azure-ai.hms.edu (HMS Azure proxy)
```

### 6.1 Plan history

- **Plan A** (2026-05-26 morning, jobids 41458272-97): 3 notes per dataset
  × 30min walltime × gpu_quad. **TIMED OUT all 15**: SapBERT init + cache
  load ate 45min, leaving < zero budget for 3 notes × ~30min API calls.
- **Plan B** (2026-05-26 ~07:00, jobids 41511335-49): 2 notes per dataset
  × 120min walltime × gpu_quad. **Never started**: 15 jobs PENDING for ~3h
  with reason "Priority" — gpu_quad queue saturated. Cancelled to free
  slots + repivot.
- **Plan C** (current, 2026-05-26 ~11:14, jobids 41516590-604): same 2
  notes per dataset, but `-p short` CPU partition, 4h walltime, 8 cores,
  96G mem, no `--gres=gpu:1`. SapBERT's `.cuda()` calls are all gated by
  `self.use_gpu = use_gpu AND torch.cuda.is_available()` (see
  `llm_interface/retrieval/retriever_coordinator.py:21` +
  `embedding_service.py:22/42/57`), so on a CPU node it auto-falls-back
  cleanly. The pre-computed 17.4GB embedding cache at
  `./cache/dense_embed_{all,bodyloc}.pt` makes `embed_dictionary()` a
  cache hit (retriever_coordinator.py:75), so the GPU's only real
  advantage (fast `embed_term` over 5.7M UMLS terms) doesn't matter
  here. Net effect: dominant cost is GPT-4o API calls (~30min × 2 notes
  per job), CPU/GPU parity for the rest.

- `runs/EXP-G/snapshot/config_resolved.yaml`: `N/A: snapshot writer 未实现，见 EXPERIMENTS.md banner; config = jobs/EXP-G_run.sh @ launch commit (字段 1)`.

## 7. 数据 / 输入模型快照

- **Input notes** (5 representative per dataset):
  - `data/4CE/{report06,KUMC_5,d30982c684512d4f0b6fd79836539d9ac,report03,BCH_1}.txt`
  - `data/coral_annotated_pdac/{9,14,1,10,6}.txt`
  - `data/coral_annotated_breastca/{23,34,36,21,24}.txt`
- **Gold standard**: `outputs/reviewed_updated2/{4CE,coral_annotated_pdac,coral_annotated_breastca}/<note_id>_updated.csv` (same gold as EXP-B / EXP-F use).
- **UMLS dictionary** (only loaded when SapBERT enabled): symlinks created at runtime by sbatch → `/n/data1/hsph/biostat/celehs/lab/SHARE/From_Zongxin/language-into-clinical-data/{umls_dictionary.txt,umls_body_loc_dictionary.txt}` (5.7M-term + 410k-term, 2025-03-17 snapshot).
- **LLM**: `gpt-4o-1120` via HMS Azure proxy `https://azure-ai.hms.edu`. Key in `OPENAIKEY` env var, not in git.

---

## 8. 结果 (TBD)

Per (ablation, dataset, column) precision / recall / F1, mention-level
and code-level. Pulled from `runs/EXP-G/eval/<ablation>/<dataset>/metrics.json`.

Headline summary will be a table:

| Dataset | Column | Full | SapBERT off | ΔF1 | SemChunk off | ΔF1 | Date off | ΔF1 | Step4 off | ΔF1 |
|---|---|---|---|---|---|---|---|---|---|---|
| 4CE | mention | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

(Columns: mention, assertion_status, value, unit, code.)

## 9. vs baseline 对比 (TBD)

For each ablation × dataset × column, ΔF1 = F1(ablation) − F1(full).
Expected directions (priors):
- SapBERT off → `code` column F1 drops large (the entire normalization layer
  is bypassed); `mention` should be roughly unchanged (NER comes before
  retrieval).
- SemChunk off → mild F1 drop especially on long notes (entities split
  across naive boundaries).
- Date off → `begin_date`/`end_date`-related metrics zero; spillover to
  other columns small (date is a parallel branch).
- Step4 off → moderate F1 drop across all columns (duplicate / unaligned
  rows leak through; precision suffers most).

## 10. 分析 (TBD)

- Which component is most impactful?
- Are there dataset-specific patterns (e.g. CORAL has longer notes → semchunk matters more there)?
- Failure modes: which columns / rows degrade most under each ablation?
- Confounds: 5-note slice is small → bootstrap CI not meaningful; report point estimates with explicit caveat in W-26.

## 11. 结论 (TBD)

`TBD` (PASS / FAIL / INCONCLUSIVE).

## 12. 下一步 (TBD)

- Feed table into W-26 (Ablation Table) for Methods / Discussion.
- If one component shows near-zero impact, consider Discussion edit acknowledging it could be simplified.

## 13. Artifact pointers

- `runs/EXP-G/preds/<ablation>/<dataset>/EXP-G_<ablation>_<dataset>_<note_id>_default.csv` — raw per-note prediction CSV.
- `runs/EXP-G/eval/<ablation>/<dataset>/metrics.json` — eval_predictions output.
- `runs/EXP-G/eval/<ablation>/<dataset>/metrics_metrics.csv` — dataset-level metrics table.
- `runs/EXP-G/logs/EXP-G_<ablation>_<dataset>_run_report.jsonl` — per-note run report (token_usage, chunk_stats, module_stats) → also feeds **EXP-D cost table**.
- `runs/EXP-G/logs/EXP-G_<ablation>_<dataset>_errors.log` — error log per cell.
- `runs/EXP-G/logs/slurm-<jobid>.{out,err}` — SLURM stdout/stderr.
- `runs/EXP-G/logs/job_ids.txt` — ledger of (ablation, dataset, jobid).
- `runs/EXP-G/notes_lists/{4CE,coral_pdac,coral_breastca}.txt` — note-id allowlists.
- `runs/EXP-G/snapshot/config_resolved.yaml` — `N/A: snapshot writer 未实现，见 EXPERIMENTS.md banner; config 见字段 6 inline copy`.
- `runs/EXP-G/snapshot/git_info.txt` — `N/A: snapshot writer 未实现; git 信息见字段 1`.
- `runs/EXP-G/snapshot/env.txt` — `N/A: snapshot writer 未实现，无 fallback`.

---

## 更新日志

- 2026-05-25: launch — branch `exp/EXP-G_ablation` cut from i2b2 @ `8735bbb`. Code changes for 4 ablation flags + `--note_id_list` committed. sbatch templates + note_id_lists scaffolded. Submit pending OPENAIKEY env var.
- 2026-05-26 morning: Plan A submitted (15 jobs 41458272-97, 3 notes × 30min × gpu_quad). All 15 TIMED OUT — SapBERT init + cache load ate the 30min budget.
- 2026-05-26 ~07:00: `disable_step4_reconcile` ablation surfaced a `KeyError: 'CODE'` in `ehr_processing_pipeline/pipeline_coordinator.py:271` (step4_off skips entity_linking → no `'CODE'` key in clean_results). Fixed: added `disable_step4_reconcile` guard with `.get('CODE')` fallback. Plan B submitted (15 jobs 41511335-49, 2 notes × 120min × gpu_quad). Never started — gpu_quad queue saturated, all 15 PENDING with reason "Priority" for ~3h. Cancelled.
- 2026-05-26 ~11:14: Plan C submitted (15 jobs 41516590-604, 2 notes × 240min × **`-p short` CPU**, `-c 8`, 96G mem, no `--gres=gpu:1`). SapBERT auto-falls-back to CPU; 17.4GB pre-computed embedding cache makes `embed_dictionary()` a cache hit so the GPU's real advantage (fast embed of 5.7M UMLS terms) is moot here. Submitted with `HOLD_ON_FAIL=1` + dual-track watchdog (sacct + .err/.out grep) per CLAUDE.md §10.

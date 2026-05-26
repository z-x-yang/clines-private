# EXP-G2_ablation_gpt4omini

EXP-G ablation grid (5 ablations × 3 datasets) re-run with **gpt-4o-mini**
(`gpt-4o-mini-0718`) instead of gpt-4o-1120. Sister of EXP-G. Tests whether
the CLINES per-module contribution (the ablation ΔF1 pattern) generalizes
to a cheaper model — a robustness + cost-efficiency argument for the BMJ
revision (R5 cost concerns + reviewer interest in model-agnostic gains).

---

## 1. 元数据

- **EXP-ID**: EXP-G2
- **作战表 E#**: E7' (sister-of-EXP-G)
- **日期**: 2026-05-26
- **Branch**: `exp/EXP-G2_ablation_gpt4omini`
- **Base**: cut from `exp/EXP-G_ablation` @ `69d0a52` (the missing-CODE fix
  commit). Inherits the fixed pipeline + the matched 2-notes-per-dataset
  slice + CPU `short` partition strategy.
- **Job IDs**: 41548813-41548833 (15 jobs, gaps from interleaved submit)
- **Owner**: zongxin (main session)

## 2. 目的

EXP-G establishes per-module contribution on gpt-4o-1120. Reviewers (esp.
R5) question cost; a natural follow-up is "does the architecture still help
with a cheaper backbone, or is gpt-4o-1120 doing all the heavy lifting?"
EXP-G2 answers by replaying the identical ablation grid on gpt-4o-mini.

**Expected**: ablation ΔF1 pattern (SapBERT off → code F1 drops most,
step4_off → dedup degrades, etc.) should be directionally similar; absolute
F1 lower than gpt-4o-1120. If the ΔF1 pattern holds → architecture gains
are model-agnostic (strong claim). If it collapses → gains were
model-specific (reframe needed).

## 3. Baseline

- Direct predecessor: **EXP-G** (`experiments/EXP-G_ablation.md`), branch
  `exp/EXP-G_ablation`, base commit `69d0a52`.
- Same data slice: 4CE {KUMC_5, d30982c684512d4f0b6fd79836539d9ac},
  coral_pdac {14, 1}, coral_breastca {34, 36}.
- Same gold: `outputs/reviewed_updated2/`.
- Only difference vs EXP-G: `MODEL_NAME=gpt4omini` → `gpt-4o-mini-0718`
  deployment (via `openai_provider.n2n_dict`).

## 4. Diff (vs EXP-G)

- New `jobs/EXP-G2_run.sh` + `jobs/EXP-G2_submit_all.sh`: identical to
  EXP-G's except MODEL_NAME default = gpt4omini, MARKER = `EXP-G2_*`,
  OUTPUT_DIR = `runs/EXP-G2/preds/...`, LOG_DIR = `runs/EXP-G2/logs`,
  NOTE_ID_LIST = `runs/EXP-G2/notes_lists/...`, walltime 08:00:00 (vs
  EXP-G's 04:00:00 — coral_breastca cells ran 3h+ for gpt-4o; gpt-4o-mini
  retry behavior unknown so extra margin avoids a TIMEOUT round).
- Pipeline code is byte-identical to EXP-G @ 69d0a52 (incl. the
  result_aggregation missing-CODE fix).

## 5. 复现命令

```bash
git checkout exp/EXP-G2_ablation_gpt4omini
cd <project root or this worktree>
export OPENAIKEY="<HMS Azure key>"
export OPENAIENDPOINT="https://azure-ai.hms.edu"
# Submit 15 jobs (gpt-4o-mini, CPU short partition, HOLD_ON_FAIL opt-in)
HOLD_ON_FAIL=1 bash jobs/EXP-G2_submit_all.sh
# Ledger: runs/EXP-G2/logs/job_ids.txt
# Eval (after all COMPLETED) — same eval as EXP-G
```

## 6. 配置快照

```bash
MODEL_NAME=gpt4omini               # → gpt-4o-mini-0718 via openai_provider.n2n_dict
SCHEMA=default
MAX_RETRIES=1
CHUNK_SIZE=768
# partition: short | walltime: 08:00:00 | mem: 96G | -c 8 | no GPU
# OPENAIENDPOINT: https://azure-ai.hms.edu
```

## 7. 数据 / 输入模型快照

- Same notes/gold as EXP-G (字段 3).
- LLM: `gpt-4o-mini-0718` via HMS Azure proxy. Key in OPENAIKEY env, not git.
- UMLS dict + 17.4GB SapBERT embed cache: symlinked at runtime (cache is a
  hit so no re-embed).

## 8. 结果 (TBD)

Per (ablation, dataset, column) F1, to be backfilled after all 15 jobs
COMPLETE. Same headline table shape as EXP-G §8.

## 9. vs baseline 对比 (TBD)

Two comparisons:
1. **vs EXP-G (gpt-4o-1120)**: same-ablation ΔF1(model) = does mini lose
   a lot of absolute F1?
2. **within-EXP-G2 ablation ΔF1**: does the per-module contribution
   pattern survive on the cheaper model?

## 10. 分析 (TBD)

## 11. 结论 (TBD)

## 12. 下一步 (TBD)

## 13. Artifact pointers

- Predictions: `runs/EXP-G2/preds/<ablation>/<dataset>/*.csv`
- Logs: `runs/EXP-G2/logs/slurm-<jobid>.{out,err}` + `*_run_report.jsonl`
- Ledger: `runs/EXP-G2/logs/job_ids.txt`
- Eval (post-process): `runs/EXP-G2/eval/...`

## 更新日志

- 2026-05-26: launch — branch cut from EXP-G `69d0a52` (missing-CODE fix).
  15 jobs (41548813-833) submitted to `-p short` CPU with MODEL_NAME=
  gpt4omini, HOLD_ON_FAIL=1, 8h walltime. Watchdog (sacct+grep dual-track)
  armed. User request: "EXP-G 这里用 gpt-4o-mini 也跑一遍" (2026-05-26).

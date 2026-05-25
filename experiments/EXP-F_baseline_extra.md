# EXP-F: Baseline 补强 — o3-mini single-prompt + GPT-4o CoT single-call

## 1. 元数据

- **日期**: 2026-05-25
- **SLURM Job IDs**: 待 sbatch 时填入(每个 (model, dataset) 一个 job)
- **Launch commit hash**: `<COMMIT_HASH>` (实验跑前在 launch commit 处取 `git rev-parse HEAD`)
- **Branch**: `exp/EXP-F_baseline_extra`
- **Base branch**: `i2b2` @ commit `8735bbb` (`docs(revision): add response plan + revision artifacts for BMJ R1`)

## 2. 目的

回答 Reviewer 5 Major Action Required A1(及 R1 M7):**CLINES 的性能提升来自其 4-step + retrieval 架构,而不是 base model 或 prompt engineering**。补两个 single-call baseline:

1. **o3-mini single-prompt**: 用 o3-mini-0131(reasoning model)+ 单 prompt 一次抽出 mention/code/assertion/value/unit,不走 CLINES 4-step pipeline。
2. **GPT-4o CoT single-call**: 用 gpt-4o-1120 + chain-of-thought instruction 单 prompt 抽全部字段,**不分 4-step**。

R5 措辞:"include single-prompt baselines (e.g., o3-mini, GPT-4o with CoT) on the same datasets, or substantially reframe the central contribution claim." 不补就要彻底重写 Abstract 主张。

## 3. Baseline

- **代码 base**: i2b2 @ 8735bbb(无前序 EXP)
- **数据 base**: 同主结果使用的 gold(`outputs/reviewed_updated2/`)和 prediction 评估脚本(`scripts/eval_predictions.py`)
- **比较对象(CLINES main result)**: `outputs/evaluation_results_0904/gpt4_eval_*.json` 的 4-step CLINES + gpt-4o-1120 + o3mini-medium 评估

## 4. Diff(vs baseline / 原 CLINES pipeline)

- **代码改动**:
  - 新增 `scripts/baselines/single_call_baseline.py`(self-contained,不调用 CLINES `pipeline_coordinator`)
  - 新增 `jobs/EXP-F_baseline.sh`(sbatch 入口,支持 `MODEL`/`MODE`/`DATASETS`/`AGENT_LABEL` 通过 env var 传入)
  - 新增 `scripts/slurm_failure_hold.sh`(template 复制自 `~/.claude/templates/`,per §7)
- **超参 / 设计选择**(故意保持简洁,per RESPONSE_PLAN §1.5 "不过度优化"):
  - **保留 chunking**: semchunk + 768 tokens + **CLINES 同款 post-merge 规则**(`if len(prev)<200 or len(item)<300: prev += item`,见 `pipeline_coordinator.py:499-504`)。两边 chunk 边界 / per-chunk size / API call 数才可比。
  - **单 prompt 内合并 4-step**: mention + code + assertion + value + unit + **begin_date/end_date** 全在一个 user message 里出 JSON(对比 CLINES 的 entity / info / status / date 4 个 prompt + 11 个 step 实例)。
  - **CoT 版本**:在 single-prompt 基础上 prepend"think step by step inside `<reasoning>` tags then output JSON inside `<answer>` tags"。**不给 task-specific 推理脚手架**(那样就变成 task decomp,失去 baseline 意义)。**不给 few-shot**(除了格式描述)。
  - **o3-mini effort=medium**(default),temperature 不可设。
  - **gpt-4o-1120 temperature=0.2**(near-deterministic 评估,不引入随机噪声)。
  - **不跑多 seed**(reviewer 未要求,1 seed 也能给答案;避免 API budget 翻倍)。
- **数据改动**: 无。复用 `data/` 原文 + `outputs/reviewed_updated2/` gold。

## 5. 复现命令

**先决条件**:user 必须先把 `OPENAIKEY` 设到 shell env(从 SharePoint 拿 — `~/.claude/projects/.../memory/hms-api-status.md`)。脚本会用 `sbatch --export=ALL` 把它转发到 compute node。

```bash
# 在主仓库 checkout EXP 分支(或者 cd 到 worktree;launcher 自动从自身位置推导 PROJECT_ROOT)
cd /n/data1/hsph/biostat/celehs/lab/zoy043/My\ works/longwood_backup/LLM_Info_Extract/language-into-clinical-data
git checkout exp/EXP-F_baseline_extra   # 或 git fetch + checkout

# 必须设置 HMS Azure key(SharePoint 获取)
export OPENAIKEY="<from SharePoint>"
export OPENAIENDPOINT="https://azure-ai.hms.edu"   # optional, default 同此

# 一键提交 6 个 job(2 models × 3 datasets)
# Launcher 会自动从脚本位置推导 PROJECT_ROOT(无论在主仓库还是 worktree)
bash jobs/EXP-F_launch_all.sh

# 监控(每个 job 一个 monitor;或合并)
for jid in $(awk -F'|' '{print $1}' runs/EXP-F/job_dispatch.log); do
    out_log=$(grep "^$jid|" runs/EXP-F/job_dispatch.log | cut -d'|' -f4)
    err_log=$(grep "^$jid|" runs/EXP-F/job_dispatch.log | cut -d'|' -f5)
    bash ~/.claude/templates/slurm_monitor.sh $jid "$err_log" "$out_log" &
done

# 所有 job COMPLETED 后做 eval
bash scripts/baselines/run_eval.sh    # 默认 AGENTS=o3mini_sp,gpt4o_cot
```

**手动版**(如果不想用 launcher):

```bash
PROJECT_ROOT=$(pwd)
CONDA_PY="/home/zoy043/miniconda3/envs/sglang/bin/python"   # per memory `clines-env-setup.md`

for DS in 4CE coral_annotated_pdac coral_annotated_breastca; do
  sbatch --export=ALL,\
MODEL=o3-mini-0131,MODE=single,DATASETS=$DS,AGENT_LABEL=o3mini_sp,\
PROJECT_ROOT=$PROJECT_ROOT,OUTPUT_DIR=$PROJECT_ROOT/runs/EXP-F/o3mini_sp/$DS,\
CONDA_PYTHON=$CONDA_PY,HOLD_ON_FAIL=1 \
    jobs/EXP-F_baseline.sh
done
for DS in 4CE coral_annotated_pdac coral_annotated_breastca; do
  sbatch --export=ALL,\
MODEL=gpt-4o-1120,MODE=cot,DATASETS=$DS,AGENT_LABEL=gpt4o_cot,\
PROJECT_ROOT=$PROJECT_ROOT,OUTPUT_DIR=$PROJECT_ROOT/runs/EXP-F/gpt4o_cot/$DS,\
CONDA_PYTHON=$CONDA_PY,HOLD_ON_FAIL=1 \
    jobs/EXP-F_baseline.sh
done
```

## 6. 配置快照

**模型 & API**:
- `o3-mini-0131`: api_version=`2024-12-01-preview`, reasoning_effort=`medium`, max_completion_tokens=16384
- `gpt-4o-1120`: api_version=`2025-04-01-preview`, temperature=0.2, max_tokens=4096

**Chunking**(**与 CLINES 完全一致** — 这是公平比较的硬约束):
- backbone: `semchunk` + tiktoken `cl100k_base`(`encoding_for_model("gpt-4")`)
- chunk_size_tokens: 768
- **post-merge rule**(mirrors `pipeline_coordinator.py:499-504`):`if len(prev) < 200 or len(item) < 300: prev += item; else: chunks.append(item)`。两个 baseline 都要应用,否则跟 CLINES 的 chunk 边界 / per-chunk token / API call 数都不可比。

**Retry policy**(per CLAUDE.md §2 fail-fast,explicit + bounded):
- API transient(rate limit / 5xx / timeout): max 3 retries,exponential backoff(2s → 4s → 8s),non-transient(auth / model not found / 4xx)立即 raise
- Chunk parse failure(JSON 不符合 contract):max 2 重试 same chunk;超过则**整 note RAISE**(fail-fast,不再静默 swallow 然后 emit 部分 prediction)
- 失败时 SLURM HOLD_ON_FAIL=1 会保留节点;user `ssh node + tmux a -t debug_<jobid>` 进去用 `--start-index <i>` 续跑(`i` 是 .err log 里报的 index)

**Parser 严格性**(per CLAUDE.md §2,no hidden fallback):
- `single` mode:response 必须 strip 后 `[...]`;code fences / 周围 prose / `{"entities":[...]}` wrapper 全部 reject
- `cot` mode:必须有 `<answer>...</answer>` tags;tag 内必须 `[...]`;无 fallback 到裸 bracket / fence
- demjson3 fallback **仅**为容忍 trailing comma 等 cosmetic 问题保留(json 失败时显式 log,不静默)

**Prompt 关键内容**(完整内联,防 `single_call_baseline.py` 后续被改):

```
# SINGLE_PROMPT_TEMPLATE (full in scripts/baselines/single_call_baseline.py):
# - "Extract structured clinical information from the medical note chunk below."
# - 要求 JSON array(每项 keys 都不能 omit,用 null 替代):
#   mention, code (CUI||name), assertion_status, value, unit, begin_date, end_date
# - assertion_status 枚举 7 类:Present / Absent / Possible / Conditional /
#   Hypothetical / Notassociated / Historical
# - begin_date / end_date: YYYY[-MM[-DD]] format if explicit, else null
# - 抽取 scope:diseases / symptoms / procedures / medications / labs / allergies /
#   findings / devices;panel test 拆分;否定 finding extract + assertion=Absent
# - 不抽取:person names, generic locations, 独立 values/units
# - "Output ONLY the JSON array. No prose, no markdown fences. First char '[', last ']'."

# COT_PROMPT_TEMPLATE (full in scripts/baselines/single_call_baseline.py):
# - "First think step by step inside <reasoning>; then output JSON inside <answer>"
# - 同 single-prompt 字段定义
# - 同抽取/不抽取 scope
```

## 7. 数据 / 输入快照

- **数据 manifest**:
  - `/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data/data/4CE/*.txt` (49 raw, 21 有 gold)
  - `.../data/coral_annotated_pdac/*.txt` (20 raw, 15 有 gold)
  - `.../data/coral_annotated_breastca/*.txt` (20 raw, 13 有 gold)
- **Gold manifest**:
  - `.../outputs/reviewed_updated2/{4CE,coral_annotated_pdac,coral_annotated_breastca}/*_updated.csv`
- **总 inference 工作量**:
  - notes per baseline: 21 + 15 + 13 = **49 notes**
  - 总 chunks 估算(平均 ~10K 字符 / 768 token ≈ 1.5K char per chunk → ~7 chunks/note)≈ 350 chunks per baseline
  - 总 API calls(假设 ~1 retry rate)≈ 400 per baseline,800 total
- **关键 caveat**:
  - **本次 EXP-F 仅覆盖 3 个数据集**(4CE / CORAL-pancreas / CORAL-breast)。原 paper 的 4 个数据集中 **MIMIC-III gold 在 `outputs/reviewed_updated2/` 不在**(也未在 `outputs/evaluation_results_0904/` 的 metrics keys 中)。EXP-F 任务 prompt 中"5 datasets"包含 i2b2 与 MIMIC,但 i2b2 是 code-mapping 后处理(`outputs/gpt4o_output_0526_i2b2/`),不是独立 eval dataset。如 user 有 MIMIC gold 的实际路径,可补跑(扩展 `DATASETS` env var 即可,代码不需要改)。
  - 不跑多 seed(per §4)。

## 8. 结果

**TBD** — 等所有 sbatch job COMPLETED 后回填:

| Dataset | Model / Mode | Mention F1 | Code F1 | Assertion F1 | Value F1 | Unit F1 |
|---|---|---|---|---|---|---|
| 4CE | o3-mini single-prompt | TBD | TBD | TBD | TBD | TBD |
| 4CE | gpt-4o CoT single-call | TBD | TBD | TBD | TBD | TBD |
| CORAL-P | o3-mini single-prompt | TBD | TBD | TBD | TBD | TBD |
| CORAL-P | gpt-4o CoT single-call | TBD | TBD | TBD | TBD | TBD |
| CORAL-B | o3-mini single-prompt | TBD | TBD | TBD | TBD | TBD |
| CORAL-B | gpt-4o CoT single-call | TBD | TBD | TBD | TBD | TBD |

**Token usage / Latency / API \$**(供 EXP-D 用):

| Model | Total notes | Total chunks | Total prompt tokens | Total completion tokens | Wall (s) | Est. API \$ |
|---|---|---|---|---|---|---|
| o3-mini-0131 (sp) | TBD | TBD | TBD | TBD | TBD | TBD |
| gpt-4o-1120 (cot) | TBD | TBD | TBD | TBD | TBD | TBD |

## 9. vs baseline 对比

**TBD** — 跑完后填,对照 `outputs/evaluation_results_0904/gpt4_eval_*.json` 的 CLINES 主结果(4-step + gpt-4o):

```
ΔF1 (mention) = CLINES_main - single_baseline
```

预期方向:CLINES 主结果在 mention/code F1 上**应该明显高于** single-call baseline(否则架构论点垮);assertion 可能差距小(单 prompt 也能学到分类)。

## 10. 分析

**TBD** — 等结果回填。关注点:

- Parse error 率(JSON 出错频率)— 高 parse error 会说明 single-prompt 对复杂任务"硬塞 JSON"的脆性,但也是公平比较(reviewer 本就质疑 CLINES 4-step 是 over-engineering)。
- o3-mini reasoning vs gpt-4o CoT 的差异:reasoning model 是否在 single-prompt 下也能逼近 CLINES?如果是,论点要小心 reframe。
- Chunk 边界 entity 漏抽率(出现在 chunk overlap 区域的 entity):比较两个 baseline 是否系统性丢失。

## 11. 结论

**TBD**(`PASS` / `FAIL` / `INCONCLUSIVE` + 一句话)

## 12. 下一步

**EXP-B** 跑完后,将 EXP-F 两个新 baseline 列纳入 bootstrap CI + permutation test,出最终 Figure 3 增强版。

如果发现:
- baseline F1 显著低于 CLINES → 直接回应 R5 A1,不需要 reframe contribution
- baseline F1 接近 CLINES → 需要在 Discussion 强调 CLINES 的其他价值(可解释性、可分步审计、cost trade-off — 见 EXP-D)

## 13. Artifact pointers

- **Predictions**(per model × dataset):
  - `runs/EXP-F/o3mini_sp/{4CE,coral_annotated_pdac,coral_annotated_breastca}/*_with_positions.csv`
  - `runs/EXP-F/gpt4o_cot/{4CE,coral_annotated_pdac,coral_annotated_breastca}/*_with_positions.csv`
- **Token usage / latency**:
  - `runs/EXP-F/{o3mini_sp,gpt4o_cot}/{<dataset>}/usage.jsonl`(per-note)
  - `runs/EXP-F/{o3mini_sp,gpt4o_cot}/{<dataset>}/run_summary.json`(per-run)
- **Evaluation**(post-process):
  - `runs/EXP-F/{o3mini_sp,gpt4o_cot}/eval/results.json` + `*_metrics.csv` + `*_error_cases.csv`
- **SLURM logs**: `logs/slurm/EXP-F_baseline_<jobid>.{out,err}`
- **Snapshot**: 未实现(per EXPERIMENTS.md banner — 本轮 revision 不引入新基建)。复现强度依赖:(a) 本 .md 字段 6 inline prompt + config copy(b) `exp/EXP-F_baseline_extra` git branch(push to remote)

## 更新日志

- 2026-05-25:实验骨架创建(字段 1-7 + 13 框架)。代码 + sbatch 模板就位,所有 offline smoke 测试通过(11/11)。Codex adversarial review 已跑(详见 commit message);根据 review feedback 修复了 8 个 substantive issue:(1) 加入 date 字段到 prompt 真正实现 4-step collapse;(2) chunk parse failure 改为 fail-fast raise(不再 silent partial output);(3) 移除 parser 隐式 fallback(`{"entities":[...]}` wrapper / code fence / bare bracket);(4) 空 prediction 用 schema-complete empty DataFrame;(5) chunking 加 CLINES 同款 post-merge(`<200/<300` 规则);(6) span localization 加 used-span tracking 处理 repeated mentions;(7) per-chunk token usage 正确累计;(8) launcher 自动从脚本位置推导 PROJECT_ROOT 避免 worktree/main-repo 路径漂移。批量提交待 user 在 shell 设 `OPENAIKEY` 后 `bash jobs/EXP-F_launch_all.sh`。

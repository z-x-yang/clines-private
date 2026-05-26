# EXP-F: Baseline 补强 — o3-mini single-prompt + GPT-4o CoT single-call

## 1. 元数据

- **日期**: 2026-05-25
- **SLURM Job IDs**: 多轮提交(早期 round 因 API key 轮换 / parse 问题重提),完整 ledger 见 `runs/EXP-F/job_dispatch.log`。最终成功 round 的预测写入 `runs/EXP-F/<agent>/<dataset>/`(各目录的 `run_summary.json` 是该 round 的权威 token/cost 记录)。
- **Launch commit hash**: `80ecf305273f7aa9336749dda7e591856cdb7cfa` (sub-agent infrastructure commit;sbatch 跑的代码就是这个 hash 的 worktree state,branch HEAD 之后只会加元数据 commit / 回填字段 8-13)
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

回填于 2026-05-26(所有 6 个 (model,dataset) job COMPLETED 后 eval)。F1 来源:
`runs/EXP-F/{o3mini_sp,gpt4o_cot}/eval/results_metrics.csv`。**注意 4CE 数据是
在修复 `run_eval.sh` 自引用 symlink bug 后重跑得到的**(旧版 `find -mindepth 2
-maxdepth 2` 会把 `all/` 自身的 symlink 再匹配一遍 → `ln -sfn` 把 4CE 链接覆盖成
指向自己,导致 4CE 被静默从 eval 中漏掉;修复 = `rm -rf all/` 后重建 + `-path prune`)。

| Dataset | Model / Mode | Mention F1 | Code F1 | Assertion F1 | Value F1 | Unit F1 |
|---|---|---|---|---|---|---|
| 4CE | o3-mini single-prompt | 0.6731 | 0.5005 | 0.6498 | 0.6587 | 0.4419 |
| 4CE | gpt-4o CoT single-call | 0.4794 | 0.3976 | 0.5179 | 0.6760 | 0.6082 |
| CORAL-P | o3-mini single-prompt | 0.6771 | 0.4311 | 0.6441 | 0.7496 | 0.5562 |
| CORAL-P | gpt-4o CoT single-call | 0.5467 | 0.3407 | 0.5338 | 0.7813 | 0.7285 |
| CORAL-B | o3-mini single-prompt | 0.6586 | 0.3633 | 0.6044 | 0.6700 | 0.6462 |
| CORAL-B | gpt-4o CoT single-call | 0.4819 | 0.2745 | 0.4502 | 0.5730 | 0.5836 |

**Token usage / Latency / API \$**(供 EXP-D / Figure 5 cost panel 用)。汇总自 6 个
`runs/EXP-F/<agent>/<dataset>/run_summary.json`(3 dataset 求和):

| Model | Total notes | API calls | Prompt tokens | Completion tokens | Wall (s) | Est. API \$ |
|---|---|---|---|---|---|---|
| o3-mini-0131 (sp) | 49 | 296 | 276,012 | 2,119,484 | 13,601 | \$9.63 |
| gpt-4o-1120 (cot) | 49 | 298 | 251,985 | 530,258 | 8,711 | \$5.93 |

**Cost 假设(锁定,Figure 5 / EXP-D 必须沿用)**: o3-mini-0131 = \$1.10/1M input +
\$4.40/1M output;gpt-4o-1120 = \$2.50/1M input + \$10.00/1M output。
- o3-mini 烧了 **2.12M completion tokens**(gpt-4o-cot 的 **4×**),因为 reasoning
  model 的 reasoning tokens 计入 completion → 单 baseline 成本反而最高,且 wall time
  也 ~1.56× gpt-4o(13.6k vs 8.7k s)。这是 EXP-D "reasoning model 又贵又不如 CLINES
  架构" 的核心数据点。

## 9. vs baseline 对比

**可比列的不对称(重要)**: 主结果 eval(`gpt4_eval_*_metrics.csv`)的列是
`code / assertion_status / begin_date / end_date / value / unit`(**无 mention**);
EXP-F baseline eval 的列是 `mention / code / assertion_status / value / unit`
(**无 date**)。两边都有的可比列 = **code / assertion / value / unit**。mention 只在
baseline 侧、date 只在主结果侧,不参与 ΔF1。

**⚠ 主结果参照系待你确认**: `outputs/evaluation_results_0904/` 下有 **3 个
gpt4_eval 时间戳,数值显著分歧**,不是同 config 的重跑:

| timestamp | 4CE code F1 | coral_pdac code F1 | 4CE code TP | 备注 |
|---|---|---|---|---|
| 150537 | 0.7591 | 0.7122 | 849 | 最低,本节用作**保守下界** |
| 154356 | 0.8966 | 0.8467 | 1118 | 高 |
| 160641 | 0.8737 | 0.8482 | 4360 | 高,但 TP 量级差 4×(gold 匹配域不同?) |

我**不擅自认定**哪个是 paper 的 canonical 主结果(选错会误报架构优势量级)。下表用
**最保守的 150537** 做对比 —— 即使对最弱的主结果候选,baseline 也明显落后;换成
154356/160641 则差距更大。**最终 rebuttal 里报的 ΔF1 数值取决于你确认用哪个时间戳。**

**ΔF1 = CLINES_main(150537) − single-call baseline**(可比列):

| Dataset | Col | CLINES(150537) | o3-mini sp | Δ vs o3mini | gpt-4o cot | Δ vs gpt4o |
|---|---|---|---|---|---|---|
| 4CE | **code** | 0.7591 | 0.5005 | **+0.259** | 0.3976 | **+0.362** |
| 4CE | assertion | 0.8282 | 0.6498 | +0.178 | 0.5179 | +0.310 |
| 4CE | value | 0.6032 | 0.6587 | −0.056 | 0.6760 | −0.073 |
| 4CE | unit | 0.6338 | 0.4419 | +0.192 | 0.6082 | +0.026 |
| CORAL-P | **code** | 0.7122 | 0.4311 | **+0.281** | 0.3407 | **+0.372** |
| CORAL-P | assertion | 0.8202 | 0.6441 | +0.176 | 0.5338 | +0.286 |
| CORAL-P | value | 0.8349 | 0.7496 | +0.085 | 0.7813 | +0.054 |
| CORAL-P | unit | 0.7972 | 0.5562 | +0.241 | 0.7285 | +0.069 |
| CORAL-B | **code** | 0.6513 | 0.3633 | **+0.288** | 0.2745 | **+0.377** |
| CORAL-B | assertion | 0.7470 | 0.6044 | +0.143 | 0.4502 | +0.297 |
| CORAL-B | value | 0.6930 | 0.6700 | +0.023 | 0.5730 | +0.120 |
| CORAL-B | unit | 0.7448 | 0.6462 | +0.099 | 0.5836 | +0.161 |

## 10. 分析

**核心发现:架构优势集中在 code(UMLS linking),不在 value/unit。** 这恰好是回应
R5 A1 最有力的形态 —— CLINES 的 4-step + SapBERT retrieval 的增益落在**依赖实体链接的
指标**上,而不是"任何 LLM 单 prompt 都能做"的字段。

1. **code F1 是分水岭**: 对每个数据集,CLINES 主结果(即便用最保守的 150537)都比
   两个 baseline 高 **+0.26 ~ +0.38**。换 154356/160641 差距扩大到 +0.35~+0.50。
   single-prompt 让 LLM"自己报 CUI"必然弱 —— 它没有 SapBERT 的 dense retrieval over
   UMLS,只能凭参数化记忆猜 code,precision 尚可但 recall 崩(o3mini code recall
   0.31~0.42,gpt4o 0.20~0.29 vs CLINES 0.67~0.77)。**这是架构论点的硬证据。**

2. **value/unit 差距小甚至反超**: 4CE value 上两个 baseline 都**略高于** CLINES
   主结果(o3mini +0.056, gpt4o +0.073)。说明单 prompt 抽数值/单位本就够用 ——
   架构在这里不带来增益,诚实写进 Discussion 反而增强可信度(不是 oversell 全面碾压)。

3. **reasoning model(o3-mini)没能逼近 CLINES**: o3-mini 在 code F1 上(0.36~0.50)
   仍远低于 CLINES,且**烧了 4× completion tokens、1.56× wall time、总成本最高**
   (\$9.63 vs gpt4o-cot \$5.93)。即"用更强更贵的 reasoning model + 单 prompt"也补不上
   架构缺口 —— 直接堵住 R5"是不是 base model 在起作用"的质疑。

4. **mention F1**(仅 baseline 侧有): o3mini 0.66~0.68 > gpt4o-cot 0.48~0.55。
   CoT 的 `<reasoning>` 段似乎让 gpt-4o 更"挑剔"少抽(recall 0.33~0.39),抽得少则
   下游 code/assertion 的分母也小。主结果无 mention 列,无法直接对比,但 baseline 的
   mention recall(0.34~0.52)本身就低,佐证单 prompt 在召回上的天花板。

**Caveat**: 每数据集 notes 少(13~21),F1 的 CI 较宽;EXP-B bootstrap 会给出
显著性。但 code F1 的 gap 量级(>0.25)远大于这个样本量下的噪声,方向稳健。

## 11. 结论

**PASS**(待你确认主结果参照系后定稿数值)。两个 single-call baseline(o3-mini reasoning
单 prompt + gpt-4o CoT 单 call)在 **code F1 上一致地、显著地低于 CLINES 4-step**
(每数据集 +0.26~+0.38,对最保守的主结果候选),且更强/更贵的 reasoning model 也补不上
缺口 —— **直接支撑 R5 A1:性能增益来自 4-step + retrieval 架构,不是 base model 或
prompt engineering**,无需 reframe Abstract 主张。诚实边界:value/unit 上架构无增益
(单 prompt 够用),应写进 Discussion。

**唯一 open item**: §9 的 3 个 gpt4_eval 时间戳需你确认 canonical 那个,以锁定 rebuttal
里报的确切 ΔF1(方向与 PASS 结论不受影响)。

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
- **Evaluation**(post-process,**2026-05-26 重跑后含 4CE**):
  - `runs/EXP-F/{o3mini_sp,gpt4o_cot}/eval/results.json` + `*_metrics.csv` + `*_error_cases.csv`
- **Eval harness fix**: `scripts/baselines/run_eval.sh` 的自引用 symlink bug 已在源头修复
  (`rm -rf all/` + `-path "$flat_dir/*" -prune`),否则 4CE 会被静默漏掉(见 §8 顶注)。
- **CLINES 主结果参照**(§9 对比用): `outputs/evaluation_results_0904/gpt4_eval_20250904_{150537,154356,160641}_metrics.csv`(3 个时间戳数值分歧,canonical 待确认)。
- **SLURM logs**: `logs/slurm/EXP-F_baseline_<jobid>.{out,err}`
- **Snapshot**: 未实现(per EXPERIMENTS.md banner — 本轮 revision 不引入新基建)。复现强度依赖:(a) 本 .md 字段 6 inline prompt + config copy(b) `exp/EXP-F_baseline_extra` git branch(push to remote)

## 更新日志

- 2026-05-25:实验骨架创建(字段 1-7 + 13 框架)。代码 + sbatch 模板就位,所有 offline smoke 测试通过(11/11)。Codex adversarial review 已跑(详见 commit message);根据 review feedback 修复了 8 个 substantive issue:(1) 加入 date 字段到 prompt 真正实现 4-step collapse;(2) chunk parse failure 改为 fail-fast raise(不再 silent partial output);(3) 移除 parser 隐式 fallback(`{"entities":[...]}` wrapper / code fence / bare bracket);(4) 空 prediction 用 schema-complete empty DataFrame;(5) chunking 加 CLINES 同款 post-merge(`<200/<300` 规则);(6) span localization 加 used-span tracking 处理 repeated mentions;(7) per-chunk token usage 正确累计;(8) launcher 自动从脚本位置推导 PROJECT_ROOT 避免 worktree/main-repo 路径漂移。批量提交待 user 在 shell 设 `OPENAIKEY` 后 `bash jobs/EXP-F_launch_all.sh`。
- 2026-05-26:**所有 6 个 (model,dataset) job COMPLETED,eval 完成,回填字段 8-11**(PASS,待确认主结果参照系)。期间救援两件事:(a) sglang env 的 scipy/numpy ABI 冲突 → 固定 `scipy==1.11.4`;(b) `run_eval.sh` 自引用 symlink bug 导致 o3mini_sp 的 4CE 被静默漏掉 → 源头修复(`rm -rf all/` + `-path prune`)并重跑得到完整 4CE 指标。核心结论:两个 single-call baseline 在 **code F1 上比 CLINES 4-step 低 +0.26~+0.38**(对最保守主结果候选),reasoning model(o3-mini)也补不上且成本最高(\$9.63,4× completion tokens)→ 支撑 R5 A1 架构论点。`run_eval.sh` harness 改动待 codex review 后 commit。

# CLINES BMJ Major Revision — 实验索引

## 元数据

- **稿件号**：bmjdh-2026-000027
- **期刊**：BMJ Digital Health & AI
- **决定**：Major Revision
- **Revision 截止**：**2026-05-31**（原 2026-05-17，已 grant 延期）
- **Editor**：Dr. Chris Paton（Editor in Chief）
- **当前 working branch**：`i2b2`
- **Remote**：`git@github.com:hms-dbmi/language-into-clinical-data.git`

## 关键 Notion 入口

- [📋 审稿意见总结](https://www.notion.so/4ee9b509c7634a64a3a1d99aad91bb98) — 5 位 reviewer 共识 + 各 reviewer 详细意见
- [🗂️ 实验补强 & 写作改进作战表](https://www.notion.so/f44ef91e381e4db5bf1b3f2664032e9a) — **主作战图**（每个 E# 都有详细说明列）
- [🧪 实验补强 task tracker](https://www.notion.so/4ff308694f104f7b9cc021b732fc4d5e)
- [📨 提交 CLINES BMJ Major Revision (邮件状态)](https://www.notion.so/a7c0ef70309248e2b92bf745e887c3b0)
- [📨 原始审稿邮件备份](https://www.notion.so/176016172ebe4985bb056235219b59ef)

## 本轮实验策略（user 拍板，2026-05-13）

> **能不跑就不跑**：尽量复用现有 outputs（`outputs/reviewed_updated2/` gold + `outputs/with_positions/` 等已有 prediction），通过 bootstrap / 统计计算 / 后处理模拟得到 reviewer 想要的指标。**只有"新 baseline"和"无法从已有产物推出的 ablation"才跑新 LLM/GPU 实验**。

> **E9 (Relation Extraction)**：走方案 (b)，不评测；在 Methods/Limitations 里写明 "not evaluated in this study"，把 Supp 2.2 描述保留在 Supplement。**不立 EXP 项**。

## ⚠️ Reproducibility limitations

- **`runs/<EXP-ID>/snapshot/` 写入未实现**。半年后复现强度仅靠：(1) `experiments/<EXP-ID>_*.md` 字段 6 的 inline config copy；(2) `exp/<EXP-ID>_<short>` git branch（push to remote）上的 commit。**没有 byte-for-byte 同 ckpt 复现保证**；rerun 同分布结果可达。建议未来在 inference entrypoint（`main.py` / `run_inference.sh`）加一段约 10 行 bash：`git rev-parse HEAD > runs/<EXP>/snapshot/git_info.txt` / `pip freeze > runs/<EXP>/snapshot/env.txt` / 落 resolved CLI args。**本轮 revision 暂不引入此基建**（不与 deadline 抢工时）。
- ~~**HMS Azure OpenAI key 截至 2026-05-13 仍全失效**~~（已解除，见 2026-05-19 更新日志；详见 memory `hms-api-status`）。当前可用 deployment：`gpt-4o-1120` / `gpt-4o-mini-0718` / `gpt-4.1` 系列 / `o3-mini-0131` / `o4-mini-0416`。HMS proxy 要求**完整 deployment ID**，不接受 alias。

## 已有 Baseline（pre-revision，archive）

最全的全模型评估结果：`outputs/evaluation_results_0904/`（含 deepseek / gpt4o / o3mini-medium / llama3-405b 的 JSON + metrics CSV + PNG）。**已知缺口**：未包含 `coral_pdac/19_reviewed.csv`，后续如需补全在此说明。

| 模型 | 数据集 | Output 路径（O2 上） | 状态 |
|---|---|---|---|
| GPT-4o (`gpt-4o-1120`) | 4CE / CORAL-B / CORAL-P / MIMIC | `outputs/gpt4o_output/`, `outputs/with_positions/`, `outputs/gpt4o_output_0405_4/`(带 historical) | DONE |
| o3-mini-medium | 同上 | `outputs/o3mini_medium_output_0526/`（带 historical） | DONE |
| Deepseek (local sglang) | 同上 | `outputs/deepseek_output/` | DONE |
| Llama-3.1-405B (local sglang, 8×H100) | 同上 | `outputs/llama-405b-output{,1,2}/` | DONE |
| Phi-4 14B (GENIE) | matched-only | `outputs/Phi_4_output_0922/`, `outputs/with_positions_phi4/` | DONE |
| Clinical-MobileBERT / DistilBERT (i2b2-2010 fine-tune) | 4CE / CORAL-B / CORAL-P | `~/Works/ClinicalNER/{outputs,evaluations}/{mobilebert,distilbert}/`（O2 上**未确认是否已迁移**） | DONE-但要核实 |
| **Gold standard** | 全部 | `outputs/reviewed_updated2/`（不带 historical 的 assertion） | — |

Phi-4 vs GPT-4o（matched-only）对比报告：`docs/phi4_vs_gpt4o_evaluation.md`（GPT-4o 在所有四个数据集 mention/assertion/value/unit 全面胜出）。

GPT-4o 案例集：`reports/gpt4o_case_studies.md`。

## Revision 实验（E1-E9 → EXP-A..EXP-H）

| EXP-ID | E# | 名称 | 优先级 | 状态 | 新跑量 | 一句话结论 | 详情 |
|---|---|---|---|---|---|---|---|
| EXP-A | E1 | IAA Cohen's κ + F1-based agreement | P0 | **PASS** | 0 (Mo cross-annotation 已收齐 05-25) | entity-keep κ=0.40 / F1=0.81; assertion-kept κ=0.79. 低 entity-keep κ 提供 rebuttal 论据 (human 间 disagreement 本身 ~40%) | experiments/EXP-A_iaa_cohen_kappa.md |
| EXP-A2 | E1' | IAA improved (PABAK + fuzzy align + raw agreement) | P0 | **PASS** | 0 (同 A 数据,加算法层) | PABAK=0.46 (Cohen's paradox 解释 entity-keep κ low); fuzzy align 47 added rows 0/47 pairs (annotators 独立扩展不重叠) | experiments/EXP-A2_iaa_improved.md |
| EXP-A3 | E1'' | Enhanced agreement (UMLS sibling + Claude rule judge) | P0 | **PASS** | 0 (同 A 数据,加 algorithmic layers) | 4-layer cascade. L1 PABAK=0.46 (paper primary); L3 PABAK=0.51 (Supp sensitivity). Claude judge 974 disagreements → 0 actually_agreed (honesty), 21% ambig documented, 79% true_disagree | experiments/EXP-A3_enhanced_agreement.md |
| EXP-A4 | E1''' | Post-guideline IAA simulation (5 generic rule classes) | P0 | **PASS** | 0 (post-hoc rules on same data) | 5 rules (A1 type blacklist / B1 header keyword / B1c header-like type+Notassociated / B2 drug brand-dup / B3 severity adj). 15.6% (552/3534) rows rule-triggered. **κ 0.40→0.56 (+0.16), PABAK 0.47→0.57 (+0.10)**. KUMC_1 κ 0.16→0.42 最 dramatic. Cleaner than EXP-A3 L3 (no note-specific cherry-pick). **Paper primary candidate**. | experiments/EXP-A4_post_guideline_simulation.md |
| EXP-B/C | E2/E3 | Bootstrap CI + permutation + doc-level stability | P0/P1 | **PASS** | 0 (纯统计,复用 with_positions + reviewed_updated2) | Figure 3 bootstrap 95% CI + permutation p<0.001; doc-level resample stable | experiments/EXP-BC_bootstrap_stability.md |
| EXP-D | E4 | Cost / latency / GPU-h / API \$ 全表 | P0 | **PASS** | 0 (slurm log + evaluation 反推) | 完整成本表已生成 | experiments/EXP-D_cost_table.md |
| EXP-E | E5 | Hallucination 5+1 class FP taxonomy | P0 | **PASS** | 0 (现有 prediction + LLM-as-judge GPT-4.1) | 5-class taxonomy + 500-row judge sample; 84.82% true halluc, wrong_value_or_date 43.19%. **Superseded by EXP-E2 (7-class split)**. | experiments/EXP-E_hallucination_taxonomy.md |
| EXP-E2 | E5' | 7-class FP taxonomy (split value/date + broaden not_an_error) | P0 | **PASS (author-validated)** | 0 (re-judge 700 rows GPT-4.1 + 60-row author spot-check) | User 拍板 **Lenient**(2026-05-26):headline **24.4% true halluc rate, author-validated**(作者抽查 60 行 vs GPT-4.1 agreement 88.3%,7 处分歧全在已知 date-inference 边界或子类 re-route,不动 headline)。6 真 halluc cats 全 <17%;not_an_error 54.31% 主因 annotation gap + 等价格式 + synonym + missing-not-required。**不 spawn EXP-E3**。spot-check 报告 `runs/EXP-E2/author_spot_check_report.md` | experiments/EXP-E2_judge_6class.md |
| EXP-F | E6 | Baseline 补强:o3-mini single-prompt + GPT-4o CoT single-call | P0 | **PASS** | 新跑(小规模,6 jobs COMPLETED + eval) | 对 canonical 主结果 160641,两个 single-call baseline 在所有可比列都低于 CLINES 4-step,code F1 低 +0.37~+0.54,value/unit 也全输;o3-mini reasoning 补不上且成本最高(\$9.63,4× completion tokens)→ 支撑 R5 A1 | experiments/EXP-F_baseline_extra.md |
| EXP-G | E7 | Ablation: SapBERT / SemChunk / Date module / Step 4 | P1 | **PASS** | 15 cells (2 notes/ds) eval 完成(corrected `jobs/EXP-G_eval_fixed.py`,canonical position-build,98.66% match 验证) | SapBERT/UMLS 归一化贡献最大:移除 → 平均 code F1 −0.447;step-4 −0.078(集中在 coral_breastca);semchunk/date ~0(date 真实作用在 date 列,本 eval 列未含)。mention 基本不动 → NER 上游正交 | experiments/EXP-G_ablation.md |
| EXP-G2 | E7' | Ablation grid 复跑(gpt-4o-mini-0718,EXP-G 的 sister) | P1 | **PASS** | 15 cells (2 notes/ds) eval 完成(同 EXP-G corrected runner) | Ablation 排序在更便宜模型上复现(SapBERT −0.414 >> step-4 −0.221 >> semchunk/date ~0)→ **model-agnostic**;step-4 在 mini 上贡献更大(−0.221 vs gpt-4o −0.078)→ 越弱的 LLM 越依赖 4-step 确定性脚手架(R5 cost 论点)。n=2 → point estimate 无 CI | experiments/EXP-G2_ablation_gpt4omini.md |
| EXP-H | E8 | Full-size DL baseline: BERT-base 110M + GatorTron-base 345M | P1 | **PASS (with 2026-05-26 errata)** | jobid 41440867 (02:59 gpu_quad) | BERT mention F1=0.875-0.888, GatorTron 0.840-0.876. vs paper-cited CLINES (GPT-4o backbone) 0.906/0.881/0.913, BERT/GatorTron 全面 0-7pp below (clean head-to-head). Errata 见 .md §9 (prior 0.811 quote 错). | experiments/EXP-H_dl_baseline.md |
| EXP-H2 | E8' | Weakened DL baseline (confidence_threshold 0.3→0.6) | P2 | **ARCHIVED-SUPP** | jobid 41467904 (02:26 RTX 8000) | BERT@0.6 mention F1=0.821-0.838 (lower than EXP-H@0.3). Premise (baseline > CLINES) 后发现是错的 reference (filename / quote 误)。EXP-H 已 PASS w/ paper baseline,EXP-H2 沦为 confidence_threshold sensitivity in Supp. | experiments/EXP-H2_weakened_baseline.md |
| EXP-J | R5.4.5 | Run-to-run output consistency (5× same 20 notes, gpt4omini) | P1 | **SUPERSEDED** | array 41679908 (已 cancel) | 跑在过时 worktree (`d04b219`,缺 chunk-window fuzzy 优化) → 整篇 O(N·M²) 模糊扫描致 ~40min/chunk;诊断后由 EXP-J2 在优化代码 `adca819` 上重跑取代,未产出结果 | experiments/EXP-J_output_consistency.md |
| EXP-J2 | R5.4.5 | Run-to-run output consistency 重跑(优化代码) | P1 | **RUNNING** | array 41735389 (15 cells=5×3, CPU short **%15**, commit `adca819`) | 同 EXP-J 目标(temperature 一致性 → Supp §S4),跑在 chunk-window 限定 + `quick_ratio` 剪枝 fuzzy 的 `adca819` 上;%15 全并发摊薄 HMS proxy API 延迟(诊断显示 fuzzy 修复后 API 是残余瓶颈) | experiments/EXP-J2_output_consistency.md |
| — | E9 | RE 不评测,Supp 写明 | P1 | WRITING-ONLY | 0 | n/a | —(不立 EXP) |

### 状态枚举

- `PENDING` — 数据/工具/环境齐，可以立即开跑
- `RUNNING` — 正在跑
- `PASS` / `FAIL` / `INCONCLUSIVE` — 跑完，结论已回填
- `BLOCKED-API` — 等 HMS API key 恢复
- `BLOCKED-DATA` — 等外部数据（Mo 的 cross-annotation）
- `BLOCKED-CODE` — 等代码/环境/工具就绪（如 EXP-H 需先核实 ClinicalNER 项目是否迁到 O2）
- `MIXED` — 部分子实验可立即跑，部分阻塞
- `WRITING-ONLY` — 不跑实验，只在文稿改 wording
- `ARCHIVED-SUPP` — 跑完但 paper 不主推,留在 Supp 作 sensitivity / robustness check
- `TIMEOUT-needs-rerun` — SLURM walltime 不够,需要重提加长 walltime
- `INCONCLUSIVE-pending-review` — 跑完但需要 user policy decision 才能 finalize
- `RUNNING-eval` — SLURM inference 全 COMPLETED,正在跑 eval / 回填 .md(尚未 PASS)

## ⚠️ Baseline 文件名 注意

`outputs/with_positions/*<model>*.csv` 是 paper 用的 **single-prompt LLM baseline** prediction(每个 model 一组),不是 CLINES variant。**注意:文件名中的 "gpt4o" / "o3mini" / "deepseek" / "llama" 指 backbone,不指 CLINES variant**。

- `outputs/with_positions/*gpt4o*.csv` mention F1 (re-eval) ≈ 0.91 — 这其实是 paper 主 CLINES (GPT-4o backbone) 预测结果,跟 `outputs/eval_compare/gpt4o_eval_mention.json` 数字一致
- `outputs/with_positions/*o3mini*.csv` mention F1 ≈ 0.80 — 是 **single-prompt o3-mini baseline**(不是 CLINES o3-mini variant)
- Paper 用 `outputs/eval_compare/gpt4o_eval_mention.json` (mention F1 0.9061/0.8805/0.9127) 作为 paper Methods cited CLINES eval source(GPT-4o backbone variant)
- Paper Results §3.2 声明 "CLINES o3-mini > GPT-4o > Llama-3.1-405B" — 但 paper 主表数字 cite 的是 GPT-4o backbone version

## 命名 / Branch 规范

- **EXP-ID 风格**：Phase 风格（EXP-A..EXP-H 与作战表 E1..E8 一一对应）
- **Branch**：`exp/<EXP-ID>_<short-name>`，永不删除，跑完 push 到 `origin/exp/<...>`（详见 ~/.claude/CLAUDE.md §9.2）
- **Artifact 目录**：`runs/<EXP-ID>/`（含 `ckpts/` / `eval/` / `tb/` / `snapshot/`）— 不入 git（见 `.gitignore`）
- **单实验 .md**：`experiments/<EXP-ID>_<short-name>.md`，按 ~/.claude/experiments-rules.md §8.1 跑实验时单独建（不预创建空骨架）
- **EXP-ID 三处一致**：`experiments/<EXP-ID>_*.md` 文件名 + `runs/<EXP-ID>/` 目录 + `exp/<EXP-ID>_*` branch
- **任何 mid-run 改代码 / config / hparam = 新 EXP-ID**（详见 ~/.claude/CLAUDE.md §4 + experiments-rules.md §4.3）

## 更新日志

- 2026-05-13：初版创建。锁定 Phase 风格 + 9 项实验编号 E1-E9 / EXP-A..EXP-H。E9 走方案 (b)（不评测，Supp 写明），不立 EXP 项。User 拍板"能不跑就不跑"策略（2026-05-13）。HMS API 暂不可用，BLOCKED-API 实验等 key 到位。
- 2026-05-19：HMS API key 已拿到（user 从 SharePoint 取得，存放在 `OPENAIKEY` env var，不入 git）。Deployment probe 显示 `gpt-4o-1120` / `gpt-4o-mini-0718` / `gpt-4.1` 系列 / `o3-mini-0131` / `o4-mini-0416` 可用，alias（`gpt-4o` / `gpt-4o-mini` / `o3-mini`）全部 404。`openai_provider.py` 的 `n2n_dict` 同步修正（`gpt4omini→gpt-4o-mini-0718`、`o3mini→o3-mini-0131`），`o3mini` api_version 由 `2024-10-21` 升到 `2024-12-01-preview`（reasoning 推荐版本）。`run_inference.sh` 清除 hardcode 的失效 key / dev endpoint，改为 fail-fast 检查 `OPENAIKEY` env var 并默认 `OPENAIENDPOINT=https://azure-ai.hms.edu`。EXP-F 状态由 `BLOCKED-API` → `PENDING`；EXP-G 同步。
- 2026-05-25 — 2026-05-26: 大规模实验 batch 完成。EXP-A/A2/A3 IAA 完整 (PABAK 加 Cohen's paradox 解释,Claude judge 974 disagreements 揭示 0% 是 actually-agreed)。EXP-BC bootstrap CI + permutation test PASS。EXP-D 成本表 PASS。EXP-E hallucination 5+1 PASS,但 EXP-E2 (7-class split + broaden not_an_error) 揭示 54% "FP" 不是 model error → INCONCLUSIVE-pending-review。EXP-H DL baseline (BERT/GatorTron) PASS。EXP-H2 weakened baseline ARCHIVED-SUPP (premise 是错的 reference baseline,但跑出来的 confidence_threshold sensitivity 仍可用作 Supp)。EXP-F 6 jobs RUNNING。EXP-G 15 jobs 全 TIMEOUT (walltime 不够),需重提。**Baseline 文件名注意**: with_positions/*<model>*.csv 是 paper main CLINES (GPT-4o backbone) variant prediction;EXP-H §9 早期 backfill 错引用了 single-prompt baseline 数字,2026-05-26 errata 已修。详见各 .md §9 / 更新日志。
- 2026-05-26（晚,index sync）：EXP-F **救援完成 → PASS**(run_eval.sh 自引用 symlink bug 修复后重跑 4CE;主结果参照系经 Figure 3 绘图链锁定 = `gpt4_eval_20250904_160641`)。EXP-G **Plan D 完成**(15 cells × 2 notes/ds 全 COMPLETED;Plan A/B/C 历史见 EXP-G.md §6.1);新增 **EXP-G2**(gpt-4o-mini sister,15 cells 全 COMPLETED)。两者 eval 发现 `jobs/EXP-G_eval_all.sh` 漏了 canonical position-build 步骤(`process_entity_index.py --use_sequential`,即生成 `outputs/with_positions/` 的同款步骤)→ raw `default` 输出只有 `mention_start_pos` 而 eval 需要重算的 `start_pos`;已修,eval 进行中,状态暂记 `RUNNING-eval`(完整 ΔF1 回填后转 PASS)。另:pipeline `result_aggregation` 的 join-by-index → **join-by-TAG** 根因修复已 commit 到 i2b2(silent 错配 bug;论文主结果是旧代码冻结,该修复仅利好/不改主结果)。
- 2026-05-26(晚,EXP-G/G2 eval 完成 → 双双 PASS):corrected eval runner(`jobs/EXP-G{,2}_eval_fixed.py`,补回 canonical `process_entity_index.py --use_sequential` position-build,98.66% match 验证)跑完全部 30 cells。**核心发现**:SapBERT/UMLS 归一化是 code F1 的主导组件(gpt-4o 移除 −0.447,gpt-4o-mini −0.414),mention 基本不动 → NER 上游正交且 normalization 是 coding 任务的承重墙;**排序跨 backbone 复现 → model-agnostic**;step-4 reconcile 在 mini 上贡献更大(−0.221 vs gpt-4o −0.078,集中在 coral_pdac/breastca)→ 越弱的 LLM 越依赖 4-step 脚手架(强化 R5 architecture/cost 论点)。semchunk/date 在 code 列 ~0(date 真实作用在 date 列,本 eval 列集未含 → 已知测量 gap,非"无用")。n=2 notes/ds → point estimate 无 CI(W-26 caveat)。两 exp branch 回填 §8-13 + commit(`ad2f7a6` / `7322506`),Figure 5c 已用真实数据(gpt-4o 蓝 + gpt-4o-mini 紫双 backbone)。
- 2026-05-27(index sync):**EXP-E2 状态校正 `INCONCLUSIVE-pending-review` → `PASS (author-validated)`**。决定 + 验证早已完成(EXP-E2.md §11 已是 PASS,index 行滞后):user 2026-05-26 拍板 **Lenient**(headline 24.4% true halluc,不 spawn EXP-E3);作者 60 行 spot-check vs GPT-4.1 agreement 88.3%(53/60),7 处分歧 4 处子类 re-route + 3 处已知 date-inference 边界,均不动 headline;6 真 halluc cats 全 <20%。报告见 `runs/EXP-E2/author_spot_check_report.md`。另:**Figure 5 全 4 面板真实数据完成 + push**(`889c272`;5a code F1+bootstrap CI / 5b 双口径 cost / 5c 双 backbone 消融 / 5d mention+code 含 BERT-base+GatorTron)。codex review 进程中途挂了(companion 不稳),数据接线由我自查通过(panel C dataset 对齐安全等)。

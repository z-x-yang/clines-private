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
- **HMS Azure OpenAI key 截至 2026-05-13 仍全失效**（详见 memory `hms-api-status`）。所有 `BLOCKED-API` 状态的实验需等到拿到有效 key 后才能开跑。

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
| EXP-A | E1 | IAA Cohen's κ + F1-based agreement | P0 | BLOCKED-DATA | 0（等 Mo cross-annotation, ~05-21） | TBD | experiments/EXP-A_iaa.md |
| EXP-B | E2 | Bootstrap 95% CI + permutation test（Figure 3A-D） | P0 | PENDING | 0（复用 with_positions + reviewed_updated2，纯统计） | TBD | experiments/EXP-B_bootstrap_ci.md |
| EXP-C | E3 | Document-level resample stability | P1 | PENDING | 0（同上） | TBD | experiments/EXP-C_stability.md |
| EXP-D | E4 | Cost / latency / GPU-h / API \$ 全表 | P0 | PENDING | 0（slurm-\*.out + evaluation\_results\_0904 反推） | TBD | experiments/EXP-D_cost.md |
| EXP-E | E5 | Hallucination 5-class FP taxonomy | P0 | PENDING | 0（从现有 prediction 拉 FP + 人工归类） | TBD | experiments/EXP-E_hallucination.md |
| EXP-F | E6 | Baseline 补强：o3-mini single-prompt + GPT-4o CoT single-call | P0 | BLOCKED-API | **新跑**（小规模） | TBD | experiments/EXP-F_baseline_extra.md |
| EXP-G | E7 | Ablation: SapBERT / SemChunk / Date module / Step 4 | P1 | MIXED | Date/Step4 off 可在现有产物上**模拟**；SemChunk / SapBERT 必须新跑（依赖 API） | TBD | experiments/EXP-G_ablation.md |
| EXP-H | E8 | Full-size DL baseline: BioClinicalBERT 或 GatorTron | P1 | BLOCKED-CODE | **新跑**（GPU；不依赖 HMS API） | TBD | experiments/EXP-H_dl_baseline.md |
| — | E9 | RE 不评测，Supp 写明 | P1 | WRITING-ONLY | 0 | n/a | —（不立 EXP） |

### 状态枚举

- `PENDING` — 数据/工具/环境齐，可以立即开跑
- `RUNNING` — 正在跑
- `PASS` / `FAIL` / `INCONCLUSIVE` — 跑完，结论已回填
- `BLOCKED-API` — 等 HMS API key 恢复
- `BLOCKED-DATA` — 等外部数据（Mo 的 cross-annotation）
- `BLOCKED-CODE` — 等代码/环境/工具就绪（如 EXP-H 需先核实 ClinicalNER 项目是否迁到 O2）
- `MIXED` — 部分子实验可立即跑，部分阻塞
- `WRITING-ONLY` — 不跑实验，只在文稿改 wording

## 命名 / Branch 规范

- **EXP-ID 风格**：Phase 风格（EXP-A..EXP-H 与作战表 E1..E8 一一对应）
- **Branch**：`exp/<EXP-ID>_<short-name>`，永不删除，跑完 push 到 `origin/exp/<...>`（详见 ~/.claude/CLAUDE.md §9.2）
- **Artifact 目录**：`runs/<EXP-ID>/`（含 `ckpts/` / `eval/` / `tb/` / `snapshot/`）— 不入 git（见 `.gitignore`）
- **单实验 .md**：`experiments/<EXP-ID>_<short-name>.md`，按 ~/.claude/experiments-rules.md §8.1 跑实验时单独建（不预创建空骨架）
- **EXP-ID 三处一致**：`experiments/<EXP-ID>_*.md` 文件名 + `runs/<EXP-ID>/` 目录 + `exp/<EXP-ID>_*` branch
- **任何 mid-run 改代码 / config / hparam = 新 EXP-ID**（详见 ~/.claude/CLAUDE.md §4 + experiments-rules.md §4.3）

## 更新日志

- 2026-05-13：初版创建。锁定 Phase 风格 + 9 项实验编号 E1-E9 / EXP-A..EXP-H。E9 走方案 (b)（不评测，Supp 写明），不立 EXP 项。User 拍板"能不跑就不跑"策略（2026-05-13）。HMS API 暂不可用，BLOCKED-API 实验等 key 到位。

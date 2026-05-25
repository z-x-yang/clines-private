# CLINES BMJ Major Revision — Response Plan

## 用法说明

本文档与 `EXPERIMENTS.md`（项目根）配套：

- **`EXPERIMENTS.md`** 面向「跑实验」：EXP-ID 命名 / branch 规范 / artifact 路径 / 复现命令
- **`RESPONSE_PLAN.md`**（本文档）面向「对接 reviewer」：每条 comment → action 完整 traceability / 每个 EXP 的实操方案 / 写作 checklist / response letter 起草准备

迭代节奏：

1. 本文档先建骨架 + 每个 EXP 的初步实操思路（**当前阶段**）
2. 与用户 dialogue 逐个 EXP 拍板（跑 / 不跑 / 换法子），decision 写回本文档相应 section（状态 `TBD` → `DECIDED`）
3. 所有 EXP 全 `DECIDED` 后才进入跑实验阶段（per-EXP launch 按 `~/.claude/experiments-rules.md §8.1`）
4. 实验跑完回填 `experiments/EXP-X_*.md` 字段 8-13 + 同步本文档 §6 response letter 准备段
5. 所有实验完成后才起草 response letter + 改 LaTeX 正文

## 元数据

- **Manuscript**: `bmjdh-2026-000027`
- **Journal**: BMJ Digital Health & AI
- **Decision**: Major Revision
- **Due**: 2026-05-31（已 grant 延期，原 5-17）
- **Editor**: Dr. Chris Paton（Editor in Chief）
- **Reviewer 数**: 5 + Associate Editor
- **Raw reviewer comments**: `papers/BMJ_AI_Submission/Major Revision/revision_comments.txt`
- **原文稿 LaTeX**: `papers/BMJ_AI_Submission/Submission/CLINES latex bmj/`（`lancet_draft.tex` 主入口 + `sections/` + `supplement_sections/`）
- **PDF**: `papers/BMJ_AI_Submission/Submission/main.pdf`

---

# §1 Reviewer → Action 完整 Traceability

逐条 reviewer comment 映射到 (实验 EXP-X / 可规避 S# / 写作 W-§X)。**E# = 实验类**、**S# = 可规避（话术化解）**、**W §X = writing-only**。

## §1.1 Reviewer 1（22 条 — 最详尽）

### Major

| # | 内容 | 映射 | 状态 |
|---|---|---|---|
| M1 | 缺 Inter-Annotator Agreement | **EXP-A** | TBD |
| M2 | Figure 3A-D 无 CI / 无统计检验（点估计） | **EXP-B** | TBD |
| M3 | 评估集小（24/21/13/16）+ 缺 power analysis | **EXP-C** + S7 化解 power analysis | TBD |
| M4 | STROBE 不适用，应用 MI-CLAIM / TRIPOD+AI / STARD-AI | W §3.3 | TBD |
| M5 | 缺 cost / latency / 计算效率报告；披露真实 LLM 调用数 | **EXP-D** | TBD |

### Moderate

| # | 内容 | 映射 | 状态 |
|---|---|---|---|
| M6 | "Agentic" overclaim | W §3.2 | TBD |
| M7 | Baseline 不完整（缺 o3-mini single-prompt + GPT-4o CoT） | **EXP-F** | TBD |
| M8 | Prompt 敏感性 / 消融 | **EXP-G** + S8（prompt rewording 化解） | TBD |
| M9 | Hallucination 未量化 | **EXP-E** | TBD |
| M10 | Ref 14 错（Kohane 2012 → Uzuner 2011 JAMIA 18(5):552-556） | W §3.6 | TBD |
| M11 | Prompt examples 被 redact 成 placeholder | W §3.6（Supp 补 full prompts） | TBD |
| M12 | "Four-step" 与实际 11 prompt types 不符 | W §3.3 + EXP-D 的 per-step invocation table | TBD |
| M13 | RE 模块未评估 | **W only**（E9 走 (b)，Methods + Limitations 写明 + Supp 2.2 保留） | TBD |
| M14 | UMLS retrieval params 不全（SapBERT ckpt / FAISS index / top-k / threshold / UMLS version / tie-break） | W §3.6（Supp Algorithm 1 补 6 项） | TBD |
| M15 | Annotator credentialing + API DUA governance | W §3.6 ethics | TBD |
| M16 | Demographic extraction 风险 | W §3.5 Discussion + S4 化解 fairness subgroup | TBD |

### Minor

| # | 内容 | 映射 | 状态 |
|---|---|---|---|
| m17 | MIMIC-III F1 偏低 (0.69) 原因讨论 | W §3.4 | TBD |
| m18 | Abstract 格式（Lancet 风格 → BMJ） | W §3.1 | TBD |
| m19 | STROBE checklist PDF 转换乱码 | W §3.6（用 TRIPOD+AI 替换后自然消失） | TBD |
| m20 | 缺 PPI statement | W §3.6 | TBD |
| m21 | Ethics approval IRB 名称不明 | W §3.6 | TBD |
| m22 | "value&unit" / "value-unit" / "value/unit" 术语不统一 | W §3.6 | TBD |

## §1.2 Reviewer 2（5 条）

| # | 内容 | 映射 | 状态 |
|---|---|---|---|
| M1 | "Zero-shot" 命名不当（含 prompt eng / decomp / RAG / rule） | W §3.1（改 "training-free" 或加 §2.6 限定） | TBD |
| M2 | 缺 IAA（重 R1 M1） | **EXP-A** | TBD |
| M3 | Hallucination 未量化（重 R1 M9） | **EXP-E** | TBD |
| M4 | 泛化性声明过强（未覆盖 discharge / operative / radiology） | W §3.2 / §3.5 + S6 化解 | TBD |
| m1 | 软化 chart-review 替代声明 | W §3.5 | TBD |

## §1.3 Reviewer 3（13 条）

| # | 内容 | 映射 | 状态 |
|---|---|---|---|
| C1 | Introduction 缺引文（EF / tumor size 的临床重要性） | W §3.2 | TBD |
| C2 | 缺 ML/DL 中间层文献（BiLSTM-CRF / BioBERT / ClinicalBERT） | W §3.2 | TBD |
| C3 | Step 1 chunking 细节不足（boundary / truncation / sliding window? / context） | W §3.3 | TBD |
| C4 | Step 4 reconciliation 不清（冲突 / 优先级 / 去重） | W §3.3 + Figure 2 扩展 | TBD |
| C5 | 缺消融 | **EXP-G** | TBD |
| C6 | "words" 未定义 | W §3.3 | TBD |
| C7 | "clinical phrases" 定义模糊 | W §3.3 | TBD |
| C8 | Baseline 缺全尺寸 DL | **EXP-H** | TBD |
| C9 | Figure 3 可读性差 | W §3.4（重出图） | TBD |
| C10 | Results 解读不足 | W §3.4 | TBD |
| C11 | Limitation 展开不够（缺克服路径） | W §3.5 | TBD |
| C12 | 缺独立 Conclusion section | W §3.5 | TBD |
| C13 | Future Work 简略 | W §3.5 | TBD |

## §1.4 Reviewer 4（5 条）

| # | 内容 | 映射 | 状态 |
|---|---|---|---|
| C1 | Chunking 连续性（与 R3 C3 重） | W §3.3 | TBD |
| C2 | 聚合验证机制（与 R3 C4 重） | W §3.3 | TBD |
| C3 | Error Analysis（与 R1 M9 重） | **EXP-E** | TBD |
| C4 | 成本分析（与 R1 M5 重） | **EXP-D** | TBD |
| C5 | Hybrid model pipeline | **S5**（future work 化解） | TBD |

## §1.5 Reviewer 5（含 4 个 hard Action Required）

### Formatting

| # | 内容 | 映射 | 状态 |
|---|---|---|---|
| F1 | Abstract 改 BMJ DH&AI 子标题（Objective / Methods and Analysis / Results / Conclusion） | W §3.1 | TBD |
| F2 | Summary Box（What is known / What this study adds / How this may affect） | W §3.1（新增） | TBD |
| F3 | CLINES 缩写一致（title vs p6 L11） | W §3.1 | TBD |
| F4 | Figure 分辨率不足 | W §3.4 | TBD |

### Minor

| # | 内容 | 映射 | 状态 |
|---|---|---|---|
| S1 | Prompt suite repo URL | W §3.6 | TBD |
| S2 | Hallucination 5-class 量化 | **EXP-E** | TBD |
| S3 | STROBE → TRIPOD-AI 等（重 R1 M4） | W §3.3 | TBD |
| S4 | SemChunk 局限 + context window 机制 | W §3.3 | TBD |
| S5 | Figure 3E 每 bin n | W §3.4 | TBD |

### Major Action Required（hard requirement）

| # | 内容 | 映射 | 状态 |
|---|---|---|---|
| **A1 (4.1)** | **Single-prompt baseline 缺 o3-mini SP + GPT-4o CoT；要么补、要么重新框定贡献** | **EXP-F** | TBD |
| **A2 (4.2)** | **IAA hard requirement；MIMIC F1 重新措辞为 "agreement-with-annotator"** | **EXP-A** | TBD |
| **A3 (4.3)** | Scalability 声明过度：input cleanliness / Llama-405B 部署门槛 / 量化精度 / API governance | W §3.5（含 Llama 量化精度 fact-check） | TBD |
| **A3 (4.4)** | Interoperability 过度：CUI → SNOMED / FHIR / RxNorm / LOINC / OMOP-CDM 映射步骤 | W §3.3 + Supp Figure（mapping flow） | TBD |
| **A4 (4.5)** | 缺 Healthcare NLP (Spark NLP v6.3) / CLEAR (npj Digit Med 2025) / Ntinopoulos (BMJ HCI 2025) 对比 | **S1 / S2 / S3** 话术化解 + Discussion comparison table | TBD |

## §1.6 Associate Editor

承认工作价值，要求 major revision，特别关注方法学问题。无单独需要补的实验。

---

# §1.5 User decisions (2026-05-25) — 实验 cheat sheet 拍板结果

每个 EXP 的执行约束 / 关键变通点 / 推荐路径。后面 §2 的 detailed plan 应在此约束下读。

| EXP | 决策 | 关键约束 / 变通 |
|---|---|---|
| EXP-A IAA | ✅ 跑 | 直接用 cross-annotation 数据；CORAL-P + CORAL-B 合并报；MIMIC 不报；Methods 诚实交代 cross-annotation 是 review-style (annotators independently reviewed AI-suggested draft, not blank double annotation) |
| EXP-B Bootstrap CI | ✅ 跑 | 用现有 prediction + gold 算 |
| EXP-C Stability | ✅ 与 B 合并 | 同一份 bootstrap 顺便给 stability + Figure 3E 加 per-bin n |
| EXP-D Cost report | ✅ 跑（统计反推） | **Llama-3.1-405B 不能新部署**（O2 无 8×H100）— 用现有数据估算。**rebuttal 措辞用「统计 / quantified」不用「估算 / estimated」**，避免给 reviewer 新 concern。如需 simple smoke 验证可补 |
| EXP-E Hallucination | ✅ LLM-as-judge | GPT-4.1 当 judge + 人工 validate sample + 出 case study 进 Discussion |
| EXP-F new baselines | ✅ 跑 | **baseline 不过度优化**（避免不公平比较）+ **保留 chunk 处理**（整 note 太长，单次 4-500 entities 超 token 限制会让 baseline 严重下降）+ 目标平衡（够用即可，不要刻意提高） |
| EXP-G Ablation | ✅ 跑（精简） | **每个 dataset 挑几个代表性 note** 跑 ablation（不是 4CE 全跑 + 其他 spot-check） |
| EXP-H DL baseline | ✅ 跑 | ClinicalNER 项目在父目录（`../ClinicalNER/` from project root），含 `clinical_ner.py` + `ClinicalTransformerNER/` + `evaluation.log` — 之前跑过 fine-tune，但用户不记得具体什么；sub-agent 需 audit 现有状态 + 想合理办法补 1 个 baseline，**结果不需要好但必须有** |
| EXP-I (RE) | ❌ 不跑 | Methods + Limitations 写 not evaluated；rebuttal 时强调 entity 数量大 (4-500 per note) + relation 标注歧义性强 + 标注成本爆炸 |

**Cross-annotation 决定**：不补任何（4CE 29% + CORAL 14% ≥ 10% 已够）。

---

# §1.6 Pre-flight findings (2026-05-25)

Sub-agent dispatch 前的环境/数据快速验证。

1. **EXP-H ClinicalNER 位置**：✅ `/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/ClinicalNER/`（项目根的父目录）。含 `clinical_ner.py` (30KB), `batch_clinical_ner.py` (11KB), `ClinicalTransformerNER/`, `data/`, `download_models.sh`, `evaluation.log` (508KB), `entity_matcher.py`, `data_loader.py`, `config/`. Sub-agent EXP-H 首步：audit 现有 fine-tuned ckpt + 决定增量补还是重 fine-tune。
2. **EXP-G chunk-level outputs**：⚠️ `outputs/with_positions/` 是 final aggregated output（schema 含 mention/code/assertion_status/start_pos/end_pos/agent_type，**无 chunk_id**），(c) Date off / (d) Step 4 off 不能直接在产物上模拟，必须新跑。但用户决策"每个 dataset 几个代表性 note"使新跑量可控。
3. **EXP-D token_usage source**：⚠️ `outputs/evaluation_results_0904/*.json` 顶层只有 `{metrics, error_cases}`，**无 token_usage**。Sub-agent EXP-D 第一步：grep `slurm-*.out` 或找 inference 时 `LLMManager.note_token_stats` / `chunk_token_stats` 的 dump location。如果找不到 source data，按用户决策可补 1 个小 smoke 跑 + 把 LLMManager stats 落盘。Llama-3.1-405B 量化精度：**不能新部署验证**（无 8×H100），从历史 deployment config + memo 取（用户提示 fact-check 自己）。
4. **EXP-A cross-annotation schema**：✅ Mo 给的 CSV (`agent_type=deepseek`) + Enci 给的 CSV (`agent_type=gpt4o`) 都是 review-style（不是 blank double）。schema 含 term_index / mention / code / assertion_status / value / unit / start_pos / end_pos / agent_type，匹配原 `for_review.csv` 格式。**Methods 必须诚实交代 "review-style independent re-annotation of AI drafts"** — 不能 misrepresent 成 blind double annotation。
5. **sacct 窗口**：✅ O2 sacct 能拿到 2025-04-19 起的 job 记录（含 `Elapsed`, `Start`, `End`, `State`, `MaxRSS`）。**但 Longwood 时代 job 不在 O2 sacct**；那部分 wall-clock 只能从 `slurm-*.out` 自带 timestamps 反推。

---

# §2 实验类 EXP plan（per-EXP 详细方案）

每个 EXP 用统一结构：**覆盖 reviewer / 状态 / 新跑量 / 目标 / 现有数据 / 初步实操思路 / 待协作决策点 / 工作量估算**。

> **当前 status 解释**：
> - `PENDING` 可立即开跑
> - `BLOCKED-DATA` 等外部数据（Mo / 同事 fact-check）
> - `BLOCKED-CODE` 等代码 / 环境就绪
> - 各 section 内部细分子项也可独立 PENDING / BLOCKED

## EXP-A: IAA Cohen's κ + F1-based agreement

- **覆盖 reviewer**: R1 M1 / R2 M2 / **R5 A2 (hard)**
- **状态**: **PENDING**（cross-annotation 数据已到位 2026-05-25）
- **新跑量**: 0 LLM 调用（纯统计计算）
- **优先级**: P0

**目标**：

报告 4 个抽取任务（mention / assertion / value / unit）在 ≥10-15% 双标注样本上的 Cohen's κ + F1-based agreement；MIMIC-III 因为是 single-annotator-per-paragraph，重新措辞 F1 为 "agreement-with-annotator"。

**现有数据**：

Cross-annotation 数据全部在 `papers/BMJ_AI_Submission/Major Revision/cross-annotation/`：

**任务设计（来自 `My original email.txt`）**：

Zongxin 让 Mo 和 Enci 各自**独立**重标对方原本标过的 5 个 note（不看 original）：
- `For_Mo_IAA_cross_annotation.zip` — Mo 要标的 5 个（原 Enci 标）
- `For_Enci_IAA_cross_annotation.zip` — Enci 要标的 5 个（原 Mo 标）

**实际返回**：

| 标注员 | 任务清单 | 实际返回 | 备注 |
|---|---|---|---|
| **Mo** (`From Mo_2_Zongxin_Compressed...zip`) | 4CE: KUMC_7, report03, report04 / Coral: pdac 7, pdac 17 | 全 5 个 ✅ | 完成 5/8 - 5/13 |
| **Enci** (`To_Zongxin_Enci_add_annotation.zip`) | 4CE: BCH_6, **COL_4**, KUMC_1 / Coral: pdac 14, breastca 38 | 4CE: BCH_6, **BCH_7**, KUMC_1 / Coral: 14, 38 | ⚠️ **Enci 漏 COL_4，多标 BCH_7** — 待 Zongxin 核实是任务调整还是误标 |

Gold standard 原标参考：`outputs/reviewed_updated2/`（用于和 cross-annotation 比对，定 inter-annotator agreement）。

**样本规模满足度（reviewer R5 A2 ≥10-15%）**：

| 数据集 | 原标注总 N | Cross-annotated N | 占比 |
|---|---|---|---|
| 4CE | 21 notes | 6 unique (Enci 任务 3 + Mo 任务 3) | **~29%** ✅ |
| CORAL-Pancreas | 16 notes | 3 unique (pdac 7, 14, 17) | **~19%** ✅ |
| CORAL-Breast | 13 notes | 1 unique (breastca 38) | **~8%** ⚠️ 略低于 10% |
| MIMIC-III | 24 paragraphs | **0** | 0% — 仍 single-annotator |

**初步实操思路**：

1. **数据整理**：unzip 所有 cross-annotation zip 到工作目录；对齐两个标注员对同一 note 的两份 CSV（结构应该相同——同 schema `for_review.csv` 格式）。需要建一个 `pairs/` 目录：每对 (note_id, annotator_A_csv, annotator_B_csv)。
2. **Span-level alignment**：mention 是 character-level span，两个标注员的 begin/end pos 可能差 1-2 字符。定义 IoU ≥ 0.5（或更严 0.7）算作同一 span。
3. **IAA metric 计算**（per dataset，per task）：
   - **Mention level**: 先做 span alignment，然后报 F1-based agreement（一人当 GT、另一人当 pred 互算 F1，取平均）+ Cohen's κ（如果离散化为 "found / not found" 在每个 token / 每个 chunk）
   - **Assertion**: 仅在匹配 mention 上比 assertion 类别（present / absent / possible / conditional / historical-合并到 present）— Cohen's κ
   - **Value**: 仅在匹配 mention 上比 value — 数值严格相等 → agreement rate (binary)
   - **Unit**: 仅在匹配 mention 上比 unit — 字符串包含相等 → agreement rate (binary)
4. **报告**：
   - Per dataset × per task 的 IAA matrix
   - MIMIC-III: 写明 "single-annotator-per-paragraph, F1 herein interpreted as agreement-with-annotator" 写在 Methods + 单独 caveat 段
   - CORAL-Breast: 写明 "limited by coordinator availability; n=1 cross-annotated, κ should be interpreted as illustrative" 或补一份
5. **Methods 加 "Annotation reliability" 子节**（W-18，对应 R5 A2 要求 IAA 进 main Methods 而非 Limitations）

**待协作决策点**：

- [ ] **核实 Enci 任务清单 COL_4 → BCH_7 切换**：是您当时跟 Enci 改了任务吗？如果是，更新文档；如果是误标，决定 (a) 把 BCH_7 也纳入分析（多一个 sample 不亏）还是 (b) 跟 Enci 补标 COL_4
- [ ] **CORAL-Breast n=1 是否够**：补一份让 Mo 或 Enci 再标一个 breastca（保证 ≥10%），还是用 n=1 直接写过去 + Limitation 说明？补的成本是再一轮邮件来回 ~1 周
- [ ] **MIMIC-III**：完全不补（reviewer 接受 "agreement-with-annotator" caveat），还是想办法找另一位 PhysioNet credentialed 同事补少量？
- [ ] **Span alignment IoU 阈值**：0.5（标准 NER 评估）或 0.7（更严，agreement 数值会更低但更严谨）
- [ ] **Cohen's κ 报告颗粒度**：per-dataset 表（4 行 × 4 task = 16 cells）还是 per-task heatmap？
- [ ] **是否对 CLINES 也算 "agreement-with-CLINES"**：除了 annotator vs annotator，把每个 cross-annotator 跟 CLINES prediction 也算一个 F1-agreement，看 CLINES 跟人类哪一位更接近 — 这是 reviewer R5 没明确要求但能加分的额外 angle

**工作量估算**：

- 数据整理 + pair 对齐脚本：~2 小时
- IAA 计算脚本（span alignment + κ + agreement rate）：~3-4 小时
- 出表 + 写 Methods 子节 "Annotation reliability"：~2 小时
- **总计**：~1 天（数据已到位，立即可启动）

**状态机**：

```
[PENDING: 数据到位 2026-05-25] → [RUNNING: 脚本跑] → [PASS]
        ↑
  待 4 个 decision points 拍板后即可启动
```

---

## EXP-B: Bootstrap 95% CI + permutation test

- **覆盖 reviewer**: R1 M2
- **状态**: PENDING（可立即开跑）
- **新跑量**: 0（纯统计，复用现有 prediction + gold）
- **优先级**: P0

**目标**：

对 Figure 3A-D 所有主要 (model × dataset) cell 报告 95% bootstrap CI；对 CLINES vs strongest single-prompt baseline 的 pairwise 比较跑 permutation test 报 p-value。

**现有数据**：

- Predictions: `outputs/with_positions/`（CLINES GPT-4o）+ `outputs/{deepseek_output,o3mini_medium_output_0526,llama-405b-output*,Phi_4_output_0922,with_positions_phi4}/`
- Gold: `outputs/reviewed_updated2/`
- 全模型评估汇总: `outputs/evaluation_results_0904/*.json`
- **现成参考**：Figure 3E 已有 95% bootstrap CI ribbon → `scripts/eval_predictions.py` 里**应该**已经实现了 bootstrap 路径

**初步实操思路**：

1. 读 `scripts/eval_predictions.py` 定位 bootstrap 实现段，确认 resample 单位是 document-level 还是 phrase-level
2. 扩展 / 抽出一个统一函数：输入 (predictions_dir, gold_dir, metric_columns, n_boot, resample_unit) → 输出 {metric: (mean, ci_lo, ci_hi)}
3. 加 permutation test：对每对 (CLINES, baseline) × dataset × metric，跑 1000-10000 次 permutation（exchange labels per-document），输出 p-value
4. 输出格式：
   - 主结果 JSON：`runs/EXP-B/eval/main_results_with_ci.json`
   - p-value matrix CSV：`runs/EXP-B/eval/pairwise_pvalues.csv`
   - 重出 Figure 3A-D 加 error bar

**待协作决策点**：

- [ ] **Bootstrap 次数**：1000（快，CI 粗）vs 10000（慢，CI 紧）。R1 M2 没指定，按惯例 10000 给 publication-grade。
- [ ] **Resample 单位**：document-level（保守，跟 R1 M3 的 stability 一致）vs phrase-level（更紧 CI）。我倾向 document-level 与 EXP-C 统一。
- [ ] **Paired bootstrap for ΔF1**：除了各自 CI，是否同时跑 paired bootstrap on (CLINES F1 - baseline F1)？更 informative，但增加脚本复杂度。
- [ ] **Multiple comparisons correction**：5 模型 × 4 数据集 × 4 metric = 80 pairwise comparisons。Bonferroni 太保守，FDR (Benjamini-Hochberg) 更常用。报哪个？
- [ ] **要不要包含 Phi-4 / DL baselines 进 pairwise**：原文 Figure 3 包含 transformer encoder baselines。是否一并跑 permutation test？

**工作量估算**：

- 读 `eval_predictions.py` + 抽 bootstrap：2-3 小时
- 加 permutation test 实现：1-2 小时
- 跑全 dataset × model（10K resamples）：1-3 小时机器时间
- 重出 Figure 3A-D：半天
- 写 Methods 子节 + Results 数字更新：半天
- **总计**：~1.5 天

---

## EXP-C: Document-level resample stability

- **覆盖 reviewer**: R1 M3 / R5 S5（+ 替代 R1 要求的 power analysis，对应 S7）
- **状态**: PENDING（可立即开跑）
- **新跑量**: 0（同 EXP-B 数据 + 重采样）
- **优先级**: P1

**目标**：

回答 "评估集这么小（24/21/13/16），换一批文档结论会不会翻车？"。报告 document-level resample 下 F1 的分布（spread / 中位数 / 95% interval）；同时为 Figure 3E 每 bin 加 n。

**现有数据**：同 EXP-B。

**初步实操思路**：

1. Document-level bootstrap（与 EXP-B 复用 resample code，只是输出形式不同）：每次 resample 全 N 篇文档（with replacement），重算 F1；report 1000-5000 iteration 下 F1 的 box plot / CI band。
2. Figure 3E 重出：每个 token-length bin 上方标 n（注意作战表 R5 S5 提到长 bin 可能 n=1-2）。
3. Methods 加 1 句 "in lieu of formal power analysis, we performed bootstrap stability analysis"（对应 S7 化解 R1 power analysis 要求）。

**待协作决策点**：

- [ ] **跟 EXP-B 合并跑还是单独 EXP**：技术上 EXP-B 的 document-level bootstrap 已经能给出每 dataset 的 CI band；EXP-C 主要差异是**报告 spread 的方式**（box plot / variance number）+ Figure 3E n 标注。是否真有必要分开两个 EXP？或者合并为 EXP-B+C 一起跑？
- [ ] **Iteration 数**：与 EXP-B 是否需要相同？
- [ ] **Figure 3E 是否同时加 n + 重新检查 ribbon 显著性**（R3 C9 + R5 F4 的 figure 可读性同时改）

**工作量估算**：

- 如果与 EXP-B 合并：增量 0.5 天（box plot + Figure 3E 重出）
- 单独 EXP-C：~1 天
- **总计**：~0.5-1 天

---

## EXP-D: Cost / latency / GPU-h / API \$ 全表

- **覆盖 reviewer**: R1 M5 / R4 C4 / R5 4.3 + R1 M12 (per-step invocation)
- **状态**: PENDING（先核实数据齐不齐）
- **新跑量**: 0 lab（最差需补 1 个短 wall-clock smoke）；**fact-check** Llama 量化精度（外部信息源）
- **优先级**: P0

**目标**：

per model × per dataset 表，报告：
1. per-note 总 LLM 调用次数（**拆到** entity / normalization / date / attribute / Step 4 / reconciliation 等 sub-step）
2. wall-clock 秒/分（per note 平均 + per dataset 总）
3. API 美元（OpenAI 模型 = input/output token × pricing）
4. 本地 GPU-hours（Llama-3.1-405B / Deepseek 等 sglang 模型）
5. **明示 Llama-3.1-405B 实际量化精度**（FP8 还是别的）

**现有数据**：

- Per-chunk token usage 已有：`outputs/evaluation_results_0904/*.json` 里 CLINES `LLMManager.note_token_stats` 应该记录了
- SLURM job log：`slurm-*.out`（项目根有大量历史，最大单个 26MB）
- sacct 历史：SLURM sacct 默认保留 ~30 天 — **需立刻查现有 sacct 是否覆盖了关键 job**

**初步实操思路**：

1. **先做 audit**：扫 `outputs/evaluation_results_0904/*.json`，看 token usage 字段是否齐 + 哪些 model × dataset cell 缺。
2. **grep `slurm-*.out`**：提 wall-clock（start/end timestamps from SLURM banner）+ peak GPU 使用
3. **sacct -j <jobid> --format=JobID,Elapsed,MaxRSS,ReqMem,Start,End,State**：取所有相关 job 的 elapsed time + maxRSS
4. **API \$**：从 token usage × OpenAI pricing（gpt-4o input \$2.5/M output \$10/M / gpt-4o-mini \$0.15/\$0.6 / o3-mini 需要核实当前 Microsoft pricing）算
5. **本地 GPU-hours**：8×H100 × wall-clock（Llama-405B）；Deepseek 类似
6. **per-step invocation breakdown**：CLINES `LLMManager` 的 `chunk_token_stats` 字段可能区分了 sub-step；若没区分，需要从 `pipeline_coordinator.py` 反推每 chunk 的调用次数（4-step + 11 prompt types 拆）
7. **Llama 量化精度 fact-check**：跟本地部署同事问 — 是 FP8 / INT8 / BF16+TP / AWQ / GPTQ 中哪个？**这点直接影响 W §3.5 关于 R5 4.3 的回应**

**待协作决策点**：

- [ ] **sacct 是否还能取到老 job**：需立刻 `sacct -S 2025-04-01 -u $USER` 看保留窗口。如果取不到，怎么估 wall-clock？从 slurm-*.out 自带的 timestamps 反推可能够。
- [ ] **API pricing 数字版本**：R1 M5 在写文时用当前公开 pricing，但 HMS 内部跟 Microsoft 可能另签 — 用公开 pricing 还是 institutional pricing？通常 public pricing 是 upper bound。
- [ ] **是否需要 per-note breakdown 还是 per-dataset summary**：reviewer 要 per-note，但发表常用 per-dataset summary + Supp 给 per-note detail。
- [ ] **Llama 量化精度问谁** — 是 user 自己跑的还是合作者？需要确定问的 contact。
- [ ] **若现有 token usage 数据不齐**：是否补 1 个最小 smoke job 拿当前每 sub-step 的 token usage 模板？（这就是 0 新跑变成"补一个最小 smoke"）

**工作量估算**：

- audit + sacct/slurm grep：~0.5 天
- 整表 + per-step breakdown 反推：~0.5-1 天
- Llama 量化精度 fact-check：等同事回复（独立时间线）
- API pricing 核实 + 算钱：~1 小时
- 写 Methods + Supp table + Discussion 段：~0.5 天
- **总计**：~1.5-2 天（不含等同事回复）

---

## EXP-E: Hallucination 5-class FP taxonomy

- **覆盖 reviewer**: R1 M9 / R2 M3 / R4 C3 / **R5 S2**
- **状态**: PENDING
- **新跑量**: 0 LLM **如果**人工分类；若 LLM-as-judge 则小量新跑（便宜）
- **优先级**: P0

**目标**：

把所有（或 sample 的）false positive（模型抽到但 gold 没有的）按 5 类分类并报百分比：
1. Hallucinated entity（原文根本没这概念）
2. Span boundary error（实体存在但边界错位）
3. Wrong normalization（UMLS CUI 映射错）
4. Wrong assertion（present/absent/possible 判错）
5. Fabricated date（时间戳编造）

**现有数据**：

- FP set 可从现有 prediction × gold 直接 diff 得到
- CLINES paper §4.4 已有 1 个例子（"OD 2 gtt qd" 误为 overdose）作为 anchor
- `scripts/eval_predictions.py` 应该已经 export 出 error_cases.csv（看 `outputs/evaluation_results_0904/*_error_cases.csv`）

**初步实操思路**：

3 种 sample 策略：

**(a) Full audit on 4CE only**：4CE 是 entity 数最多的（5,731），audit 全部 FP，其他 dataset spot-check 20-30。工作量 ~1-2 天人工 + 1 天 codify。

**(b) Uniform sample 100-200 FP per dataset**：每 dataset 抽 100-200 FP 做人工分类。工作量 ~0.5 天人工 per dataset。

**(c) LLM-as-judge**：用 GPT-4o judge 把每个 FP 分类到 5 类（input = (note_excerpt, predicted_entity, gold_in_neighborhood, 5-class 定义)）。需要小心 — judge 本身也会 hallucinate。需要在小样本（50-100）上先 human-validate judge 的准确率，再放心扩到全量。
   - 工作量：~1 天写 + 跑（小 API \$，估 < \$5）+ ~0.5 天 human validate

**待协作决策点**：

- [ ] **采哪个策略**：(a) Full audit + spot-check 给 reviewer 最满意但工作量最大；(b) 中庸；(c) 最快但 judge 可信度需要 validate
- [ ] **是否需要分 model**：只在 CLINES GPT-4o 上做、还是 CLINES vs single-prompt baseline 都做？前者只支持 "CLINES 内部 error breakdown"；后者支持 "CLINES vs baseline 的 hallucination 率对比" 更强论点
- [ ] **是否分 dataset 报**：4 × 4 (model × dataset) 还是 1 × 4 (CLINES only × dataset)
- [ ] **如果走 LLM-as-judge**：用哪个 model judge？避免 self-evaluation bias，应该用 gpt-4.1 judge gpt-4o-1120 的输出，反之亦然

**工作量估算**：

- 策略 (a) Full audit on 4CE: ~3 天（含人工）
- 策略 (b) Sample 100-200 per dataset: ~1.5 天（含人工）
- 策略 (c) LLM-as-judge: ~2 天（含小规模 human validation）
- 加上：写 Methods 子节 + Results 表：~0.5 天

---

## EXP-F: Baseline 补强 — o3-mini SP + GPT-4o CoT

- **覆盖 reviewer**: R1 M7 / **R5 A1 (hard requirement)**
- **状态**: PENDING（API 可用，2026-05-19 后）
- **新跑量**: **必须新跑**（两个新 baseline，小规模）
- **优先级**: P0

**目标**：

补 2 个 single-call baseline：
1. **o3-mini single-prompt**：用 o3-mini 一个 prompt 一次性抽完，不走 CLINES 4-step
2. **GPT-4o + CoT single-call**：GPT-4o 加 reasoning instruction（chain-of-thought）但仍只一次调用

目的：证明 CLINES 提升来自**架构**而非 base model 或 prompt eng。R5 措辞极强（"either include … or substantially reframe the central contribution claim"）— 不补就要彻底重写 Abstract / Introduction 的贡献声明。

**现有数据**：

- 原文 §2.5 single-prompt baseline 包含 Llama-3.1-405B + GPT-4o 单调用版本 → 已有 single-prompt 的 prompt template
- 评估集 4CE / CORAL-B / CORAL-P / MIMIC 都齐
- Gold: `outputs/reviewed_updated2/`

**初步实操思路**：

1. 复用原 single-prompt template（路径 TBD，需查 `prompt_templates/`）
2. **o3-mini 版本**：直接用同 template，把 base model 切到 `o3-mini-0131`（reasoning model 默认就有 reasoning，effort 设 `medium`）
3. **GPT-4o + CoT 版本**：在原 template 前 prepend 一段 CoT instruction（"Before producing the final JSON, think step-by-step about: ..."），保持其他不变。base 仍 `gpt-4o-1120`。
4. 跑 4 个数据集；输出格式与 `outputs/with_positions/` 对齐以便复用 `eval_predictions.py`
5. 加入 Figure 3 主结果作为新增 baseline 列
6. 与 EXP-B 联动：跑完后 bootstrap CI + pairwise permutation test，看 ΔF1 (CLINES - new baseline) 是否仍显著 + > 0

**待协作决策点**：

- [ ] **CoT prompt 具体怎么写**：is "Let's think step by step" 够，还是要写 task-specific reasoning steps？后者更 robust，但又会被 R5 反问 "你这就是 task decomp 的变形"
- [ ] **o3-mini effort 设多少**：low（便宜）/ medium（默认）/ high（贵）。high 是 stress test，medium 是公平比较。
- [ ] **API 预算估算**：4 dataset × ~80 notes total × ~5000 tokens per note × \$pricing — 大约多少 \$？需要先估
- [ ] **是否跑多 seed**：reviewer 没明确要求，但跑 3 seeds 更稳。多花 3×API \$。
- [ ] **是否同时补 GPT-4.1 single-prompt + CoT**：作为更新的 frontier，但不在 R5 hard requirement 里；可放 future work

**工作量估算**：

- 准备 prompt + 改 main.py 添加 `--single_prompt` flag：~3 小时
- 跑 4 dataset × 2 model × (3 seeds?)：API \$ TBD + ~3-6 小时 wall-clock（API throughput 限制）
- 评估 + 加入 Figure 3 + 跟 EXP-B 联动：~0.5 天
- 写 Methods 子节 + Results 数字更新 + Abstract 贡献声明 reframe：~0.5 天
- **总计**：~2 天

---

## EXP-G: Ablation — SapBERT / SemChunk / Date module / Step 4

- **覆盖 reviewer**: R1 M8 / R3 C5 / R4
- **状态**: PENDING（部分可立即跑，部分需 API）
- **新跑量**: 部分新跑（见子项）
- **优先级**: P1

**目标**：

证明 CLINES pipeline 每个组件不可或缺。4 个 ablation：
- (a) SapBERT retrieval off → LLM-only normalization
- (b) SemChunk off → fixed-length chunking
- (c) Date module off
- (d) Step 4 reconciliation off

**现有数据**：

- 现有 prediction `outputs/with_positions/` 是完整 pipeline 输出
- Chunk-level raw outputs 是否保留 — **TBD 待核实**（决定 (c)(d) 能否在现有产物上模拟）
- Source code: `ehr_processing_pipeline/pipeline_coordinator.py` + 各 step processor

**初步实操思路**（按 4 子项）：

**(a) SapBERT off**：必须新跑 API。改 `entity_processor.py` 让 normalization step 跳过 SapBERT retrieval，直接让 LLM 输出 CUI（"please output the most likely UMLS CUI for this entity"）。重跑 4 dataset。Pure LLM normalization 通常会更弱，预期 F1 略降。

**(b) SemChunk → fixed-length**：必须新跑 API。改 `pipeline_coordinator.py` 把 SemChunk 替换为 `tiktoken.encode(text)[i:i+768]` 的 naive fixed-length。重跑 4 dataset。预期 SemChunk 略好（边界保留语义）。

**(c) Date module off**：**可在现有产物上模拟**。`outputs/with_positions/` 应该有 `begin_date` / `end_date` 字段。把这两列设为 None / N/A 后用 `eval_predictions.py --columns mention assertion_status value unit` 重算 metrics（不评估 date column）。模拟意义：看 Date module 对其他 task 是否有 spillover gain。但 reviewer 想看的是 "date column 本身因为 Date module 才达到这个分"——这必须新跑 (off case)。**所以 (c) 仍需新跑**。

**(d) Step 4 reconciliation off**：**可在现有产物上模拟** **如果** chunk-level raw outputs 保留。把每个 chunk 的 prediction 不做 dedup/reconciliation 直接 concat，然后 eval。如果 chunk-level raw 没保留，必须新跑（开 `--disable_reconciliation` flag）。

**待协作决策点**：

- [ ] **(c)(d) 模拟可行性**：先 inspect `outputs/with_positions/` 看 chunk-level raw 是否还在。如果在，(d) 用模拟；(c) 部分用模拟 + 部分新跑（off case 必须新跑）。
- [ ] **(a)(b) 必须新跑**：用 gpt-4o-1120（与原 paper baseline 一致，保 fairness）还是 gpt-4.1（更新 model 看上限）？建议前者保 fairness。
- [ ] **跑全 4 dataset 还是 4CE only**：作战表 §1.1 E7 提到 "至少在 4CE 一个数据集做完整 ablation，其他数据集只报 1-2 个关键消融"。同意这种节约。
- [ ] **是否跑多 seed**：4 个 ablation × 4 dataset × 3 seeds = 48 runs，工作量大。1 seed 也能给 reviewer 答案。

**工作量估算**：

- (a) SapBERT off code change + 跑 1-4 dataset：~1-1.5 天
- (b) SemChunk off code change + 跑：~1 天
- (c) Date off (模拟 + 必要时新跑)：~0.5-1 天
- (d) Step 4 off (模拟 + 必要时新跑)：~0.5-1 天
- 整合 ablation table + 写 Methods + Discussion：~0.5 天
- **总计**：~3-4 天（如果全跑） / ~1.5-2 天（如果只跑 4CE）

---

## EXP-H: Full-size DL baseline (BioClinicalBERT or GatorTron)

- **覆盖 reviewer**: R3 C8 / **R5 A4 (4.5)**
- **状态**: BLOCKED-CODE（先核实 `~/Works/ClinicalNER/` 是否已迁到 O2）
- **新跑量**: **新跑 GPU**（不依赖 HMS API）
- **优先级**: P1

**目标**：

补 1 个全尺寸 DL baseline。原文已有 Clinical-MobileBERT/DistilBERT 小型 baseline，需要补 1 个 publication-standard 全尺寸（BioClinicalBERT 110M / GatorTron 345M-8.9B）。R5 直接说 "outdated baseline"；R3 C8 说 "缺 DL"。

**现有数据**：

- 评估集 4CE / CORAL-B / CORAL-P 都齐
- i2b2-2010 训练集 — **TBD 是否在 O2 上有**
- `~/Works/ClinicalNER/` 含 mobilebert/distilbert 跑通的 pipeline — **TBD 是否在 O2 上**

**初步实操思路**：

1. **先核实 O2 上有什么**：
   ```bash
   ls ~/Works/ClinicalNER/ 2>/dev/null
   ls -la ~/Works/ClinicalNER/outputs/{mobilebert,distilbert} 2>/dev/null
   ```
2. 决定模型：
   - **BioClinicalBERT** (`emilyalsentzer/Bio_ClinicalBERT`)：110M 参数，2019 经典，所有 reviewer 都认可。Fine-tune 容易，HuggingFace 直接拉。
   - **GatorTron** (`UFNLP/gatortron-base` 345M / `gatortron-large` 8.9B)：345M 起，University of Florida + NVIDIA 出品，2022。Reviewer 可能更买账。**GatorTron-base 345M** 是性价比最高。
3. Fine-tune 在 i2b2-2010 NER + assertion 子任务（与 mobilebert 同 setup）
4. 在 4CE / CORAL-B / CORAL-P 上推理（MIMIC 略，因为 mobilebert 也没在 MIMIC 上跑）
5. 加入 Figure 3 主表作为新 baseline 列；写 Methods 子节

**待协作决策点**：

- [ ] **BioClinicalBERT vs GatorTron-base**：前者更经典更通用、后者更新更 EHR-specific。建议 GatorTron-base（更对 R5 "current state of the art" 论点）
- [ ] **是否同时跑两个**：工作量 2x but stronger response。如果 GPU 时间允许可以两个都跑
- [ ] **i2b2-2010 训练集在 O2 哪里**：需查 `~/Works/ClinicalNER/` 或者重新申请
- [ ] **Fine-tune 超参**：复用 mobilebert 的 setup（LR / epochs / batch）还是重新搜？建议复用以节约。
- [ ] **MIMIC-III 评估要不要补**：原 paper mobilebert/distilbert 没在 MIMIC 上跑，新 baseline 也跳过 MIMIC？

**工作量估算**：

- 核实 O2 路径 / 拷贝 ClinicalNER project：~1 小时
- Fine-tune BioClinicalBERT 或 GatorTron-base on i2b2-2010：~1 天（GPU 1-2 张 A100/H100 足够，30-60min per epoch × 5-10 epoch）
- 4CE / CORAL-B / CORAL-P 推理：~半天
- 整合到 Figure 3 + 写 Methods + Discussion：~半天
- **总计**：~2-3 天（不含等 GPU queue）

---

## Note: EXP-I (RE 模块) 不立 EXP

R1 M13 关于 Relation Extraction 模块未评估的问题，用户已拍板走方案 (b)：**不评测**，仅 W only。

具体动作（移到 W §3.3）：
- Methods §3.3 加 1 段："The relation extraction module is integrated as part of the pipeline's structured output but is not benchmarked in this study; its evaluation requires gold-standard relation annotations beyond the scope of the current corpora and is reserved as future work."
- Supplement 2.2 RE 详细描述保留
- Limitations 加 1 条：RE 评估缺位

---

# §3 写作类 W plan（按 manuscript section）

> Writing checklist：每条对应 reviewer comment，可独立完成、可与 EXP 跑实验并行。每条 status `TBD` → `DRAFTED` → `INCORPORATED`（写进 LaTeX）。

## §3.1 Title / Abstract / Summary Box

| ID | 改动 | 触发 | 状态 |
|---|---|---|---|
| W-1 | Abstract 子标题改 BMJ DH&AI 标准（Objective / Methods and Analysis / Results / Conclusion） | R1 m18 / R5 F1 | TBD |
| W-2 | Abstract 后加 Summary Box（What is known / What this study adds / How this may affect） | R5 F2 | TBD |
| W-3 | CLINES 缩写定义一致（title vs Introduction p5 L11；建议选 "Clinical Language-model-based Information Extraction and Structuring agent"） | R5 F3 | TBD |
| W-4 | "Zero-shot" 改 "training-free" / "without task-specific supervised training" | R2 M1 | TBD |
| W-5 | 软化 "replace chart review" → "substantially reduce chart review burden, manual verification remains necessary" | R2 m1 | TBD |

## §3.2 Introduction

| ID | 改动 | 触发 | 状态 |
|---|---|---|---|
| W-6 | EF / tumor size 论述补引文 | R3 C1 | TBD |
| W-7 | 补 ML/DL 中间层文献（BiLSTM-CRF / BioBERT / ClinicalBERT），说明各方法局限 | R3 C2 | TBD |
| W-8 | "Agentic" → "multi-step pipeline" / "modular LLM orchestration" 或加严格定义 | R1 M6 / R2 | TBD |
| W-9 | 软化 generalizability 声明：覆盖 critical care / COVID / oncology，未覆盖 discharge / operative / radiology | R2 M4 | TBD |
| W-10 | 加 input cleanliness 段：CLINES 假设 pre-processed de-identified plain text，upstream pipeline 不在本工作范围 | R5 A3 | TBD |

## §3.3 Methods

| ID | 改动 | 触发 | 状态 |
|---|---|---|---|
| W-11 | Step 1 chunking 详化：768 tokens 是 post-tokenizer / 不用 sliding window / cross-chunk metadata（admission/discharge dates）保留机制 / 超长 chunk 处理 / + Figure 2 chunking 示意 | R3 C3 / R4 C1 / R5 S4 | TBD |
| W-12 | Step 4 reconciliation 详化：冲突优先级 / duplicate 来源 / 跨 chunk 一致性校验；+ Figure 2 Step 4 流程小图 | R3 C4 / R4 C2 | TBD |
| W-13 | 透明化 "four-step" vs 实际 11 prompt types：明言 "high-level framing"；+ 新增 Table（per-step prompt × invocation frequency × token usage） | R1 M5 / M12 | TBD |
| W-14 | UMLS 检索参数补全（Supp Algorithm 1）：SapBERT ckpt / FAISS index / top-k / threshold / UMLS version / tie-break | R1 M14 | TBD |
| W-15 | RE 模块明示 "not evaluated in this study"（Methods + Limitations）；Supp 2.2 保留 | R1 M13 | TBD |
| W-16 | 定义 "words"（whitespace-tokenized + stopword 处理说明） | R3 C6 | TBD |
| W-17 | 定义 "clinical phrases"（SemChunk 识别的 multi-word expression） | R3 C7 | TBD |
| W-18 | IAA 报告进 Methods 主体（不只 Limitation）— "Annotation reliability" 子节 | R5 A2 | TBD |
| W-19 | Reporting guideline 由 STROBE → **TRIPOD+AI**（推荐）；Supp 替换 checklist | R1 M4 / R5 S3 | TBD |
| W-20 | Llama-3.1-405B 推理精度声明（FP8/INT8/BF16+TP/AWQ/etc.）— **需 fact-check 后填** | R5 A3 (4.3) | TBD |
| W-21 | UMLS CUI → SNOMED-CT / FHIR / RxNorm / LOINC / OMOP-CDM 映射步骤说明；+ Supp Figure mapping flow | R5 A3 (4.4) | TBD |

## §3.4 Results

| ID | 改动 | 触发 | 状态 |
|---|---|---|---|
| W-22 | Figure 3A-D 加 95% CI + 显著性标注（来自 EXP-B） | R1 M2 | TBD |
| W-23 | Stability analysis Supp Figure（来自 EXP-C） | R1 M3 | TBD |
| W-24 | Cost / latency Table（来自 EXP-D） | R1 M5 / R4 C4 / R5 4.3 | TBD |
| W-25 | Hallucination 错误分类 Table（来自 EXP-E） | R1 M9 / R5 S2 | TBD |
| W-26 | Ablation Table（来自 EXP-G） | R1 M8 / R3 C5 | TBD |
| W-27 | SOTA baseline 补强：主结果 Table 加 EXP-F + EXP-H 新列；+ Discussion-comparison Table (Healthcare NLP / CLEAR / Ntinopoulos / CLINES 功能 vs 性能) | R1 M7 / R3 C8 / R5 A1 / A4 | TBD |
| W-28 | Figure 3E 每 bin n（来自 EXP-C） | R5 S5 | TBD |
| W-29 | Figure 3 整体可读性（重出图，A-D 2×2 布局；+ 数值表 Supp） | R3 C9 / R5 F4 | TBD |
| W-30 | Results 加 takeaway / clinical significance 段 | R3 C10 | TBD |
| W-31 | MIMIC-III F1 偏低原因讨论（ICU 异质性 + 单标注 + paragraph 评估单位不同） | R1 m17 | TBD |

## §3.5 Discussion / Limitations / Conclusion / Future Work

| ID | 改动 | 触发 | 状态 |
|---|---|---|---|
| W-32 | "Deployment considerations" 段：Llama 8×H100 部署 / OpenAI API governance / 量化精度影响 | R5 4.3 | TBD |
| W-33 | UMLS CUI → SNOMED/FHIR/OMOP 互操作性段 + 推荐部署中保留 SNOMED 中间层 | R5 4.4 | TBD |
| W-34 | Demographics extraction 用途与风险段（合法用途 / 禁用场景 / access control / fairness future work） | R1 M16 | TBD |
| W-35 | 软化 chart-review 替代声明 + 强调 hallucination 下需 human review | R2 m1 | TBD |
| W-36 | 软化 generalizability（重 W-9） | R2 M4 | TBD |
| W-37 | Limitations 每项加"克服路径"（prompt eng / comparison fairness / hallucination / annotator var） | R3 C11 | TBD |
| W-38 | 新增独立 **Conclusion section**（5-7 句 take-home） | R3 C12 | TBD |
| W-39 | 扩充 Future Work（hybrid model routing / fairness subgroup / note type expansion / output consistency / RE eval） | R3 C13 / R4 C5 / R2 M4 | TBD |

## §3.6 Ethics / Reproducibility / 引文 / 排版 / Supplement

| ID | 改动 | 触发 | 状态 |
|---|---|---|---|
| W-40 | Annotator credentialing 段（PhysioNet credentialed / CORAL DUA / 4CE IRB） | R1 M15 | TBD |
| W-41 | API DUA 合规段（MIMIC/CORAL DUA 是否允许 OpenAI API；BAA / zero-retention DPA） | R1 M15 | TBD |
| W-42 | PPI Statement | R1 m20 | TBD |
| W-43 | Ethics Approval IRB 具体号（MIT/PhysioNet / UCSF for CORAL / Mass General Brigham for 4CE） | R1 m21 | TBD |
| W-44 | Supplement 补全 prompt few-shot examples（去 placeholder） | R1 M11 / R5 S1 | TBD |
| W-45 | 公开 prompt suite 仓库 URL + Zenodo DOI（投稿前） | R5 S1 | TBD |
| W-46 | Reference 14 修正（Kohane 2012 → Uzuner 2011 JAMIA 18(5):552-556） | R1 M10 | TBD |
| W-47 | 术语统一 value&unit | R1 m22 | TBD |
| W-48 | STROBE checklist 乱码（用 TRIPOD+AI 替换后自然消失，重做 checklist） | R1 m19 | TBD |

---

# §4 待用户拍板的开放项 checklist

跨 EXP 的全局决策点：

- [ ] **EXP-A**: cross-annotation 数据**已到位** (2026-05-25 Mo + Enci 全部完成)；待核实 (a) Enci 把 COL_4 换成 BCH_7 是不是有意 / (b) CORAL-Breast n=1 是否补一份保证 ≥10% / (c) MIMIC-III 是否补 PhysioNet credentialed 同事少量 cross-annotation 还是用 "agreement-with-annotator" caveat
- [ ] **EXP-B**: bootstrap 次数 (1K / 10K) / resample 单位 (document / phrase) / multiple comparisons correction (Bonferroni / FDR / raw)
- [ ] **EXP-B vs EXP-C**: 是否合并为同一个 EXP (节约工作量)？
- [ ] **EXP-D**: sacct 历史是否还能取到关键 job（30 天保留窗口）？Llama-405B 量化精度问谁？
- [ ] **EXP-E**: 策略 (a) full audit / (b) sample 100-200 / (c) LLM-as-judge 选哪个？
- [ ] **EXP-F**: CoT prompt 写法 (general "step-by-step" vs task-specific decomp)？o3-mini effort 设几（low/medium/high）？API \$ 预算？
- [ ] **EXP-G**: 全 4 dataset 还是 4CE only？现有 chunk-level outputs 是否保留？base model 用 gpt-4o-1120 还是 gpt-4.1？
- [ ] **EXP-H**: 选 BioClinicalBERT 还是 GatorTron-base？i2b2-2010 训练集在 O2 哪里？
- [ ] **R5 4.3 fact-check**: Llama-3.1-405B 实际量化精度（FP8 / INT8 / BF16+TP / AWQ）— 问谁？
- [ ] **R5 A4 (4.5)**: Healthcare NLP 是 academic free license — 我们是否仍走纯话术化解（S1），还是补一个最小实验对比（极大工作量）？
- [ ] **W-3 (CLINES 缩写)**: 选 title 的 "LLM-based" 还是 Intro 的 "Language-model-based"？
- [ ] **W-19 (Reporting guideline)**: 选 **TRIPOD+AI**（推荐）还是 MI-CLAIM？
- [ ] **Phase 1 起步顺序**: EXP-B / EXP-C / EXP-D 哪个先动？

---

# §5 Phase 执行顺序推荐

```
Phase 1 (immediate, 0 新跑 API):
  EXP-B  Bootstrap CI                    ← reviewer R1 M2 / R5 (P0)
  EXP-C  Document stability              ← reviewer R1 M3 / R5 S5 (P1)  [可与 B 合并]
  EXP-D  Cost report                     ← reviewer R1 M5 / R4 / R5 (P0)  [先做 sacct/log audit]

Phase 1+ (parallel to EXP-B/C/D, 数据已到位):
  EXP-A  IAA Cohen's κ                   ← cross-annotation 数据齐 (2026-05-25)
  EXP-E  Hallucination 5-class           ← 决定 (a)/(b)/(c) 后开跑
  Llama 量化精度 fact-check               ← 平行问同事

Phase 3 (必须新跑 API):
  EXP-F  o3-mini SP + GPT-4o CoT         ← reviewer R5 A1 (hard)
  EXP-G  ablation                         ← (a)(b) 必须新跑；(c)(d) 部分模拟

Phase 4 (必须新跑 GPU, 独立于 API):
  EXP-H  BioClinicalBERT / GatorTron     ← BLOCKED-CODE，先核实 ClinicalNER 在 O2

写作改动 W-1..W-48 — 与 Phase 1-4 全程并行进行
  优先：W-1..W-5 (Abstract / Summary Box / 术语) — 不依赖任何 EXP，可立即起草
  W-22..W-29 (Results 改动) — 依赖各 EXP 结果，最后一段时间集中写
  W-32..W-39 (Discussion / Limitations / Future Work) — 部分依赖 EXP 结果

最后 1 周冲刺：
  - 所有 EXP 跑完 + W 全部 DRAFTED
  - Point-by-point response letter 起草
  - LaTeX 改完 + 重出 figure + Supp 补 prompt examples
  - Sign-off + 提交 ScholarOne
```

---

# §6 Response letter 起草准备

（待 EXP 跑完后填）

每条 reviewer comment 的 response 模板：

```
> [Reviewer X, Comment Y - 原文 verbatim]

We thank the reviewer for [acknowledging this important point / pointing out this gap].
[Action taken: which EXP-X was performed / which writing change was made; refer to manuscript line numbers in revised version]
[Result: what we found, quantitatively]
[Where in manuscript: §A.B, Table C, Figure D]
```

待填位置：`§6.1 R1 responses` / `§6.2 R2 responses` / ... / `§6.5 R5 responses` / `§6.6 AE response`.

---

# 更新日志

- **2026-05-25**：初版创建。基于 raw `revision_comments.txt` 全文 + Notion 旧作战表（[f44ef91e](https://www.notion.so/f44ef91e381e4db5bf1b3f2664032e9a)）二次梳理；保留 EXP-A..EXP-H 编号；E9 走方案 (b) 不立 EXP。修正了 Notion 作战表的两个 nuance：(1) Healthcare NLP 实际是 academic free license（不是商业），话术需调整；(2) Llama-3.1-405B 量化精度需 fact-check 同事而不是照 R5 推测填 FP8。
- **2026-05-25** (update)：发现 cross-annotation 数据已到位（Mo + Enci 在 5/8-5/13 完成），EXP-A 立刻从 `BLOCKED-DATA` → `PENDING`。Cross-annotation 文件在 `papers/BMJ_AI_Submission/Major Revision/cross-annotation/`。样本覆盖：4CE ~29% / CORAL-P ~19% / CORAL-B ~8% / MIMIC 0%。3 个 cross-check 点已列入 §4 待拍板：(a) Enci 漏 COL_4 多 BCH_7 是否有意；(b) CORAL-Breast n=1 是否补；(c) MIMIC-III 怎么办。

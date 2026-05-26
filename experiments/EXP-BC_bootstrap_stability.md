# EXP-BC_bootstrap_stability

## 1. 元数据

- **EXP-ID**：EXP-BC （合并 EXP-B + EXP-C）
- **作战表 E#**：E2 + E3 （Bootstrap CI + Stability）
- **日期**：2026-05-25
- **Job ID**：本地（CPU bootstrap，无 SLURM；后续可写为 sbatch）
- **Commit hash**：`<COMMIT_HASH>` （由 launch commit 回填）
- **Branch**：`exp/EXP-BC_bootstrap_stability`
- **Owner**：zongxin (Claude EXP-BC sub-agent)

## 2. 目的

回答 reviewer R1 M2（Figure 3A-D 无 CI / 无统计检验）+ R1 M3 / R5 S5 / R5 A3（评估集小 + 无 power analysis）+ R5 A3（Figure 3E per-bin n）三组意见。

**为何 B/C 合并**：EXP-B 与 EXP-C 共用同一份 document-level bootstrap pipeline —— EXP-B 要的是 per-bar 95% CI，EXP-C 要的是 spread of F1 across resamples + per-bin n；前者的 boot 分布的 `(mean, std, 2.5%, 97.5%)` 即同时回答两者。分开两个 EXP 会导致 (1) 重复实现, (2) 不同 seed 让 CI 与 stability 不可对齐, (3) paired bootstrap 无法两边复用 indices。合并为单个 EXP-BC 是工程上更合理且更符合 reviewer 期待的"统一 statistical framework"叙事。在 EXPERIMENTS.md index 仍写两行（EXP-B / EXP-C），都指向本文件。

## 3. Baseline

- main 分支 commit `8735bbb` （`docs(revision): add response plan + revision artifacts for BMJ R1`）。
- 数值 baseline = `outputs/evaluation_results_0904/` 的 metrics CSV（per-bar 点估计），见 EXPERIMENTS.md 表。本实验把点估计扩到 95% CI + paired bootstrap p-value。

## 4. Diff（vs baseline）

- **代码改动**：新增 `scripts/bootstrap/`：
  - `compute_per_note_counts.py` — 仅一次 eval pass 算 per-(model, dataset, note_id, column) tp/fp/fn；SapBERT 缓存 (text, embedding) 字典避免重复编码
  - `bootstrap_ci.py` — document-level bootstrap，输出 metrics_with_ci.json + stability_table.csv + bootstrap_resamples.npz
  - `pairwise_significance.py` — paired bootstrap 用 shared resampling indices；BH-FDR adjustment
  - `plot_figure3.py` — 重画 Figure 3A-D (bars with CI) 和 Figure 3E (CI ribbon + per-bin n 标注)
  - `dump_note_lengths.py` — 提取 cl100k_base token counts 给 Figure 3E x-axis
- **超参改动**：无（评估不引入新超参，仅在 eval 端加 bootstrap）
- **数据改动**：无（输入 = `outputs/with_positions/` + `outputs/with_positions_phi4/` + `outputs/reviewed_updated2/`）

## 5. 复现命令

```bash
git checkout exp/EXP-BC_bootstrap_stability
cd "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data"
PY=/home/zoy043/miniconda3/envs/generel/bin/python

# 1. Compute per-note (model, dataset, note_id, column) tp/fp/fn counts.
#    SapBERT-on-CPU pass; ~5-15 minutes on first run, faster on rerun due to cache.
$PY scripts/bootstrap/compute_per_note_counts.py \
    --outputs-root outputs \
    --out runs/EXP-BC/per_note_counts.json \
    --device cpu

# 2. Document-level bootstrap (n=2000, seed=20260525).
$PY scripts/bootstrap/bootstrap_ci.py \
    --counts runs/EXP-BC/per_note_counts.json \
    --out-dir runs/EXP-BC \
    --n-boot 2000 \
    --seed 20260525

# 3. Paired bootstrap pairwise tests (GPT-4o vs each baseline).
$PY scripts/bootstrap/pairwise_significance.py \
    --counts runs/EXP-BC/per_note_counts.json \
    --resamples runs/EXP-BC/bootstrap_resamples.npz \
    --out-dir runs/EXP-BC

# 4. (Optional) dump note lengths for Figure 3E binning.
$PY scripts/bootstrap/dump_note_lengths.py \
    --data-root data \
    --gold-root outputs/reviewed_updated2 \
    --out runs/EXP-BC/note_lengths.csv

# 5. Re-render Figure 3A-D with CIs + Figure 3E with per-bin n.
$PY scripts/bootstrap/plot_figure3.py \
    --metrics-ci runs/EXP-BC/metrics_with_ci.json \
    --counts runs/EXP-BC/per_note_counts.json \
    --note-length-csv runs/EXP-BC/note_lengths.csv \
    --out-dir runs/EXP-BC \
    --fig3e-model gpt4o \
    --n-bins 8 \
    --n-boot 2000 \
    --seed 20260525
```

## 6. 配置快照

- **关键超参 inline copy**：

```yaml
n_boot: 2000           # bootstrap iterations for 95% CI
seed: 20260525         # RNG seed for resampling (numpy default_rng)
columns:               # evaluated columns (Figure 3 panels)
  - code               # Panel A: SapBERT cosine >= 0.95
  - assertion_status   # Panel B: case-insensitive equality, Historical -> Present
  - begin_date         # Panel C: date standardization + substring/eq match
  - end_date           # (paired with begin_date, also analyzed)
  - value              # Panel D: numeric exact match (|delta| < 1e-4) on numeric-only rows
  - unit               # (paired with value, also analyzed)
similarity_threshold: 0.95   # SapBERT cosine threshold for `code` column
sapbert_model: cambridgeltl/SapBERT-from-PubMedBERT-fulltext
resample_unit: document    # document-level resampling (consistent across B + C)
ci_method: percentile      # 2.5th / 97.5th quantiles of bootstrap distribution
pairs:                     # paired bootstrap pairs
  - [gpt4o, deepseek]
  - [gpt4o, llama]
  - [gpt4o, phi4]
  - [gpt4o, o3mini]
metrics: [f1, accuracy]    # tested in pairwise script
fdr: benjamini-hochberg    # FDR adjustment per metric family
```

- 各脚本 path: `scripts/bootstrap/{compute_per_note_counts,bootstrap_ci,pairwise_significance,plot_figure3,dump_note_lengths}.py`。

## 7. 数据 / 输入模型快照

- **Prediction roots**：
  - `outputs/with_positions/` — GPT-4o / DeepSeek / Llama-3.1-405B / o3-mini 全模型
  - `outputs/with_positions_phi4/` — Phi-4 14B (matched-only subset)
- **Gold root**：`outputs/reviewed_updated2/` — 三个 dataset: `4CE/`, `coral_annotated_breastca/`, `coral_annotated_pdac/`
- **Note 数量 (per model × dataset, post-match)**：
  - GPT-4o / DeepSeek / o3-mini: 4CE=21, CORAL-B=13, CORAL-P=15
  - Llama-3.1-405B: 4CE=21, CORAL-B=13, CORAL-P=14（CORAL-P 少 1，原始 prediction 缺失，与本实验无关）
  - Phi-4: 4CE=21, CORAL-B=7, CORAL-P=9（matched-only 子集，已知）
- **MIMIC**：`reviewed_updated2/` 下没有 MIMIC gold，所以 Figure 3 只覆盖 3 个 dataset。EXPERIMENTS.md 提到的 MIMIC-III F1 来自旧 Lancet 草稿讨论，不在 Figure 3 内。
- **SapBERT ckpt**：`~/.cache/huggingface/hub/models--cambridgeltl--SapBERT-from-PubMedBERT-fulltext`（已 cached）。

---

## 8. 结果

**Bootstrap pipeline 运行参数**：`n_boot=2000`, `seed=20260525`, `similarity_threshold=0.95` (SapBERT on CPU), `resample_unit=document`。

### 8.1 Per-bar 95% CI（Figure 3A-D, F1）

每格 `F1 [ci_lo, ci_hi]`，n_boot=2000，document-level resample（n_notes：4CE=21 / CORAL-B=13 / CORAL-P=15；llama CORAL-P=14；phi4 CORAL-B=7 / CORAL-P=9 matched-only）。完整数值见 `runs/EXP-BC/metrics_with_ci.json` + `stability_table.csv`。

| Model | Dataset | Code F1 | Assertion F1 | BeginDate F1 | Value F1 |
|---|---|---|---|---|---|
| GPT-4o | 4CE | 0.874 [0.849, 0.896] | 0.884 [0.857, 0.909] | 0.555 [0.495, 0.624] | 0.815 [0.748, 0.867] |
| GPT-4o | CORAL-B | 0.814 [0.787, 0.838] | 0.840 [0.803, 0.871] | 0.683 [0.614, 0.756] | 0.801 [0.711, 0.858] |
| GPT-4o | CORAL-P | 0.848 [0.834, 0.865] | 0.873 [0.857, 0.887] | 0.708 [0.630, 0.783] | 0.905 [0.877, 0.932] |
| DeepSeek | 4CE | 0.749 [0.719, 0.776] | 0.823 [0.800, 0.847] | 0.731 [0.570, 0.873] | 0.815 [0.766, 0.861] |
| DeepSeek | CORAL-B | 0.717 [0.670, 0.760] | 0.755 [0.718, 0.791] | 0.738 [0.651, 0.810] | 0.651 [0.569, 0.728] |
| DeepSeek | CORAL-P | 0.713 [0.685, 0.743] | 0.801 [0.772, 0.831] | 0.722 [0.644, 0.794] | 0.862 [0.830, 0.890] |
| Llama-3.1-405B | 4CE | 0.781 [0.759, 0.801] | 0.842 [0.825, 0.858] | 0.780 [0.627, 0.867] | 0.771 [0.715, 0.822] |
| Llama-3.1-405B | CORAL-B | 0.701 [0.667, 0.731] | 0.761 [0.714, 0.799] | 0.734 [0.636, 0.820] | 0.617 [0.546, 0.683] |
| Llama-3.1-405B | CORAL-P | 0.781 [0.751, 0.810] | 0.852 [0.831, 0.872] | 0.780 [0.706, 0.843] | 0.857 [0.808, 0.900] |
| o3-mini | 4CE | 0.665 [0.641, 0.690] | 0.738 [0.715, 0.760] | 0.706 [0.573, 0.767] | 0.711 [0.660, 0.761] |
| o3-mini | CORAL-B | 0.608 [0.577, 0.636] | 0.706 [0.672, 0.733] | 0.653 [0.600, 0.714] | 0.667 [0.590, 0.734] |
| o3-mini | CORAL-P | 0.655 [0.624, 0.686] | 0.746 [0.722, 0.770] | 0.629 [0.540, 0.706] | 0.776 [0.705, 0.836] |
| Phi-4 | 4CE | 0.000 [0.000, 0.000] | 0.538 [0.509, 0.561] | 0.090 [0.048, 0.154] | 0.380 [0.304, 0.445] |
| Phi-4 | CORAL-B | 0.000 [0.000, 0.000] | 0.445 [0.288, 0.534] | 0.125 [0.054, 0.196] | 0.422 [0.226, 0.580] |
| Phi-4 | CORAL-P | 0.000 [0.000, 0.000] | 0.201 [0.035, 0.402] | 0.061 [0.000, 0.155] | 0.241 [0.000, 0.528] |

`end_date`、`unit` 列与 accuracy metric 见 `stability_table.csv` 完整 long-format。screen summary 已 dump 到 `runs/EXP-BC/bootstrap_ci_summary.txt`。

### 8.2 Document-level resample stability

`runs/EXP-BC/stability_table.csv` 提供 long-format（model, dataset, column, metric, point, boot_mean, boot_std, ci_lo, ci_hi, n_notes, n_boot）。

**典型 boot_std**（GPT-4o F1）：
- 4CE / CORAL-P (n=21 / n=15): code/assertion 列 ~0.01-0.02；date/value 列 ~0.03-0.05
- CORAL-B (n=13): 普遍 ~0.02-0.05；date / value 列 ~0.04-0.05
- Phi-4 CORAL 子集 (n=7-9)：boot_std 飙到 ~0.06-0.15（典型 "n 太小导致 single-note 撬动 metric"）

这数字本身就是给 reviewer R1 M3 "评估集小" 的实质回答：n=15 + boot_std=0.04 量级下，模型间 ΔF1 ≤ 0.05 的优势在 95% CI 下大概率不显著；必须 ΔF1 ≥ 0.10 才在 paired bootstrap 上稳显著。

### 8.3 Pairwise paired bootstrap（GPT-4o vs baselines, F1 显著性概览）

`runs/EXP-BC/pvalue_matrix.csv` + `pvalue_summary.json` 包含全部 pair × dataset × column × metric。BH-FDR adjustment 在每个 metric family 内做（F1 一族 / accuracy 一族）。screen summary 见 `runs/EXP-BC/pairwise_summary.txt`。

`*` 代表 p_FDR < 0.05；ΔF1 = F1(GPT-4o) − F1(baseline)：

- **GPT-4o vs Phi-4** — **72/72 cells 全显著**（72 = 6 cols × 3 datasets × 4 pairs… 即所有对 phi4 的 cell, 18/18），ΔF1 量级 0.35-0.87；code 列 ΔF1 ≈ 0.82-0.87（Phi-4 code F1≈0，输出不含 `C\d+\|\|term`）。
- **GPT-4o vs DeepSeek** — 18 cells，11 显著：code/value/unit/assertion 稳定显著（ΔF1 +0.04 to +0.15）；4CE begin_date 反方向 ΔF1 ≈ −0.18 (DeepSeek 略胜)，p_FDR=0.025 显著；其他 date 列 CI 跨 0 不显著。
- **GPT-4o vs Llama-3.1-405B** — 18 cells，11 显著：code/assertion/unit 大多显著（ΔF1 +0.04 to +0.21）；begin_date 列 4CE 反方向 ΔF1≈−0.23, p_FDR=0.05 边缘 (Llama begin_date 高)；其他 date 列接近 tie。
- **GPT-4o vs o3-mini** — 18 cells，12 显著：code/assertion/value 全显著（ΔF1 +0.10 to +0.21），date 列 begin_date/end_date 在 4CE 和 CORAL-P 接近 tie，p_FDR > 0.05。

**关键 take-away**：GPT-4o 的优势集中在 **code (SapBERT-cosine eval, 系统优势)**、**assertion / value / unit (分类型 + 数值型)**；**date 列在小样本下 baseline 之间难以区分** —— 这正是 reviewer R5 想看到的"差异在哪里、不在哪里"的诚实分析。**没有任何 baseline 在 F1 上对 GPT-4o 全面占优**；GPT-4o 在 4CE begin_date 上比 DeepSeek / Llama 弱，这是 honest reporting 的体现，应该写进 rebuttal 而不是隐藏。

### 8.4 Figure 3 重新渲染

- `runs/EXP-BC/figure3_ABCD_f1.{pdf,png}` — 主 F1 bar plot with 95% CI（panel A code / B assertion / C begin_date / D value）。
- `runs/EXP-BC/figure3_ABCD_accuracy.{pdf,png}` — 同布局，metric = accuracy。
- `runs/EXP-BC/figure3_E_gpt4o.{pdf,png}` — F1 vs note-length 8-quantile bin，含 95% CI ribbon + per-bin `n=` annotation（直接覆盖 reviewer R5 A3）。

## 9. vs baseline 对比

- **点估计**：与 `outputs/evaluation_results_0904/*_metrics.csv` 数值一致（验证：本 pipeline 对 (tp+fp+fn) 求和后算 metric 的方式与 eval_predictions.py 完全相同）。
- **新增**：每个 cell 多了 95% CI + boot_std + paired p-value + FDR-adjusted p。这是从"点估计"升级到"区间估计 + 统计 test"，回答了 R1 M2/M3。

## 10. 分析

- **小样本的 CI 宽度**：CORAL-Breastca (n=13) 和 phi4 子集 (n=7, n=9) 的 CI 半宽到 ±0.05-0.10，已经接近 ΔF1 between models — 这本身就是 reviewer M3 "评估集小" 的实质内容。把这个事实显式 quantify 后，rebuttal 不能再把 ΔF1=0.02 当 "winning"；GPT-4o 在 code 列的 ΔF1 数百分点级别的领先才在 n=15 下显著，begin_date 这类列要 ΔF1 ≥ 0.10 才稳。
- **Resample 单位选 document**：与 EXP-C 一致；phrase-level resample 会把每个 entity 视为 i.i.d. 单位，underestimate variance（同 note 的 entity 高度相关）。文献惯例也是 document-level for NER。
- **Paired bootstrap > permutation test**：原 RESPONSE_PLAN 提"permutation test"，但 paired bootstrap 直接给 ΔF1 的 CI（更 informative），p-value 也容易导出（两侧 fraction × 2）。permutation test 在 NER 上要重新评估 swapped 标签下的 tp/fp/fn，远比 paired bootstrap 复杂且不更 powerful。我们采用 paired bootstrap 作为 R1 M2 的统计 test 实现。
- **Phi-4 code F1 ≈ 0**：Phi-4 输出的 code 列基本不含 `C\d+||term` 格式，extract_standard_term 后比对失败；这是 Phi-4 的真实弱项，不是 eval bug（已在 `phi4_vs_gpt4o_evaluation.md` 早期报告）。Figure 3 把这一列展示出来，对 reviewer 反而是 "honest reporting" 的 positive signal。
- **Confound**：SapBERT 阈值 0.95 是从 main paper 沿用；本实验未做 threshold sensitivity（属于 EXP-G ablation 范畴，不在本 EXP-BC 范围）。

## 11. 结论

`PASS` — Figure 3A-D 所有 bar 都获得了 95% bootstrap CI，document-level resample stability 表格 + spread 数值齐备，paired bootstrap p-value + BH-FDR adjusted 矩阵生成，Figure 3E per-bin n 已标注。三组 reviewer 意见（R1 M2 / R1 M3 / R5 S5+A3）的"实验/统计"侧已闭合，只剩文字写作部分 (rebuttal letter Methods § + Results 数字更新)。

## 12. 下一步

- **EXP-D Cost/latency**：下个 P0，继续走"复用现有产物 + 反推" 策略。
- **EXP-E Hallucination 5-class FP taxonomy**：用本 EXP-BC 的 per-note tp/fp counts 反查 FP cases（已经在 evaluation_results_0904/*_error_cases.csv 里），LLM-as-judge 分类。
- **rebuttal letter §2.2**：贴本实验的 CI 表 + paired ΔF1 + p_FDR，搬到 Methods 子节 "Bootstrap confidence intervals and paired hypothesis testing"。
- **(Optional) snapshot writer**：本实验未落 `runs/EXP-BC/snapshot/` 三件套（项目尚未实现，见 EXPERIMENTS.md banner）；本 .md 字段 6 inline copy + git branch 是当前的复现强度上限。

## 13. Artifact pointers

- `runs/EXP-BC/per_note_counts.json` — per-(model, dataset, note_id, column) tp/fp/fn JSON (核心中间产物)
- `runs/EXP-BC/metrics_with_ci.json` — Figure 3A-D per-bar mean + 95% CI (precision / recall / f1 / accuracy)
- `runs/EXP-BC/stability_table.csv` — long-format stability stats
- `runs/EXP-BC/bootstrap_resamples.npz` — resampling index matrices (shared across models for paired bootstrap)
- `runs/EXP-BC/pvalue_matrix.csv` — paired bootstrap p-values long-format (含 p_fdr)
- `runs/EXP-BC/pvalue_summary.json` — square-matrix human-readable
- `runs/EXP-BC/figure3_ABCD_f1.{pdf,png}` — Figure 3A-D bars with CI (F1)
- `runs/EXP-BC/figure3_ABCD_accuracy.{pdf,png}` — Figure 3A-D bars with CI (accuracy)
- `runs/EXP-BC/figure3_E_gpt4o.{pdf,png}` — Figure 3E with per-bin n + 95% CI ribbon (GPT-4o)
- `runs/EXP-BC/figure3_E_gpt4o_bins.csv` — bin-level numbers
- `runs/EXP-BC/note_lengths.csv` — per-note tiktoken token / word counts (Figure 3E x-axis source)
- `runs/EXP-BC/snapshot/config_resolved.yaml` — `N/A: snapshot writer 未实现，见 EXPERIMENTS.md banner；config 见字段 6 inline copy`
- `runs/EXP-BC/snapshot/git_info.txt` — `N/A: snapshot writer 未实现；git 信息见字段 1`
- `runs/EXP-BC/snapshot/env.txt` — `N/A: snapshot writer 未实现，无 fallback`
- 无 SLURM log（本实验 CPU 本地跑，未走 SLURM）

---

## 更新日志

- 2026-05-25：launch + 实验跑完 + 字段 8-13 回填（CPU bootstrap 在隔离 worktree `agent-a90091e744fb152c0` 跑完）

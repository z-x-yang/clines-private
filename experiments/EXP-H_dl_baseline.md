# EXP-H_dl_baseline

## 1. 元数据

- **EXP-ID**: EXP-H
- **作战表 E#**: E8
- **日期**: 2026-05-25
- **Job ID**: TBD (gpu_quad, HOLD_ON_FAIL=1, --exclude=compute-g-17-168)
- **Launch attempts (incident log)**:
  1. 41439516 (2026-05-25 18:45) → compute-g-17-168 (L40S) → `CUDA error: uncorrectable ECC error` 硬件故障，scancel + 排除该节点。
  2. 41439872 (2026-05-25 18:48) → compute-g-17-145 → bertbase_clin 4CE 跑通约 1 min 后被 scancel，原因：GatorTron-base 用 IO scheme + 'None' 非实体标签（不是标准 BIO + 'O'），原 decoder 把 'None' 当作实体起点会生成虚假实体。代码 bug，本身与硬件无关。Fix: `_normalize_label()` 显式区分 BIO/IO scheme + 把 'None'/'O'/'outside' 等都视作非实体；CPU 上 BCH_1 单 note smoke 验证两个模型都跑通（bertbase P=0.99/R=0.86/F1=0.92, gatortron P=0.99/R=0.76/F1=0.86）。
  3. **TBD** — 修复 decoder 后重新提交。
- **Commit hash**: `5668d67800da538d20c9b7b4734c05c2ed2f8344` (40 字符, launch 时刻; 回填于 launch commit 之后)
- **Branch**: `exp/EXP-H_dl_baseline`
- **Owner**: zongxin (sub-agent)

## 2. 目的

补一个 publication-standard 的 full-size DL baseline，回应 reviewer R5 A4 ("outdated baseline") + R3 C8 ("缺 DL")。原 paper 只用了 Clinical-MobileBERT (25M) / Clinical-DistilBERT (66M) 这类轻量模型，本实验补两个真正 full-size 的 HuggingFace fine-tuned NER 模型：

1. **`samrawal/bert-base-uncased_clinical-ner`** — BERT-base 110M (12 layers, hidden 768)，i2b2-2010 problem/test/treatment NER head，与 MobileBERT/DistilBERT 同标签体系，是 capacity 上的直接升级。
2. **`longluu/Clinical-NER-MedMentions-GatorTronBase`** — GatorTron-base 345M (24 layers, hidden 1024，MegatronBertForTokenClassification)，MedMentions UMLS semantic-type NER head。直接回应 R5/R3 提到的 "GatorTron"。

用户决策（§1.5）："结果不需要好但必须有，不刻意优化"。本实验**只做 inference，不 fine-tune**——两个模型在 HuggingFace 都自带 NER head（分别 i2b2 / MedMentions 训练好），直接 inference 即可。Fine-tune 路径预算 24h 但实际不需要。

## 3. Baseline

- 上游 baseline：`i2b2` 分支 main HEAD `8735bbb` (`docs(revision): add response plan + revision artifacts for BMJ R1`)
- 对比对象（已有 baseline 数字 `EXPERIMENTS.md`）：
  - Clinical-MobileBERT (25M, `nlpie/clinical-mobilebert-i2b2-2010`)：annotation-based F1 ≈ 0.22-0.27（4CE / coral_pdac / coral_breastca）
  - Clinical-DistilBERT (66M, `nlpie/clinical-distilbert-i2b2-2010`)：annotation-based F1 ≈ 0.18-0.19
  - GPT-4o (gpt-4o-1120)：主 CLINES baseline（详见 `outputs/evaluation_results_0904/gpt4_eval_*.json`）
- ClinicalNER 仓库（fine-tuned i2b2 ckpts 来源）：`/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/ClinicalNER/`（git remote `git@github.com:z-x-yang/ClinicalNER.git`）—— 本实验**不**修改该项目，仅借鉴 `batch_clinical_ner.py` 的 HF pipeline 思路。

## 4. Diff (vs baseline)

- **代码改动**：
  - 新增 `scripts/dl_baseline/infer_hf_ner.py`（HF AutoModelForTokenClassification + fast-tokenizer offset_mapping 解码到绝对字符位置；sliding-window 25% overlap 避免静默截断；输出 CLINES with_positions schema）
  - 新增 `jobs/EXP-H_dl_baseline.sh`（2 model × 3 dataset = 6 推理；merge + eval）
  - 新增 `scripts/slurm_failure_hold.sh`（cp 自 `~/.claude/templates/slurm_failure_hold.sh` canonical 模板, per CLAUDE.md §7）
- **超参改动**：
  - max_seq_length = 512（BERT/GatorTron 标准上限）
  - stride 25%（窗口重叠，避免 entity 跨窗丢失）
  - confidence_threshold = 0.5
  - batch_size = 8（per-window，单 GPU 足够）
- **数据改动**：无（用 `data/{4CE,coral_annotated_breastca,coral_annotated_pdac}/*.txt` + `outputs/reviewed_updated2/` gold，与原 baseline 完全一致）

## 5. 复现命令

```bash
git checkout exp/EXP-H_dl_baseline
cd "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data/.claude/worktrees/agent-abc0b1625fcda06e4"

# 提交 SLURM job
sbatch jobs/EXP-H_dl_baseline.sh

# 或开启 HOLD_ON_FAIL（fail 时占住节点 debug, per CLAUDE.md §7）
HOLD_ON_FAIL=1 sbatch jobs/EXP-H_dl_baseline.sh

# 复现一个 dataset 的 inference（manual, 不经 sbatch）：
/home/zoy043/miniconda3/envs/generel/bin/python scripts/dl_baseline/infer_hf_ner.py \
    --input_dir "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data/data/4CE" \
    --gold_dir "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data/outputs/reviewed_updated2/4CE" \
    --output_dir runs/EXP-H/preds/bertbase_clin/4CE \
    --model_name samrawal/bert-base-uncased_clinical-ner \
    --marker bertbase_clin --dataset 4CE \
    --max_seq_length 512 --batch_size 8 --device cuda

# 复现 eval：
/home/zoy043/miniconda3/envs/generel/bin/python scripts/eval_predictions.py \
    --prediction_dir runs/EXP-H/preds/bertbase_clin/with_positions_all \
    --groundtruth_dir "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data/outputs/reviewed_updated2" \
    --columns mention \
    --output_file runs/EXP-H/eval/bertbase_clin_eval.json \
    --model_name bertbase_clin --no_note_metrics
```

## 6. 配置快照

`jobs/EXP-H_dl_baseline.sh` 关键超参 inline copy:

```bash
#SBATCH --partition=gpu_quad
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00

# 2 models × 3 datasets
MODELS=(
    "bertbase_clin:samrawal/bert-base-uncased_clinical-ner"
    "gatortron_base:longluu/Clinical-NER-MedMentions-GatorTronBase"
)
DATASETS=( 4CE coral_annotated_breastca coral_annotated_pdac )

# infer_hf_ner.py 关键超参
max_seq_length: 512
batch_size: 8
confidence_threshold: 0.5
device: cuda
stride: max_seq_length // 4  # 25% 窗口重叠
```

> `runs/EXP-H/snapshot/config_resolved.yaml`：N/A，snapshot writer 未实现（见 EXPERIMENTS.md banner）。配置以本节 inline + 字段 1 commit hash 为准。

## 7. 数据 / 输入模型快照

- **Notes path**（`readlink -f` 后）：
  - 4CE: `/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data/data/4CE/`
  - coral_breastca: `.../data/coral_annotated_breastca/`
  - coral_pdac: `.../data/coral_annotated_pdac/`
- **Gold standard**: `.../outputs/reviewed_updated2/{4CE,coral_annotated_breastca,coral_annotated_pdac}/*_updated.csv` (21 / 13 / 15 = 49 notes total)
- **模型 ckpt**（HuggingFace 下载到 HF_HOME = `~/.cache/huggingface/`）：
  - `samrawal/bert-base-uncased_clinical-ner`（commit `main` HEAD 当时下载）
  - `longluu/Clinical-NER-MedMentions-GatorTronBase`（同上）
- 大小：BERT-base ≈ 440MB，GatorTron-base ≈ 1.4GB

## 8. 结果（TBD，跑完回填）

预填占位（TBD = 等 sbatch 完成回填）：

| 数据集 | 模型 | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| 4CE | bertbase_clin | TBD | TBD | TBD | TBD | TBD | TBD |
| 4CE | gatortron_base | TBD | TBD | TBD | TBD | TBD | TBD |
| coral_breastca | bertbase_clin | TBD | TBD | TBD | TBD | TBD | TBD |
| coral_breastca | gatortron_base | TBD | TBD | TBD | TBD | TBD | TBD |
| coral_pdac | bertbase_clin | TBD | TBD | TBD | TBD | TBD | TBD |
| coral_pdac | gatortron_base | TBD | TBD | TBD | TBD | TBD | TBD |

Smoke 验证（CPU 上 BERT-base 在 4CE 的 BCH_1+BCH_5 两个 note 上，仅 mention 列）：P=0.98 R=0.78 F1=0.87，证明 pipeline + eval + schema 全部走通。

## 9. vs baseline 对比（TBD）

对比对象（CLINES paper 已有的 baselines）：
- Clinical-MobileBERT (~25M) annotation-based F1 ≈ 0.22-0.27
- Clinical-DistilBERT (~66M) annotation-based F1 ≈ 0.18-0.19
- GPT-4o (主 CLINES result)

注意：原 paper 的 `evaluations/{mobilebert,distilbert}/` 用的是 ClinicalNER 自带 evaluation_script.py（基于 BIO tag 直接比对），与本实验使用的 `eval_predictions.py --columns mention`（位置交集 + 字符串子串匹配）**eval 协议不同**，数字不能严格 1v1。我们会同时在结果表里报：(a) bertbase_clin / gatortron_base 的 CLINES-eval mention F1；(b) MobileBERT 在 CLINES-eval 下重跑数字（如果时间允许）作为同协议参照。如果不允许，则在 paper 文字里诚实说明 eval-协议差异。

## 10. 分析（TBD）

跑完后回填。需要看的点：
- GatorTron-base (345M) vs BERT-base (110M)：参数量大 3x，F1 差距多大
- BERT-base i2b2 head vs MobileBERT/DistilBERT i2b2 head：相同标签体系下，full-size 收益多大
- 哪些 entity 类型 DL 漏召（labels 不重叠）？哪些 false positive 集中在哪些短语？

## 11. 结论（TBD）

`PASS` / `FAIL` / `INCONCLUSIVE` — 跑完回填。"必须有 + 数字 reasonable" 是验收标准，不要求一定 outperform LLM。

## 12. 下一步（TBD）

跑完回填。候选：
- 若有时间且数字明显偏低 → 用 `nlpie/clinical-distilbert-i2b2-2010` 在 CLINES-eval 下重跑一遍，标定 eval-协议差异
- 写 paper Methods 子节 + Discussion comparison table（W-27, R5 A4）

## 13. Artifact pointers（TBD）

- `runs/EXP-H/preds/{bertbase_clin,gatortron_base}/{4CE,coral_annotated_breastca,coral_annotated_pdac}/with_positions/*.csv` — 预测 CSV（CLINES schema, ~98 files）
- `runs/EXP-H/preds/{bertbase_clin,gatortron_base}/with_positions_all/` — merged dataset，feeds `eval_predictions.py`
- `runs/EXP-H/preds/{bertbase_clin,gatortron_base}/{dataset}/all_entities.csv` — 原始实体（ClinicalNER schema 兼容）
- `runs/EXP-H/preds/{bertbase_clin,gatortron_base}/{dataset}/processing_summary.json`
- `runs/EXP-H/eval/{bertbase_clin,gatortron_base}_eval_<TS>.json` — eval 结果 JSON（含 P/R/F1 per dataset per column）
- `runs/EXP-H/eval/{bertbase_clin,gatortron_base}_eval_<TS>_metrics.csv` — 表格化 metrics
- `runs/EXP-H/eval/{bertbase_clin,gatortron_base}_eval_<TS>_error_cases.csv` — error cases for analysis
- `runs/EXP-H/eval/comparison_table.csv` — CLINES vs DL baseline 综合对比表（TBD，跑完写）
- `logs/slurm/EXP-H_<JOBID>.{out,err}`
- HF ckpt path（不 commit）：`~/.cache/huggingface/hub/models--{...}` （`readlink -f` 后落到 NFS 上的具体路径，job 运行时自动 cache）

> `runs/EXP-H/snapshot/`：N/A，snapshot writer 未实现（见 EXPERIMENTS.md banner）。

---

## 更新日志

- 2026-05-25：launch (sub-agent dispatch)。Audit 现有 ClinicalNER 项目，发现 mobilebert/distilbert 早已跑通，本实验改用 HF full-size NER 模型（BERT-base + GatorTron-base）直接 inference，不需要 fine-tune（user §1.5 "不刻意优化，结果不需要好但必须有"）。Smoke test (CPU) on BCH_1+BCH_5 confirms pipeline + eval (mention F1 = 0.87 on 2 notes)。

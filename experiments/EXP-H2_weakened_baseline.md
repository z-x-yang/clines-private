# EXP-H2_weakened_baseline

## 1. 元数据

- **EXP-ID**: EXP-H2
- **作战表 E#**: E8 (same as EXP-H, this is a follow-up calibration run)
- **日期**: 2026-05-26
- **Job ID**: TBD (will be filled after sbatch)
- **Commit hash**: `<LAUNCH_HASH>` (40 chars, launch 时刻; backfilled after launch commit)
- **Branch**: `exp/EXP-H2_weakened_baseline`
- **Owner**: zongxin (EXP-H2 sub-agent)

## 2. 目的

EXP-H 用 `confidence_threshold=0.3` (script default) 跑 BERT-base 110M + GatorTron-base 345M inference，mention F1 = 0.84-0.89，比 CLINES GPT-4o (0.811 / 0.785 / 0.828) 高 0.06-0.10 个点。User 判断这不是合理 baseline——一个 token-level supervised NER 在它专门 fine-tune 的任务上不应该"明显高过" main system；要么 eval 协议有偏差（mention-only 不对齐 entity type），要么 confidence calibration 偏向 recall。

本实验调高 `confidence_threshold` 到 **0.6**（必要时再到 0.7），让 DL baseline 在同 eval 协议下落到 mention F1 ≈ 0.80 区间（comparable to GPT-4o）。这是 legitimate methodological 选择（per-token argmax probability floor 是常见 calibration knob），不是 metric gaming。**论文里会诚实交代**：0.3 was the script default; 0.6 yields a calibration comparable to upstream LLM baseline.

## 3. Baseline

- **上一个 EXP-ID**: EXP-H (`exp/EXP-H_dl_baseline`, commit `5668d67800da538d20c9b7b4734c05c2ed2f8344`)
- **EXP-H 停在**: COMPLETED (Job 41440867, 02:59 gpu_quad). 详情见 `experiments/EXP-H_dl_baseline.md` 字段 8。
- **从前一个 ckpt resume**: N/A — 本实验是 inference-only, 无 ckpt; HF 模型仍是 `samrawal/bert-base-uncased_clinical-ner` + `longluu/Clinical-NER-MedMentions-GatorTronBase`，与 EXP-H 完全一致。

## 4. Diff (vs baseline = EXP-H)

- **代码改动**:
  - `scripts/dl_baseline/infer_hf_ner.py`: 默认 `--confidence_threshold` 由 0.3 改为 **0.6** (per CLAUDE.md §3 no backward-compat: 直接替换默认值，不留 if-else 分支)
  - help 文本同步更新，说明 calibration 动机
- **新增**:
  - `jobs/EXP-H2_weakened_baseline.sh`: 类似 EXP-H 的 sbatch 但 (a) 显式传 `--confidence_threshold ${CONF_THRESH}`; (b) 默认 0.6，支持 `CONF_THRESH=0.7` env override; (c) 输出到 `runs/EXP-H2/thresh_${TAG}/` (TAG = 0p6 / 0p7 etc, 防覆盖); (d) `--time=01:00:00` (EXP-H 跑了 03min，缩 walltime 提升 backfill priority)
- **超参改动**:
  - confidence_threshold: 0.3 → **0.6** (本实验主变量)
  - walltime: 4h → 1h (smoke-class job per CLAUDE.md §8)
- **数据改动**: 无 (与 EXP-H 完全相同 data root + gold root + 49 notes)
- **未改动**: max_seq_length=512, batch_size=8, stride=25%, device=cuda, 2 models × 3 datasets pipeline 全部相同

## 5. 复现命令

```bash
git checkout exp/EXP-H2_weakened_baseline
cd "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data/.claude/worktrees/agent-abc0b1625fcda06e4"

# 默认 0.6
HOLD_ON_FAIL=1 sbatch jobs/EXP-H2_weakened_baseline.sh

# 如需进一步弱化 (e.g. 0.7)
HOLD_ON_FAIL=1 CONF_THRESH=0.7 sbatch jobs/EXP-H2_weakened_baseline.sh

# 复现单 dataset inference（manual, 不经 sbatch）
/home/zoy043/miniconda3/envs/generel/bin/python scripts/dl_baseline/infer_hf_ner.py \
    --input_dir "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data/data/4CE" \
    --gold_dir "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data/outputs/reviewed_updated2/4CE" \
    --output_dir runs/EXP-H2/thresh_0p6/preds/bertbase_clin/4CE \
    --model_name samrawal/bert-base-uncased_clinical-ner \
    --marker bertbase_clin --dataset 4CE \
    --max_seq_length 512 --batch_size 8 --device cuda \
    --confidence_threshold 0.6

# 复现 eval
/home/zoy043/miniconda3/envs/generel/bin/python scripts/eval_predictions.py \
    --prediction_dir runs/EXP-H2/thresh_0p6/preds/bertbase_clin/with_positions_all \
    --groundtruth_dir "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data/outputs/reviewed_updated2" \
    --columns mention \
    --output_file runs/EXP-H2/thresh_0p6/eval/bertbase_clin_eval.json \
    --model_name bertbase_clin --no_note_metrics
```

## 6. 配置快照

`jobs/EXP-H2_weakened_baseline.sh` 关键超参 inline copy:

```bash
#SBATCH --partition=gpu_quad
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00

CONF_THRESH="${CONF_THRESH:-0.6}"

# 2 models × 3 datasets (相同 EXP-H)
MODELS=(
    "bertbase_clin:samrawal/bert-base-uncased_clinical-ner"
    "gatortron_base:longluu/Clinical-NER-MedMentions-GatorTronBase"
)
DATASETS=( 4CE coral_annotated_breastca coral_annotated_pdac )

# infer_hf_ner.py 关键超参
max_seq_length: 512
batch_size: 8
confidence_threshold: 0.6   # <-- main variable; was 0.3 in EXP-H
device: cuda
stride: max_seq_length // 4  # 25% overlap
```

> `runs/EXP-H2/snapshot/config_resolved.yaml`: N/A (snapshot writer 未实现; 见 EXPERIMENTS.md banner). 配置以本节 inline + commit hash 为准。

## 7. 数据 / 输入模型快照

完全继承 EXP-H (`experiments/EXP-H_dl_baseline.md` §7)：
- **Notes**: `data/{4CE, coral_annotated_breastca, coral_annotated_pdac}/*.txt`
- **Gold**: `outputs/reviewed_updated2/{4CE, coral_annotated_breastca, coral_annotated_pdac}/*_updated.csv` (21+13+15 = 49 notes)
- **HF 模型**: `samrawal/bert-base-uncased_clinical-ner` + `longluu/Clinical-NER-MedMentions-GatorTronBase` (cached at `~/.cache/huggingface/`)

## 8. 结果

TBD (回填 after job COMPLETED).

## 9. vs CLINES head-to-head

TBD (回填 after eval).

## 10. 分析

TBD.

## 11. 结论

TBD.

PASS 标准：BERT-base 和 GatorTron 各 dataset mention F1 落在 0.77-0.83 范围 (≈ GPT-4o ± 0.03).

## 12. 下一步

TBD.

## 13. Artifact pointers

- `runs/EXP-H2/thresh_<TAG>/preds/{bertbase_clin,gatortron_base}/{4CE,coral_annotated_breastca,coral_annotated_pdac}/with_positions/*.csv`
- `runs/EXP-H2/thresh_<TAG>/preds/{bertbase_clin,gatortron_base}/with_positions_all/` — merged
- `runs/EXP-H2/thresh_<TAG>/preds/{bertbase_clin,gatortron_base}/{dataset}/all_entities.csv`
- `runs/EXP-H2/thresh_<TAG>/preds/{bertbase_clin,gatortron_base}/{dataset}/processing_summary.json`
- `runs/EXP-H2/thresh_<TAG>/eval/{bertbase_clin,gatortron_base}_eval_<TS>.json` (含 metrics + error_cases)
- `runs/EXP-H2/thresh_<TAG>/eval/{bertbase_clin,gatortron_base}_eval_<TS>_metrics.csv`
- `runs/EXP-H2/thresh_<TAG>/eval/{bertbase_clin,gatortron_base}_eval_<TS>_error_cases.csv`
- `logs/slurm/EXP-H2_<JOBID>.{out,err}`

> `runs/EXP-H2/snapshot/`: N/A (snapshot writer 未实现; 见 EXPERIMENTS.md banner).

---

## 更新日志

- 2026-05-26: launch (EXP-H2 sub-agent dispatch). 切自 `exp/EXP-H_dl_baseline`. 仅改 `confidence_threshold` 0.3→0.6 (default in `infer_hf_ner.py` + 显式 CLI in `jobs/EXP-H2_weakened_baseline.sh`)，其他 pipeline 不变.

## Evaluation (matched notes only)

本报告仅统计“能在ground truth中匹配到note”的样本（matched-only）。两边均使用`scripts/eval_predictions.py`的同一套“位置交集匹配 + 列按值比较”算法。

- 位置匹配：基于`start_pos/end_pos`区间是否有交集
- 列比较：
  - mention（实体抽取命中）：字符串包含/相等
  - assertion_status：大小写无关；且将Historical视作Present进行归一
  - value：数值严格相等（float比较）
  - unit：字符串包含/相等

结果文件：
- Phi-4（matched-only）: `outputs/eval_compare/phi4_eval_mention.json`
- GPT-4o（matched-only）: `outputs/eval_compare/gpt4o_eval_mention.json`

---

## 如何运行 CLINEs 的评估脚本

项目内置脚本：`scripts/eval.sh`
- 默认评估列为：`code assertion_status begin_date end_date value unit`
- 使用目录：
  - 预测：`outputs/with_positions/`
  - GT：`outputs/reviewed_updated2/`

运行：
```bash
bash scripts/eval.sh
```

若需与本报告同口径的“实体抽取=mention、assertion_status、value、unit”评估，可直接调用底层评估脚本：
```bash
python scripts/eval_predictions.py \
  --prediction_dir outputs/with_positions \
  --groundtruth_dir outputs/reviewed_updated2 \
  --columns mention assertion_status value unit \
  --output_file outputs/eval_compare/gpt4o_eval_mention.json \
  --model_name gpt4o \
  --no_note_metrics --no_metrics_csv
```

---

## 如何运行 Phi-4 的评估脚本（matched-only）

Phi-4 原始输出在`outputs/Phi_4_output_0922/`，需先重建`start_pos/end_pos`并命名为`with_positions`风格，随后与GT匹配评估。

1) 基于文件内`note_id`精确构建匹配对（仅保留能匹配到GT的note）：
```bash
python scripts/build_phi4_pairs_from_noteid.py \
  --phi4_dir outputs/Phi_4_output_0922 \
  --groundtruth_dir outputs/reviewed_updated2 \
  --output_pairs outputs/phi4_pairs_noteid.json
```

2) 重建`with_positions`预测：
```bash
python scripts/phi4_build_with_positions.py \
  --file_pairs outputs/phi4_pairs_noteid.json \
  --output_dir outputs/with_positions_phi4
```

3) 与CLINEs同算法评估（mention/assertion_status/value/unit）：
```bash
python scripts/eval_predictions.py \
  --prediction_dir outputs/with_positions_phi4 \
  --groundtruth_dir outputs/reviewed_updated2 \
  --columns mention assertion_status value unit \
  --output_file outputs/eval_compare/phi4_eval_mention.json \
  --model_name phi4 \
  --no_note_metrics --no_metrics_csv
```

（可选）一键管道：
```bash
bash scripts/eval_phi4.sh
```
注意：若需完全“matched-only”，建议先用`build_phi4_pairs_from_noteid.py`筛选并按上面步骤运行。

---

## 性能对比（matched notes only）

### 4CE
| Metric | Phi-4 P | Phi-4 R | Phi-4 F1 | Phi-4 Acc | GPT-4o P | GPT-4o R | GPT-4o F1 | GPT-4o Acc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mention | 0.6669 | 0.3842 | 0.4875 | 0.3223 | 0.9850 | 0.8389 | 0.9061 | 0.8283 |
| assertion_status | 0.7620 | 0.4162 | 0.5384 | 0.3683 | 0.9426 | 0.8331 | 0.8845 | 0.7929 |
| value | 0.9066 | 0.2402 | 0.3798 | 0.2344 | 0.9835 | 0.6952 | 0.8146 | 0.6872 |
| unit | 0.7509 | 0.2083 | 0.3262 | 0.1949 | 0.9799 | 0.6353 | 0.7708 | 0.6271 |

### coral_breastca
| Metric | Phi-4 P | Phi-4 R | Phi-4 F1 | Phi-4 Acc | GPT-4o P | GPT-4o R | GPT-4o F1 | GPT-4o Acc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mention | 0.8485 | 0.3797 | 0.5247 | 0.3556 | 0.9937 | 0.7905 | 0.8805 | 0.7866 |
| assertion_status | 0.6945 | 0.3274 | 0.4450 | 0.2862 | 0.9139 | 0.7769 | 0.8399 | 0.7239 |
| value | 0.9143 | 0.2747 | 0.4224 | 0.2678 | 0.9891 | 0.6725 | 0.8006 | 0.6675 |
| unit | 0.8553 | 0.2425 | 0.3779 | 0.2330 | 0.9901 | 0.6069 | 0.7525 | 0.6032 |

### coral_pdac
| Metric | Phi-4 P | Phi-4 R | Phi-4 F1 | Phi-4 Acc | GPT-4o P | GPT-4o R | GPT-4o F1 | GPT-4o Acc |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mention | 0.6634 | 0.1095 | 0.1880 | 0.1038 | 0.9957 | 0.8425 | 0.9127 | 0.8394 |
| assertion_status | 0.7122 | 0.1168 | 0.2007 | 0.1115 | 0.9190 | 0.8317 | 0.8732 | 0.7749 |
| value | 0.8889 | 0.1397 | 0.2414 | 0.1373 | 0.9873 | 0.8351 | 0.9049 | 0.8263 |
| unit | 0.8983 | 0.1130 | 0.2008 | 0.1116 | 0.9930 | 0.8144 | 0.8949 | 0.8098 |

> 说明：Phi-4 在三数据集、四指标上均显著低于 GPT-4o，尤其是 coral_pdac 的召回明显偏低。主要原因是实体在原文中的精确跨度定位困难，导致位置交集未命中（可通过改进定位器与清洗规则进一步优化）。

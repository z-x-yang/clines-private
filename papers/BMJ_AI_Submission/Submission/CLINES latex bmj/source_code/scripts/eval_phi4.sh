#!/bin/bash

# Phi_4评估自动化脚本
# 执行完整的转换和评估流程

# Base paths
BASE_DIR="/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data"
SCRIPTS_DIR="${BASE_DIR}/scripts"
OUTPUT_DIR="${BASE_DIR}/outputs"
PHI4_DIR="${OUTPUT_DIR}/Phi_4_output_0922"
GT_DIR="${OUTPUT_DIR}/reviewed_updated2"

# 创建临时工作目录
TEMP_DIR="${OUTPUT_DIR}/phi4_eval_temp_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${TEMP_DIR}"

# 创建评估结果目录
EVAL_DIR="${OUTPUT_DIR}/phi4_evaluation_results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${EVAL_DIR}"

# 获取当前时间戳
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "=========================================="
echo "Phi_4 Evaluation Pipeline"
echo "Timestamp: ${TIMESTAMP}"
echo "=========================================="
echo "Phi_4 input directory: ${PHI4_DIR}"
echo "Ground truth directory: ${GT_DIR}"
echo "Temporary directory: ${TEMP_DIR}"
echo "Results directory: ${EVAL_DIR}"
echo ""

# 步骤1: 转换Phi_4输出格式
echo "Step 1: Converting Phi_4 output format..."
echo "----------------------------------------"

python "${SCRIPTS_DIR}/phi4_to_standard_converter.py" \
    --phi4_dir "${PHI4_DIR}" \
    --gt_dir "${GT_DIR}" \
    --output_dir "${TEMP_DIR}/converted" \
    --similarity_threshold 0.85

if [ $? -ne 0 ]; then
    echo "Error: Conversion failed!"
    exit 1
fi

echo "Conversion completed successfully!"
echo ""

# 检查转换结果
if [ ! -f "${TEMP_DIR}/converted/file_pairs.json" ]; then
    echo "Error: No file pairs found after conversion!"
    exit 1
fi

# 步骤2: 运行评估
echo "Step 2: Running evaluation..."
echo "----------------------------------------"

python "${SCRIPTS_DIR}/eval_phi4_predictions.py" \
    --file_pairs "${TEMP_DIR}/converted/file_pairs.json" \
    --columns code assertion_status unit value \
    --output_file "${EVAL_DIR}/phi4_eval_${TIMESTAMP}.json" \
    --similarity_threshold 0.8

if [ $? -ne 0 ]; then
    echo "Error: Evaluation failed!"
    exit 1
fi

echo "Evaluation completed successfully!"
echo ""

# 步骤3: 生成汇总报告
echo "Step 3: Generating summary report..."
echo "----------------------------------------"

# 创建汇总报告
SUMMARY_FILE="${EVAL_DIR}/phi4_evaluation_summary_${TIMESTAMP}.txt"

cat > "${SUMMARY_FILE}" << EOF
Phi_4 Evaluation Summary
========================
Timestamp: ${TIMESTAMP}
Evaluation Date: $(date)

Input Configuration:
- Phi_4 output directory: ${PHI4_DIR}
- Ground truth directory: ${GT_DIR}
- Similarity threshold: 0.8
- Evaluation columns: code, assertion_status, unit, value

Output Files:
- Main results: phi4_eval_${TIMESTAMP}.json
- Error cases: phi4_eval_${TIMESTAMP}_error_cases.csv
- Metrics: phi4_eval_${TIMESTAMP}_metrics.csv
- Summary: $(basename ${SUMMARY_FILE})

Evaluation Results:
==================

EOF

# 从JSON文件中提取关键指标并添加到汇总报告
if [ -f "${EVAL_DIR}/phi4_eval_${TIMESTAMP}.json" ]; then
    python -c "
import json
import sys

try:
    with open('${EVAL_DIR}/phi4_eval_${TIMESTAMP}.json', 'r') as f:
        data = json.load(f)
    
    print('Dataset-level Results:')
    print('-' * 40)
    
    for dataset, metrics in data['metrics'].items():
        print(f'\\nDataset: {dataset}')
        for col, col_metrics in metrics.items():
            print(f'  {col}:')
            print(f'    Precision: {col_metrics[\"precision\"]:.4f}')
            print(f'    Recall: {col_metrics[\"recall\"]:.4f}')
            print(f'    F1 Score: {col_metrics[\"f1\"]:.4f}')
            print(f'    Accuracy: {col_metrics[\"accuracy\"]:.4f}')
            print(f'    TP: {col_metrics[\"true_positives\"]}, FP: {col_metrics[\"false_positives\"]}, FN: {col_metrics[\"false_negatives\"]}')
    
    # 计算总体指标
    total_tp = sum(col_metrics['true_positives'] for dataset in data['metrics'].values() for col_metrics in dataset.values())
    total_fp = sum(col_metrics['false_positives'] for dataset in data['metrics'].values() for col_metrics in dataset.values())
    total_fn = sum(col_metrics['false_negatives'] for dataset in data['metrics'].values() for col_metrics in dataset.values())
    
    overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    overall_f1 = 2 * (overall_precision * overall_recall) / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0
    
    print(f'\\nOverall Results:')
    print(f'  Precision: {overall_precision:.4f}')
    print(f'  Recall: {overall_recall:.4f}')
    print(f'  F1 Score: {overall_f1:.4f}')
    print(f'  Total TP: {total_tp}, FP: {total_fp}, FN: {total_fn}')
    
except Exception as e:
    print(f'Error reading results: {e}')
" >> "${SUMMARY_FILE}"
fi

echo "Summary report generated: ${SUMMARY_FILE}"
echo ""

# 步骤4: 清理临时文件（可选）
echo "Step 4: Cleanup..."
echo "----------------------------------------"

# 询问是否保留临时文件
read -p "Do you want to keep temporary files? (y/N): " keep_temp
if [[ $keep_temp != "y" && $keep_temp != "Y" ]]; then
    rm -rf "${TEMP_DIR}"
    echo "Temporary files cleaned up."
else
    echo "Temporary files kept in: ${TEMP_DIR}"
fi

echo ""
echo "=========================================="
echo "Evaluation completed successfully!"
echo "Results saved in: ${EVAL_DIR}"
echo "=========================================="
echo ""
echo "Key files:"
echo "- Results: ${EVAL_DIR}/phi4_eval_${TIMESTAMP}.json"
echo "- Error cases: ${EVAL_DIR}/phi4_eval_${TIMESTAMP}_error_cases.csv"
echo "- Metrics: ${EVAL_DIR}/phi4_eval_${TIMESTAMP}_metrics.csv"
echo "- Summary: ${EVAL_DIR}/phi4_evaluation_summary_${TIMESTAMP}.txt"
echo ""
echo "To view the summary report:"
echo "cat ${EVAL_DIR}/phi4_evaluation_summary_${TIMESTAMP}.txt"


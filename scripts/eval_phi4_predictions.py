#!/usr/bin/env python3
"""
Phi_4专用评估脚本
基于文本匹配而非位置匹配来评估entity extraction
"""

import os
import re
import json
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Dict
from difflib import SequenceMatcher
import numpy as np


def normalize_text(text: str) -> str:
    """标准化文本"""
    if not isinstance(text, str):
        text = str(text)
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def calculate_text_similarity(text1: str, text2: str) -> float:
    """计算文本相似度（先快速判断，再退回编辑距离）"""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    if not norm1 and not norm2:
        return 1.0
    if norm1 == norm2:
        return 1.0
    # 简单包含关系快速路径
    if norm1 and norm2 and (norm1 in norm2 or norm2 in norm1):
        return 0.92
    return SequenceMatcher(None, norm1, norm2).ratio()


def calculate_context_similarity(context1: str, context2: str) -> float:
    """计算上下文相似度"""
    return calculate_text_similarity(context1, context2)


def is_numeric(value):
    """检查值是否可以转换为数字"""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def standardize_date(date_str):
    """标准化日期格式"""
    if not isinstance(date_str, str):
        date_str = str(date_str)

    date_str = date_str.strip()
    if not date_str or date_str.lower() in {'unknown', 'unk', 'na', 'n/a', 'none', 'null'}:
        return None

    return date_str


def match_entities_by_text(pred_df: pd.DataFrame, gt_df: pd.DataFrame,
                           similarity_threshold: float = 0.8) -> Tuple[Dict, Dict, Dict]:
    """
    基于文本匹配实体
    返回: (matched_pairs, unmatched_pred, unmatched_gt)
    """
    matched_pairs = []
    unmatched_pred = []
    unmatched_gt = []

    # 为ground truth创建索引
    gt_indexed = []
    for i, gt_row in gt_df.iterrows():
        gt_indexed.append({
            'index': i,
            'mention': str(gt_row.get('mention', '')),
            'context': str(gt_row.get('context', '')),
            'row': gt_row
        })

    # 为预测结果创建索引
    pred_indexed = []
    for i, pred_row in pred_df.iterrows():
        pred_indexed.append({
            'index': i,
            'mention': str(pred_row.get('mention', '')),
            'context': str(pred_row.get('context', '')),
            'row': pred_row
        })

    # 匹配过程
    used_gt_indices = set()
    used_pred_indices = set()

    for idx, pred_item in enumerate(pred_indexed):
        if (idx + 1) % 50 == 0:
            print(
                f"  Matching progress: {idx + 1}/{len(pred_indexed)} predictions...", flush=True)
        best_match = None
        best_similarity = 0

        for gt_item in gt_indexed:
            if gt_item['index'] in used_gt_indices:
                continue

            # 计算mention相似度
            mention_sim = calculate_text_similarity(
                pred_item['mention'], gt_item['mention'])

            # 计算上下文相似度
            context_sim = calculate_context_similarity(
                pred_item['context'], gt_item['context'])

            # 综合相似度
            combined_sim = 0.7 * mention_sim + 0.3 * context_sim

            if combined_sim > best_similarity and combined_sim >= similarity_threshold:
                best_similarity = combined_sim
                best_match = gt_item

        if best_match:
            matched_pairs.append({
                'pred_row': pred_item['row'],
                'gt_row': best_match['row'],
                'similarity': best_similarity
            })
            used_gt_indices.add(best_match['index'])
            used_pred_indices.add(pred_item['index'])
        else:
            unmatched_pred.append(pred_item['row'])

    # 找出未匹配的ground truth
    for gt_item in gt_indexed:
        if gt_item['index'] not in used_gt_indices:
            unmatched_gt.append(gt_item['row'])

    return matched_pairs, unmatched_pred, unmatched_gt


def evaluate_entity_extraction_text_based(file_pairs: List[Dict], columns: List[str],
                                          similarity_threshold: float = 0.8, max_pairs: int = None) -> Tuple[Dict, Dict, Dict]:
    """
    基于文本匹配评估entity extraction
    """
    # 初始化结果结构
    results = {}
    note_results = {}

    # 按数据集分组
    dataset_results = {}

    if max_pairs is not None:
        file_pairs = file_pairs[:max_pairs]

    for pair_idx, pair_info in enumerate(file_pairs):
        pred_file = pair_info['converted_file']
        gt_file = pair_info['gt_file']
        note_id = pair_info['note_id']

        # 确定数据集
        dataset_label = '4CE'  # 默认数据集
        if 'coral' in gt_file.lower():
            if 'breastca' in gt_file.lower():
                dataset_label = 'coral_breastca'
            elif 'pdac' in gt_file.lower():
                dataset_label = 'coral_pdac'

        if dataset_label not in dataset_results:
            dataset_results[dataset_label] = {
                col: {'tp': 0, 'fp': 0, 'fn': 0, 'error_cases': []}
                for col in columns
            }

        if dataset_label not in note_results:
            note_results[dataset_label] = {}

        print(
            f"\n[{pair_idx+1}/{len(file_pairs)}] Processing: {note_id} (Dataset: {dataset_label})", flush=True)
        print(f"Prediction: {pred_file}", flush=True)
        print(f"Groundtruth: {gt_file}", flush=True)

        try:
            # 加载文件
            pred_df = pd.read_csv(pred_file)
            gt_df = pd.read_csv(gt_file)
            print(
                f"  Loaded rows - pred: {len(pred_df)}, gt: {len(gt_df)}", flush=True)

            # 过滤空值
            pred_df = pred_df.dropna(subset=['mention'])
            gt_df = gt_df.dropna(subset=['mention'])

            # 文本匹配
            matched_pairs, unmatched_pred, unmatched_gt = match_entities_by_text(
                pred_df, gt_df, similarity_threshold
            )

            print(f"  Matched pairs: {len(matched_pairs)}", flush=True)
            print(
                f"  Unmatched predictions: {len(unmatched_pred)}", flush=True)
            print(f"  Unmatched ground truth: {len(unmatched_gt)}", flush=True)

            # 初始化note级别的计数器
            note_key = (dataset_label, note_id)
            if note_key not in note_results[dataset_label]:
                note_results[dataset_label][note_key] = {
                    'tp': 0, 'fp': 0, 'fn': 0}

            # 增加 entity_extraction 统计（以是否匹配为准）
            if 'entity_extraction' not in dataset_results[dataset_label]:
                dataset_results[dataset_label]['entity_extraction'] = {
                    'tp': 0, 'fp': 0, 'fn': 0, 'error_cases': []}
            dataset_results[dataset_label]['entity_extraction']['tp'] += len(
                matched_pairs)
            dataset_results[dataset_label]['entity_extraction']['fp'] += len(
                unmatched_pred)
            dataset_results[dataset_label]['entity_extraction']['fn'] += len(
                unmatched_gt)

            # 评估每个列
            for col in columns:
                # 过滤列数据
                pred_col_df = pred_df.dropna(subset=[col])
                gt_col_df = gt_df.dropna(subset=[col])

                # 如果是value列，过滤非数字值
                if col == 'value':
                    pred_col_df = pred_col_df[pred_col_df[col].apply(
                        is_numeric)]
                    gt_col_df = gt_col_df[gt_col_df[col].apply(is_numeric)]

                # 评估匹配的实体
                for match in matched_pairs:
                    pred_row = match['pred_row']
                    gt_row = match['gt_row']

                    # 检查该列是否在两个数据框中都存在
                    pred_has_col = col in pred_row and pd.notna(
                        pred_row[col]) and str(pred_row[col]).strip()
                    gt_has_col = col in gt_row and pd.notna(
                        gt_row[col]) and str(gt_row[col]).strip()

                    if pred_has_col and gt_has_col:
                        pred_value = pred_row[col]
                        gt_value = gt_row[col]

                        # 特殊处理assertion status
                        if 'assertion' in col.lower() and 'status' in col.lower():
                            if str(pred_value).strip().lower() == 'historical':
                                pred_value = 'Present'

                            pred_value_lower = str(pred_value).strip().lower()
                            gt_value_lower = str(gt_value).strip().lower()

                            if pred_value_lower == gt_value_lower:
                                dataset_results[dataset_label][col]['tp'] += 1
                                note_results[dataset_label][note_key]['tp'] += 1
                            else:
                                dataset_results[dataset_label][col]['fp'] += 1
                                note_results[dataset_label][note_key]['fp'] += 1
                                dataset_results[dataset_label][col]['error_cases'].append({
                                    'dataset': dataset_label,
                                    'note_id': note_id,
                                    'predicted': pred_value,
                                    'ground_truth': gt_value,
                                    'similarity': match['similarity'],
                                    'context': str(pred_row.get('context', ''))
                                })

                        # 处理日期
                        elif 'date' in col.lower():
                            std_pred = standardize_date(pred_value)
                            std_gt = standardize_date(gt_value)

                            if std_pred is None or std_gt is None:
                                continue

                            pred_value = str(std_pred)
                            gt_value = str(std_gt)

                            if pred_value in gt_value or gt_value in pred_value or pred_value == gt_value:
                                dataset_results[dataset_label][col]['tp'] += 1
                                note_results[dataset_label][note_key]['tp'] += 1
                            else:
                                dataset_results[dataset_label][col]['fp'] += 1
                                note_results[dataset_label][note_key]['fp'] += 1
                                dataset_results[dataset_label][col]['error_cases'].append({
                                    'dataset': dataset_label,
                                    'note_id': note_id,
                                    'predicted': pred_value,
                                    'ground_truth': gt_value,
                                    'similarity': match['similarity'],
                                    'context': str(pred_row.get('context', ''))
                                })

                        # 处理数值
                        elif isinstance(pred_value, (float, int)) and isinstance(gt_value, (float, int)):
                            if abs(float(pred_value) - float(gt_value)) < 0.0001:
                                dataset_results[dataset_label][col]['tp'] += 1
                                note_results[dataset_label][note_key]['tp'] += 1
                            else:
                                dataset_results[dataset_label][col]['fp'] += 1
                                note_results[dataset_label][note_key]['fp'] += 1
                                dataset_results[dataset_label][col]['error_cases'].append({
                                    'dataset': dataset_label,
                                    'note_id': note_id,
                                    'predicted': pred_value,
                                    'ground_truth': gt_value,
                                    'similarity': match['similarity'],
                                    'context': str(pred_row.get('context', ''))
                                })

                        # 处理字符串
                        else:
                            pred_str = str(pred_value)
                            gt_str = str(gt_value)

                            if pred_str in gt_str or gt_str in pred_str or pred_str == gt_str:
                                dataset_results[dataset_label][col]['tp'] += 1
                                note_results[dataset_label][note_key]['tp'] += 1
                            else:
                                dataset_results[dataset_label][col]['fp'] += 1
                                note_results[dataset_label][note_key]['fp'] += 1
                                dataset_results[dataset_label][col]['error_cases'].append({
                                    'dataset': dataset_label,
                                    'note_id': note_id,
                                    'predicted': pred_value,
                                    'ground_truth': gt_value,
                                    'similarity': match['similarity'],
                                    'context': str(pred_row.get('context', ''))
                                })

                    elif pred_has_col and not gt_has_col:
                        # 预测有值，但ground truth没有
                        dataset_results[dataset_label][col]['fp'] += 1
                        note_results[dataset_label][note_key]['fp'] += 1

                # 处理未匹配的ground truth（假阴性）
                for gt_row in unmatched_gt:
                    if col in gt_row and pd.notna(gt_row[col]) and str(gt_row[col]).strip():
                        dataset_results[dataset_label][col]['fn'] += 1
                        note_results[dataset_label][note_key]['fn'] += 1
                        dataset_results[dataset_label][col]['error_cases'].append({
                            'dataset': dataset_label,
                            'note_id': note_id,
                            'predicted': 'Missing prediction',
                            'ground_truth': gt_row[col],
                            'context': str(gt_row.get('context', ''))
                        })

        except Exception as e:
            print(f"Error processing {note_id}: {e}")
            continue

    # 计算指标
    metrics = {}
    for dataset_label in dataset_results:
        metrics[dataset_label] = {}
        # 包括 entity_extraction
        calc_cols = ['entity_extraction'] + list(columns)
        for col in calc_cols:
            tp = dataset_results[dataset_label][col]['tp']
            fp = dataset_results[dataset_label][col]['fp']
            fn = dataset_results[dataset_label][col]['fn']

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision +
                                             recall) if (precision + recall) > 0 else 0
            accuracy = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0

            metrics[dataset_label][col] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'accuracy': accuracy,
                'true_positives': tp,
                'false_positives': fp,
                'false_negatives': fn
            }

    return metrics, dataset_results, note_results


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Evaluate Phi_4 predictions using text-based matching')
    parser.add_argument('--file_pairs', type=str, required=True,
                        help='JSON file containing file pairs information')
    parser.add_argument('--columns', type=str, nargs='+', required=True,
                        help='List of column names to evaluate')
    parser.add_argument('--output_file', type=str, default='phi4_evaluation_results.json',
                        help='Output file to save evaluation results')
    parser.add_argument('--similarity_threshold', type=float, default=0.8,
                        help='Text similarity threshold for matching')
    parser.add_argument('--max_pairs', type=int, default=None,
                        help='Limit number of file pairs for quick test')

    args = parser.parse_args()

    # 加载文件对信息
    with open(args.file_pairs, 'r') as f:
        file_pairs = json.load(f)

    print(f"Loaded {len(file_pairs)} file pairs")

    # 评估
    metrics, results, note_results = evaluate_entity_extraction_text_based(
        file_pairs, args.columns, args.similarity_threshold, args.max_pairs
    )

    # 打印结果
    print("\nEvaluation Results:")
    print("=" * 80)

    for dataset_label, dataset_metrics in metrics.items():
        print(f"\nDataset: {dataset_label}")
        print("-" * 40)
        for col, col_metrics in dataset_metrics.items():
            print(f"\nColumn: {col}")
            print(f"Precision: {col_metrics['precision']:.4f}")
            print(f"Recall: {col_metrics['recall']:.4f}")
            print(f"F1 Score: {col_metrics['f1']:.4f}")
            print(f"Accuracy: {col_metrics['accuracy']:.4f}")
            print(f"True Positives: {col_metrics['true_positives']}")
            print(f"False Positives: {col_metrics['false_positives']}")
            print(f"False Negatives: {col_metrics['false_negatives']}")

            error_count = len(results[dataset_label][col]['error_cases'])
            print(f"Number of error cases: {error_count}")

    # 保存结果
    output = {
        'metrics': metrics,
        'error_cases': {
            dataset_label: {
                col: results[dataset_label][col]['error_cases']
                for col in args.columns
            } for dataset_label in metrics.keys()
        }
    }

    with open(args.output_file, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {args.output_file}")

    # 保存错误案例到CSV
    error_cases_file = args.output_file.replace('.json', '_error_cases.csv')
    error_rows = []
    for dataset_label in metrics.keys():
        for col in args.columns:
            for error in results[dataset_label][col]['error_cases']:
                error['dataset'] = dataset_label
                error['column'] = col
                error_rows.append(error)

    if error_rows:
        error_df = pd.DataFrame(error_rows)
        error_df.to_csv(error_cases_file, index=False)
        print(f"Error cases saved to: {error_cases_file}")

    # 保存指标到CSV
    metrics_rows = []
    for dataset_label, dataset_metrics in metrics.items():
        for col, col_metrics in dataset_metrics.items():
            row = {
                'dataset': dataset_label,
                'column': col,
                'precision': col_metrics['precision'],
                'recall': col_metrics['recall'],
                'f1': col_metrics['f1'],
                'accuracy': col_metrics['accuracy'],
                'true_positives': col_metrics['true_positives'],
                'false_positives': col_metrics['false_positives'],
                'false_negatives': col_metrics['false_negatives'],
            }
            metrics_rows.append(row)

    if metrics_rows:
        metrics_df = pd.DataFrame(metrics_rows)
        metrics_csv_file = args.output_file.replace('.json', '_metrics.csv')
        metrics_df.to_csv(metrics_csv_file, index=False)
        print(f"Metrics overview saved to: {metrics_csv_file}")


if __name__ == '__main__':
    main()

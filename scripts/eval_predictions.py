import os
import pandas as pd
import json
from datetime import datetime
from typing import List, Tuple, Dict


def load_csv_files(prediction_dir, groundtruth_dir, model_name):
    """Load and pair original and groundtruth CSV files."""
    file_pairs = []

    # Get all subdirectories in groundtruth_dir
    groundtruth_datasets = [d for d in os.listdir(
        groundtruth_dir) if os.path.isdir(os.path.join(groundtruth_dir, d))]

    print(f"\nFound {len(groundtruth_datasets)} datasets in {groundtruth_dir}")

    for dataset in groundtruth_datasets:
        groundtruth_dataset_dir = os.path.join(groundtruth_dir, dataset)
        groundtruth_files = [f for f in os.listdir(
            groundtruth_dataset_dir) if f.endswith('_updated.csv')]

        print(f"\nProcessing dataset: {dataset}")
        print(f"Found {len(groundtruth_files)} groundtruth files")

        for groundtruth_file in groundtruth_files:
            # Extract the number from groundtruth file (e.g., "21" from "21_updated.csv")
            file_number = groundtruth_file.split('_updated')[0]

            # Construct original file name (e.g., "coral_annotated_breastca_21_default.csv")
            original_file = os.path.join(
                prediction_dir, f"{dataset}_{file_number}_default_{model_name}_with_positions.csv")

            if os.path.exists(original_file):
                file_pairs.append((
                    original_file,
                    os.path.join(groundtruth_dataset_dir, groundtruth_file)
                ))
                print(
                    f"✓ Matched: {groundtruth_file} -> {os.path.basename(original_file)}")
            else:
                print(f"✗ No matching original file for: {groundtruth_file}")

    return file_pairs


def standardize_date(date_str):
    """
    将各种格式的日期标准化为YYYY-MM-DD格式。
    如果只有年份，则返回年份；
    如果只有年月，则返回YYYY-MM格式。
    """
    if not isinstance(date_str, str):
        date_str = str(date_str)

    # 清理日期字符串
    date_str = date_str.strip()

    try:
        # 尝试不同的日期格式
        for fmt in [
            '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y',
            '%Y-%m', '%Y/%m', '%m/%Y', '%Y.%m.%d', '%d.%m.%Y',
            '%Y'
        ]:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                # 如果只有年份
                if fmt == '%Y':
                    return parsed_date.strftime('%Y')
                # 如果只有年月
                elif fmt in ['%Y-%m', '%m-%Y', '%Y/%m', '%m/%Y']:
                    return parsed_date.strftime('%Y-%m')
                # 完整日期
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue
        return date_str  # 如果无法解析，返回原始字符串
    except Exception:
        return date_str


def evaluate_entity_extraction(file_pairs: List[Tuple[str, str]], columns: List[str]) -> Dict[str, Dict]:
    """
    Evaluate entity extraction accuracy for specified columns, grouped by dataset.

    Args:
        file_pairs: List of tuples containing (prediction_file, groundtruth_file) paths
        columns: List of column names to evaluate

    Returns:
        Dictionary containing evaluation metrics for each dataset and column
    """
    # Group file pairs by dataset
    dataset_file_pairs = {}
    for pred_file, gt_file in file_pairs:
        # Extract dataset name from prediction file path
        dataset = os.path.basename(pred_file).split(
            '_')[0]  # Assuming first part is dataset name
        if dataset not in dataset_file_pairs:
            dataset_file_pairs[dataset] = []
        dataset_file_pairs[dataset].append((pred_file, gt_file))

    # Initialize results structure for each dataset
    results = {
        dataset: {
            col: {
                'tp': 0,
                'fp': 0,
                'fn': 0,
                'error_cases': []
            } for col in columns
        } for dataset in dataset_file_pairs
    }

    def is_numeric(value):
        """检查值是否可以转换为数字"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    # Process each dataset separately
    for dataset, dataset_pairs in dataset_file_pairs.items():
        print(f"\nProcessing dataset: {dataset}")

        for pred_file, gt_file in dataset_pairs:
            print(f"\nProcessing files:")
            print(f"Prediction: {pred_file}")
            print(f"Groundtruth: {gt_file}")

            # Load CSV files
            pred_df = pd.read_csv(pred_file)
            gt_df = pd.read_csv(gt_file)

            # Filter out rows where start_pos or end_pos is missing or -1
            pred_df = pred_df.dropna(subset=['start_pos', 'end_pos'])
            gt_df = gt_df.dropna(subset=['start_pos', 'end_pos'])
            pred_df = pred_df[(pred_df['start_pos'] != -1)
                              & (pred_df['end_pos'] != -1)]
            gt_df = gt_df[(gt_df['start_pos'] != -1)
                          & (gt_df['end_pos'] != -1)]

            for col in columns:
                # Filter out rows where the column is empty
                pred_col_df = pred_df.dropna(subset=[col])
                gt_col_df = gt_df.dropna(subset=[col])

                # 如果是value列，过滤掉非数字的值
                if col == 'value':
                    pred_col_df = pred_col_df[pred_col_df[col].apply(
                        is_numeric)]
                    gt_col_df = gt_col_df[gt_col_df[col].apply(is_numeric)]

                # Create position-based index for groundtruth entities
                gt_positions = {}
                for _, row in gt_col_df.iterrows():
                    pos_key = (row['start_pos'], row['end_pos'])
                    gt_positions[pos_key] = row

                # Check predictions against groundtruth
                for _, pred_row in pred_col_df.iterrows():
                    pos_key = (pred_row['start_pos'], pred_row['end_pos'])

                    # 查找与pos_key存在交集最大的gt_row
                    max_intersection = 0
                    best_gt_row = None
                    pred_start, pred_end = pos_key

                    for gt_key, gt_row in gt_positions.items():
                        gt_start, gt_end = gt_key
                        # 检查位置是否有交集: 两个区间有交集的条件是 start1 <= end2 AND start2 <= end1
                        if pred_start <= gt_end and gt_start <= pred_end:
                            # 计算交集大小
                            intersection_length = min(
                                pred_end, gt_end) - max(pred_start, gt_start)
                            if intersection_length > max_intersection:
                                max_intersection = intersection_length
                                best_gt_row = gt_row

                    if best_gt_row is not None:
                        gt_row = best_gt_row
                        pred_value = pred_row[col]
                        gt_value = gt_row[col]

                        # 记录错误信息的函数
                        def record_error():
                            error_info = {
                                'dataset': dataset,
                                'file': os.path.basename(pred_file),
                                'position': pos_key,
                                'gt_position': (gt_row['start_pos'], gt_row['end_pos']),
                                'intersection_length': max_intersection,
                                'predicted': pred_value,
                                'ground_truth': gt_value,
                                # 如果有原文上下文的话
                                'context': pred_row.get('text', '')
                            }
                            results[dataset][col]['error_cases'].append(
                                error_info)

                        # 在比较值之前添加日期标准化处理
                        if 'date' in col.lower():
                            pred_value = str(standardize_date(pred_value))
                            gt_value = str(standardize_date(gt_value))

                            if pred_value in gt_value or gt_value in pred_value or pred_value == gt_value:
                                results[dataset][col]['tp'] += 1
                            else:
                                results[dataset][col]['fp'] += 1
                                record_error()
                        # 如果两个值都是数值类型
                        elif isinstance(pred_value, (float, int)) and isinstance(gt_value, (float, int)):
                            if abs(float(pred_value) - float(gt_value)) < 0.0001:
                                results[dataset][col]['tp'] += 1
                            else:
                                results[dataset][col]['fp'] += 1
                                record_error()
                        # 如果是字符串类型
                        elif isinstance(pred_value, str) and isinstance(gt_value, str):
                            if pred_value in gt_value or gt_value in pred_value or pred_value == gt_value:
                                results[dataset][col]['tp'] += 1
                            else:
                                results[dataset][col]['fp'] += 1
                                record_error()
                        else:
                            str_pred = str(pred_value)
                            str_gt = str(gt_value)
                            if str_pred in str_gt or str_gt in str_pred or str_pred == str_gt:
                                results[dataset][col]['tp'] += 1
                            else:
                                results[dataset][col]['fp'] += 1
                                record_error()

                # 记录假阴性错误
                pred_positions = {(row['start_pos'], row['end_pos'])
                                  for _, row in pred_col_df.iterrows()}
                for _, gt_row in gt_col_df.iterrows():
                    gt_key = (gt_row['start_pos'], gt_row['end_pos'])

                    # 检查是否有任何预测位置与当前gt_key有交集
                    has_intersection = False
                    gt_start, gt_end = gt_key

                    for pred_key in pred_positions:
                        pred_start, pred_end = pred_key
                        if pred_start <= gt_end and gt_start <= pred_end:
                            has_intersection = True
                            break

                    if not has_intersection:
                        results[dataset][col]['fn'] += 1
                        results[dataset][col]['error_cases'].append({
                            'dataset': dataset,
                            'file': os.path.basename(gt_file),
                            'position': gt_key,
                            'predicted': 'Missing prediction',
                            'ground_truth': gt_row[col],
                            'context': gt_row.get('text', '')
                        })

    # Calculate metrics for each dataset and column
    metrics = {}
    for dataset in dataset_file_pairs:
        metrics[dataset] = {}
        for col in columns:
            tp = results[dataset][col]['tp']
            fp = results[dataset][col]['fp']
            fn = results[dataset][col]['fn']

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision +
                                             recall) if (precision + recall) > 0 else 0
            accuracy = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0

            metrics[dataset][col] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'accuracy': accuracy,
                'true_positives': tp,
                'false_positives': fp,
                'false_negatives': fn
            }

    return metrics, results


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Evaluate entity extraction accuracy')
    parser.add_argument('--prediction_dir', type=str, required=True,
                        help='Directory containing prediction CSV files')
    parser.add_argument('--groundtruth_dir', type=str, required=True,
                        help='Directory containing groundtruth CSV files')
    parser.add_argument('--columns', type=str, nargs='+', required=True,
                        help='List of column names to evaluate')
    parser.add_argument('--output_file', type=str, default='evaluation_results.json',
                        help='Output file to save evaluation results')
    parser.add_argument('--model_name', type=str, required=True,
                        help='Name of the model to evaluate')

    args = parser.parse_args()

    # Load file pairs
    file_pairs = load_csv_files(
        args.prediction_dir, args.groundtruth_dir, args.model_name)

    if not file_pairs:
        print("No matching file pairs found!")
        return

    # Evaluate entity extraction
    metrics, results = evaluate_entity_extraction(file_pairs, args.columns)

    # Print results for each dataset
    print("\nEvaluation Results:")
    print("=" * 80)
    for dataset, dataset_metrics in metrics.items():
        print(f"\nDataset: {dataset}")
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

            # Print error case count for this dataset and column
            error_count = len(results[dataset][col]['error_cases'])
            print(f"Number of error cases: {error_count}")

    # Save results to file
    output = {
        'metrics': metrics,
        'error_cases': {
            dataset: {
                col: results[dataset][col]['error_cases']
                for col in args.columns
            } for dataset in metrics.keys()
        }
    }

    with open(args.output_file, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {args.output_file}")

    # Save error cases to CSV
    error_cases_file = args.output_file.replace('.json', '_error_cases.csv')
    error_rows = []
    for dataset in metrics.keys():
        for col in args.columns:
            for error in results[dataset][col]['error_cases']:
                error['dataset'] = dataset
                error['column'] = col
                error_rows.append(error)

    if error_rows:
        error_df = pd.DataFrame(error_rows)
        error_df.to_csv(error_cases_file, index=False)
        print(f"Error cases saved to: {error_cases_file}")


if __name__ == '__main__':
    main()

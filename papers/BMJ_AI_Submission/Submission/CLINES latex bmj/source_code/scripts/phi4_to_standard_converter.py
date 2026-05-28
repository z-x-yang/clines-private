#!/usr/bin/env python3
"""
Phi_4输出格式转换脚本
将Phi_4的输出转换为与标准评估脚本兼容的格式
"""

import os
import re
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Set
from difflib import SequenceMatcher
import hashlib


def normalize_text(text: str) -> str:
    """标准化文本：小写、去除标点、统一空格"""
    if not isinstance(text, str):
        text = str(text)
    # 转换为小写
    text = text.lower().strip()
    # 去除多余空格和标点
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def calculate_text_similarity(text1: str, text2: str) -> float:
    """计算两个文本的相似度"""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    if norm1 == norm2:
        return 1.0
    return SequenceMatcher(None, norm1, norm2).ratio()


def extract_context_signature(context: str, max_length: int = 100) -> str:
    """提取上下文的签名，用于区分同名entity"""
    if not isinstance(context, str):
        return ""
    # 取上下文的前后部分
    context = context.strip()
    if len(context) <= max_length:
        return context
    # 取前半部分和后半部分
    half = max_length // 2
    return context[:half] + "..." + context[-half:]


def deduplicate_entities(df: pd.DataFrame, similarity_threshold: float = 0.85) -> pd.DataFrame:
    """去除重复的entity"""
    if df.empty:
        return df

    # 检查是否有phrase列
    if 'phrase' not in df.columns and 'mention' in df.columns:
        phrase_col = 'mention'
    elif 'phrase' in df.columns:
        phrase_col = 'phrase'
    else:
        print("Error: Neither 'phrase' nor 'mention' column found")
        return df

    # 按phrase分组
    phrase_groups = df.groupby(phrase_col)
    deduplicated_rows = []
    virtual_pos = 0

    for phrase, group in phrase_groups:
        if len(group) == 1:
            # 只有一个，直接添加
            row = group.iloc[0].copy()
            row['start_pos'] = virtual_pos
            row['end_pos'] = virtual_pos + len(str(phrase))
            virtual_pos += len(str(phrase)) + 10  # 添加间隔
            deduplicated_rows.append(row)
        else:
            # 多个同名entity，需要去重
            unique_entities = []

            for _, row in group.iterrows():
                is_duplicate = False

                # 检查是否与已有entity重复
                for existing in unique_entities:
                    # 比较上下文相似度
                    context_sim = calculate_text_similarity(
                        str(row.get('context', '')),
                        str(existing.get('context', ''))
                    )

                    # 比较其他属性
                    assertion_match = str(row.get('assertion_status', '')) == str(
                        existing.get('assertion_status', ''))
                    value_match = str(row.get('value', '')) == str(
                        existing.get('value', ''))
                    unit_match = str(row.get('unit', '')) == str(
                        existing.get('unit', ''))

                    # 如果上下文相似度高且其他属性匹配，认为是重复
                    if context_sim > similarity_threshold and assertion_match and value_match and unit_match:
                        is_duplicate = True
                        break

                if not is_duplicate:
                    unique_entities.append(row)

            # 为去重后的entity分配虚拟位置
            for entity in unique_entities:
                entity_copy = entity.copy()
                entity_copy['start_pos'] = virtual_pos
                entity_copy['end_pos'] = virtual_pos + len(str(phrase))
                virtual_pos += len(str(phrase)) + 10
                deduplicated_rows.append(entity_copy)

    return pd.DataFrame(deduplicated_rows)


def convert_phi4_file(input_file: str, output_file: str, note_id: str) -> bool:
    """转换单个Phi_4输出文件"""
    try:
        # 读取Phi_4输出
        df = pd.read_csv(input_file)

        if df.empty:
            print(f"Warning: {input_file} is empty")
            return False

        # 创建新的DataFrame
        converted_df = pd.DataFrame()

        # 映射现有列
        if 'phrase' in df.columns:
            converted_df['mention'] = df['phrase']
        else:
            print(f"Error: 'phrase' column not found in {input_file}")
            return False

        if 'assertion_status' in df.columns:
            converted_df['assertion_status'] = df['assertion_status']
        else:
            converted_df['assertion_status'] = ''

        if 'value' in df.columns:
            converted_df['value'] = df['value']
        else:
            converted_df['value'] = ''

        if 'unit' in df.columns:
            converted_df['unit'] = df['unit']
        else:
            converted_df['unit'] = ''

        if 'start_date' in df.columns:
            converted_df['begin_date'] = df['start_date']
        else:
            converted_df['begin_date'] = ''

        if 'end_date' in df.columns:
            converted_df['end_date'] = df['end_date']
        else:
            converted_df['end_date'] = ''

        # 添加key列
        converted_df['key'] = note_id

        # 添加context列（如果有的话）
        if 'context' in df.columns:
            converted_df['context'] = df['context']
        else:
            converted_df['context'] = converted_df['mention']

        # 去重处理
        converted_df = deduplicate_entities(converted_df)

        # 添加其他必要列
        converted_df['term_index'] = range(1, len(converted_df) + 1)
        converted_df['agent_type'] = 'phi4'

        # 确保所有必要的列都存在
        required_columns = ['term_index', 'key', 'mention', 'context', 'assertion_status',
                            'value', 'unit', 'begin_date', 'end_date', 'start_pos', 'end_pos', 'agent_type']

        for col in required_columns:
            if col not in converted_df.columns:
                converted_df[col] = ''

        # 重新排列列顺序
        converted_df = converted_df[required_columns]

        # 保存转换后的文件
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        converted_df.to_csv(output_file, index=False)

        print(
            f"Converted: {input_file} -> {output_file} ({len(converted_df)} entities)")
        return True

    except Exception as e:
        print(f"Error converting {input_file}: {e}")
        return False


def find_matching_ground_truth_files(phi4_file: str, gt_dir: str) -> List[str]:
    """找到与Phi_4文件匹配的ground truth文件"""
    phi4_filename = os.path.basename(phi4_file)
    phi4_name = os.path.splitext(phi4_filename)[0]

    matching_files = []

    # 搜索所有ground truth目录
    for root, dirs, files in os.walk(gt_dir):
        for file in files:
            if file.endswith('_updated.csv'):
                # 提取note ID
                note_id = file.replace('_updated.csv', '')

                # 检查是否匹配
                if (phi4_name == note_id or
                    phi4_name in note_id or
                        note_id in phi4_name):
                    matching_files.append(os.path.join(root, file))

    return matching_files


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert Phi_4 output to standard format')
    parser.add_argument('--phi4_dir', type=str, required=True,
                        help='Directory containing Phi_4 output files')
    parser.add_argument('--gt_dir', type=str, required=True,
                        help='Directory containing ground truth files')
    parser.add_argument('--output_dir', type=str, required=True,
                        help='Output directory for converted files')
    parser.add_argument('--similarity_threshold', type=float, default=0.85,
                        help='Similarity threshold for deduplication')

    args = parser.parse_args()

    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)

    # 获取所有Phi_4输出文件
    phi4_files = []
    for root, dirs, files in os.walk(args.phi4_dir):
        for file in files:
            if file.endswith('.csv'):
                phi4_files.append(os.path.join(root, file))

    print(f"Found {len(phi4_files)} Phi_4 output files")

    # 转换文件
    converted_count = 0
    matched_pairs = []

    for phi4_file in phi4_files:
        note_id = os.path.splitext(os.path.basename(phi4_file))[0]

        # 查找匹配的ground truth文件
        matching_gt_files = find_matching_ground_truth_files(
            phi4_file, args.gt_dir)

        if not matching_gt_files:
            print(f"Warning: No ground truth file found for {phi4_file}")
            continue

        # 使用第一个匹配的ground truth文件
        gt_file = matching_gt_files[0]

        # 转换Phi_4文件
        output_file = os.path.join(args.output_dir, f"{note_id}_converted.csv")

        if convert_phi4_file(phi4_file, output_file, note_id):
            converted_count += 1
            matched_pairs.append({
                'phi4_file': phi4_file,
                'gt_file': gt_file,
                'converted_file': output_file,
                'note_id': note_id
            })

    # 保存匹配信息
    pairs_file = os.path.join(args.output_dir, 'file_pairs.json')
    with open(pairs_file, 'w') as f:
        json.dump(matched_pairs, f, indent=2)

    print(f"\nConversion completed:")
    print(f"- Converted {converted_count} files")
    print(f"- File pairs saved to: {pairs_file}")
    print(f"- Converted files in: {args.output_dir}")


if __name__ == '__main__':
    main()

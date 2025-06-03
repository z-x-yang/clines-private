#!/usr/bin/env python3
"""
脚本：将文件夹下的default格式的csv结果转换成i2b2格式

用法：
python convert_default_to_i2b2.py --input_dir <输入文件夹路径> --output_dir <输出文件夹路径>

示例：
python convert_default_to_i2b2.py --input_dir outputs/gpt4o_output_0526_test2 --output_dir outputs/gpt4o_output_0526_test2_i2b2
"""

import os
import sys
import argparse
import pandas as pd
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
import traceback

# Import schema processor from core module
from core.schema import SchemaProcessor, SchemaName, OutputType


def setup_logging():
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('convert_default_to_i2b2.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def read_default_csv(csv_file_path):
    """
    读取default格式的CSV文件并转换为适合i2b2转换的格式

    Args:
        csv_file_path: CSV文件路径

    Returns:
        转换后的数据列表，适合i2b2_transform处理
    """
    logger = logging.getLogger(__name__)

    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file_path)
        logger.info(f"成功读取CSV文件：{csv_file_path}，共{len(df)}行数据")

        # 将DataFrame转换为字典列表
        converted_data = []

        for _, row in df.iterrows():
            # 创建基础记录
            record = {}

            # 映射基础字段
            record['patient_num'] = None  # 可以从key中提取或设置为默认值
            record['birth_date'] = row.get('birth_date', None)
            record['death_date'] = row.get('death_date', None)
            record['gender'] = row.get('gender', None)
            record['race'] = row.get('race', None)
            record['ethnicity'] = row.get('ethnicity', None)
            record['zip_code'] = row.get('zip_code', None)

            # 时间字段
            record['begin_date'] = row.get('begin_date', None)
            record['end_date'] = row.get('end_date', None)

            # 如果begin_date和end_date为空，尝试使用admission_date和discharge_date
            if pd.isna(record['begin_date']) and not pd.isna(row.get('admission_date')):
                record['begin_date'] = row.get('admission_date')
            if pd.isna(record['end_date']) and not pd.isna(row.get('discharge_date')):
                record['end_date'] = row.get('discharge_date')

            # 概念相关字段
            record['code'] = row.get('code', None)
            record['mention'] = row.get('mention', None)
            record['context'] = row.get('context', None)

            # 值相关字段
            record['value'] = row.get('value', None)
            record['unit'] = row.get('unit', None)
            record['freq'] = row.get('freq', None)
            record['route'] = row.get('route', None)
            record['note'] = row.get('note', None)
            # 处理infer字段的NaN值，确保是布尔值
            infer_value = row.get('infer')
            if infer_value is None or pd.isna(infer_value):
                record['infer'] = False
            elif isinstance(infer_value, str):
                record['infer'] = infer_value.lower(
                ) in ['true', '1', 'yes', 't', 'y']
            else:
                record['infer'] = bool(infer_value)

            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None

            converted_data.append(record)

        logger.info(f"成功转换{len(converted_data)}条记录")
        return converted_data

    except Exception as e:
        logger.error(f"读取CSV文件失败：{csv_file_path}，错误：{e}")
        return []


def convert_file(input_file_path, output_dir, logger):
    """
    转换单个文件从default格式到i2b2格式

    Args:
        input_file_path: 输入文件路径
        output_dir: 输出目录
        logger: 日志记录器
    """
    try:
        # 读取default格式的数据
        data = read_default_csv(input_file_path)

        if not data:
            logger.warning(f"文件{input_file_path}没有有效数据，跳过转换")
            return

        # 创建i2b2 SchemaProcessor
        schema_processor = SchemaProcessor(
            schema_name_str="i2b2",
            output_type_str="csv",
            output_dir=output_dir
        )

        # 提取文件名作为key_identifier
        file_name = Path(input_file_path).stem  # 去掉扩展名
        # 移除'_default'后缀（如果存在）
        if file_name.endswith('_default'):
            key_identifier = file_name[:-8]  # 移除'_default'
        else:
            key_identifier = file_name

        # 执行转换
        schema_processor(data, key_identifier)

        logger.info(
            f"成功转换文件：{input_file_path} -> {output_dir}/{key_identifier}_i2b2.csv")

    except Exception as e:
        logger.error(f"转换文件失败：{input_file_path}，错误：{e}")


def convert_directory(input_dir, output_dir):
    """
    转换整个目录下的default格式CSV文件为i2b2格式

    Args:
        input_dir: 输入目录路径
        output_dir: 输出目录路径
    """
    logger = setup_logging()

    # 检查输入目录是否存在
    if not os.path.exists(input_dir):
        logger.error(f"输入目录不存在：{input_dir}")
        return

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"输出目录已创建：{output_dir}")

    # 查找所有包含'default'的CSV文件
    input_path = Path(input_dir)
    csv_files = []

    # 查找所有CSV文件
    for file_path in input_path.glob("*.csv"):
        if 'default' in file_path.name.lower():
            csv_files.append(file_path)

    if not csv_files:
        logger.warning(f"在目录{input_dir}中没有找到包含'default'的CSV文件")
        return

    logger.info(f"找到{len(csv_files)}个default格式的CSV文件")

    # 转换每个文件
    success_count = 0
    for csv_file in csv_files:
        logger.info(f"正在转换文件：{csv_file}")
        try:
            convert_file(str(csv_file), output_dir, logger)
            success_count += 1
        except Exception as e:
            logger.error(f"转换文件失败：{csv_file}，错误：{e}")

    logger.info(f"转换完成！成功转换{success_count}/{len(csv_files)}个文件")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="将default格式的CSV文件转换为i2b2格式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  python convert_default_to_i2b2.py --input_dir outputs/gpt4o_output_0526_test2 --output_dir outputs/gpt4o_output_0526_test2_i2b2
  python convert_default_to_i2b2.py -i outputs/gpt4o_output_0526_test2 -o outputs/gpt4o_output_0526_test2_i2b2
        """
    )

    parser.add_argument(
        '--input_dir', '-i',
        required=True,
        help='包含default格式CSV文件的输入目录路径'
    )

    parser.add_argument(
        '--output_dir', '-o',
        required=True,
        help='输出i2b2格式CSV文件的目录路径'
    )

    args = parser.parse_args()

    # 执行转换
    convert_directory(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()

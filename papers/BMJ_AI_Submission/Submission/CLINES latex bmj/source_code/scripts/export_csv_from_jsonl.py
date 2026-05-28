import json
import csv
import os
import argparse


def process_jsonl_to_csv(input_file, output_dir='output_csvs'):
    # 创建输出目录(如果不存在)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 读取jsonl文件
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_number, line in enumerate(f, 1):
            try:
                # 解析每一行的json
                line = line.strip()
                if not line:  # 跳过空行
                    continue

                data = json.loads(line)

                # 检查是否有必要的字段
                if 'key' not in data or 'output_genie' not in data:
                    print(
                        f"Line {line_number}: Missing required fields (key or output_genie)")
                    continue

                try:
                    # 尝试清理output_genie字段
                    output_genie = data['output_genie']
                    if isinstance(output_genie, str):
                        # 如果已经是字符串，尝试解析
                        try:
                            genie_data = json.loads(output_genie)
                        except json.JSONDecodeError:

                            genie_data = json.loads(output_genie)

                            print(
                                f"Line {line_number}: Error parsing output_genie field: {e}")
                            print(
                                f"output_genie content (first 100 chars): {str(data['output_genie'])[:100]}...")
                            # 保存问题数据到文件以便调试
                            with open(f'problematic_genie_line_{line_number}.txt', 'w', encoding='utf-8') as error_file:
                                error_file.write(
                                    f"Original output_genie:\n{data['output_genie']}\n")
                                error_file.write(f"\nError message: {str(e)}")
                                error_file.write(f"\nError position: {e.pos}")
                                if isinstance(output_genie, str):
                                    error_file.write(
                                        f"\nContext around error (20 chars):\n{output_genie[max(0, e.pos-10):e.pos+10]}")
                            continue
                    else:
                        # 如果不是字符串（可能已经是对象），直接使用
                        genie_data = output_genie

                except json.JSONDecodeError as e:
                    print(
                        f"\nLine {line_number}: Error parsing output_genie field: {e}")
                    print(
                        f"output_genie content (first 100 chars): {str(data['output_genie'])[:100]}...")

                    # 显示错误位置的上下文
                    if isinstance(output_genie, str):
                        error_pos = e.pos
                        start = max(0, error_pos - 50)
                        end = min(len(output_genie), error_pos + 50)
                        context = output_genie[start:end]
                        pointer = " " * (min(50, error_pos - start)) + "^"

                        print("\nError context:")
                        print(context)
                        print(pointer)
                        print(f"Error at position {error_pos}: {e.msg}")

                    # 保存问题数据到文件以便调试
                    with open(f'problematic_genie_line_{line_number}.txt', 'w', encoding='utf-8') as error_file:
                        error_file.write(
                            f"Original output_genie:\n{data['output_genie']}\n")
                        error_file.write(f"\nError message: {str(e)}")
                        error_file.write(f"\nError position: {e.pos}")
                        if isinstance(output_genie, str):
                            error_file.write(
                                f"\nContext around error:\n{context}\n")
                            error_file.write(f"{pointer}\n")
                    continue

                if not genie_data:  # 如果是空数组则跳过
                    print(f"Line {line_number}: Empty output_genie data")
                    continue

                # 从key中提取前缀
                key = data['key']
                # 将key按下划线分割，去掉最后一个数字作为前缀
                parts = key.rsplit('_', 1)  # 从右边分割一次
                prefix = parts[0]  # 获取除最后一个部分的所有内容

                # 修改CSV文件名，使用前缀
                csv_filename = os.path.join(output_dir, f"{prefix}.csv")

                # 获取所有可能的列名(字段名)
                fieldnames = set()
                for item in genie_data:
                    fieldnames.update(item.keys())
                fieldnames = sorted(list(fieldnames))

                # 检查文件是否存在，决定是否需要写入表头
                file_exists = os.path.exists(csv_filename)

                # 写入或追加到CSV文件
                mode = 'a' if file_exists else 'w'
                with open(csv_filename, mode, newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    if not file_exists:  # 只在新文件时写入表头
                        writer.writeheader()
                    writer.writerows(genie_data)

                print(f"Added data to CSV file: {csv_filename}")

            except json.JSONDecodeError as e:
                print(f"Error parsing JSON at line {line_number}: {e}")
                print(
                    f"Problematic line content (first 100 chars): {line[:100]}...")
                print(f"Full line length: {len(line)} characters")
                # 可选：保存问题行到单独的文件
                with open('problematic_lines.txt', 'a', encoding='utf-8') as error_file:
                    error_file.write(f"Line {line_number}:\n{line}\n\n")
            except Exception as e:
                print(f"Error processing line {line_number}: {e}")
                print(f"Full error details:", str(e))


# 使用示例
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert JSONL to CSV files')
    parser.add_argument('--input-file', '-i',
                        default='/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/results/coral_breastcancer_genie_result.jsonl',
                        help='Input JSONL file path')
    parser.add_argument('--output-dir', '-o',
                        default='../outputs/genie_coral_breastcancer_output',
                        help='Output directory for CSV files (default: output_csvs)')

    args = parser.parse_args()
    process_jsonl_to_csv(args.input_file, args.output_dir)

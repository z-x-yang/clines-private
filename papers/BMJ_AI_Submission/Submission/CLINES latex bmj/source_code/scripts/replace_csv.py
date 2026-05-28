import os
import glob
import shutil


def replace_csv_files():
    # 获取所有需要被替换的文件路径
    source_pattern = 'outputs/split/part*/*/*.csv'
    source_files = glob.glob(source_pattern)

    # 遍历每个找到的文件
    for source_file in source_files:
        # 获取文件名（xxx.csv）
        filename = os.path.basename(source_file)

        # 构建替换文件的路径
        replacement_file = os.path.join('outputs', 'final2', filename)

        # 检查替换文件是否存在
        if os.path.exists(replacement_file):
            try:
                # 执行文件替换
                shutil.copy2(replacement_file, source_file)
                print(f"成功替换文件: {source_file}")
            except Exception as e:
                print(f"替换文件时出错 {source_file}: {str(e)}")
        else:
            print(f"替换文件不存在: {replacement_file}")


if __name__ == "__main__":
    replace_csv_files()

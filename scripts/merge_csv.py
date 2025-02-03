import pandas as pd
import sys


def merge_and_sort_csv(file1, file2, output_file):
    # 读取CSV文件
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    # 合并两个DataFrame
    merged_df = pd.concat([df1, df2], ignore_index=True)

    # 删除'related'列（如果存在）
    if 'related' in merged_df.columns:
        merged_df = merged_df.drop(columns=['related'])

    # 排序：先按start_pos升序，start_pos相同则按end_pos升序，start_pos==-1的最后
    merged_df = merged_df.sort_values(
        by=['start_pos', 'end_pos'],
        ascending=[True, True]
    )
    # 将start_pos == -1 的行移动到最后
    not_negative = merged_df['start_pos'] != -1
    negative = merged_df['start_pos'] == -1
    merged_df = pd.concat(
        [merged_df[not_negative], merged_df[negative]], ignore_index=True)

    # 重新分配term_index
    merged_df = merged_df.reset_index(drop=True)
    term_index = 0
    previous = None
    term_indices = []

    for _, row in merged_df.iterrows():
        current = (row['start_pos'], row['end_pos'])
        if current != previous:
            term_index += 1
        term_indices.append(term_index)
        previous = current

    merged_df['term_index'] = term_indices

    # 保存合并后的CSV
    merged_df.to_csv(output_file, index=False)
    print(f"合并后的文件已保存到 {output_file}")


def main():

    # files = ["/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/4CE_BCH_1_deepseek_with_positions.csv",
    #          "/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/4CE_BCH_1_genie_with_positions.csv",
    #          "/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/4CE_BCH_1_gpt4o_with_positions.csv",
    #          "/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/4CE_BCH_1_llama_with_positions.csv"]
    files = ["/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/coral_breastcancer_gpt4o_with_positions.csv",
             "/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/coral_breastcancer_llama_with_positions.csv",
             "/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/coral_breastcancer_deepseek_with_positions.csv",
             "/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/outputs/annotations/coral_annotated_breastca_21.csv"]
    output_file = "../outputs/coral_breastcancer_all_with_positions.csv"
    # Start with first file
    merged_df = files[0]

    # Merge remaining files one by one
    for file in files[1:]:
        print(f"Merging {file} with {merged_df}")
        merge_and_sort_csv(merged_df, file, output_file)
        merged_df = output_file


if __name__ == "__main__":
    print("Starting merge")
    main()

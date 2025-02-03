import pandas as pd
import os
import html
from bs4 import BeautifulSoup
import argparse


def remove_overlapping_terms(terms):
    """
    移除重叠的术语，保留最长的术语。
    假设terms按start_pos降序排序。
    """
    non_overlapping = []
    last_end = float('inf')
    for term in terms:
        start, end, mention, term_idx = term
        if end <= last_end:
            non_overlapping.append(term)
            last_end = start
    return non_overlapping


def verify_terms(text, terms):
    """
    验证每个术语的start_pos和end_pos是否与文本匹配。
    """
    mismatches = []
    for idx, (start, end, term) in enumerate(terms, start=1):
        extracted = text[start:end]
        if extracted != term:
            mismatches.append((idx, term, extracted))
    return mismatches


def highlight_terms_with_numbers(merged_csv_path, ehr_txt_path, output_html_path):
    """
    读取合并后的CSV和原始EHR文本，突出显示术语，并为每个术语添加序号和所有来源，
    最终输出一个HTML文件。
    """
    # 为不同的agent_type定义颜色
    COLOR_MAP = {
        'gpt4o': '#ffcccb',      # 浅红色
        'llama': '#bce3bc',     # 浅绿色
        'genie': '#add8e6',      # 浅蓝色
        'deepseek': '#ffe4b5',       # 浅橙色
        'annotation': '#ffd700',    # 浅金色
    }

    # 读取合并后的CSV文件
    df = pd.read_csv(merged_csv_path)

    # 读取原始EHR文本
    with open(ehr_txt_path, 'r', encoding='utf-8') as file:
        text = file.read()

    # 收集所有出现的agent_type
    all_agents = sorted(df['agent_type'].unique())

    # 为每个term_index收集所有的agent_type
    term_sources = {}
    for _, row in df[df['start_pos'] != -1].iterrows():
        if row['term_index'] not in term_sources:
            term_sources[row['term_index']] = set()
        term_sources[row['term_index']].add(row['agent_type'])

    # 将术语按start_pos降序排序，并对于相同start_pos保留end_pos最大的记录
    df_sorted = df[df['start_pos'] != -1].sort_values(
        by=['start_pos', 'end_pos'],
        ascending=[False, False]).drop_duplicates(
        subset=['start_pos'], keep='first').reset_index(drop=True)

    # 提取术语、位置和term_index
    terms_with_numbers = list(zip(df_sorted['start_pos'], df_sorted['end_pos'],
                                  df_sorted['mention'], df_sorted['term_index']))

    # 按start_pos降序排序
    terms_with_numbers_sorted = sorted(
        terms_with_numbers, key=lambda x: x[0], reverse=True)

    # 移除重叠的术语
    non_overlapping_terms = remove_overlapping_terms(terms_with_numbers_sorted)

    # 插入高亮标签
    for start, end, term, term_idx in non_overlapping_terms:
        sources = sorted(term_sources[term_idx])
        sources_text = ', '.join(sources)

        # 创建渐变背景
        if len(sources) > 1:
            gradient_colors = [COLOR_MAP[source] for source in sources]
            background_style = f"background: linear-gradient(45deg, {', '.join(gradient_colors)})"
        else:
            background_style = f"background-color: {COLOR_MAP[sources[0]]}"

        # 调试输出
        print(
            f"插入术语 {term_idx}: '{term}' (来源: {sources_text}) 在位置 [{start}, {end}]")

        # 构建高亮的<span>标签
        highlighted = (
            f'<span style="{background_style}; position: relative;">'
            f'{html.escape(term)}'
            f'<sup style="color: red;">{term_idx}</sup>'
            f'<sub style="color: blue; font-size: 0.7em;">[{sources_text}]</sub>'
            f'</span>'
        )
        # 替换文本中的术语
        text = text[:start] + highlighted + text[end:]

    # 创建图例HTML
    legend_html = '<div class="legend">\n'
    legend_html += '<h3>Source Models:</h3>\n'
    for agent in all_agents:
        legend_html += (
            f'<div class="legend-item">'
            f'<span class="color-box" style="background-color: {COLOR_MAP[agent]}"></span>'
            f'{agent}'
            f'</div>\n'
        )
    legend_html += '</div>\n'

    # 构建完整的HTML内容
    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Highlighted EHR Note with Term Numbers and Sources</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 20px;
            }}
            sup {{
                font-size: 0.8em;
                vertical-align: super;
                color: red;
            }}
            sub {{
                font-size: 0.7em;
                vertical-align: sub;
                color: blue;
                margin-left: 2px;
            }}
            pre {{
                white-space: pre-wrap;
                margin-top: 20px;
            }}
            .legend {{
                margin-bottom: 20px;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
            }}
            .legend h3 {{
                margin-top: 0;
            }}
            .legend-item {{
                display: inline-block;
                margin-right: 20px;
            }}
            .color-box {{
                display: inline-block;
                width: 20px;
                height: 20px;
                margin-right: 5px;
                vertical-align: middle;
                border: 1px solid #666;
            }}
        </style>
    </head>
    <body>
        {legend_html}
        <pre>{text}</pre>
    </body>
    </html>
    """

    # 将处理后的文本写入HTML文件
    with open(output_html_path, 'w', encoding='utf-8') as file:
        file.write(html_content)

    print(f"高亮并标注序号后的文件已保存到 {output_html_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Highlight terms in EHR text with numbers and sources')
    parser.add_argument('--merged_csv',
                        default="../outputs/coral_breastcancer_all_with_positions.csv",
                        help='Path to the merged CSV file containing terms and positions')
    parser.add_argument('--ehr_txt',
                        default="/home/zoy043/Works/LLM_Info_Extract/language-into-clinical-data/data/coral_annotated_breastca/21.txt",
                        help='Path to the EHR text file')
    parser.add_argument('--output_html',
                        default="../outputs/coral_breastcancer_highlighted_with_numbers.html",
                        help='Path to save the output HTML file')

    args = parser.parse_args()

    # 确保输入文件存在
    if not os.path.exists(args.merged_csv):
        print(f"合并的CSV文件不存在: {args.merged_csv}")
        return
    if not os.path.exists(args.ehr_txt):
        print(f"EHR文本文件不存在: {args.ehr_txt}")
        return

    highlight_terms_with_numbers(
        args.merged_csv, args.ehr_txt, args.output_html)


if __name__ == "__main__":
    print("开始高亮并标注序号处理")
    main()
